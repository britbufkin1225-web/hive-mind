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
    MUTATING_GIT_SUBCOMMANDS,
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


def _dirty_executor() -> ScriptedExecutor:
    return ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/repo\n"
            ),
            GitReadOperation.STATUS: _result(
                GitReadOperation.STATUS,
                (
                    b"# branch.oid abc\0# branch.head main\0"
                    b"# branch.upstream origin/main\0"
                    b"1 .M N... 100644 100644 100644 aaaaaa bbbbbb apps/mod.py\0"
                    b"? docs/new.md\0"
                ),
            ),
            GitReadOperation.REMOTES: _result(
                GitReadOperation.REMOTES,
                b"origin\thttps://token@example.com/u/repo.git (fetch)\n",
            ),
        }
    )


def test_compatibility_wrapper_matches_canonical_service_for_equivalent_inputs() -> None:
    # The adapter's legacy observe_repository(...) must delegate into the same
    # service path and produce a byte-identical snapshot to the canonical entry
    # point for equivalent inputs (scope=None) - no divergent semantics.
    wrapper_snapshot = observe_repository(
        repository_path="C:/repo/subdir",
        observed_at=FIXED_TS,
        executor=_dirty_executor(),  # type: ignore[arg-type]
    )
    service_snapshot = observe_repository_snapshot(
        repository_path="C:/repo/subdir",
        observed_at=FIXED_TS,
        executor=_dirty_executor(),  # type: ignore[arg-type]
    )

    assert wrapper_snapshot.model_dump(mode="json") == service_snapshot.model_dump(
        mode="json"
    )


def test_compatibility_wrapper_does_not_recurse() -> None:
    # Delegation must terminate: exactly the three allowlisted read commands run
    # once each, proving the wrapper does not re-enter itself or the service.
    executor = _dirty_executor()

    observe_repository(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=executor,  # type: ignore[arg-type]
    )

    assert [call[0] for call in executor.calls] == [
        GitReadOperation.RESOLVE_ROOT,
        GitReadOperation.STATUS,
        GitReadOperation.REMOTES,
    ]


def _executor_with_status(status_body: bytes) -> ScriptedExecutor:
    return ScriptedExecutor(
        {
            GitReadOperation.RESOLVE_ROOT: _result(
                GitReadOperation.RESOLVE_ROOT, b"C:/repo\n"
            ),
            GitReadOperation.STATUS: _result(GitReadOperation.STATUS, status_body),
            GitReadOperation.REMOTES: _result(GitReadOperation.REMOTES, b""),
        }
    )


def test_snapshot_service_is_byte_stable_for_identical_input() -> None:
    # Repeatability across the full orchestration proves no dict/set iteration,
    # process-hash, wall-clock, or random-identifier nondeterminism leaks into
    # the assembled snapshot.
    body = b"# branch.oid abc\0# branch.head main\0? b.md\0? a.md\0? docs/c.md\0"
    first = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=_executor_with_status(body),  # type: ignore[arg-type]
    )
    second = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=_executor_with_status(body),  # type: ignore[arg-type]
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_snapshot_service_orders_structured_collections_independent_of_input() -> None:
    # Structured collections (changed files, omitted paths, warning ids) are
    # canonically ordered regardless of the raw record order git happened to
    # emit. The verbatim evidence excerpt is intentionally a faithful raw
    # capture, so it is compared separately from the normalized structure.
    header = b"# branch.oid abc\0# branch.head main\0"
    first = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=_executor_with_status(header + b"? b.md\0? a.md\0? docs/c.md\0"),  # type: ignore[arg-type]
    )
    second = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=_executor_with_status(header + b"? docs/c.md\0? b.md\0? a.md\0"),  # type: ignore[arg-type]
    )

    assert [f.repository_relative_path for f in first.changed_files] == [
        "a.md",
        "b.md",
        "docs/c.md",
    ]
    assert [f.repository_relative_path for f in first.changed_files] == [
        f.repository_relative_path for f in second.changed_files
    ]
    assert first.omitted_paths == second.omitted_paths
    assert [f.file_id for f in first.changed_files] == [
        f.file_id for f in second.changed_files
    ]
    assert first.repository_identity.warning_ids == second.repository_identity.warning_ids


def test_snapshot_service_only_issues_allowlisted_read_only_commands() -> None:
    executor = _dirty_executor()

    observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=executor,  # type: ignore[arg-type]
    )

    for operation, _root in executor.calls:
        args = READ_ONLY_GIT_COMMANDS[operation]
        assert args[0] == "git"
        assert args[1] not in MUTATING_GIT_SUBCOMMANDS


def test_snapshot_service_uses_only_caller_supplied_timestamp_no_wall_clock() -> None:
    executor = _dirty_executor()

    snapshot = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        executor=executor,  # type: ignore[arg-type]
    )

    # No wall-clock read: the snapshot timestamp and every evidence capture time
    # equal the caller-supplied observed_at exactly.
    assert snapshot.observed_at == FIXED_TS
    assert all(e.captured_at == FIXED_TS for e in snapshot.evidence)


def test_snapshot_service_mvp_always_includes_untracked_files() -> None:
    # KNOWN MVP LIMITATION (deferred to Phase 37L): the service does not yet
    # honor ObserverScope.include_untracked_files. The adapter always runs
    # --untracked-files=all, so untracked paths are retained regardless of the
    # flag. This test pins that behavior honestly; a future untracked-policy
    # implementation is expected to change it (and must preserve working-tree
    # truth so an untracked-only repo is never reported CLEAN).
    scope = ObserverScope(repository_root="C:/repo", include_untracked_files=False)

    snapshot = observe_repository_snapshot(
        repository_path="C:/repo",
        observed_at=FIXED_TS,
        scope=scope,
        executor=_dirty_executor(),  # type: ignore[arg-type]
    )

    untracked_paths = [
        f.repository_relative_path
        for f in snapshot.changed_files
        if f.change_kind.value == "untracked"
    ]
    assert untracked_paths == ["docs/new.md"]
