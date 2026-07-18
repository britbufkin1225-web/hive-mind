"""Phase 37J - deterministic Git adapter tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pytest

from app.models.repository_observer import (
    FileChangeKind,
    SnapshotCompleteness,
    WorkingTreeState,
)
from app.services.repository_git_adapter import (
    DEFAULT_GIT_ADAPTER_LIMITS,
    GitAdapterLimits,
    GitCommandResult,
    GitCommandExecutor,
    GitCommandFailedError,
    GitCommandTimeoutError,
    GitExecutableUnavailableError,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
    GitReadOperation,
    READ_ONLY_GIT_COMMANDS,
    MUTATING_GIT_SUBCOMMANDS,
    convert_git_evidence_to_snapshot,
    observe_repository,
    parse_porcelain_v2_z,
    parse_remote_verbose,
)


FIXED_TS = datetime(2026, 7, 18, 12, 0, 0)


def _completed(args: tuple[str, ...], stdout: bytes = b"", stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr=stderr)


def _status_output(*records: bytes) -> bytes:
    return b"\0".join(records) + b"\0"


def test_command_executor_uses_shell_false_explicit_cwd_timeout_and_allowlisted_args() -> None:
    calls: list[dict[str, object]] = []

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append({"args": args, "kwargs": kwargs})
        return _completed(args[0], stdout=b"C:/repo\n")  # type: ignore[arg-type]

    executor = GitCommandExecutor(runner=runner)
    result = executor.run(GitReadOperation.RESOLVE_ROOT, Path("C:/repo"))

    assert result.args == READ_ONLY_GIT_COMMANDS[GitReadOperation.RESOLVE_ROOT]
    assert calls[0]["args"][0] == READ_ONLY_GIT_COMMANDS[GitReadOperation.RESOLVE_ROOT]
    assert calls[0]["kwargs"]["cwd"] == "C:\\repo" or calls[0]["kwargs"]["cwd"] == "C:/repo"
    assert calls[0]["kwargs"]["shell"] is False
    assert calls[0]["kwargs"]["timeout"] == DEFAULT_GIT_ADAPTER_LIMITS.command_timeout_seconds
    assert calls[0]["kwargs"]["capture_output"] is True
    assert calls[0]["kwargs"]["check"] is False


def test_application_command_set_excludes_mutating_git_subcommands() -> None:
    observed_subcommands = {args[1] for args in READ_ONLY_GIT_COMMANDS.values()}
    assert not (observed_subcommands & MUTATING_GIT_SUBCOMMANDS)
    assert {
        GitReadOperation.RESOLVE_ROOT,
        GitReadOperation.STATUS,
        GitReadOperation.REMOTES,
    } == set(READ_ONLY_GIT_COMMANDS)


def test_command_executor_bounds_stdout_and_stderr() -> None:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return _completed(args[0], stdout=b"abcdef", stderr=b"uvwxyz")  # type: ignore[arg-type]

    executor = GitCommandExecutor(
        limits=GitAdapterLimits(stdout_bytes=3, stderr_bytes=2),
        runner=runner,
    )
    result = executor.run(GitReadOperation.REMOTES, Path("C:/repo"))

    assert result.stdout == b"abc"
    assert result.stderr == b"uv"
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True


def test_command_executor_handles_nonzero_timeout_and_missing_git() -> None:
    def nonzero(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=args[0], returncode=128, stdout=b"", stderr=b"fatal: not a git repository")

    with pytest.raises(GitCommandFailedError, match="exited with 128"):
        GitCommandExecutor(runner=nonzero).run(GitReadOperation.STATUS, Path("C:/repo"))

    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    with pytest.raises(GitCommandTimeoutError, match="timeout"):
        GitCommandExecutor(runner=timeout).run(GitReadOperation.STATUS, Path("C:/repo"))

    def missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise FileNotFoundError("git")

    with pytest.raises(GitExecutableUnavailableError, match="unavailable"):
        GitCommandExecutor(runner=missing).run(GitReadOperation.STATUS, Path("C:/repo"))


def test_parse_clean_branch_status() -> None:
    evidence = parse_porcelain_v2_z(
        _status_output(
            b"# branch.oid 8064b1eeddc80685c95a823c779237cb4db0e811",
            b"# branch.head main",
            b"# branch.upstream origin/main",
            b"# branch.ab +0 -0",
        )
    )

    assert evidence.branch.head == "main"
    assert evidence.branch.oid == "8064b1eeddc80685c95a823c779237cb4db0e811"
    assert evidence.branch.upstream == "origin/main"
    assert evidence.branch.ahead == 0
    assert evidence.branch.behind == 0
    assert evidence.files == ()


def test_parse_staged_unstaged_mixed_deletions_untracked_and_spaces() -> None:
    evidence = parse_porcelain_v2_z(
        _status_output(
            b"# branch.oid abc",
            b"# branch.head main",
            b"1 A. N... 100644 100644 100644 000000 aaaaaa file added.md",
            b"1 .M N... 100644 100644 100644 aaaaaa aaaaaa docs/changed file.md",
            b"1 MD N... 100644 100644 100644 aaaaaa bbbbbb apps/mixed.py",
            b"1 .D N... 100644 100644 000000 aaaaaa 000000 docs/deleted.md",
            b"? docs/new note.md",
        )
    )

    by_path = {item.path: item for item in evidence.files}
    assert by_path["file added.md"].change_kind is FileChangeKind.ADDED
    assert by_path["file added.md"].staged is True
    assert by_path["docs/changed file.md"].change_kind is FileChangeKind.MODIFIED
    assert by_path["docs/changed file.md"].staged is False
    assert by_path["apps/mixed.py"].change_kind is FileChangeKind.MODIFIED
    assert by_path["apps/mixed.py"].staged is True
    assert by_path["docs/deleted.md"].change_kind is FileChangeKind.DELETED
    assert by_path["docs/new note.md"].change_kind is FileChangeKind.UNTRACKED


def test_parse_rename_and_copy_relationships() -> None:
    evidence = parse_porcelain_v2_z(
        _status_output(
            b"# branch.oid abc",
            b"# branch.head main",
            b"2 R. N... 100644 100644 100644 aaaaaa bbbbbb R100 docs/new name.md",
            b"docs/old name.md",
            b"2 C. N... 100644 100644 100644 aaaaaa bbbbbb C087 docs/copied.md",
            b"docs/source.md",
        )
    )

    by_path = {item.path: item for item in evidence.files}
    assert by_path["docs/new name.md"].change_kind is FileChangeKind.RENAMED
    assert by_path["docs/new name.md"].prior_path == "docs/old name.md"
    assert by_path["docs/copied.md"].change_kind is FileChangeKind.COPIED
    assert by_path["docs/copied.md"].prior_path == "docs/source.md"


def test_parse_detached_head_unborn_and_missing_upstream_metadata() -> None:
    detached = parse_porcelain_v2_z(
        _status_output(b"# branch.oid abc", b"# branch.head (detached)")
    )
    unborn = parse_porcelain_v2_z(
        _status_output(b"# branch.oid (initial)", b"# branch.head main")
    )

    assert detached.branch.detached is True
    assert detached.branch.head is None
    assert unborn.branch.unborn is True
    assert unborn.branch.oid is None
    assert unborn.branch.upstream is None


def test_parse_rejects_malformed_unexpected_unsafe_and_undecodable_records() -> None:
    with pytest.raises(GitPorcelainParseError, match="malformed ordinary"):
        parse_porcelain_v2_z(_status_output(b"1 M"))
    with pytest.raises(GitPorcelainParseError, match="missing prior"):
        parse_porcelain_v2_z(_status_output(b"2 R. N... 100644 100644 100644 a b R100 docs/new.md"))
    with pytest.raises(GitPorcelainParseError, match="unexpected"):
        parse_porcelain_v2_z(_status_output(b"x surprising"))
    with pytest.raises(GitPorcelainParseError, match="unsafe"):
        parse_porcelain_v2_z(_status_output(b"? ../secret.txt"))
    with pytest.raises(GitPorcelainParseError, match="undecodable"):
        parse_porcelain_v2_z(_status_output(b"? \xff"))


def test_parser_orders_file_records_deterministically() -> None:
    first = parse_porcelain_v2_z(
        _status_output(b"? z.md", b"? a.md", b"? docs/b.md")
    )
    second = parse_porcelain_v2_z(
        _status_output(b"? docs/b.md", b"? z.md", b"? a.md")
    )

    assert [item.path for item in first.files] == ["a.md", "docs/b.md", "z.md"]
    assert [item.path for item in first.files] == [item.path for item in second.files]


def test_convert_status_evidence_to_complete_contract_snapshot() -> None:
    status = parse_porcelain_v2_z(
        _status_output(
            b"# branch.oid abc",
            b"# branch.head main",
            b"# branch.upstream origin/main",
            b"? docs/new.md",
            b"1 .M N... 100644 100644 100644 aaaaaa bbbbbb apps/backend/app.py",
        )
    )
    remotes = parse_remote_verbose(
        b"origin\thttps://token@example.com/britbufkin1225-web/hive-mind.git (fetch)\n"
        b"origin\thttps://token@example.com/britbufkin1225-web/hive-mind.git (push)\n"
    )

    snapshot = convert_git_evidence_to_snapshot(
        repository_root=Path("C:/Users/britb/Documents/hive-mind"),
        status=status,
        remotes=remotes,
        observed_at=FIXED_TS,
    )

    assert snapshot.repository_identity.current_branch == "main"
    assert snapshot.repository_identity.current_commit == "abc"
    assert snapshot.repository_identity.remotes[0].url == "https://example.com/britbufkin1225-web/hive-mind.git"
    assert snapshot.repository_identity.primary_remote_url == "example.com/britbufkin1225-web/hive-mind"
    assert snapshot.working_tree.states == [WorkingTreeState.MODIFIED, WorkingTreeState.UNTRACKED]
    assert snapshot.working_tree.unstaged_count == 1
    assert snapshot.working_tree.untracked_count == 1
    assert snapshot.completeness is SnapshotCompleteness.COMPLETE
    assert snapshot.evidence[0].authority == "direct_git_output"
    assert snapshot.limitations[0].category == "metadata_only"


def test_convert_preserves_rename_copy_relationship_validation() -> None:
    status = parse_porcelain_v2_z(
        _status_output(
            b"# branch.oid abc",
            b"# branch.head feature",
            b"2 R. N... 100644 100644 100644 a b R100 docs/new.md",
            b"docs/old.md",
            b"2 C. N... 100644 100644 100644 a b C100 docs/copy.md",
            b"docs/source.md",
        )
    )
    snapshot = convert_git_evidence_to_snapshot(
        repository_root=Path("C:/repo"),
        status=status,
        remotes=(),
        observed_at=FIXED_TS,
    )

    by_kind = {item.change_kind: item for item in snapshot.changed_files}
    assert by_kind[FileChangeKind.RENAMED].path_relationship is not None
    assert by_kind[FileChangeKind.RENAMED].path_relationship.prior_path == "docs/old.md"
    assert by_kind[FileChangeKind.COPIED].path_relationship is not None
    assert by_kind[FileChangeKind.COPIED].path_relationship.prior_path == "docs/source.md"


def test_file_observation_limit_adds_overflow_and_partial_completeness() -> None:
    status = parse_porcelain_v2_z(_status_output(b"? b.md", b"? a.md", b"? c.md"))
    snapshot = convert_git_evidence_to_snapshot(
        repository_root=Path("C:/repo"),
        status=status,
        remotes=(),
        observed_at=FIXED_TS,
        limits=GitAdapterLimits(max_file_observations=2),
    )

    assert [item.repository_relative_path for item in snapshot.changed_files] == ["a.md", "b.md"]
    assert snapshot.omitted_paths == ["c.md"]
    assert snapshot.overflow[0].observed_count == 3
    assert snapshot.overflow[0].omitted_count == 1
    assert snapshot.completeness is SnapshotCompleteness.PARTIAL


def test_output_truncation_adds_overflow_warning_and_partial_completeness() -> None:
    status = parse_porcelain_v2_z(_status_output(b"# branch.oid abc", b"# branch.head main"))
    status_result = GitCommandResult(
        operation=GitReadOperation.STATUS,
        args=READ_ONLY_GIT_COMMANDS[GitReadOperation.STATUS],
        cwd="C:/repo",
        returncode=0,
        stdout=b"# branch.oid abc",
        stderr=b"",
        stdout_truncated=True,
    )
    snapshot = convert_git_evidence_to_snapshot(
        repository_root=Path("C:/repo"),
        status=status,
        remotes=(),
        observed_at=FIXED_TS,
        limits=GitAdapterLimits(stdout_bytes=16),
        status_result=status_result,
    )

    assert snapshot.completeness is SnapshotCompleteness.PARTIAL
    assert snapshot.overflow[0].overflow_id == "overflow-git-status-stdout"
    assert snapshot.overflow[0].limit_kind == "text_bytes"
    assert snapshot.warnings[0].category == "byte_limit_reached"
    assert snapshot.evidence[0].truncation_state == "truncated"


def test_repeated_identical_input_serializes_identically() -> None:
    status = parse_porcelain_v2_z(_status_output(b"# branch.oid abc", b"# branch.head main", b"? a.md"))
    kwargs = {
        "repository_root": Path("C:/repo"),
        "status": status,
        "remotes": (),
        "observed_at": FIXED_TS,
    }

    assert convert_git_evidence_to_snapshot(**kwargs).model_dump(mode="json") == convert_git_evidence_to_snapshot(**kwargs).model_dump(mode="json")


def test_observe_repository_rejects_root_output_truncation() -> None:
    class Executor:
        def run(self, operation: GitReadOperation, repository_root: Path):  # noqa: ANN001
            return GitCommandResult(
                operation=operation,
                args=READ_ONLY_GIT_COMMANDS[operation],
                cwd=str(repository_root),
                returncode=0,
                stdout=b"C:/",
                stderr=b"",
                stdout_truncated=True,
            )

    with pytest.raises(GitOutputLimitExceededError, match="root"):
        observe_repository(repository_path="C:/repo", observed_at=FIXED_TS, executor=Executor())
