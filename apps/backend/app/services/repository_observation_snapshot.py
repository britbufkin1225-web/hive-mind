"""Phase 37K - repository observation snapshot service MVP.

This service owns request-triggered snapshot orchestration over the Phase 37J
Git adapter. It adds no API route, persistence, watcher, polling loop, Active
Memory ingestion, GitHub integration, frontend surface, or repository mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models.repository_observer import (
    ObserverScope,
    RepositorySnapshot,
)
from app.services.repository_git_adapter import (
    DEFAULT_GIT_ADAPTER_LIMITS,
    GitAdapterLimits,
    GitCommandExecutor,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
    GitReadOperation,
    convert_git_evidence_to_snapshot,
    parse_porcelain_v2_z,
    parse_remote_verbose,
)


OBSERVATION_SNAPSHOT_SERVICE_VERSION = "repo-observer.v1-phase-37k"


class RepositoryObservationSnapshotError(Exception):
    """Base class for bounded snapshot-service failures."""


class RepositoryObservationScopeError(RepositoryObservationSnapshotError):
    """Raised when a requested observer scope is unsupported or mismatched."""


@dataclass(frozen=True)
class RepositoryObservationSnapshotRequest:
    repository_path: str | Path
    observed_at: datetime
    scope: ObserverScope | None = None
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS
    executor: GitCommandExecutor | None = None


class RepositoryObservationSnapshotService:
    """Assemble one deterministic repository snapshot from read-only Git evidence."""

    def observe(self, request: RepositoryObservationSnapshotRequest) -> RepositorySnapshot:
        _validate_scope_contract(request.scope)
        target = Path(request.repository_path)
        limits = _limits_for_scope(request.limits, request.scope)
        command_executor = request.executor or GitCommandExecutor(limits=limits)

        root_result = command_executor.run(GitReadOperation.RESOLVE_ROOT, target)
        if root_result.stdout_truncated or root_result.stderr_truncated:
            raise GitOutputLimitExceededError("repository root evidence exceeded command bounds")
        root_text = _decode_root(root_result.stdout)
        root = Path(root_text)
        _validate_scope_matches_resolved_root(request.scope, root)

        status_result = command_executor.run(GitReadOperation.STATUS, root)
        remote_result = command_executor.run(GitReadOperation.REMOTES, root)
        status = parse_porcelain_v2_z(
            status_result.stdout,
            output_complete=not status_result.stdout_truncated,
        )
        remotes = parse_remote_verbose(remote_result.stdout)

        return convert_git_evidence_to_snapshot(
            repository_root=root,
            status=status,
            remotes=remotes,
            observed_at=request.observed_at,
            limits=limits,
            status_result=status_result,
            remote_result=remote_result,
            observer_version=OBSERVATION_SNAPSHOT_SERVICE_VERSION,
        )


def observe_repository_snapshot(
    *,
    repository_path: str | Path,
    observed_at: datetime,
    scope: ObserverScope | None = None,
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS,
    executor: GitCommandExecutor | None = None,
) -> RepositorySnapshot:
    """Observe one repository through the Phase 37K snapshot service."""

    request = RepositoryObservationSnapshotRequest(
        repository_path=repository_path,
        observed_at=observed_at,
        scope=scope,
        limits=limits,
        executor=executor,
    )
    return RepositoryObservationSnapshotService().observe(request)


def _validate_scope_contract(scope: ObserverScope | None) -> None:
    if scope is None:
        return
    if scope.included_paths or scope.excluded_paths:
        raise RepositoryObservationScopeError(
            "included_paths and excluded_paths are deferred for the snapshot service MVP"
        )
    if scope.allow_file_contents or not scope.metadata_only:
        raise RepositoryObservationScopeError(
            "the snapshot service MVP is metadata-only and cannot read file contents"
        )
    if scope.include_ignored_files or scope.include_binary_files:
        raise RepositoryObservationScopeError(
            "ignored-file and binary-file observation are deferred for the snapshot service MVP"
        )


def _validate_scope_matches_resolved_root(scope: ObserverScope | None, root: Path) -> None:
    if scope is None:
        return
    if _normalize_path(scope.repository_root) != _normalize_path(str(root)):
        raise RepositoryObservationScopeError(
            "observer scope repository_root does not match the resolved Git root"
        )


def _limits_for_scope(
    limits: GitAdapterLimits, scope: ObserverScope | None
) -> GitAdapterLimits:
    if scope is None:
        return limits
    return GitAdapterLimits(
        command_timeout_seconds=limits.command_timeout_seconds,
        stdout_bytes=min(limits.stdout_bytes, scope.max_snapshot_bytes),
        stderr_bytes=limits.stderr_bytes,
        max_file_observations=scope.max_file_count,
        max_excerpt_chars=limits.max_excerpt_chars,
        max_warning_count=limits.max_warning_count,
        max_limitation_count=limits.max_limitation_count,
    )


def _decode_root(stdout: bytes) -> str:
    try:
        root_text = stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise GitPorcelainParseError("repository root contained undecodable UTF-8") from exc
    if not root_text:
        raise GitPorcelainParseError("repository root evidence was empty")
    return root_text


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").casefold()
