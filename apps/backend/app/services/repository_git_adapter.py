"""Phase 37J - deterministic read-only Git adapter.

This module is the backend-only foundation for converting bounded Git CLI
evidence into the Phase 37I ``repo-observer.v1`` contracts. It deliberately adds
no watcher, API route, persistence, filesystem crawler, GitHub integration, or
repository mutation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
from pathlib import Path
import subprocess
from typing import Callable, Iterable, Sequence

from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    FileChangeKind,
    FileContentKind,
    FileObservationCategory,
    FileObservationSummary,
    ObserverLimitation,
    ObserverLimitationCategory,
    ObserverWarning,
    ObserverWarningCategory,
    OverflowLimitKind,
    OverflowMetadata,
    PathRelationship,
    RepositoryEvidence,
    RepositoryIdentity,
    RepositoryIdentityStatus,
    RepositoryOperationState,
    RepositoryRemote,
    RepositorySnapshot,
    SnapshotCompleteness,
    TruncationState,
    WorkingTreeState,
    WorkingTreeStatus,
)


OBSERVER_VERSION = "repo-observer.v1-phase-37j"


@dataclass(frozen=True)
class GitAdapterLimits:
    command_timeout_seconds: float = 5.0
    stdout_bytes: int = 262_144
    stderr_bytes: int = 8_192
    max_file_observations: int = 200
    max_excerpt_chars: int = 512
    max_warning_count: int = 200
    max_limitation_count: int = 200


DEFAULT_GIT_ADAPTER_LIMITS = GitAdapterLimits()


class GitReadOperation(StrEnum):
    RESOLVE_ROOT = "resolve_root"
    STATUS = "status"
    REMOTES = "remotes"


READ_ONLY_GIT_COMMANDS: dict[GitReadOperation, tuple[str, ...]] = {
    GitReadOperation.RESOLVE_ROOT: ("git", "rev-parse", "--show-toplevel"),
    GitReadOperation.STATUS: (
        "git",
        "status",
        "--porcelain=v2",
        "-z",
        "--branch",
        "--untracked-files=all",
    ),
    GitReadOperation.REMOTES: ("git", "remote", "-v"),
}

MUTATING_GIT_SUBCOMMANDS = frozenset(
    {
        "add",
        "commit",
        "checkout",
        "switch",
        "reset",
        "clean",
        "stash",
        "fetch",
        "pull",
        "push",
        "update-index",
        "config",
        "merge",
        "rebase",
        "cherry-pick",
        "am",
        "apply",
        "restore",
        "rm",
        "mv",
    }
)


class RepositoryGitAdapterError(Exception):
    """Base class for bounded, typed adapter failures."""


class GitExecutableUnavailableError(RepositoryGitAdapterError):
    pass


class GitCommandTimeoutError(RepositoryGitAdapterError):
    pass


class GitCommandFailedError(RepositoryGitAdapterError):
    pass


class GitOutputLimitExceededError(RepositoryGitAdapterError):
    pass


class GitPorcelainParseError(RepositoryGitAdapterError):
    pass


@dataclass(frozen=True)
class GitCommandResult:
    operation: GitReadOperation
    args: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool = False
    stderr_truncated: bool = False


@dataclass(frozen=True)
class GitBranchInfo:
    head: str | None = None
    oid: str | None = None
    upstream: str | None = None
    ahead: int | None = None
    behind: int | None = None
    detached: bool = False
    unborn: bool = False


@dataclass(frozen=True)
class GitFileStatus:
    path: str
    change_kind: FileChangeKind
    staged: bool | None
    tracked: bool | None
    index_status: str | None = None
    worktree_status: str | None = None
    prior_path: str | None = None
    copied: bool = False


@dataclass(frozen=True)
class GitStatusEvidence:
    branch: GitBranchInfo
    files: tuple[GitFileStatus, ...]
    warnings: tuple[str, ...] = ()


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class GitCommandExecutor:
    """Allowlisted, bounded, shell-free Git command execution."""

    def __init__(
        self,
        *,
        limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS,
        runner: Runner = subprocess.run,
    ) -> None:
        self._limits = limits
        self._runner = runner
        self._assert_command_set_is_read_only()

    def run(self, operation: GitReadOperation, repository_root: Path) -> GitCommandResult:
        args = READ_ONLY_GIT_COMMANDS[operation]
        cwd = str(repository_root)
        try:
            completed = self._runner(
                args,
                cwd=cwd,
                shell=False,
                capture_output=True,
                timeout=self._limits.command_timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitExecutableUnavailableError("git executable is unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise GitCommandTimeoutError(
                f"git {operation.value} exceeded "
                f"{self._limits.command_timeout_seconds:.1f}s timeout"
            ) from exc
        except OSError as exc:
            raise GitCommandFailedError(
                f"git {operation.value} could not be started"
            ) from exc

        stdout, stdout_truncated = _bounded_bytes(
            completed.stdout or b"", self._limits.stdout_bytes
        )
        stderr, stderr_truncated = _bounded_bytes(
            completed.stderr or b"", self._limits.stderr_bytes
        )
        result = GitCommandResult(
            operation=operation,
            args=args,
            cwd=cwd,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
        if completed.returncode != 0:
            raise GitCommandFailedError(_failure_message(result))
        return result

    @staticmethod
    def _assert_command_set_is_read_only() -> None:
        for args in READ_ONLY_GIT_COMMANDS.values():
            if len(args) < 2 or args[0] != "git":
                raise RepositoryGitAdapterError("Git command set is malformed")
            if args[1] in MUTATING_GIT_SUBCOMMANDS:
                raise RepositoryGitAdapterError(
                    f"Mutating Git command {args[1]!r} is not allowed"
                )


def observe_repository(
    *,
    repository_path: str | Path,
    observed_at: datetime,
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS,
    executor: GitCommandExecutor | None = None,
) -> RepositorySnapshot:
    """Observe one repository through bounded read-only Git commands."""

    target = Path(repository_path)
    command_executor = executor or GitCommandExecutor(limits=limits)
    root_result = command_executor.run(GitReadOperation.RESOLVE_ROOT, target)
    if root_result.stdout_truncated or root_result.stderr_truncated:
        raise GitOutputLimitExceededError("repository root evidence exceeded command bounds")
    root = Path(_decode_text(root_result.stdout, "repository root").strip())
    if not str(root):
        raise GitPorcelainParseError("repository root evidence was empty")

    status_result = command_executor.run(GitReadOperation.STATUS, root)
    remote_result = command_executor.run(GitReadOperation.REMOTES, root)
    status = parse_porcelain_v2_z(status_result.stdout)
    remotes = parse_remote_verbose(remote_result.stdout)

    return convert_git_evidence_to_snapshot(
        repository_root=root,
        status=status,
        remotes=remotes,
        observed_at=observed_at,
        limits=limits,
        status_result=status_result,
        remote_result=remote_result,
    )


def parse_porcelain_v2_z(output: bytes) -> GitStatusEvidence:
    """Parse NUL-delimited ``git status --porcelain=v2 -z --branch`` evidence."""

    if output == b"":
        return GitStatusEvidence(branch=GitBranchInfo(), files=())
    tokens = [token for token in output.split(b"\0") if token]
    branch = GitBranchInfo()
    files: list[GitFileStatus] = []
    warnings: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith(b"# "):
            branch = _parse_branch_header(_decode_text(token, "branch header"), branch)
            index += 1
            continue
        marker = token[:1]
        if marker == b"1":
            files.append(_parse_ordinary_status(token))
            index += 1
            continue
        if marker == b"2":
            if index + 1 >= len(tokens):
                raise GitPorcelainParseError("rename/copy record is missing prior path")
            files.append(_parse_rename_or_copy_status(token, tokens[index + 1]))
            index += 2
            continue
        if marker == b"?":
            files.append(_parse_untracked_status(token))
            index += 1
            continue
        if marker == b"u":
            files.append(_parse_unmerged_status(token))
            index += 1
            continue
        if marker == b"!":
            warnings.append("ignored status record omitted")
            index += 1
            continue
        raise GitPorcelainParseError(
            f"unexpected porcelain-v2 record type {_safe_excerpt(token)!r}"
        )
    return GitStatusEvidence(
        branch=branch,
        files=tuple(_ordered_statuses(files)),
        warnings=tuple(sorted(warnings)),
    )


def parse_remote_verbose(output: bytes) -> tuple[RepositoryRemote, ...]:
    remotes: dict[tuple[str, str], RepositoryRemote] = {}
    text = _decode_text(output, "remote output")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3 or parts[2] not in ("(fetch)", "(push)"):
            continue
        name, url, direction = parts[0], parts[1], parts[2]
        if direction != "(fetch)":
            continue
        remotes[(name, url)] = RepositoryRemote(
            name=name,
            url=_redact_remote_url(url),
            normalized_url=_normalize_remote_url(url),
        )
    return tuple(
        remotes[key]
        for key in sorted(remotes, key=lambda item: (item[0].casefold(), item[1]))
    )


def convert_git_evidence_to_snapshot(
    *,
    repository_root: Path,
    status: GitStatusEvidence,
    remotes: Sequence[RepositoryRemote],
    observed_at: datetime,
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS,
    status_result: GitCommandResult | None = None,
    remote_result: GitCommandResult | None = None,
) -> RepositorySnapshot:
    root_text = _normalize_root(repository_root)
    repository_name = repository_root.name or root_text.rsplit("/", 1)[-1]
    primary_remote = _primary_remote(remotes)
    retained_files, overflow = _bounded_file_observations(status.files, limits)
    overflow.extend(_output_overflow(status_result, remote_result, limits))
    warnings = _warnings_for(status, status_result, remote_result, overflow, limits)
    limitations = _default_limitations(limits)
    evidence = _status_evidence(status_result, remote_result, observed_at, limits)
    operation_state = _operation_state(status.branch)
    working_tree = _working_tree_status(retained_files, overflow)
    completeness = (
        SnapshotCompleteness.PARTIAL
        if overflow or any(item.truncated for item in overflow)
        else SnapshotCompleteness.COMPLETE
    )
    identity = RepositoryIdentity(
        repository_id=_repository_id(primary_remote, root_text),
        canonical_root=str(repository_root),
        normalized_root=root_text,
        repository_name=repository_name,
        remotes=list(remotes),
        primary_remote_url=primary_remote.normalized_url if primary_remote else None,
        current_branch=None
        if status.branch.detached or status.branch.unborn
        else status.branch.head,
        current_commit=None if status.branch.unborn else status.branch.oid,
        upstream_reference=status.branch.upstream,
        operation_state=operation_state,
        status=RepositoryIdentityStatus.VERIFIED,
        warning_ids=[warning.warning_id for warning in warnings],
    )
    changed_files = [_file_summary(item) for item in retained_files]
    return RepositorySnapshot(
        snapshot_id=_stable_id("snapshot", root_text, observed_at.isoformat()),
        repository_identity=identity,
        observed_at=observed_at,
        observer_version=OBSERVER_VERSION,
        branch=identity.current_branch,
        commit=identity.current_commit,
        working_tree=working_tree,
        changed_files=changed_files,
        evidence=evidence,
        warnings=warnings,
        limitations=limitations,
        omitted_paths=[
            item.path
            for item in status.files
            if item not in retained_files
        ],
        overflow=overflow,
        completeness=completeness,
        read_only=True,
    )


def _parse_branch_header(raw: str, current: GitBranchInfo) -> GitBranchInfo:
    parts = raw.split()
    if len(parts) < 3:
        raise GitPorcelainParseError("malformed branch header")
    key = parts[1]
    value = " ".join(parts[2:])
    if key == "branch.oid":
        return GitBranchInfo(
            head=current.head,
            oid=None if value == "(initial)" else value,
            upstream=current.upstream,
            ahead=current.ahead,
            behind=current.behind,
            detached=current.detached,
            unborn=value == "(initial)",
        )
    if key == "branch.head":
        detached = value == "(detached)"
        return GitBranchInfo(
            head=None if detached else value,
            oid=current.oid,
            upstream=current.upstream,
            ahead=current.ahead,
            behind=current.behind,
            detached=detached,
            unborn=current.unborn,
        )
    if key == "branch.upstream":
        return GitBranchInfo(
            head=current.head,
            oid=current.oid,
            upstream=value,
            ahead=current.ahead,
            behind=current.behind,
            detached=current.detached,
            unborn=current.unborn,
        )
    if key == "branch.ab":
        ahead, behind = _parse_ahead_behind(parts[2:])
        return GitBranchInfo(
            head=current.head,
            oid=current.oid,
            upstream=current.upstream,
            ahead=ahead,
            behind=behind,
            detached=current.detached,
            unborn=current.unborn,
        )
    return current


def _parse_ahead_behind(parts: Sequence[str]) -> tuple[int | None, int | None]:
    ahead: int | None = None
    behind: int | None = None
    for part in parts:
        if part.startswith("+"):
            ahead = int(part[1:])
        elif part.startswith("-"):
            behind = int(part[1:])
    return ahead, behind


def _parse_ordinary_status(token: bytes) -> GitFileStatus:
    text = _decode_text(token, "ordinary status")
    fields = text.split(" ", 8)
    if len(fields) != 9 or fields[0] != "1" or len(fields[1]) != 2:
        raise GitPorcelainParseError("malformed ordinary status record")
    return _status_from_xy(fields[8], fields[1][0], fields[1][1])


def _parse_rename_or_copy_status(token: bytes, prior_path: bytes) -> GitFileStatus:
    text = _decode_text(token, "rename/copy status")
    fields = text.split(" ", 9)
    if len(fields) != 10 or fields[0] != "2" or len(fields[1]) != 2:
        raise GitPorcelainParseError("malformed rename/copy status record")
    score = fields[8]
    if not score or score[0] not in ("R", "C"):
        raise GitPorcelainParseError("rename/copy status record lacks relationship marker")
    current_path = _safe_relative_path(fields[9])
    prior = _safe_relative_path(_decode_text(prior_path, "prior path"))
    kind = FileChangeKind.RENAMED if score[0] == "R" else FileChangeKind.COPIED
    return GitFileStatus(
        path=current_path,
        change_kind=kind,
        staged=True,
        tracked=True,
        index_status=fields[1][0],
        worktree_status=fields[1][1],
        prior_path=prior,
        copied=kind is FileChangeKind.COPIED,
    )


def _parse_untracked_status(token: bytes) -> GitFileStatus:
    text = _decode_text(token, "untracked status")
    if not text.startswith("? "):
        raise GitPorcelainParseError("malformed untracked status record")
    return GitFileStatus(
        path=_safe_relative_path(text[2:]),
        change_kind=FileChangeKind.UNTRACKED,
        staged=False,
        tracked=False,
        index_status=None,
        worktree_status="?",
    )


def _parse_unmerged_status(token: bytes) -> GitFileStatus:
    text = _decode_text(token, "unmerged status")
    fields = text.split(" ", 10)
    if len(fields) != 11 or fields[0] != "u" or len(fields[1]) != 2:
        raise GitPorcelainParseError("malformed unmerged status record")
    return GitFileStatus(
        path=_safe_relative_path(fields[10]),
        change_kind=FileChangeKind.CONFLICTED,
        staged=True,
        tracked=True,
        index_status=fields[1][0],
        worktree_status=fields[1][1],
    )


def _status_from_xy(path: str, index_status: str, worktree_status: str) -> GitFileStatus:
    path = _safe_relative_path(path)
    if index_status != ".":
        return GitFileStatus(
            path=path,
            change_kind=_change_kind(index_status),
            staged=True,
            tracked=True,
            index_status=index_status,
            worktree_status=worktree_status,
        )
    return GitFileStatus(
        path=path,
        change_kind=_change_kind(worktree_status),
        staged=False,
        tracked=True,
        index_status=index_status,
        worktree_status=worktree_status,
    )


def _change_kind(status: str) -> FileChangeKind:
    return {
        "A": FileChangeKind.ADDED,
        "M": FileChangeKind.MODIFIED,
        "D": FileChangeKind.DELETED,
        "R": FileChangeKind.RENAMED,
        "C": FileChangeKind.COPIED,
        "U": FileChangeKind.CONFLICTED,
        "?": FileChangeKind.UNTRACKED,
        ".": FileChangeKind.UNKNOWN,
    }.get(status, FileChangeKind.UNKNOWN)


def _working_tree_status(
    files: Sequence[GitFileStatus], overflow: Sequence[OverflowMetadata]
) -> WorkingTreeStatus:
    if not files and not overflow:
        return WorkingTreeStatus(states=[WorkingTreeState.CLEAN])
    staged = sum(1 for item in files if item.staged)
    unstaged = sum(
        1
        for item in files
        if item.tracked and not item.staged and item.change_kind is not FileChangeKind.UNTRACKED
    )
    untracked = sum(1 for item in files if item.change_kind is FileChangeKind.UNTRACKED)
    conflicted = sum(1 for item in files if item.change_kind is FileChangeKind.CONFLICTED)
    states: list[WorkingTreeState] = []
    if staged:
        states.append(WorkingTreeState.STAGED)
    if unstaged:
        states.append(WorkingTreeState.MODIFIED)
    if untracked:
        states.append(WorkingTreeState.UNTRACKED)
    if conflicted:
        states.append(WorkingTreeState.CONFLICTED)
    if overflow and not states:
        states.append(WorkingTreeState.UNKNOWN)
    return WorkingTreeStatus(
        states=states or [WorkingTreeState.UNKNOWN],
        staged_count=staged,
        unstaged_count=unstaged,
        untracked_count=untracked,
        conflicted_count=conflicted,
    )


def _file_summary(status: GitFileStatus) -> FileObservationSummary:
    relationship = None
    if status.prior_path is not None:
        relationship = PathRelationship(
            change_kind=status.change_kind,
            prior_path=status.prior_path,
            current_path=status.path,
        )
    return FileObservationSummary(
        file_id=_stable_id("file", status.path, status.change_kind.value),
        repository_relative_path=status.path,
        normalized_path=status.path,
        change_kind=status.change_kind,
        observation_category=FileObservationCategory.GIT_STATUS,
        content_kind=FileContentKind.UNKNOWN,
        tracked=status.tracked,
        staged=status.staged,
        path_relationship=relationship,
        evidence_ids=["evidence-git-status"],
    )


def _bounded_file_observations(
    files: Sequence[GitFileStatus], limits: GitAdapterLimits
) -> tuple[list[GitFileStatus], list[OverflowMetadata]]:
    ordered = _ordered_statuses(files)
    retained = ordered[: limits.max_file_observations]
    if len(ordered) <= limits.max_file_observations:
        return retained, []
    omitted = len(ordered) - len(retained)
    return retained, [
        OverflowMetadata(
            overflow_id="overflow-file-observations",
            limit_kind=OverflowLimitKind.FILE_COUNT,
            truncated=True,
            configured_limit=limits.max_file_observations,
            observed_count=len(ordered),
            retained_count=len(retained),
            omitted_count=omitted,
            deterministic_cutoff="first N paths by normalized path",
            snapshot_partial=True,
        )
    ]


def _output_overflow(
    status_result: GitCommandResult | None,
    remote_result: GitCommandResult | None,
    limits: GitAdapterLimits,
) -> list[OverflowMetadata]:
    overflow: list[OverflowMetadata] = []
    for result, evidence_id in (
        (status_result, "git-status"),
        (remote_result, "git-remotes"),
    ):
        if result is None:
            continue
        if result.stdout_truncated:
            overflow.append(
                OverflowMetadata(
                    overflow_id=f"overflow-{evidence_id}-stdout",
                    limit_kind=OverflowLimitKind.TEXT_BYTES,
                    truncated=True,
                    configured_limit=limits.stdout_bytes,
                    observed_size_bytes=None,
                    retained_count=len(result.stdout),
                    deterministic_cutoff="first N stdout bytes",
                    snapshot_partial=True,
                )
            )
        if result.stderr_truncated:
            overflow.append(
                OverflowMetadata(
                    overflow_id=f"overflow-{evidence_id}-stderr",
                    limit_kind=OverflowLimitKind.TEXT_BYTES,
                    truncated=True,
                    configured_limit=limits.stderr_bytes,
                    observed_size_bytes=None,
                    retained_count=len(result.stderr),
                    deterministic_cutoff="first N stderr bytes",
                    snapshot_partial=True,
                )
            )
    return sorted(overflow, key=lambda item: item.overflow_id)


def _warnings_for(
    status: GitStatusEvidence,
    status_result: GitCommandResult | None,
    remote_result: GitCommandResult | None,
    overflow: Sequence[OverflowMetadata],
    limits: GitAdapterLimits,
) -> list[ObserverWarning]:
    warnings: list[ObserverWarning] = []
    if status.branch.detached:
        warnings.append(
            ObserverWarning(
                warning_id="warning-detached-head",
                category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
                summary="Repository HEAD is detached; branch-specific metadata is unavailable.",
            )
        )
    if status.branch.unborn:
        warnings.append(
            ObserverWarning(
                warning_id="warning-unborn-branch",
                category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
                summary="Repository is on an unborn initial branch with no current commit.",
            )
        )
    if status.branch.upstream is None:
        warnings.append(
            ObserverWarning(
                warning_id="warning-missing-upstream",
                category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
                summary="Git status did not report upstream branch metadata.",
            )
        )
    for raw in status.warnings:
        warnings.append(
            ObserverWarning(
                warning_id=_stable_id("warning", raw),
                category=ObserverWarningCategory.OBSERVER_CAPABILITY_UNAVAILABLE,
                summary=raw,
            )
        )
    if status_result is not None and status_result.stdout_truncated:
        warnings.append(
            ObserverWarning(
                warning_id="warning-status-stdout-truncated",
                category=ObserverWarningCategory.BYTE_LIMIT_REACHED,
                summary="Git status stdout exceeded the configured byte limit.",
                evidence_ids=["evidence-git-status"],
            )
        )
    if remote_result is not None and remote_result.stdout_truncated:
        warnings.append(
            ObserverWarning(
                warning_id="warning-remotes-stdout-truncated",
                category=ObserverWarningCategory.BYTE_LIMIT_REACHED,
                summary="Git remote stdout exceeded the configured byte limit.",
                evidence_ids=["evidence-git-remotes"],
            )
        )
    if overflow:
        warnings.append(
            ObserverWarning(
                warning_id="warning-file-limit-reached",
                category=ObserverWarningCategory.FILE_LIMIT_REACHED,
                summary="Changed-file observation count exceeded the configured limit.",
            )
        )
    return _ordered_warnings(warnings)[: limits.max_warning_count]


def _default_limitations(limits: GitAdapterLimits) -> list[ObserverLimitation]:
    return [
        ObserverLimitation(
            limitation_id="limitation-metadata-only",
            category=ObserverLimitationCategory.METADATA_ONLY,
            summary="Phase 37J uses Git metadata only and does not read file contents.",
        ),
        ObserverLimitation(
            limitation_id="limitation-bounded-git-output",
            category=ObserverLimitationCategory.BOUNDED_COLLECTION,
            summary=(
                "Git command output and file observations are bounded by "
                f"{limits.stdout_bytes} stdout bytes, {limits.stderr_bytes} stderr bytes, "
                f"and {limits.max_file_observations} file observations."
            ),
        ),
    ][: limits.max_limitation_count]


def _status_evidence(
    status_result: GitCommandResult | None,
    remote_result: GitCommandResult | None,
    observed_at: datetime,
    limits: GitAdapterLimits,
) -> list[RepositoryEvidence]:
    evidence = [
        RepositoryEvidence(
            evidence_id="evidence-git-status",
            category=EvidenceCategory.GIT_METADATA,
            authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
            source="git status --porcelain=v2 -z --branch --untracked-files=all",
            summary="Bounded porcelain-v2 Git status output.",
            bounded_excerpt=_command_excerpt(status_result, limits),
            excerpt_limit=limits.max_excerpt_chars,
            captured_at=observed_at,
            truncation_state=_truncation_state(status_result),
        ),
        RepositoryEvidence(
            evidence_id="evidence-git-remotes",
            category=EvidenceCategory.GIT_METADATA,
            authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
            source="git remote -v",
            summary="Bounded Git remote listing output.",
            bounded_excerpt=_command_excerpt(remote_result, limits),
            excerpt_limit=limits.max_excerpt_chars,
            captured_at=observed_at,
            truncation_state=_truncation_state(remote_result),
        ),
    ]
    return evidence


def _command_excerpt(
    result: GitCommandResult | None, limits: GitAdapterLimits
) -> str:
    if result is None:
        return ""
    return _safe_excerpt(result.stdout, limits.max_excerpt_chars)


def _truncation_state(result: GitCommandResult | None) -> TruncationState:
    if result is not None and (result.stdout_truncated or result.stderr_truncated):
        return TruncationState.TRUNCATED
    return TruncationState.NOT_TRUNCATED


def _bounded_bytes(raw: bytes, limit: int) -> tuple[bytes, bool]:
    if len(raw) <= limit:
        return raw, False
    return raw[:limit], True


def _failure_message(result: GitCommandResult) -> str:
    stderr = _safe_excerpt(result.stderr, 240)
    return (
        f"git {result.operation.value} exited with {result.returncode}"
        + (f": {stderr}" if stderr else "")
    )


def _decode_text(raw: bytes, label: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitPorcelainParseError(f"{label} contained undecodable UTF-8") from exc


def _safe_excerpt(raw: bytes, limit: int = 120) -> str:
    text = raw.decode("utf-8", errors="replace")
    safe = "".join(ch if ch >= " " and ch != "\x7f" else " " for ch in text)
    return " ".join(safe.split())[:limit]


def _safe_relative_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if (
        not normalized
        or normalized.startswith("/")
        or normalized.startswith("//")
        or (len(normalized) >= 2 and normalized[1] == ":")
    ):
        raise GitPorcelainParseError("unsafe repository-relative path")
    parts = [part for part in normalized.split("/") if part]
    if any(part in ("..", ".") for part in parts):
        raise GitPorcelainParseError("unsafe repository-relative path")
    return "/".join(parts)


def _ordered_statuses(files: Iterable[GitFileStatus]) -> list[GitFileStatus]:
    return sorted(
        files,
        key=lambda item: (
            item.path.casefold(),
            item.change_kind.value,
            item.prior_path or "",
            item.index_status or "",
            item.worktree_status or "",
        ),
    )


def _ordered_warnings(warnings: Iterable[ObserverWarning]) -> list[ObserverWarning]:
    return sorted(
        warnings,
        key=lambda warning: (warning.category.value, warning.warning_id),
    )


def _operation_state(branch: GitBranchInfo) -> RepositoryOperationState:
    if branch.detached:
        return RepositoryOperationState.DETACHED
    return RepositoryOperationState.NORMAL


def _normalize_root(root: Path) -> str:
    return str(root).replace("\\", "/").casefold()


def _primary_remote(remotes: Sequence[RepositoryRemote]) -> RepositoryRemote | None:
    for remote in remotes:
        if remote.name == "origin":
            return remote
    return remotes[0] if remotes else None


def _repository_id(primary_remote: RepositoryRemote | None, normalized_root: str) -> str:
    basis = primary_remote.normalized_url if primary_remote else normalized_root
    return _stable_id("repo", basis or normalized_root)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _redact_remote_url(url: str) -> str:
    if "://" not in url or "@" not in url.split("://", 1)[1].split("/", 1)[0]:
        return url
    scheme, rest = url.split("://", 1)
    host_and_path = rest.split("@", 1)[1]
    return f"{scheme}://{host_and_path}"


def _normalize_remote_url(url: str) -> str:
    redacted = _redact_remote_url(url).strip()
    if redacted.startswith("git@") and ":" in redacted:
        host, path = redacted[4:].split(":", 1)
        redacted = f"{host}/{path}"
    elif "://" in redacted:
        redacted = redacted.split("://", 1)[1]
    if redacted.endswith(".git"):
        redacted = redacted[:-4]
    return redacted.rstrip("/").casefold()
