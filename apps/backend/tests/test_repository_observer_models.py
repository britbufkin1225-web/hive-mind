"""Phase 37I - Repository Observer contract model tests."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.repository_observer import (
    REPOSITORY_OBSERVER_CONTRACT_VERSION,
    EvidenceAuthority,
    EvidenceCategory,
    FileChangeKind,
    FileContentKind,
    FileObservationCategory,
    FileObservationSummary,
    ObserverLimitation,
    ObserverLimitationCategory,
    ObserverScope,
    ObserverWarning,
    ObserverWarningCategory,
    OverflowLimitKind,
    OverflowMetadata,
    PathRelationship,
    RepositoryDriftAnalysis,
    RepositoryDriftFile,
    RepositoryDriftStatus,
    RepositoryDriftSummary,
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

FIXED_TS = datetime(2026, 7, 17, 12, 0, 0)


def _identity(status: RepositoryIdentityStatus = RepositoryIdentityStatus.UNVERIFIED) -> RepositoryIdentity:
    return RepositoryIdentity(
        repository_id="repo-hive-mind",
        canonical_root="C:/Users/britb/Documents/hive-mind",
        normalized_root="c:/users/britb/documents/hive-mind",
        repository_name="hive-mind",
        status=status,
    )


def test_minimal_repository_identity_defaults() -> None:
    identity = _identity()
    assert identity.status is RepositoryIdentityStatus.UNVERIFIED
    assert identity.operation_state is RepositoryOperationState.UNKNOWN
    assert identity.remotes == []
    assert identity.warning_ids == []


def test_verified_repository_identity_with_remote_round_trips() -> None:
    identity = RepositoryIdentity(
        repository_id="repo-hive-mind",
        canonical_root="C:/Users/britb/Documents/hive-mind",
        normalized_root="c:/users/britb/documents/hive-mind",
        repository_name="hive-mind",
        remotes=[
            RepositoryRemote(
                name="origin",
                url="https://github.com/britbufkin1225-web/hive-mind.git",
                normalized_url="github.com/britbufkin1225-web/hive-mind",
            )
        ],
        primary_remote_url="github.com/britbufkin1225-web/hive-mind",
        current_branch="main",
        current_commit="8064b1eeddc80685c95a823c779237cb4db0e811",
        upstream_reference="origin/main",
        default_branch="main",
        operation_state=RepositoryOperationState.NORMAL,
        status=RepositoryIdentityStatus.VERIFIED,
    )
    dumped = identity.model_dump(mode="json")
    assert dumped["status"] == "verified"
    assert dumped["operation_state"] == "normal"
    assert RepositoryIdentity.model_validate(dumped) == identity


def test_observer_scope_defaults_are_conservative() -> None:
    scope = ObserverScope(repository_root="C:/Users/britb/Documents/hive-mind")
    assert scope.included_paths == []
    assert scope.excluded_paths == []
    assert scope.max_file_count == 200
    assert scope.max_evidence_entries == 200
    assert scope.max_text_bytes == 0
    assert scope.include_untracked_files is False
    assert scope.include_ignored_files is False
    assert scope.include_binary_files is False
    assert scope.allow_file_contents is False
    assert scope.metadata_only is True


def test_minimal_snapshot_is_read_only_and_unavailable_by_default() -> None:
    snapshot = RepositorySnapshot(
        snapshot_id="snap-1",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
    )
    assert snapshot.contract_version == REPOSITORY_OBSERVER_CONTRACT_VERSION
    assert snapshot.observer_version == REPOSITORY_OBSERVER_CONTRACT_VERSION
    assert snapshot.read_only is True
    assert snapshot.completeness is SnapshotCompleteness.UNAVAILABLE
    assert snapshot.changed_files == []
    assert snapshot.evidence == []
    assert snapshot.warnings == []
    assert snapshot.limitations == []
    assert snapshot.overflow == []
    assert snapshot.working_tree.states == [WorkingTreeState.UNKNOWN]


def test_clean_working_tree_snapshot() -> None:
    snapshot = RepositorySnapshot(
        snapshot_id="snap-clean",
        repository_identity=_identity(RepositoryIdentityStatus.VERIFIED),
        observed_at=FIXED_TS,
        branch="main",
        commit="8064b1eeddc80685c95a823c779237cb4db0e811",
        working_tree=WorkingTreeStatus(states=[WorkingTreeState.CLEAN]),
        completeness=SnapshotCompleteness.COMPLETE,
    )
    dumped = snapshot.model_dump(mode="json")
    assert dumped["working_tree"]["states"] == ["clean"]
    assert dumped["completeness"] == "complete"
    assert RepositorySnapshot.model_validate(dumped) == snapshot


def test_dirty_working_tree_snapshot_with_changed_file() -> None:
    changed = FileObservationSummary(
        file_id="file-doc",
        repository_relative_path="docs/roadmap.md",
        normalized_path="docs/roadmap.md",
        change_kind=FileChangeKind.MODIFIED,
        observation_category=FileObservationCategory.GIT_STATUS,
        size_bytes=2048,
        content_kind=FileContentKind.TEXT,
        tracked=True,
        ignored=False,
        staged=False,
        evidence_ids=["ev-status"],
    )
    snapshot = RepositorySnapshot(
        snapshot_id="snap-dirty",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
        working_tree=WorkingTreeStatus(states=[WorkingTreeState.MODIFIED], unstaged_count=1),
        changed_files=[changed],
        completeness=SnapshotCompleteness.PARTIAL,
    )
    assert snapshot.changed_files[0].change_kind is FileChangeKind.MODIFIED
    assert snapshot.working_tree.unstaged_count == 1


def test_renamed_file_summary_preserves_prior_and_current_path() -> None:
    renamed = FileObservationSummary(
        file_id="file-rename",
        repository_relative_path="docs/new-name.md",
        normalized_path="docs/new-name.md",
        change_kind=FileChangeKind.RENAMED,
        path_relationship=PathRelationship(
            change_kind=FileChangeKind.RENAMED,
            prior_path="docs/old-name.md",
            current_path="docs/new-name.md",
        ),
    )
    assert renamed.path_relationship is not None
    assert renamed.path_relationship.prior_path == "docs/old-name.md"


def test_bounded_evidence_warning_limitation_and_partial_overflow_snapshot() -> None:
    evidence = RepositoryEvidence(
        evidence_id="ev-1",
        category=EvidenceCategory.BOUNDED_TEXT_EXCERPT,
        authority=EvidenceAuthority.PARSED_REPOSITORY_DOCUMENT,
        source="phase-37h-plan",
        repository_relative_path="docs/planning/phase-37h-repository-observer-planning.md",
        summary="Bounded excerpt from the repository observer planning doc.",
        bounded_excerpt="repo-observer.v1",
        excerpt_limit=64,
        captured_at=FIXED_TS,
        truncation_state=TruncationState.TRUNCATED,
        related_file_ids=["file-plan"],
    )
    warning = ObserverWarning(
        warning_id="warn-limit",
        category=ObserverWarningCategory.FILE_LIMIT_REACHED,
        summary="The configured file limit was reached.",
    )
    limitation = ObserverLimitation(
        limitation_id="lim-metadata",
        category=ObserverLimitationCategory.METADATA_ONLY,
        summary="The scope allows metadata only.",
    )
    overflow = OverflowMetadata(
        overflow_id="overflow-files",
        limit_kind=OverflowLimitKind.FILE_COUNT,
        truncated=True,
        configured_limit=1,
        observed_count=3,
        retained_count=1,
        omitted_count=2,
        deterministic_cutoff="first N paths by normalized path",
        snapshot_partial=True,
    )
    snapshot = RepositorySnapshot(
        snapshot_id="snap-partial",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
        evidence=[evidence],
        warnings=[warning],
        limitations=[limitation],
        omitted_paths=["apps/frontend/src/App.tsx"],
        overflow=[overflow],
        completeness=SnapshotCompleteness.PARTIAL,
    )
    dumped = snapshot.model_dump(mode="json")
    assert dumped["evidence"][0]["authority"] == "parsed_repository_document"
    assert dumped["warnings"][0]["category"] == "file_limit_reached"
    assert dumped["limitations"][0]["category"] == "metadata_only"
    assert dumped["overflow"][0]["snapshot_partial"] is True
    assert RepositorySnapshot.model_validate(dumped) == snapshot


def test_enum_wire_values_cover_contract_vocabularies() -> None:
    assert {item.value for item in RepositoryIdentityStatus} == {
        "verified",
        "unverified",
        "mismatched_root",
        "mismatched_remote",
        "missing_git_metadata",
        "unsafe_location",
    }
    assert {item.value for item in WorkingTreeState} == {
        "clean",
        "modified",
        "staged",
        "untracked",
        "conflicted",
        "unavailable",
        "unknown",
    }
    assert {item.value for item in FileChangeKind} == {
        "added",
        "modified",
        "deleted",
        "renamed",
        "copied",
        "untracked",
        "type_changed",
        "conflicted",
        "unchanged",
        "unknown",
    }
    assert {item.value for item in EvidenceAuthority} == {
        "direct_git_output",
        "direct_filesystem_metadata",
        "parsed_repository_document",
        "validated_execution_source",
        "user_supplied_statement",
        "agent_generated_summary",
        "unsupported_assumption",
        "unavailable_information",
    }
    assert {item.value for item in SnapshotCompleteness} == {
        "complete",
        "partial",
        "unavailable",
        "invalid",
        "rejected",
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_file_count": -1},
        {"max_evidence_entries": -1},
        {"max_text_bytes": -1},
        {"max_snapshot_bytes": -1},
    ],
)
def test_observer_scope_rejects_negative_limits(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        ObserverScope(repository_root="C:/Users/britb/Documents/hive-mind", **kwargs)


@pytest.mark.parametrize("bad_path", ["C:/secret.txt", "/secret.txt", "../secret.txt", "docs/../secret.txt", "."])
def test_relative_path_fields_reject_absolute_or_traversal_paths(bad_path: str) -> None:
    with pytest.raises(ValidationError):
        FileObservationSummary(
            file_id="file-bad",
            repository_relative_path=bad_path,
            normalized_path="docs/ok.md",
        )
    with pytest.raises(ValidationError):
        ObserverScope(
            repository_root="C:/Users/britb/Documents/hive-mind",
            included_paths=[bad_path],
        )


def test_working_tree_rejects_clean_with_dirty_states() -> None:
    with pytest.raises(ValidationError):
        WorkingTreeStatus(states=[WorkingTreeState.CLEAN, WorkingTreeState.MODIFIED])


def test_malformed_rename_and_copy_records_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FileObservationSummary(
            file_id="file-missing-relationship",
            repository_relative_path="docs/new.md",
            normalized_path="docs/new.md",
            change_kind=FileChangeKind.RENAMED,
        )
    with pytest.raises(ValidationError):
        PathRelationship(
            change_kind=FileChangeKind.RENAMED,
            prior_path="docs/same.md",
            current_path="docs/same.md",
        )
    with pytest.raises(ValidationError):
        FileObservationSummary(
            file_id="file-wrong-relationship",
            repository_relative_path="docs/file.md",
            normalized_path="docs/file.md",
            change_kind=FileChangeKind.MODIFIED,
            path_relationship=PathRelationship(
                change_kind=FileChangeKind.COPIED,
                prior_path="docs/a.md",
                current_path="docs/file.md",
            ),
        )


def test_impossible_overflow_counts_are_rejected() -> None:
    with pytest.raises(ValidationError):
        OverflowMetadata(
            overflow_id="overflow-bad",
            limit_kind=OverflowLimitKind.FILE_COUNT,
            truncated=True,
            configured_limit=1,
            observed_count=2,
            retained_count=2,
            omitted_count=1,
            deterministic_cutoff="first N paths",
            snapshot_partial=True,
        )
    with pytest.raises(ValidationError):
        OverflowMetadata(
            overflow_id="overflow-bad-2",
            limit_kind=OverflowLimitKind.FILE_COUNT,
            truncated=False,
            configured_limit=1,
            retained_count=1,
            omitted_count=1,
            deterministic_cutoff="first N paths",
        )


def test_complete_snapshot_rejects_truncation_metadata() -> None:
    overflow = OverflowMetadata(
        overflow_id="overflow-files",
        limit_kind=OverflowLimitKind.FILE_COUNT,
        truncated=True,
        configured_limit=1,
        observed_count=2,
        retained_count=1,
        omitted_count=1,
        deterministic_cutoff="first N paths",
        snapshot_partial=True,
    )
    with pytest.raises(ValidationError):
        RepositorySnapshot(
            snapshot_id="snap-contradictory",
            repository_identity=_identity(),
            observed_at=FIXED_TS,
            overflow=[overflow],
            completeness=SnapshotCompleteness.COMPLETE,
        )


def test_unbounded_or_oversized_excerpts_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositoryEvidence(
            evidence_id="ev-unbounded",
            category=EvidenceCategory.BOUNDED_TEXT_EXCERPT,
            authority=EvidenceAuthority.PARSED_REPOSITORY_DOCUMENT,
            source="doc",
            summary="excerpt",
            bounded_excerpt="abc",
        )
    with pytest.raises(ValidationError):
        RepositoryEvidence(
            evidence_id="ev-too-long",
            category=EvidenceCategory.BOUNDED_TEXT_EXCERPT,
            authority=EvidenceAuthority.PARSED_REPOSITORY_DOCUMENT,
            source="doc",
            summary="excerpt",
            bounded_excerpt="abcdef",
            excerpt_limit=3,
        )


def test_invalid_blank_identifiers_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshot(
            snapshot_id="   ",
            repository_identity=_identity(),
            observed_at=FIXED_TS,
        )
    with pytest.raises(ValidationError):
        RepositoryEvidence(
            evidence_id=" ",
            category=EvidenceCategory.GIT_METADATA,
            authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
            source="git-status",
            summary="status",
        )


def test_serialized_contracts_do_not_expose_unsafe_payloads_by_default() -> None:
    snapshot = RepositorySnapshot(
        snapshot_id="snap-safe",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
        changed_files=[
            FileObservationSummary(
                file_id="file-safe",
                repository_relative_path="apps/backend/app/models/repository_observer.py",
                normalized_path="apps/backend/app/models/repository_observer.py",
                change_kind=FileChangeKind.ADDED,
            )
        ],
        warnings=[
            ObserverWarning(
                warning_id="warn-safe",
                category=ObserverWarningCategory.UNKNOWN_OBSERVER_ERROR,
                summary="A bounded observer error was represented safely.",
            )
        ],
    )
    dumped = snapshot.model_dump(mode="json")
    serialized = snapshot.model_dump_json()
    assert "Traceback" not in serialized
    assert "SECRET" not in serialized
    assert "PASSWORD" not in serialized
    assert "C:/Users/britb/.ssh" not in serialized
    assert "file_contents" not in dumped["changed_files"][0]
    assert "bounded_excerpt" not in dumped["changed_files"][0]


def test_stable_defaults_and_deterministic_serialization() -> None:
    first = RepositorySnapshot(
        snapshot_id="snap-stable",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
    )
    second = RepositorySnapshot(
        snapshot_id="snap-stable",
        repository_identity=_identity(),
        observed_at=FIXED_TS,
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump_json() == second.model_dump_json()
    assert first.deterministic_ordering == [
        "paths_by_normalized_path",
        "evidence_by_authority_category_id",
        "warnings_by_category_id",
        "limitations_by_category_id",
        "overflow_by_limit_kind_id",
    ]


def _drift_evidence() -> RepositoryEvidence:
    return RepositoryEvidence(
        evidence_id="evidence-git-status",
        category=EvidenceCategory.GIT_METADATA,
        authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
        source="git status --porcelain=v2 -z --branch",
        summary="Bounded Git status evidence.",
        bounded_excerpt="# branch.oid abc",
        excerpt_limit=512,
        captured_at=FIXED_TS,
    )


def test_valid_clean_repository_drift_analysis_contract() -> None:
    drift = RepositoryDriftAnalysis(
        drift_id="drift-clean",
        repository_identity=_identity(RepositoryIdentityStatus.VERIFIED),
        observed_at=FIXED_TS,
        baseline_reference="HEAD",
        baseline_commit_hash="abc",
        drift_status=RepositoryDriftStatus.CLEAN,
        summary=RepositoryDriftSummary(),
        evidence=[_drift_evidence()],
        completeness=SnapshotCompleteness.COMPLETE,
    )

    assert drift.read_only is True
    assert drift.summary.total_changed_files == 0
    assert drift.files == []
    assert drift.model_dump(mode="json")["drift_status"] == "clean"


def test_valid_dirty_repository_drift_analysis_contract() -> None:
    drift_file = RepositoryDriftFile(
        file_id="drift-file-docs",
        change_kind=FileChangeKind.MODIFIED,
        current_path="docs/roadmap.md",
        normalized_path="docs/roadmap.md",
        staged=False,
        unstaged=True,
        tracked=True,
        evidence_ids=["evidence-git-status"],
    )
    drift = RepositoryDriftAnalysis(
        drift_id="drift-dirty",
        repository_identity=_identity(RepositoryIdentityStatus.VERIFIED),
        observed_at=FIXED_TS,
        baseline_reference="HEAD",
        baseline_commit_hash="abc",
        drift_status=RepositoryDriftStatus.DRIFTED,
        summary=RepositoryDriftSummary(
            total_changed_files=1,
            retained_file_count=1,
            unstaged_count=1,
            modified_count=1,
        ),
        files=[drift_file],
        evidence=[_drift_evidence()],
        completeness=SnapshotCompleteness.COMPLETE,
    )

    assert drift.files[0].change_kind is FileChangeKind.MODIFIED
    assert drift.summary.modified_count == 1


def test_drift_file_rejects_unsafe_paths_and_missing_evidence() -> None:
    with pytest.raises(ValidationError):
        RepositoryDriftFile(
            file_id="drift-unsafe",
            change_kind=FileChangeKind.MODIFIED,
            current_path="../secret.md",
            normalized_path="../secret.md",
            unstaged=True,
            tracked=True,
            evidence_ids=["evidence-git-status"],
        )
    with pytest.raises(ValidationError):
        RepositoryDriftFile(
            file_id="drift-no-evidence",
            change_kind=FileChangeKind.MODIFIED,
            current_path="docs/file.md",
            normalized_path="docs/file.md",
            unstaged=True,
            tracked=True,
            evidence_ids=[],
        )


def test_drift_rejects_negative_or_impossible_summary_counts() -> None:
    with pytest.raises(ValidationError):
        RepositoryDriftSummary(total_changed_files=-1)
    with pytest.raises(ValidationError):
        RepositoryDriftSummary(
            total_changed_files=1,
            retained_file_count=2,
            modified_count=2,
        )
    with pytest.raises(ValidationError):
        RepositoryDriftSummary(
            total_changed_files=1,
            retained_file_count=1,
            modified_count=0,
        )


def test_drift_rejects_malformed_rename_copy_relationships_and_contradictions() -> None:
    with pytest.raises(ValidationError):
        RepositoryDriftFile(
            file_id="drift-rename",
            change_kind=FileChangeKind.RENAMED,
            current_path="docs/new.md",
            normalized_path="docs/new.md",
            staged=True,
            tracked=True,
            evidence_ids=["evidence-git-status"],
        )
    with pytest.raises(ValidationError):
        RepositoryDriftFile(
            file_id="drift-contradictory",
            change_kind=FileChangeKind.UNTRACKED,
            current_path="docs/new.md",
            normalized_path="docs/new.md",
            staged=True,
            untracked=True,
            tracked=False,
            evidence_ids=["evidence-git-status"],
        )


def test_drift_analysis_rejects_missing_or_partial_evidence_and_bad_status() -> None:
    drift_file = RepositoryDriftFile(
        file_id="drift-file",
        change_kind=FileChangeKind.MODIFIED,
        current_path="docs/file.md",
        normalized_path="docs/file.md",
        unstaged=True,
        tracked=True,
        evidence_ids=["missing-evidence"],
    )
    with pytest.raises(ValidationError):
        RepositoryDriftAnalysis(
            drift_id="drift-bad-evidence",
            repository_identity=_identity(),
            observed_at=FIXED_TS,
            baseline_reference="HEAD",
            drift_status=RepositoryDriftStatus.DRIFTED,
            summary=RepositoryDriftSummary(
                total_changed_files=1,
                retained_file_count=1,
                unstaged_count=1,
                modified_count=1,
            ),
            files=[drift_file],
            evidence=[_drift_evidence()],
        )
    with pytest.raises(ValidationError):
        RepositoryDriftAnalysis(
            drift_id="drift-clean-with-files",
            repository_identity=_identity(),
            observed_at=FIXED_TS,
            baseline_reference="HEAD",
            drift_status=RepositoryDriftStatus.CLEAN,
            summary=RepositoryDriftSummary(
                total_changed_files=1,
                retained_file_count=1,
                unstaged_count=1,
                modified_count=1,
            ),
            files=[
                RepositoryDriftFile(
                    file_id="drift-file",
                    change_kind=FileChangeKind.MODIFIED,
                    current_path="docs/file.md",
                    normalized_path="docs/file.md",
                    unstaged=True,
                    tracked=True,
                    evidence_ids=["evidence-git-status"],
                )
            ],
            evidence=[_drift_evidence()],
        )
