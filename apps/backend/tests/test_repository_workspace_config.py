"""Phase 39B - configuration service: load, save, operations, resolution."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.models.repository_workspace import (
    MAX_WORKSPACE_CONFIG_BYTES,
    RepositoryWorkspace,
    RepositoryWorkspaceConfig,
)
from app.services.repository_git_adapter import (
    GitCommandFailedError,
    GitExecutableUnavailableError,
    GitReadOperation,
)
from app.services.repository_workspace_config import (
    ActiveWorkspaceResolution,
    DuplicateRepositoryRootError,
    DuplicateWorkspaceError,
    RepositoryWorkspaceConfigService,
    UnsupportedWorkspaceSchemaVersionError,
    WorkspaceConfigExistsError,
    WorkspaceConfigMalformedError,
    WorkspaceConfigNotFoundError,
    WorkspaceConfigSaveError,
    WorkspaceConfigTooLargeError,
    WorkspaceDiagnosticCode,
    WorkspaceNotFoundError,
    resolve_active_repository_workspace,
)


class FakeExecutor:
    """Stand-in for the read-only Git adapter executor.

    Records nothing about the real environment; each instance is scripted so
    availability diagnostics can be exercised without a real Git repository.
    """

    def __init__(
        self,
        *,
        is_git: bool = True,
        unavailable: bool = False,
        remotes_stdout: bytes = b"",
    ) -> None:
        self.is_git = is_git
        self.unavailable = unavailable
        self.remotes_stdout = remotes_stdout

    def run(self, operation: GitReadOperation, repository_root):
        if self.unavailable:
            raise GitExecutableUnavailableError("git unavailable")
        if operation is GitReadOperation.RESOLVE_ROOT:
            if not self.is_git:
                raise GitCommandFailedError("not a git repository")
            return SimpleNamespace(stdout=str(repository_root).encode("utf-8"))
        if operation is GitReadOperation.REMOTES:
            return SimpleNamespace(stdout=self.remotes_stdout)
        raise AssertionError(f"unexpected operation {operation}")


def _service(tmp_path, **kwargs) -> RepositoryWorkspaceConfigService:
    return RepositoryWorkspaceConfigService(
        config_path=tmp_path / "repository-workspaces.json", **kwargs
    )


# --------------------------------------------------------------------------- #
# Load behavior
# --------------------------------------------------------------------------- #
def test_absent_configuration_raises_not_found(tmp_path) -> None:
    service = _service(tmp_path)
    assert not service.exists()
    with pytest.raises(WorkspaceConfigNotFoundError):
        service.load()


def test_absent_configuration_defaults_to_empty(tmp_path) -> None:
    service = _service(tmp_path)
    config = service.load_or_default()
    assert config.workspaces == []


def test_valid_round_trip(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="hive-mind",
        display_name="Hive Mind",
        repository_root=str(tmp_path / "hive-mind"),
    )
    reloaded = _service(tmp_path).load()
    assert reloaded.get("hive-mind") is not None


def test_malformed_json_is_reported(tmp_path) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text("{not valid", encoding="utf-8")
    with pytest.raises(WorkspaceConfigMalformedError):
        _service(tmp_path).load()


def test_malformed_config_is_not_swallowed_by_default(tmp_path) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text("{not valid", encoding="utf-8")
    with pytest.raises(WorkspaceConfigMalformedError):
        _service(tmp_path).load_or_default()


def test_wrong_top_level_shape(tmp_path) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(WorkspaceConfigMalformedError):
        _service(tmp_path).load()


def test_unsupported_schema_version_file(tmp_path) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text(
        json.dumps({"schema_version": "repository-workspaces.v9", "workspaces": []}),
        encoding="utf-8",
    )
    with pytest.raises(UnsupportedWorkspaceSchemaVersionError):
        _service(tmp_path).load()


def test_oversized_file_is_rejected(tmp_path) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text("x" * (MAX_WORKSPACE_CONFIG_BYTES + 1), encoding="utf-8")
    with pytest.raises(WorkspaceConfigTooLargeError):
        _service(tmp_path).load()


# --------------------------------------------------------------------------- #
# Save behavior
# --------------------------------------------------------------------------- #
def test_initialize_creates_parent_directories(tmp_path) -> None:
    nested = tmp_path / "deep" / "nested"
    service = RepositoryWorkspaceConfigService(
        config_path=nested / "repository-workspaces.json"
    )
    service.initialize()
    assert (nested / "repository-workspaces.json").is_file()


def test_initialize_refuses_to_clobber(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize()
    with pytest.raises(WorkspaceConfigExistsError):
        service.initialize()
    # Overwrite is explicit and permitted.
    service.initialize(overwrite=True)


def test_atomic_save_leaves_no_temp_files(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize()
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(tmp_path / "a")
    )
    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_failed_write_preserves_existing_file(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="keep", display_name="Keep", repository_root=str(tmp_path / "keep")
    )
    original = (tmp_path / "repository-workspaces.json").read_bytes()

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", _boom)
    with pytest.raises(WorkspaceConfigSaveError):
        service.add_workspace(
            workspace_id="new", display_name="New", repository_root=str(tmp_path / "new")
        )
    assert (tmp_path / "repository-workspaces.json").read_bytes() == original
    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_deterministic_serialized_output(tmp_path) -> None:
    config = RepositoryWorkspaceConfig(
        workspaces=[
            RepositoryWorkspace(
                workspace_id="zeta", display_name="Z", repository_root="C:/z"
            ),
            RepositoryWorkspace(
                workspace_id="alpha", display_name="A", repository_root="C:/a"
            ),
        ]
    )
    service_a = _service(tmp_path / "a")
    service_b = _service(tmp_path / "b")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    service_a.save(config)
    service_b.save(config)
    bytes_a = (tmp_path / "a" / "repository-workspaces.json").read_bytes()
    bytes_b = (tmp_path / "b" / "repository-workspaces.json").read_bytes()
    assert bytes_a == bytes_b
    # Workspaces are ordered by id regardless of insertion order.
    payload = json.loads(bytes_a)
    assert [w["workspace_id"] for w in payload["workspaces"]] == ["alpha", "zeta"]


# --------------------------------------------------------------------------- #
# Workspace operations
# --------------------------------------------------------------------------- #
def test_add_and_reject_duplicate(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(tmp_path / "a")
    )
    with pytest.raises(DuplicateWorkspaceError):
        service.add_workspace(
            workspace_id="a", display_name="A2", repository_root=str(tmp_path / "other")
        )


def test_reject_duplicate_root(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=r"C:\repos\Shared"
    )
    with pytest.raises(DuplicateRepositoryRootError):
        service.add_workspace(
            workspace_id="b", display_name="B", repository_root="c:/repos/shared/"
        )


def test_update_safe_metadata(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a", display_name="Old", repository_root=str(tmp_path / "a")
    )
    updated = service.update_workspace("a", display_name="New", enabled=False)
    assert updated.display_name == "New"
    assert updated.enabled is False
    # Persisted.
    assert _service(tmp_path).get_workspace("a").display_name == "New"


def test_update_can_clear_expected_remote(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a",
        display_name="A",
        repository_root=str(tmp_path / "a"),
        expected_remote="https://github.com/x/y.git",
    )
    updated = service.update_workspace("a", expected_remote=None)
    assert updated.expected_remote is None


def test_set_active_and_resolve(tmp_path) -> None:
    executor = FakeExecutor(is_git=True)
    service = _service(tmp_path, executor=executor)
    root = tmp_path / "a"
    root.mkdir()
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(root)
    )
    service.set_active_workspace("a")
    resolution = service.resolve_active_workspace()
    assert isinstance(resolution, ActiveWorkspaceResolution)
    assert resolution.active_workspace_id == "a"
    assert resolution.resolved is True


def test_set_active_unknown_workspace(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize()
    with pytest.raises(WorkspaceNotFoundError):
        service.set_active_workspace("nope")


def test_remove_inactive_workspace(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(tmp_path / "a")
    )
    service.add_workspace(
        workspace_id="b", display_name="B", repository_root=str(tmp_path / "b")
    )
    service.set_active_workspace("a")
    service.remove_workspace("b")
    assert service.get_workspace("b") is None
    assert service.load().active_workspace_id == "a"


def test_remove_active_workspace_clears_selection(tmp_path) -> None:
    service = _service(tmp_path)
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(tmp_path / "a")
    )
    service.set_active_workspace("a")
    service.remove_workspace("a")
    assert service.load_or_default().active_workspace_id is None


def test_remove_unknown_workspace(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize()
    with pytest.raises(WorkspaceNotFoundError):
        service.remove_workspace("ghost")


# --------------------------------------------------------------------------- #
# Resolution / availability diagnostics
# --------------------------------------------------------------------------- #
def test_no_active_workspace_diagnostic(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize()
    resolution = service.resolve_active_workspace()
    assert resolution.resolved is False
    codes = {d.code for d in resolution.diagnostics}
    assert WorkspaceDiagnosticCode.NO_ACTIVE_WORKSPACE in codes


def test_disabled_active_workspace_diagnostic(tmp_path) -> None:
    service = _service(tmp_path)
    root = tmp_path / "a"
    root.mkdir()
    service.add_workspace(
        workspace_id="a",
        display_name="A",
        repository_root=str(root),
        enabled=False,
        make_active=True,
    )
    resolution = service.resolve_active_workspace()
    assert resolution.resolved is False
    codes = {d.code for d in resolution.diagnostics}
    assert WorkspaceDiagnosticCode.ACTIVE_WORKSPACE_DISABLED in codes


def test_absent_repository_root_diagnostic(tmp_path) -> None:
    executor = FakeExecutor(is_git=True)
    service = _service(tmp_path, executor=executor)
    service.add_workspace(
        workspace_id="a",
        display_name="A",
        repository_root=str(tmp_path / "missing"),
        make_active=True,
    )
    report = service.validate()
    availability = report.workspaces[0]
    assert availability.exists is False
    codes = {d.code for d in availability.diagnostics}
    assert WorkspaceDiagnosticCode.REPOSITORY_ROOT_ABSENT in codes


def test_non_git_directory_diagnostic(tmp_path) -> None:
    executor = FakeExecutor(is_git=False)
    service = _service(tmp_path, executor=executor)
    root = tmp_path / "plain"
    root.mkdir()
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(root), make_active=True
    )
    report = service.validate()
    availability = report.workspaces[0]
    assert availability.is_git_repository is False
    codes = {d.code for d in availability.diagnostics}
    assert WorkspaceDiagnosticCode.PATH_NOT_GIT_REPOSITORY in codes


def test_expected_remote_mismatch_diagnostic(tmp_path) -> None:
    remotes = b"origin\thttps://github.com/other/repo.git (fetch)\n"
    executor = FakeExecutor(is_git=True, remotes_stdout=remotes)
    service = _service(tmp_path, executor=executor)
    root = tmp_path / "a"
    root.mkdir()
    service.add_workspace(
        workspace_id="a",
        display_name="A",
        repository_root=str(root),
        expected_remote="https://github.com/expected/repo.git",
        make_active=True,
    )
    report = service.validate()
    codes = {d.code for d in report.workspaces[0].diagnostics}
    assert WorkspaceDiagnosticCode.EXPECTED_REMOTE_MISMATCH in codes


def test_expected_remote_match_is_available(tmp_path) -> None:
    remotes = b"origin\thttps://github.com/team/repo.git (fetch)\n"
    executor = FakeExecutor(is_git=True, remotes_stdout=remotes)
    service = _service(tmp_path, executor=executor)
    root = tmp_path / "a"
    root.mkdir()
    service.add_workspace(
        workspace_id="a",
        display_name="A",
        repository_root=str(root),
        expected_remote="git@github.com:team/repo.git",
        make_active=True,
    )
    report = service.validate()
    codes = {d.code for d in report.workspaces[0].diagnostics}
    assert WorkspaceDiagnosticCode.REPOSITORY_AVAILABLE in codes
    assert report.active_resolution.resolved is True


def test_integration_seam_resolves_active(tmp_path) -> None:
    executor = FakeExecutor(is_git=True)
    service = _service(tmp_path, executor=executor)
    root = tmp_path / "a"
    root.mkdir()
    service.add_workspace(
        workspace_id="a", display_name="A", repository_root=str(root), make_active=True
    )
    resolution = resolve_active_repository_workspace(
        config_path=tmp_path / "repository-workspaces.json", executor=executor
    )
    assert resolution.repository_root == str(root)
    assert resolution.resolved is True
