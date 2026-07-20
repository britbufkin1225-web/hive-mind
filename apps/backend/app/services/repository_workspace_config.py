"""Phase 39B - deterministic repository workspace configuration service.

This module owns local configuration I/O for the persistent repository workspace
registry: path resolution, bounded loading, atomic saving, workspace operations,
availability diagnostics, and the narrow integration seam a future Repository
Observer phase will use to resolve the active repository.

Trust boundaries (enforced by construction, not merely by convention):

* local-only: no network access; remote checks read Git's own configured
  remotes via the existing read-only adapter and never contact a server.
* read-only toward repositories: repositories are probed with the deterministic
  read-only Git adapter; Git history and repository content are never mutated.
* credential-safe: credential-bearing remotes are rejected before persistence.
* corruption-resistant: writes are atomic (temp sibling + ``os.replace``); a
  failed or malformed load never overwrites an existing file.
* bounded: file size, workspace count, and field lengths are all capped.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from app.models.repository_workspace import (
    MAX_WORKSPACE_CONFIG_BYTES,
    REPOSITORY_WORKSPACE_SCHEMA_VERSION,
    RepositoryWorkspace,
    RepositoryWorkspaceConfig,
    empty_config,
)
from app.services.repository_git_adapter import (
    DEFAULT_GIT_ADAPTER_LIMITS,
    GitAdapterLimits,
    GitCommandExecutor,
    GitCommandFailedError,
    GitCommandTimeoutError,
    GitExecutableUnavailableError,
    GitReadOperation,
    RepositoryGitAdapterError,
    parse_remote_verbose,
)
from app.services.workspace_paths import (
    normalize_remote,
    remote_has_credentials,
)

# Environment override for the configuration location (highest precedence).
WORKSPACE_CONFIG_ENV = "HIVEMIND_WORKSPACE_CONFIG_PATH"

# The on-disk filename and per-OS parent directory names. On Windows the file
# lives under the user's local application-data directory, never inside the
# repository; elsewhere it follows the XDG base-directory convention.
WORKSPACE_CONFIG_FILENAME = "repository-workspaces.json"
WORKSPACE_CONFIG_DIR_WINDOWS = "HiveMind"
WORKSPACE_CONFIG_DIR_XDG = "hive-mind"

# Sentinel distinguishing "argument not supplied" from "explicitly set to None"
# in update operations, so an operator can clear an expected remote deliberately.
_UNSET = object()


# --------------------------------------------------------------------------- #
# Typed failure states
# --------------------------------------------------------------------------- #
class WorkspaceConfigError(Exception):
    """Base class for bounded, typed workspace configuration failures."""


class WorkspaceConfigPathError(WorkspaceConfigError):
    """The configuration path could not be resolved (e.g., invalid override)."""


class WorkspaceConfigNotFoundError(WorkspaceConfigError):
    """No configuration file exists at the resolved path."""


class WorkspaceConfigMalformedError(WorkspaceConfigError):
    """The configuration file exists but is not a valid contract document."""


class UnsupportedWorkspaceSchemaVersionError(WorkspaceConfigError):
    """The configuration declares a schema version this build cannot read."""


class WorkspaceConfigInaccessibleError(WorkspaceConfigError):
    """The configuration file exists but could not be read."""


class WorkspaceConfigTooLargeError(WorkspaceConfigError):
    """The configuration file exceeds the maximum permitted size."""


class WorkspaceConfigExistsError(WorkspaceConfigError):
    """Initialization was requested but a configuration already exists."""


class WorkspaceConfigSaveError(WorkspaceConfigError):
    """The configuration could not be persisted atomically."""


class WorkspaceOperationError(WorkspaceConfigError):
    """Base class for invalid workspace mutation requests."""


class DuplicateWorkspaceError(WorkspaceOperationError):
    """A workspace with the requested identifier already exists."""


class DuplicateRepositoryRootError(WorkspaceOperationError):
    """A workspace already registers the same normalized repository root."""


class WorkspaceNotFoundError(WorkspaceOperationError):
    """The requested workspace identifier does not exist."""


class CredentialBearingRemoteError(WorkspaceOperationError):
    """The supplied expected remote embeds credentials and was rejected."""


class WorkspaceFieldError(WorkspaceOperationError):
    """A supplied workspace field failed contract validation."""


# --------------------------------------------------------------------------- #
# Diagnostics and result shapes
# --------------------------------------------------------------------------- #
class WorkspaceDiagnosticCode(StrEnum):
    NO_ACTIVE_WORKSPACE = "no_active_workspace"
    ACTIVE_WORKSPACE_DISABLED = "active_workspace_disabled"
    REPOSITORY_ROOT_ABSENT = "repository_root_absent"
    REPOSITORY_ROOT_INACCESSIBLE = "repository_root_inaccessible"
    PATH_NOT_GIT_REPOSITORY = "path_not_git_repository"
    EXPECTED_REMOTE_ABSENT = "expected_remote_absent"
    EXPECTED_REMOTE_MISMATCH = "expected_remote_mismatch"
    GIT_UNAVAILABLE = "git_unavailable"
    REPOSITORY_AVAILABLE = "repository_available"


class WorkspaceDiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class WorkspaceDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: WorkspaceDiagnosticCode
    severity: WorkspaceDiagnosticSeverity
    message: str
    workspace_id: str | None = None


class WorkspaceAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    repository_root: str
    enabled: bool
    exists: bool
    is_git_repository: bool | None
    expected_remote: str | None = None
    actual_remote: str | None = None
    diagnostics: list[WorkspaceDiagnostic] = []


class ActiveWorkspaceResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_workspace_id: str | None
    workspace: RepositoryWorkspace | None
    repository_root: str | None
    resolved: bool
    diagnostics: list[WorkspaceDiagnostic] = []


class WorkspaceValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_path: str
    schema_version: str
    active_workspace_id: str | None
    workspace_count: int
    workspaces: list[WorkspaceAvailability] = []
    active_resolution: ActiveWorkspaceResolution


# --------------------------------------------------------------------------- #
# Path resolution
# --------------------------------------------------------------------------- #
def _resolve_home(environ: dict[str, str]) -> Path:
    for key in ("USERPROFILE", "HOME"):
        value = environ.get(key)
        if value and value.strip():
            return Path(value)
    return Path(os.path.expanduser("~"))


def resolve_workspace_config_path(
    environ: dict[str, str] | None = None,
    *,
    system: str | None = None,
) -> Path:
    """Resolve the configuration path without creating or writing anything.

    Resolution order: (1) the ``HIVEMIND_WORKSPACE_CONFIG_PATH`` override, (2) the
    OS-appropriate user configuration directory, (3) a safe user-home fallback.
    ``environ`` and ``system`` are injectable so tests never touch the developer's
    real profile and can exercise every branch deterministically.
    """

    env = os.environ if environ is None else environ
    system_name = os.name if system is None else system

    override = env.get(WORKSPACE_CONFIG_ENV)
    if override is not None:
        if not override.strip() or "\x00" in override:
            raise WorkspaceConfigPathError(
                f"{WORKSPACE_CONFIG_ENV} is set but empty or invalid"
            )
        return Path(override)

    if system_name == "nt":
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data and local_app_data.strip():
            base = Path(local_app_data)
        else:
            base = _resolve_home(env) / "AppData" / "Local"
        return base / WORKSPACE_CONFIG_DIR_WINDOWS / WORKSPACE_CONFIG_FILENAME

    xdg_config_home = env.get("XDG_CONFIG_HOME")
    if xdg_config_home and xdg_config_home.strip():
        base = Path(xdg_config_home)
    else:
        base = _resolve_home(env) / ".config"
    return base / WORKSPACE_CONFIG_DIR_XDG / WORKSPACE_CONFIG_FILENAME


def _first_validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "configuration failed contract validation"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ())) or "document"
    return f"{location}: {first.get('msg', 'invalid value')}"


# --------------------------------------------------------------------------- #
# Configuration service
# --------------------------------------------------------------------------- #
@dataclass
class RepositoryWorkspaceConfigService:
    """Loads, validates, mutates, and persists the workspace configuration.

    The service is intentionally free of in-memory caching: each operation loads
    the current on-disk document, applies a validated transformation, and saves
    atomically. This matches the operator CLI's one-process-per-command usage and
    guarantees a mutation never acts on stale state.
    """

    config_path: Path | None = None
    executor: GitCommandExecutor | None = None
    git_limits: GitAdapterLimits = field(default=DEFAULT_GIT_ADAPTER_LIMITS)

    def __post_init__(self) -> None:
        self._path = (
            Path(self.config_path)
            if self.config_path is not None
            else resolve_workspace_config_path()
        )

    @property
    def path(self) -> Path:
        return self._path

    def _get_executor(self) -> GitCommandExecutor:
        if self.executor is None:
            self.executor = GitCommandExecutor(limits=self.git_limits)
        return self.executor

    # ------------------------------------------------------------------ #
    # Load / save
    # ------------------------------------------------------------------ #
    def exists(self) -> bool:
        try:
            return self._path.is_file()
        except OSError:
            return False

    def load(self) -> RepositoryWorkspaceConfig:
        """Load and fully validate the configuration, raising typed failures."""

        path = self._path
        try:
            if not path.exists():
                raise WorkspaceConfigNotFoundError(
                    f"no workspace configuration at {path}"
                )
            size = path.stat().st_size
        except WorkspaceConfigNotFoundError:
            raise
        except OSError as exc:
            raise WorkspaceConfigInaccessibleError(
                f"configuration at {path} could not be accessed: {exc}"
            ) from exc

        if size > MAX_WORKSPACE_CONFIG_BYTES:
            raise WorkspaceConfigTooLargeError(
                f"configuration at {path} is {size} bytes, exceeding the "
                f"{MAX_WORKSPACE_CONFIG_BYTES}-byte limit"
            )

        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceConfigMalformedError(
                "configuration is not valid UTF-8 text"
            ) from exc
        except OSError as exc:
            raise WorkspaceConfigInaccessibleError(
                f"configuration at {path} could not be read: {exc}"
            ) from exc

        if not raw.strip():
            raise WorkspaceConfigMalformedError("configuration file is empty")

        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise WorkspaceConfigMalformedError(
                "configuration is not valid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise WorkspaceConfigMalformedError(
                "configuration top-level value must be a JSON object"
            )

        version = data.get("schema_version")
        if version != REPOSITORY_WORKSPACE_SCHEMA_VERSION:
            raise UnsupportedWorkspaceSchemaVersionError(
                f"unsupported schema_version {version!r}; "
                f"expected {REPOSITORY_WORKSPACE_SCHEMA_VERSION!r}"
            )

        try:
            return RepositoryWorkspaceConfig.model_validate(data)
        except ValidationError as exc:
            raise WorkspaceConfigMalformedError(
                _first_validation_message(exc)
            ) from exc

    def load_or_default(self) -> RepositoryWorkspaceConfig:
        """Load the configuration, returning an empty document only if absent.

        A malformed, oversized, unsupported, or inaccessible file still raises so
        a mutation never silently discards or overwrites a damaged file.
        """

        try:
            return self.load()
        except WorkspaceConfigNotFoundError:
            return empty_config()

    def save(self, config: RepositoryWorkspaceConfig) -> None:
        """Serialize deterministically and persist atomically."""

        normalized = config.normalized()
        payload = normalized.model_dump(mode="json")
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        data = text.encode("utf-8")
        if len(data) > MAX_WORKSPACE_CONFIG_BYTES:
            raise WorkspaceConfigSaveError(
                f"serialized configuration is {len(data)} bytes, exceeding the "
                f"{MAX_WORKSPACE_CONFIG_BYTES}-byte limit"
            )
        self._atomic_write(data)

    def initialize(self, *, overwrite: bool = False) -> RepositoryWorkspaceConfig:
        """Write a fresh empty configuration, refusing to clobber unless asked."""

        if not overwrite and self.exists():
            raise WorkspaceConfigExistsError(
                f"configuration already exists at {self._path}; "
                "pass overwrite to replace it"
            )
        config = empty_config()
        self.save(config)
        return config

    def _atomic_write(self, data: bytes) -> None:
        path = self._path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(path.parent),
                prefix=".repository-workspaces-",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, path)  # atomic on POSIX and Windows
            except BaseException:
                # A failed swap must never destroy the prior valid file; the
                # destination is only replaced after a complete temp write.
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise
        except OSError as exc:
            raise WorkspaceConfigSaveError(
                f"could not persist configuration to {path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Workspace operations
    # ------------------------------------------------------------------ #
    def list_workspaces(self) -> list[RepositoryWorkspace]:
        return list(self.load_or_default().normalized().workspaces)

    def get_workspace(self, workspace_id: str) -> RepositoryWorkspace | None:
        return self.load_or_default().get(workspace_id)

    def add_workspace(
        self,
        *,
        workspace_id: str,
        display_name: str,
        repository_root: str,
        expected_remote: str | None = None,
        enabled: bool = True,
        make_active: bool = False,
    ) -> RepositoryWorkspace:
        config = self.load_or_default()
        workspace = self._build_workspace(
            workspace_id=workspace_id,
            display_name=display_name,
            repository_root=repository_root,
            expected_remote=expected_remote,
            enabled=enabled,
        )
        if config.get(workspace.workspace_id) is not None:
            raise DuplicateWorkspaceError(
                f"workspace {workspace.workspace_id!r} already exists"
            )
        new_key = workspace.comparison_key
        for existing in config.workspaces:
            if existing.comparison_key == new_key:
                raise DuplicateRepositoryRootError(
                    f"repository root already registered by workspace "
                    f"{existing.workspace_id!r}"
                )
        active = (
            workspace.workspace_id if make_active else config.active_workspace_id
        )
        self.save(
            RepositoryWorkspaceConfig(
                schema_version=config.schema_version,
                active_workspace_id=active,
                workspaces=[*config.workspaces, workspace],
            )
        )
        return workspace

    def update_workspace(
        self,
        workspace_id: str,
        *,
        display_name: str | None = None,
        expected_remote: str | None | object = _UNSET,
        enabled: bool | None = None,
    ) -> RepositoryWorkspace:
        config = self.load_or_default()
        existing = config.get(workspace_id)
        if existing is None:
            raise WorkspaceNotFoundError(f"workspace {workspace_id!r} does not exist")

        new_display = existing.display_name if display_name is None else display_name
        new_enabled = existing.enabled if enabled is None else enabled
        if expected_remote is _UNSET:
            new_remote: str | None = existing.expected_remote
        else:
            new_remote = expected_remote  # type: ignore[assignment]

        updated = self._build_workspace(
            workspace_id=existing.workspace_id,
            display_name=new_display,
            repository_root=existing.repository_root,
            expected_remote=new_remote,
            enabled=new_enabled,
        )
        workspaces = [
            updated if item.workspace_id == workspace_id else item
            for item in config.workspaces
        ]
        self.save(
            RepositoryWorkspaceConfig(
                schema_version=config.schema_version,
                active_workspace_id=config.active_workspace_id,
                workspaces=workspaces,
            )
        )
        return updated

    def set_active_workspace(self, workspace_id: str) -> RepositoryWorkspace:
        config = self.load_or_default()
        existing = config.get(workspace_id)
        if existing is None:
            raise WorkspaceNotFoundError(f"workspace {workspace_id!r} does not exist")
        self.save(
            RepositoryWorkspaceConfig(
                schema_version=config.schema_version,
                active_workspace_id=workspace_id,
                workspaces=config.workspaces,
            )
        )
        return existing

    def remove_workspace(self, workspace_id: str) -> RepositoryWorkspace:
        config = self.load_or_default()
        existing = config.get(workspace_id)
        if existing is None:
            raise WorkspaceNotFoundError(f"workspace {workspace_id!r} does not exist")
        remaining = [
            item for item in config.workspaces if item.workspace_id != workspace_id
        ]
        # Removing the active workspace deterministically clears the selection
        # rather than silently promoting an arbitrary other workspace.
        active = (
            None
            if config.active_workspace_id == workspace_id
            else config.active_workspace_id
        )
        self.save(
            RepositoryWorkspaceConfig(
                schema_version=config.schema_version,
                active_workspace_id=active,
                workspaces=remaining,
            )
        )
        return existing

    def _build_workspace(
        self,
        *,
        workspace_id: str,
        display_name: str,
        repository_root: str,
        expected_remote: str | None,
        enabled: bool,
    ) -> RepositoryWorkspace:
        if (
            expected_remote is not None
            and expected_remote.strip()
            and remote_has_credentials(expected_remote)
        ):
            raise CredentialBearingRemoteError(
                "expected remote must not embed credentials or access tokens"
            )
        try:
            return RepositoryWorkspace(
                workspace_id=workspace_id,
                display_name=display_name,
                repository_root=repository_root,
                expected_remote=expected_remote,
                enabled=enabled,
            )
        except ValidationError as exc:
            raise WorkspaceFieldError(_first_validation_message(exc)) from exc

    # ------------------------------------------------------------------ #
    # Resolution / availability
    # ------------------------------------------------------------------ #
    def resolve_active_workspace(
        self, *, check_availability: bool = True
    ) -> ActiveWorkspaceResolution:
        return self._resolve_active(self.load_or_default(), check_availability)

    def validate(self) -> WorkspaceValidationReport:
        config = self.load()
        normalized = config.normalized()
        availabilities = [self._probe_workspace(item) for item in normalized.workspaces]
        resolution = self._resolve_active(normalized, check_availability=True)
        return WorkspaceValidationReport(
            config_path=str(self._path),
            schema_version=normalized.schema_version,
            active_workspace_id=normalized.active_workspace_id,
            workspace_count=len(normalized.workspaces),
            workspaces=availabilities,
            active_resolution=resolution,
        )

    def _resolve_active(
        self, config: RepositoryWorkspaceConfig, check_availability: bool
    ) -> ActiveWorkspaceResolution:
        active_id = config.active_workspace_id
        if active_id is None:
            return ActiveWorkspaceResolution(
                active_workspace_id=None,
                workspace=None,
                repository_root=None,
                resolved=False,
                diagnostics=[
                    WorkspaceDiagnostic(
                        code=WorkspaceDiagnosticCode.NO_ACTIVE_WORKSPACE,
                        severity=WorkspaceDiagnosticSeverity.INFO,
                        message="no active workspace is selected",
                    )
                ],
            )
        workspace = config.get(active_id)
        # The contract guarantees an active id matches a workspace; guard anyway.
        if workspace is None:  # pragma: no cover - defended by contract validator
            return ActiveWorkspaceResolution(
                active_workspace_id=active_id,
                workspace=None,
                repository_root=None,
                resolved=False,
                diagnostics=[
                    WorkspaceDiagnostic(
                        code=WorkspaceDiagnosticCode.NO_ACTIVE_WORKSPACE,
                        severity=WorkspaceDiagnosticSeverity.ERROR,
                        message=f"active workspace {active_id!r} is missing",
                        workspace_id=active_id,
                    )
                ],
            )
        diagnostics: list[WorkspaceDiagnostic] = []
        if not workspace.enabled:
            diagnostics.append(
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.ACTIVE_WORKSPACE_DISABLED,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message=f"active workspace {active_id!r} is disabled",
                    workspace_id=active_id,
                )
            )
            return ActiveWorkspaceResolution(
                active_workspace_id=active_id,
                workspace=workspace,
                repository_root=workspace.repository_root,
                resolved=False,
                diagnostics=diagnostics,
            )
        resolved = True
        if check_availability:
            availability = self._probe_workspace(workspace)
            diagnostics.extend(availability.diagnostics)
            resolved = availability.exists and availability.is_git_repository is True
        return ActiveWorkspaceResolution(
            active_workspace_id=active_id,
            workspace=workspace,
            repository_root=workspace.repository_root,
            resolved=resolved,
            diagnostics=diagnostics,
        )

    def _probe_workspace(self, workspace: RepositoryWorkspace) -> WorkspaceAvailability:
        diagnostics: list[WorkspaceDiagnostic] = []
        wid = workspace.workspace_id
        root_text = workspace.repository_root
        path = Path(root_text)

        try:
            exists = path.exists()
            is_dir = path.is_dir() if exists else False
        except OSError:
            diagnostics.append(
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.REPOSITORY_ROOT_INACCESSIBLE,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message="repository root could not be accessed",
                    workspace_id=wid,
                )
            )
            return WorkspaceAvailability(
                workspace_id=wid,
                repository_root=root_text,
                enabled=workspace.enabled,
                exists=False,
                is_git_repository=None,
                expected_remote=workspace.expected_remote,
                actual_remote=None,
                diagnostics=diagnostics,
            )

        if not exists:
            diagnostics.append(
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.REPOSITORY_ROOT_ABSENT,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message="repository root does not exist",
                    workspace_id=wid,
                )
            )
            return WorkspaceAvailability(
                workspace_id=wid,
                repository_root=root_text,
                enabled=workspace.enabled,
                exists=False,
                is_git_repository=None,
                expected_remote=workspace.expected_remote,
                actual_remote=None,
                diagnostics=diagnostics,
            )

        if not is_dir:
            diagnostics.append(
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.PATH_NOT_GIT_REPOSITORY,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message="repository root exists but is not a directory",
                    workspace_id=wid,
                )
            )
            return WorkspaceAvailability(
                workspace_id=wid,
                repository_root=root_text,
                enabled=workspace.enabled,
                exists=True,
                is_git_repository=False,
                expected_remote=workspace.expected_remote,
                actual_remote=None,
                diagnostics=diagnostics,
            )

        is_git, git_diagnostic = self._probe_is_git(path, wid)
        if git_diagnostic is not None:
            diagnostics.append(git_diagnostic)

        actual_remote: str | None = None
        if is_git:
            actual_remote, remote_diagnostics = self._probe_remote(path, workspace)
            diagnostics.extend(remote_diagnostics)
            if not diagnostics:
                diagnostics.append(
                    WorkspaceDiagnostic(
                        code=WorkspaceDiagnosticCode.REPOSITORY_AVAILABLE,
                        severity=WorkspaceDiagnosticSeverity.INFO,
                        message="repository is available",
                        workspace_id=wid,
                    )
                )

        return WorkspaceAvailability(
            workspace_id=wid,
            repository_root=root_text,
            enabled=workspace.enabled,
            exists=True,
            is_git_repository=is_git,
            expected_remote=workspace.expected_remote,
            actual_remote=actual_remote,
            diagnostics=diagnostics,
        )

    def _probe_is_git(
        self, path: Path, workspace_id: str
    ) -> tuple[bool | None, WorkspaceDiagnostic | None]:
        try:
            self._get_executor().run(GitReadOperation.RESOLVE_ROOT, path)
            return True, None
        except GitCommandFailedError:
            return False, WorkspaceDiagnostic(
                code=WorkspaceDiagnosticCode.PATH_NOT_GIT_REPOSITORY,
                severity=WorkspaceDiagnosticSeverity.WARNING,
                message="path exists but is not a Git repository",
                workspace_id=workspace_id,
            )
        except GitExecutableUnavailableError:
            return None, WorkspaceDiagnostic(
                code=WorkspaceDiagnosticCode.GIT_UNAVAILABLE,
                severity=WorkspaceDiagnosticSeverity.WARNING,
                message="git executable is unavailable; repository not verified",
                workspace_id=workspace_id,
            )
        except (GitCommandTimeoutError, RepositoryGitAdapterError):
            return None, WorkspaceDiagnostic(
                code=WorkspaceDiagnosticCode.GIT_UNAVAILABLE,
                severity=WorkspaceDiagnosticSeverity.WARNING,
                message="git repository probe did not complete within bounds",
                workspace_id=workspace_id,
            )
        except PermissionError:
            return None, WorkspaceDiagnostic(
                code=WorkspaceDiagnosticCode.REPOSITORY_ROOT_INACCESSIBLE,
                severity=WorkspaceDiagnosticSeverity.WARNING,
                message="repository root could not be accessed",
                workspace_id=workspace_id,
            )

    def _probe_remote(
        self, path: Path, workspace: RepositoryWorkspace
    ) -> tuple[str | None, list[WorkspaceDiagnostic]]:
        wid = workspace.workspace_id
        if not workspace.expected_remote:
            return None, [
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.EXPECTED_REMOTE_ABSENT,
                    severity=WorkspaceDiagnosticSeverity.INFO,
                    message="workspace declares no expected remote",
                    workspace_id=wid,
                )
            ]
        try:
            result = self._get_executor().run(GitReadOperation.REMOTES, path)
        except (RepositoryGitAdapterError, PermissionError):
            return None, [
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.GIT_UNAVAILABLE,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message="remote listing did not complete within bounds",
                    workspace_id=wid,
                )
            ]
        remotes = parse_remote_verbose(result.stdout)
        origin = next((item for item in remotes if item.name == "origin"), None)
        if origin is None and remotes:
            origin = remotes[0]
        actual = origin.normalized_url if origin is not None else None
        expected = normalize_remote(workspace.expected_remote)
        if actual is None or actual != expected:
            return actual, [
                WorkspaceDiagnostic(
                    code=WorkspaceDiagnosticCode.EXPECTED_REMOTE_MISMATCH,
                    severity=WorkspaceDiagnosticSeverity.WARNING,
                    message="configured remote does not match the repository origin",
                    workspace_id=wid,
                )
            ]
        return actual, []


# --------------------------------------------------------------------------- #
# Repository Observer integration seam
# --------------------------------------------------------------------------- #
def resolve_active_repository_workspace(
    config_path: Path | None = None,
    *,
    executor: GitCommandExecutor | None = None,
    check_availability: bool = True,
) -> ActiveWorkspaceResolution:
    """Resolve the operator's active repository workspace.

    This is the narrow seam a future Repository Observer phase consumes to obtain
    the active repository root without re-entering a path each time. It performs a
    bounded, read-only resolution only: it never runs an observation snapshot,
    starts polling, watches files, mutates the repository, or inserts anything
    into Active Memory. Availability checking, when enabled, uses a single
    read-only ``git rev-parse`` probe through the existing adapter.
    """

    service = RepositoryWorkspaceConfigService(
        config_path=config_path, executor=executor
    )
    return service.resolve_active_workspace(check_availability=check_availability)
