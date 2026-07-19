"""Phase 37O - deterministic repository drift analysis service tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pytest

from app.models.repository_observer import (
    FileChangeKind,
    RepositoryDriftStatus,
    SnapshotCompleteness,
)
from app.services.repository_drift_analysis import (
    REPOSITORY_DRIFT_ANALYSIS_SERVICE_VERSION,
    RepositoryDriftBaselineError,
    RepositoryDriftPathError,
    analyze_repository_drift,
)
from app.services.repository_git_adapter import (
    GitAdapterLimits,
    GitCommandFailedError,
    MUTATING_GIT_SUBCOMMANDS,
    READ_ONLY_GIT_COMMANDS,
)


FIXED_TS = datetime(2026, 7, 19, 12, 0, 0)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], shell=False, check=True, capture_output=True)
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "config", "user.name", "Test User")
    _write(repo / "README.md", "hello\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_clean_repository_reports_no_drift(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")

    drift = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)

    assert drift.observer_version == REPOSITORY_DRIFT_ANALYSIS_SERVICE_VERSION
    assert drift.baseline_reference == "HEAD"
    assert drift.baseline_commit_hash == head
    assert drift.drift_status is RepositoryDriftStatus.CLEAN
    assert drift.summary.total_changed_files == 0
    assert drift.files == []
    assert drift.completeness is SnapshotCompleteness.COMPLETE
    assert drift.read_only is True


def test_modified_staged_mixed_deleted_untracked_and_added_files(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / "README.md", "hello changed\n")
    _write(repo / "staged.md", "staged\n")
    _git(repo, "add", "staged.md")
    _write(repo / "mixed.md", "mixed staged\n")
    _git(repo, "add", "mixed.md")
    _write(repo / "mixed.md", "mixed staged plus unstaged\n")
    (repo / "README.md").unlink()
    _write(repo / "loose.md", "untracked\n")

    drift = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)
    by_path = {item.current_path: item for item in drift.files}

    assert drift.drift_status is RepositoryDriftStatus.DRIFTED
    assert by_path["README.md"].change_kind is FileChangeKind.DELETED
    assert by_path["README.md"].unstaged is True
    assert by_path["staged.md"].change_kind is FileChangeKind.ADDED
    assert by_path["staged.md"].staged is True
    assert by_path["mixed.md"].change_kind is FileChangeKind.ADDED
    assert by_path["mixed.md"].staged is True
    assert by_path["mixed.md"].unstaged is True
    assert by_path["loose.md"].change_kind is FileChangeKind.UNTRACKED
    assert by_path["loose.md"].untracked is True
    assert drift.summary.staged_count == 2
    assert drift.summary.unstaged_count == 2
    assert drift.summary.untracked_count == 1


def test_modified_tracked_file_and_staged_tracked_file_are_distinct(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / "README.md", "unstaged change\n")

    unstaged = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)
    assert unstaged.files[0].change_kind is FileChangeKind.MODIFIED
    assert unstaged.files[0].unstaged is True
    assert unstaged.files[0].staged is False

    _git(repo, "add", "README.md")
    staged = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)
    assert staged.files[0].change_kind is FileChangeKind.MODIFIED
    assert staged.files[0].staged is True
    assert staged.files[0].unstaged is False


def test_rename_uses_authoritative_git_status_relationship(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "mv", "README.md", "README-renamed.md")

    drift = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)

    assert len(drift.files) == 1
    renamed = drift.files[0]
    assert renamed.change_kind is FileChangeKind.RENAMED
    assert renamed.old_path == "README.md"
    assert renamed.current_path == "README-renamed.md"
    assert renamed.staged is True


def test_drift_output_is_ordered_limited_and_reports_overflow(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / "z.md", "z\n")
    _write(repo / "a.md", "a\n")
    _write(repo / "docs" / "b.md", "b\n")

    drift = analyze_repository_drift(
        repository_path=repo,
        observed_at=FIXED_TS,
        max_file_count=2,
        limits=GitAdapterLimits(max_file_observations=2),
    )

    assert [item.current_path for item in drift.files] == ["a.md", "docs/b.md"]
    assert drift.omitted_paths == ["z.md"]
    assert drift.summary.total_changed_files == 3
    assert drift.summary.retained_file_count == 2
    assert drift.overflow[0].overflow_id == "overflow-drift-files"
    assert drift.overflow[0].omitted_count == 1
    assert drift.drift_status is RepositoryDriftStatus.PARTIAL
    assert drift.completeness is SnapshotCompleteness.PARTIAL


def test_no_commit_repository_reports_unsupported_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], shell=False, check=True, capture_output=True)

    drift = analyze_repository_drift(repository_path=repo, observed_at=FIXED_TS)

    assert drift.drift_status is RepositoryDriftStatus.UNSUPPORTED
    assert drift.baseline_commit_hash is None
    assert drift.files == []
    assert any(w.warning_id == "warning-baseline-head-unavailable" for w in drift.warnings)


def test_invalid_path_and_non_repository_fail_safely(tmp_path: Path) -> None:
    with pytest.raises(RepositoryDriftPathError):
        analyze_repository_drift(repository_path="relative/repo", observed_at=FIXED_TS)

    with pytest.raises(GitCommandFailedError):
        analyze_repository_drift(repository_path=tmp_path, observed_at=FIXED_TS)


def test_unsupported_baseline_is_rejected_before_git(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(RepositoryDriftBaselineError):
        analyze_repository_drift(
            repository_path=repo,
            observed_at=FIXED_TS,
            baseline_reference="origin/main",
        )


def test_bounded_evidence_and_repeated_analysis_are_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / "changed.md", "changed\n")

    first = analyze_repository_drift(
        repository_path=repo,
        observed_at=FIXED_TS,
        limits=GitAdapterLimits(max_excerpt_chars=32),
    )
    second = analyze_repository_drift(
        repository_path=repo,
        observed_at=FIXED_TS,
        limits=GitAdapterLimits(max_excerpt_chars=32),
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert all(
        evidence.bounded_excerpt is None
        or len(evidence.bounded_excerpt) <= (evidence.excerpt_limit or 0)
        for evidence in first.evidence
    )


def test_drift_service_only_uses_allowlisted_read_only_adapter_commands() -> None:
    observed_subcommands = {args[1] for args in READ_ONLY_GIT_COMMANDS.values()}

    assert not (observed_subcommands & MUTATING_GIT_SUBCOMMANDS)
