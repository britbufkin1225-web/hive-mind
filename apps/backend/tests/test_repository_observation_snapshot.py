"""Phase 37K - repository observation snapshot service tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.models.repository_observer import ObserverScope, SnapshotCompleteness
from app.services.repository_git_adapter import (
    GitAdapterLimits,
    GitCommandResult,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
    GitReadOperation,
    READ_ONLY_GIT_COMMANDS,
    observe_repository,
)
from app.services.repository_observation_snapshot import (
    OBSERVATION_SNAPSHOT_SERVICE_VERSION,
    RepositoryObservationScopeError,
    observe_repository_snapshot,
)


FIXED_TS = datetime(2026, 7, 18, 13, 0, 0)


def _result(
    operation: GitReadOperation,
    stdout: bytes,
    *,
    stdout_truncated: bool = False,
) -> GitCommandResult:
    return GitCommandResult(
        operation=operation,
        args=READ_ONLY_GIT_COMMANDS[operation],
        cwd="C:/repo",
        returncode=0,
        stdout=stdout,
        stderr=b"",
        stdout_truncated=stdout_truncated,
    )


class ScriptedExecutor:
    def __init__(self, results: dict[GitReadOperation, GitCommandResult]) -> None:
        self.results = results
        self.calls: list[tuple[GitReadOperation, Path]] = []

    def run(self, operation: GitReadOperation, repository_root: Path) -> GitCommandResult:
        self.calls.append((operation, repository_root))
        return self.results[operation]


def test_snapshot_service_orchestrates_adapter_commands_and_returns_37k_snapshot() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/repo\n"
            ),
            GitReadOperation.STATUS: _result(
                GitReadOperation.STATUS,
                (
                    b"# branch.oid abc\0# branch.head main\0"
                    b"# branch.upstream origin/main\0? docs/new.md\0"
                ),
            ),
            GitReadOperation.REMOTES: _result(
                GitReadOperation.REMOTES,
                b"origin\thttps://token@example.com/u/repo.git (fetch)\n",
            ),
        }
    )

    snapshot = observe_repository_snapshot(
        repository_path="C:/repo/subdir",
        observed_at=FIXED_TS,
        executor=executor,  # type: ignore[arg-type]
    )

    assert [call[0] for call in executor.calls] == [
        GitReadOperation.RESOLVE_ROOT,
        GitReadOperation.STATUS,
        GitReadOperation.REMOTES,
    ]
    assert executor.calls[1][1] == Path("C:/repo")
    assert snapshot.observer_version == OBSERVATION_SNAPSHOT_SERVICE_VERSION
    assert snapshot.repository_identity.current_branch == "main"
    assert snapshot.repository_identity.primary_remote_url == "example.com/u/repo"
    assert snapshot.changed_files[0].repository_relative_path == "docs/new.md"
    assert snapshot.completeness is SnapshotCompleteness.COMPLETE
    assert snapshot.read_only is True


def test_snapshot_service_applies_scope_file_limit_without_reimplementing_conversion() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/repo\n"
            ),
            GitReadOperation.STATUS: _result(
                GitReadOperation.STATUS,
                b"# branch.oid abc\0# branch.head main\0? b.md\0? a.md\0? c.md\0",
            ),
            GitReadOperation.REMOTES: _result(GitReadOperation.REMOTES, b""),
        }
    )
    scope = ObserverScope(repository_root="C:/repo", max_file_count=2)

    snapshot = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        scope=scope,
        executor=executor,  # type: ignore[arg-type]
    )

    assert [item.repository_relative_path for item in snapshot.changed_files] == [
        "a.md",
        "b.md",
    ]
    assert snapshot.omitted_paths == ["c.md"]
    assert snapshot.completeness is SnapshotCompleteness.PARTIAL


def test_snapshot_service_rejects_deferred_scope_features() -> None:
    with pytest.raises(RepositoryObservationScopeError, match="included_paths"):
        observe_repository_snapshot(
            repository_path="C:/repo",
            observed_at=FIXED_TS,
            scope=ObserverScope(repository_root="C:/repo", included_paths=["docs"]),
        )

    with pytest.raises(RepositoryObservationScopeError, match="metadata-only"):
        observe_repository_snapshot(
            repository_path="C:/repo",
            observed_at=FIXED_TS,
            scope=ObserverScope(repository_root="C:/repo", metadata_only=False),
        )


def test_snapshot_service_rejects_scope_root_mismatch_after_git_resolution() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/actual\n"
            ),
        }
    )

    with pytest.raises(RepositoryObservationScopeError, match="does not match"):
        observe_repository_snapshot(
            repository_path="C:/actual",
            observed_at=FIXED_TS,
            scope=ObserverScope(repository_root="C:/expected"),
            executor=executor,  # type: ignore[arg-type]
        )


def test_snapshot_service_preserves_root_evidence_fail_closed_behavior() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT,
                b"C:/",
                stdout_truncated=True,
            ),
        }
    )

    with pytest.raises(GitOutputLimitExceededError, match="root"):
        observe_repository_snapshot(
            repository_path="C:/repo",
            observed_at=FIXED_TS,
            executor=executor,  # type: ignore[arg-type]
        )


def test_snapshot_service_rejects_empty_root_evidence() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(GitReadOperation.RESOLVE_ROOT, b"\n"),
        }
    )

    with pytest.raises(GitPorcelainParseError, match="empty"):
        observe_repository_snapshot(
            repository_path="C:/repo",
            observed_at=FIXED_TS,
            executor=executor,  # type: ignore[arg-type]
        )


def test_adapter_observe_repository_delegates_to_snapshot_service() -> None:
    executor = ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/repo\n"
            ),
            GitReadOperation.STATUS: _result(
                GitReadOperation.STATUS, b"# branch.oid abc\0# branch.head main\0"
            ),
            GitReadOperation.REMOTES: _result(GitReadOperation.REMOTES, b""),
        }
    )

    snapshot = observe_repository(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        limits=GitAdapterLimits(max_file_observations=5),
        executor=executor,  # type: ignore[arg-type]
    )

    assert snapshot.observer_version == OBSERVATION_SNAPSHOT_SERVICE_VERSION
    assert snapshot.repository_identity.current_branch == "main"
