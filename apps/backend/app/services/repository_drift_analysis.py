"""Phase 37O - deterministic repository drift analysis service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Sequence

from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    FileChangeKind,
    ObserverLimitation,
    ObserverLimitationCategory,
    ObserverWarning,
    ObserverWarningCategory,
    OverflowLimitKind,
    OverflowMetadata,
    RepositoryDriftAnalysis,
    RepositoryDriftFile,
    RepositoryDriftStatus,
    RepositoryDriftSummary,
    RepositoryEvidence,
    SnapshotCompleteness,
    TruncationState,
)
from app.services.repository_git_adapter import (
    DEFAULT_GIT_ADAPTER_LIMITS,
    GitAdapterLimits,
    GitCommandExecutor,
    GitFileStatus,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
    GitReadOperation,
    convert_git_evidence_to_snapshot,
    git_file_status_has_staged_change,
    git_file_status_has_unstaged_change,
    git_file_status_is_untracked,
    parse_porcelain_v2_z,
    parse_remote_verbose,
)


REPOSITORY_DRIFT_ANALYSIS_SERVICE_VERSION = "repo-observer.v1-phase-37o"
SUPPORTED_BASELINE_REFERENCE = "HEAD"


class RepositoryDriftAnalysisError(Exception):
    """Base class for bounded drift-analysis failures."""


class RepositoryDriftBaselineError(RepositoryDriftAnalysisError):
    """Raised when the requested baseline is unsupported."""


class RepositoryDriftPathError(RepositoryDriftAnalysisError):
    """Raised when the requested repository path is unsafe."""


@dataclass(frozen=True)
class RepositoryDriftAnalysisRequest:
    repository_path: str | Path
    observed_at: datetime
    baseline_reference: str = SUPPORTED_BASELINE_REFERENCE
    max_file_count: int = 200
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS
    executor: GitCommandExecutor | None = None


class RepositoryDriftAnalysisService:
    """Assemble one deterministic, read-only drift analysis from Git evidence."""

    def analyze(self, request: RepositoryDriftAnalysisRequest) -> RepositoryDriftAnalysis:
        baseline_reference = _normalize_baseline_reference(request.baseline_reference)
        _validate_repository_path(request.repository_path)
        limits = GitAdapterLimits(
            command_timeout_seconds=request.limits.command_timeout_seconds,
            stdout_bytes=request.limits.stdout_bytes,
            stderr_bytes=request.limits.stderr_bytes,
            max_file_observations=request.max_file_count,
            max_excerpt_chars=request.limits.max_excerpt_chars,
            max_warning_count=request.limits.max_warning_count,
            max_limitation_count=request.limits.max_limitation_count,
        )
        executor = request.executor or GitCommandExecutor(limits=limits)

        target = Path(request.repository_path)
        root_result = executor.run(GitReadOperation.RESOLVE_ROOT, target)
        if root_result.stdout_truncated or root_result.stderr_truncated:
            raise GitOutputLimitExceededError("repository root evidence exceeded command bounds")
        root = Path(_decode_root(root_result.stdout))

        status_result = executor.run(GitReadOperation.STATUS, root)
        remote_result = executor.run(GitReadOperation.REMOTES, root)
        status = parse_porcelain_v2_z(
            status_result.stdout,
            output_complete=not status_result.stdout_truncated,
        )
        remotes = parse_remote_verbose(remote_result.stdout)
        snapshot = convert_git_evidence_to_snapshot(
            repository_root=root,
            status=status,
            remotes=remotes,
            observed_at=request.observed_at,
            limits=limits,
            status_result=status_result,
            remote_result=remote_result,
            observer_version=REPOSITORY_DRIFT_ANALYSIS_SERVICE_VERSION,
        )

        evidence = [
            _baseline_evidence(
                baseline_reference=baseline_reference,
                baseline_commit_hash=status.branch.oid,
                observed_at=request.observed_at,
            ),
            *snapshot.evidence,
        ]
        warnings = list(snapshot.warnings)
        limitations = [
            *snapshot.limitations,
            ObserverLimitation(
                limitation_id="limitation-head-baseline-only",
                category=ObserverLimitationCategory.UNSUPPORTED_DATA,
                summary="Phase 37O supports only the current HEAD baseline and does not browse arbitrary commit history.",
            ),
        ][: limits.max_limitation_count]

        if status.branch.unborn or not status.branch.oid:
            warnings.append(
                ObserverWarning(
                    warning_id="warning-baseline-head-unavailable",
                    category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
                    summary="The repository has no HEAD commit, so deterministic drift from HEAD is unavailable.",
                    evidence_ids=["evidence-baseline-head"],
                )
            )
            return _analysis(
                root=root,
                repository_identity=snapshot.repository_identity,
                observed_at=request.observed_at,
                baseline_reference=baseline_reference,
                baseline_commit_hash=None,
                status=RepositoryDriftStatus.UNSUPPORTED,
                files=[],
                total_count=0,
                evidence=evidence,
                warnings=_ordered_warnings(warnings),
                limitations=limitations,
                omitted_paths=[],
                # An unborn repository yields an UNSUPPORTED result with no drift
                # files and total_changed_files == 0. Snapshot-observation overflow
                # (partial file-count/byte truncation) describes a snapshot we do
                # not surface here; forwarding it both contradicts the zero-file
                # summary and violates the model's "partial overflow requires
                # PARTIAL completeness" invariant (with UNAVAILABLE completeness).
                # The truncation/limit signal remains reported via the forwarded
                # snapshot warnings.
                overflow=[],
                completeness=SnapshotCompleteness.UNAVAILABLE,
            )

        retained, overflow, omitted_paths = _bounded_drift_files(status.files, limits)
        merged_overflow = _ordered_overflow([*snapshot.overflow, *overflow])
        completeness = (
            SnapshotCompleteness.PARTIAL if merged_overflow else SnapshotCompleteness.COMPLETE
        )
        drift_status = (
            RepositoryDriftStatus.PARTIAL
            if merged_overflow
            else RepositoryDriftStatus.DRIFTED
            if status.files
            else RepositoryDriftStatus.CLEAN
        )
        if any(item.limit_kind is OverflowLimitKind.FILE_COUNT for item in overflow):
            warnings.append(
                ObserverWarning(
                    warning_id="warning-drift-file-limit-reached",
                    category=ObserverWarningCategory.FILE_LIMIT_REACHED,
                    summary="Drift file count exceeded the configured limit.",
                    evidence_ids=["evidence-git-status"],
                )
            )

        return _analysis(
            root=root,
            repository_identity=snapshot.repository_identity,
            observed_at=request.observed_at,
            baseline_reference=baseline_reference,
            baseline_commit_hash=status.branch.oid,
            status=drift_status,
            files=retained,
            total_count=len(status.files),
            evidence=evidence,
            warnings=_ordered_warnings(warnings),
            limitations=limitations,
            omitted_paths=omitted_paths,
            overflow=merged_overflow,
            completeness=completeness,
        )


def analyze_repository_drift(
    *,
    repository_path: str | Path,
    observed_at: datetime,
    baseline_reference: str = SUPPORTED_BASELINE_REFERENCE,
    max_file_count: int = 200,
    limits: GitAdapterLimits = DEFAULT_GIT_ADAPTER_LIMITS,
    executor: GitCommandExecutor | None = None,
) -> RepositoryDriftAnalysis:
    """Analyze deterministic drift from the supported local Git baseline."""

    request = RepositoryDriftAnalysisRequest(
        repository_path=repository_path,
        observed_at=observed_at,
        baseline_reference=baseline_reference,
        max_file_count=max_file_count,
        limits=limits,
        executor=executor,
    )
    return RepositoryDriftAnalysisService().analyze(request)


def _normalize_baseline_reference(value: str) -> str:
    if not value or not value.strip():
        raise RepositoryDriftBaselineError("baseline_reference must not be empty")
    normalized = value.strip()
    if normalized != SUPPORTED_BASELINE_REFERENCE:
        raise RepositoryDriftBaselineError("only the HEAD baseline is supported")
    return normalized


def _validate_repository_path(value: str | Path) -> None:
    text = str(value).strip()
    if not text or "\x00" in text:
        raise RepositoryDriftPathError("repository_path is malformed")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text)
    if not (windows.is_absolute() or posix.is_absolute()):
        raise RepositoryDriftPathError("repository_path must be an absolute local path")
    if ".." in set(windows.parts) or ".." in set(posix.parts):
        raise RepositoryDriftPathError("repository_path must not traverse parents")


def _baseline_evidence(
    *,
    baseline_reference: str,
    baseline_commit_hash: str | None,
    observed_at: datetime,
) -> RepositoryEvidence:
    summary = (
        f"Resolved supported baseline {baseline_reference} to current HEAD commit."
        if baseline_commit_hash
        else f"Supported baseline {baseline_reference} could not be resolved to a commit."
    )
    return RepositoryEvidence(
        evidence_id="evidence-baseline-head",
        category=EvidenceCategory.GIT_METADATA,
        authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
        source="git status --porcelain=v2 -z --branch",
        summary=summary,
        bounded_excerpt=(baseline_commit_hash or "(initial)"),
        excerpt_limit=512,
        captured_at=observed_at,
        truncation_state=TruncationState.NOT_TRUNCATED,
    )


def _bounded_drift_files(
    statuses: Sequence[GitFileStatus], limits: GitAdapterLimits
) -> tuple[list[RepositoryDriftFile], list[OverflowMetadata], list[str]]:
    ordered = [_drift_file(item) for item in statuses]
    retained = ordered[: limits.max_file_observations]
    if len(ordered) <= limits.max_file_observations:
        return retained, [], []
    omitted = ordered[limits.max_file_observations :]
    return retained, [
        OverflowMetadata(
            overflow_id="overflow-drift-files",
            limit_kind=OverflowLimitKind.FILE_COUNT,
            truncated=True,
            configured_limit=limits.max_file_observations,
            observed_count=len(ordered),
            retained_count=len(retained),
            omitted_count=len(omitted),
            deterministic_cutoff="first N paths by normalized path",
            snapshot_partial=True,
        )
    ], [item.current_path for item in omitted]


def _drift_file(status: GitFileStatus) -> RepositoryDriftFile:
    staged = git_file_status_has_staged_change(status)
    unstaged = git_file_status_has_unstaged_change(status)
    untracked = git_file_status_is_untracked(status)
    return RepositoryDriftFile(
        file_id=_stable_id(
            "drift-file",
            status.path,
            status.change_kind.value,
            status.prior_path or "",
            status.index_status or "",
            status.worktree_status or "",
        ),
        change_kind=status.change_kind,
        old_path=status.prior_path,
        current_path=status.path,
        normalized_path=status.path,
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        tracked=status.tracked,
        evidence_ids=["evidence-baseline-head", "evidence-git-status"],
    )


def _analysis(
    *,
    root: Path,
    repository_identity,  # noqa: ANN001
    observed_at: datetime,
    baseline_reference: str,
    baseline_commit_hash: str | None,
    status: RepositoryDriftStatus,
    files: list[RepositoryDriftFile],
    total_count: int,
    evidence: list[RepositoryEvidence],
    warnings: list[ObserverWarning],
    limitations: list[ObserverLimitation],
    omitted_paths: list[str],
    overflow: list[OverflowMetadata],
    completeness: SnapshotCompleteness,
) -> RepositoryDriftAnalysis:
    return RepositoryDriftAnalysis(
        drift_id=_stable_id(
            "drift",
            _normalize_root(root),
            baseline_reference,
            baseline_commit_hash or "none",
            observed_at.isoformat(),
        ),
        repository_identity=repository_identity,
        observed_at=observed_at,
        observer_version=REPOSITORY_DRIFT_ANALYSIS_SERVICE_VERSION,
        baseline_reference=baseline_reference,
        baseline_commit_hash=baseline_commit_hash,
        drift_status=status,
        summary=_summary(files, total_count),
        files=files,
        evidence=evidence,
        warnings=warnings,
        limitations=limitations,
        omitted_paths=omitted_paths,
        overflow=overflow,
        completeness=completeness,
        read_only=True,
    )


def _summary(files: Sequence[RepositoryDriftFile], total_count: int) -> RepositoryDriftSummary:
    return RepositoryDriftSummary(
        total_changed_files=total_count,
        retained_file_count=len(files),
        staged_count=sum(1 for item in files if item.staged),
        unstaged_count=sum(1 for item in files if item.unstaged),
        untracked_count=sum(1 for item in files if item.untracked),
        conflicted_count=sum(1 for item in files if item.change_kind is FileChangeKind.CONFLICTED),
        added_count=sum(1 for item in files if item.change_kind is FileChangeKind.ADDED),
        modified_count=sum(1 for item in files if item.change_kind is FileChangeKind.MODIFIED),
        deleted_count=sum(1 for item in files if item.change_kind is FileChangeKind.DELETED),
        renamed_count=sum(1 for item in files if item.change_kind is FileChangeKind.RENAMED),
        copied_count=sum(1 for item in files if item.change_kind is FileChangeKind.COPIED),
        type_changed_count=sum(1 for item in files if item.change_kind is FileChangeKind.TYPE_CHANGED),
        unknown_count=sum(1 for item in files if item.change_kind is FileChangeKind.UNKNOWN),
    )


def _ordered_warnings(warnings: Sequence[ObserverWarning]) -> list[ObserverWarning]:
    return sorted(warnings, key=lambda item: (item.category.value, item.warning_id))


def _ordered_overflow(overflow: Sequence[OverflowMetadata]) -> list[OverflowMetadata]:
    return sorted(overflow, key=lambda item: (item.limit_kind.value, item.overflow_id))


def _decode_root(stdout: bytes) -> str:
    try:
        root_text = stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise GitPorcelainParseError("repository root contained undecodable UTF-8") from exc
    if not root_text:
        raise GitPorcelainParseError("repository root evidence was empty")
    return root_text


def _normalize_root(root: Path) -> str:
    return str(root).replace("\\", "/").casefold()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
