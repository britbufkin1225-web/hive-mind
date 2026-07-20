"""Phase 39A — deterministic Repository Evidence Projection tests.

Hermetic: every test runs over directly-constructed contract fixtures. Mocks
appear only to prove prohibited dependencies (subprocess, filesystem, store)
are never invoked.
"""

from __future__ import annotations

import builtins
import inspect
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.active_memory import (
    ClaimValueKind,
    EvidenceReferenceKind,
    EvidenceType,
    LifecycleState,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScopeType,
    MemorySourceType,
    VerificationState,
)
from app.models.repository_evidence_projection import (
    ProjectionOverflowKind,
    RepositoryEvidenceProjectionLimits,
    RepositoryEvidenceProjectionRequest,
)
from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    FileChangeKind,
    FileObservationSummary,
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
    RepositoryIdentity,
    RepositoryIdentityStatus,
    RepositoryOperationState,
    RepositorySnapshot,
    SnapshotCompleteness,
    WorkingTreeState,
    WorkingTreeStatus,
)
from app.services import repository_evidence_projection as projection_module
from app.services.repository_evidence_projection import (
    ProjectionContractVersionError,
    ProjectionDuplicateIdError,
    ProjectionIdentityError,
    ProjectionInputMismatchError,
    ProjectionLimitError,
    ProjectionTimestampError,
    RepositoryEvidenceProjectionService,
    _remote_reference_is_safe,
    project_repository_evidence,
)

OBSERVED_AT = datetime(2026, 7, 18, 12, 0, 0)
# Recording time is a distinct axis from observation time and, being the moment
# of recording, is at or after the observation it records.
RECORDED_AT = datetime(2026, 7, 18, 12, 5, 0)
COMMIT = "a" * 40


def _identity(**overrides) -> RepositoryIdentity:
    kwargs: dict = dict(
        repository_id="repo-hive-mind",
        canonical_root="C:/repos/hive-mind",
        normalized_root="c:/repos/hive-mind",
        repository_name="hive-mind",
        primary_remote_url="https://github.com/example/hive-mind.git",
        current_branch="main",
        current_commit=COMMIT,
        upstream_reference="origin/main",
        default_branch="main",
        operation_state=RepositoryOperationState.NORMAL,
        status=RepositoryIdentityStatus.VERIFIED,
    )
    kwargs.update(overrides)
    return RepositoryIdentity(**kwargs)


def _snapshot(**overrides) -> RepositorySnapshot:
    kwargs: dict = dict(
        snapshot_id="snapshot-1",
        repository_identity=_identity(),
        observed_at=OBSERVED_AT,
        branch="main",
        commit=COMMIT,
        working_tree=WorkingTreeStatus(states=[WorkingTreeState.CLEAN]),
        completeness=SnapshotCompleteness.COMPLETE,
    )
    kwargs.update(overrides)
    return RepositorySnapshot(**kwargs)


def _observer_evidence(evidence_id: str = "ev-git-status") -> RepositoryEvidence:
    return RepositoryEvidence(
        evidence_id=evidence_id,
        category=EvidenceCategory.WORKING_TREE_METADATA,
        authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
        source="git status --porcelain=v2 -z --branch",
        summary="Captured working-tree status output.",
        captured_at=OBSERVED_AT,
    )


def _clean_drift(**overrides) -> RepositoryDriftAnalysis:
    kwargs: dict = dict(
        drift_id="drift-1",
        repository_identity=_identity(),
        observed_at=OBSERVED_AT,
        baseline_reference="HEAD",
        baseline_commit_hash=COMMIT,
        drift_status=RepositoryDriftStatus.CLEAN,
        completeness=SnapshotCompleteness.COMPLETE,
    )
    kwargs.update(overrides)
    return RepositoryDriftAnalysis(**kwargs)


def _drifted_drift(paths: list[str] | None = None, **overrides) -> RepositoryDriftAnalysis:
    paths = paths or ["src/app.py"]
    files = [
        RepositoryDriftFile(
            file_id=f"drift-file-{index}",
            change_kind=FileChangeKind.MODIFIED,
            current_path=path,
            normalized_path=path,
            unstaged=True,
            evidence_ids=["ev-git-status"],
        )
        for index, path in enumerate(paths)
    ]
    kwargs: dict = dict(
        drift_id="drift-1",
        repository_identity=_identity(),
        observed_at=OBSERVED_AT,
        baseline_reference="HEAD",
        baseline_commit_hash=COMMIT,
        drift_status=RepositoryDriftStatus.DRIFTED,
        summary=RepositoryDriftSummary(
            total_changed_files=len(files),
            retained_file_count=len(files),
            unstaged_count=len(files),
            modified_count=len(files),
        ),
        files=files,
        evidence=[_observer_evidence()],
        completeness=SnapshotCompleteness.COMPLETE,
    )
    kwargs.update(overrides)
    return RepositoryDriftAnalysis(**kwargs)


def _request(
    snapshot: RepositorySnapshot | None = None,
    drift: RepositoryDriftAnalysis | None = None,
    project_id: str = "hive-mind",
    limits: RepositoryEvidenceProjectionLimits | None = None,
    recorded_at: datetime = RECORDED_AT,
) -> RepositoryEvidenceProjectionRequest:
    return RepositoryEvidenceProjectionRequest(
        project_id=project_id,
        snapshot=snapshot or _snapshot(),
        drift_analysis=drift,
        recorded_at=recorded_at,
        limits=limits or RepositoryEvidenceProjectionLimits(),
    )


def _project(**kwargs):
    return RepositoryEvidenceProjectionService().project(_request(**kwargs))


def _claims(result) -> dict[str, MemoryRecord]:
    return {record.claim.predicate: record for record in result.candidate_records}


# --------------------------------------------------------------------------- #
# Core behavior
# --------------------------------------------------------------------------- #
def test_clean_repository_projects_clean_working_tree() -> None:
    claims = _claims(_project())
    assert claims["working_tree_state"].claim.value == "clean"
    assert claims["working_tree_state"].verification_state is VerificationState.VERIFIED
    assert claims["staged_count"].claim.value == "0"


def test_staged_changes_project_dirty_working_tree() -> None:
    snapshot = _snapshot(
        working_tree=WorkingTreeStatus(states=[WorkingTreeState.STAGED], staged_count=2)
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].claim.value == "dirty"
    assert claims["staged_count"].claim.value == "2"


def test_unstaged_changes_project_dirty_working_tree() -> None:
    snapshot = _snapshot(
        working_tree=WorkingTreeStatus(
            states=[WorkingTreeState.MODIFIED], unstaged_count=3
        )
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].claim.value == "dirty"
    assert claims["unstaged_count"].claim.value == "3"


def test_untracked_changes_project_dirty_working_tree() -> None:
    snapshot = _snapshot(
        working_tree=WorkingTreeStatus(
            states=[WorkingTreeState.UNTRACKED], untracked_count=1
        )
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].claim.value == "dirty"
    assert claims["untracked_count"].claim.value == "1"


def test_conflicted_changes_project_dirty_working_tree() -> None:
    snapshot = _snapshot(
        working_tree=WorkingTreeStatus(
            states=[WorkingTreeState.CONFLICTED], conflicted_count=4
        )
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].claim.value == "dirty"
    assert claims["conflicted_count"].claim.value == "4"


def test_unavailable_working_tree_omits_candidate_with_skip_note() -> None:
    snapshot = _snapshot(
        working_tree=WorkingTreeStatus(states=[WorkingTreeState.UNAVAILABLE])
    )
    result = _project(snapshot=snapshot)
    claims = _claims(result)
    assert "working_tree_state" not in claims
    assert "staged_count" not in claims
    assert any("working_tree_state" in item for item in result.skipped_observations)


def test_detached_head_is_observed_state_not_fatal() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(
            operation_state=RepositoryOperationState.DETACHED, current_branch=None
        ),
        branch=None,
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["operation_state"].claim.value == "detached"
    assert "current_branch" not in claims


def test_normal_operation_state_projected() -> None:
    assert _claims(_project())["operation_state"].claim.value == "normal"


def test_unavailable_operation_state_projected_as_observed() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(
            operation_state=RepositoryOperationState.UNAVAILABLE
        )
    )
    assert _claims(_project(snapshot=snapshot))["operation_state"].claim.value == (
        "unavailable"
    )


def test_unknown_operation_state_omitted_with_skip_note() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(operation_state=RepositoryOperationState.UNKNOWN)
    )
    result = _project(snapshot=snapshot)
    assert "operation_state" not in _claims(result)
    assert any("operation_state" in item for item in result.skipped_observations)


def test_unborn_repository_missing_commit_is_omitted_not_serialized_none() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(current_commit=None), commit=None
    )
    result = _project(snapshot=snapshot)
    claims = _claims(result)
    assert "current_commit" not in claims
    assert all(record.claim.value != "None" for record in result.candidate_records)
    assert any("current_commit" in item for item in result.skipped_observations)


def test_missing_branch_is_omitted_with_skip_note() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(current_branch=None), branch=None
    )
    result = _project(snapshot=snapshot)
    assert "current_branch" not in _claims(result)
    assert any("current_branch" in item for item in result.skipped_observations)


def test_missing_upstream_is_omitted_with_skip_note() -> None:
    snapshot = _snapshot(repository_identity=_identity(upstream_reference=None))
    result = _project(snapshot=snapshot)
    assert "upstream_reference" not in _claims(result)
    assert any("upstream_reference" in item for item in result.skipped_observations)


def test_default_branch_present_and_absent() -> None:
    present = _claims(_project())
    assert present["default_branch"].claim.value == "main"
    absent = _project(
        snapshot=_snapshot(repository_identity=_identity(default_branch=None))
    )
    assert "default_branch" not in _claims(absent)
    assert any("default_branch" in item for item in absent.skipped_observations)


def test_verified_identity_projects_identity_status() -> None:
    claims = _claims(_project())
    assert claims["identity_status"].claim.value == "verified"
    assert claims["identity_status"].verification_state is VerificationState.VERIFIED


def test_candidate_shape_uses_repository_scope_and_observer_source() -> None:
    result = _project()
    for record in result.candidate_records:
        assert record.kind is MemoryRecordKind.REPOSITORY_STATE
        assert record.project_id == "hive-mind"
        assert record.scope is not None
        assert record.scope.scope_type is MemoryScopeType.REPOSITORY
        assert record.scope.scope_id == "repo-hive-mind"
        assert record.source.source_type is MemorySourceType.REPOSITORY_OBSERVER
        assert record.lifecycle_state is LifecycleState.INACTIVE
        assert record.confidence is None
        assert record.observed_at == OBSERVED_AT
        assert record.created_at == RECORDED_AT


def test_partial_snapshot_downgrades_working_tree_claims() -> None:
    snapshot = _snapshot(completeness=SnapshotCompleteness.PARTIAL)
    result = _project(snapshot=snapshot)
    claims = _claims(result)
    assert claims["working_tree_state"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )
    assert claims["snapshot_completeness"].claim.value == "partial"
    assert result.completeness is SnapshotCompleteness.PARTIAL


def test_unavailable_snapshot_leaves_working_tree_claims_unverified() -> None:
    snapshot = _snapshot(
        completeness=SnapshotCompleteness.UNAVAILABLE,
        working_tree=WorkingTreeStatus(
            states=[WorkingTreeState.MODIFIED], unstaged_count=1
        ),
    )
    result = _project(snapshot=snapshot)
    claims = _claims(result)
    assert claims["working_tree_state"].verification_state is (
        VerificationState.UNVERIFIED
    )
    assert result.completeness is SnapshotCompleteness.UNAVAILABLE


def test_clean_drift_projects_clean_status_and_zero_count() -> None:
    result = _project(drift=_clean_drift())
    claims = _claims(result)
    assert claims["drift_status"].claim.value == "clean"
    assert claims["drift_status"].verification_state is VerificationState.VERIFIED
    assert claims["drifted_file_count"].claim.value == "0"
    assert result.source_drift_id == "drift-1"


def test_drifted_repository_projects_drift_claims() -> None:
    claims = _claims(_project(drift=_drifted_drift()))
    assert claims["drift_status"].claim.value == "drifted"
    assert claims["drifted_file_count"].claim.value == "1"


def test_drift_omitted_records_skip_and_no_drift_claims() -> None:
    result = _project()
    assert "drift_status" not in _claims(result)
    assert any("drift_status" in item for item in result.skipped_observations)
    assert result.source_drift_id is None


# --------------------------------------------------------------------------- #
# Evidence projection
# --------------------------------------------------------------------------- #
def test_evidence_mappings_for_commit_branch_remote_and_snapshot() -> None:
    result = _project()
    by_ref = {
        (record.evidence_type, record.reference.reference_kind): record
        for record in result.evidence_records
    }
    commit = by_ref[(EvidenceType.COMMIT, EvidenceReferenceKind.COMMIT_HASH)]
    assert commit.reference.value == COMMIT
    branch = by_ref[(EvidenceType.BRANCH, EvidenceReferenceKind.BRANCH_NAME)]
    assert branch.reference.value == "main"
    remote = by_ref[
        (
            EvidenceType.REPOSITORY_COMMAND_OUTPUT,
            EvidenceReferenceKind.EXTERNAL_SOURCE_ID,
        )
    ]
    assert remote.reference.value == "https://github.com/example/hive-mind.git"
    anchor = by_ref[
        (
            EvidenceType.REPOSITORY_COMMAND_OUTPUT,
            EvidenceReferenceKind.SOURCE_RECORD_ID,
        )
    ]
    assert anchor.reference.value == "snapshot-1"
    for record in result.evidence_records:
        assert record.valid_until is None
        assert record.source is not None
        assert record.source.source_type is MemorySourceType.REPOSITORY_OBSERVER


def test_observer_evidence_items_map_to_command_id_references() -> None:
    snapshot = _snapshot(evidence=[_observer_evidence()])
    result = _project(snapshot=snapshot)
    command_records = [
        record
        for record in result.evidence_records
        if record.reference.reference_kind is EvidenceReferenceKind.COMMAND_ID
    ]
    assert len(command_records) == 1
    record = command_records[0]
    assert record.reference.value == "ev-git-status"
    assert record.metadata["observer_authority"] == "direct_git_output"
    assert record.metadata["observer_category"] == "working_tree_metadata"


def test_drift_evidence_maps_to_command_id_reference() -> None:
    result = _project(drift=_drifted_drift())
    drift_records = [
        record
        for record in result.evidence_records
        if record.reference.reference_kind is EvidenceReferenceKind.COMMAND_ID
        and record.reference.value == "drift-1"
    ]
    assert len(drift_records) == 1
    assert drift_records[0].metadata["drift_status"] == "drifted"


def test_credential_bearing_remote_url_is_never_projected() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(
            primary_remote_url="https://user:secret@github.com/example/hive-mind.git"
        )
    )
    result = _project(snapshot=snapshot)
    assert all(
        "secret" not in record.reference.value for record in result.evidence_records
    )
    assert any("configured_remote" in item for item in result.skipped_observations)


def test_candidates_reference_projected_evidence_ids() -> None:
    result = _project(drift=_clean_drift())
    evidence_ids = {record.evidence_id for record in result.evidence_records}
    for record in result.candidate_records:
        assert record.evidence_ids
        assert set(record.evidence_ids) <= evidence_ids


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_identical_input_produces_equivalent_serialized_output() -> None:
    first = _project(drift=_drifted_drift()).model_dump_json()
    second = _project(drift=_drifted_drift()).model_dump_json()
    assert first == second


def test_generated_ids_are_stable_across_service_instances() -> None:
    result_a = RepositoryEvidenceProjectionService().project(_request())
    result_b = RepositoryEvidenceProjectionService().project(_request())
    assert result_a.projection_id == result_b.projection_id
    assert [r.evidence_id for r in result_a.evidence_records] == [
        r.evidence_id for r in result_b.evidence_records
    ]
    assert [r.record_id for r in result_a.candidate_records] == [
        r.record_id for r in result_b.candidate_records
    ]


def test_reordered_unordered_inputs_produce_identical_output() -> None:
    evidence = [_observer_evidence("ev-a"), _observer_evidence("ev-b")]
    warnings = [
        ObserverWarning(
            warning_id="w-b",
            category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
            summary="B",
        ),
        ObserverWarning(
            warning_id="w-a",
            category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
            summary="A",
        ),
    ]
    files = [
        FileObservationSummary(
            file_id="f-1", repository_relative_path="a.txt", normalized_path="a.txt"
        ),
        FileObservationSummary(
            file_id="f-2", repository_relative_path="b.txt", normalized_path="b.txt"
        ),
    ]
    forward = _snapshot(evidence=evidence, warnings=warnings, changed_files=files)
    reversed_snapshot = _snapshot(
        evidence=list(reversed(evidence)),
        warnings=list(reversed(warnings)),
        changed_files=list(reversed(files)),
    )
    assert (
        _project(snapshot=forward).model_dump_json()
        == _project(snapshot=reversed_snapshot).model_dump_json()
    )


def test_output_orderings_are_stable_and_sorted() -> None:
    result = _project(drift=_drifted_drift())
    assert result.warnings == sorted(result.warnings)
    assert result.skipped_observations == sorted(result.skipped_observations)
    predicates = [record.claim.predicate for record in result.candidate_records]
    assert predicates[0] == "identity_status"
    assert predicates.index("current_commit") < predicates.index("staged_count")
    assert result.candidate_records == projection_module.RepositoryEvidenceProjectionService._ordered_candidates(
        list(reversed(result.candidate_records))
    )


def test_caller_mutation_of_result_cannot_alter_subsequent_results() -> None:
    service = RepositoryEvidenceProjectionService()
    baseline = service.project(_request()).model_dump_json()
    tampered = service.project(_request())
    tampered.candidate_records[0].metadata["tampered"] = True
    tampered.evidence_records[0].metadata["tampered"] = True
    tampered.warnings.append("tampered")
    assert service.project(_request()).model_dump_json() == baseline


# --------------------------------------------------------------------------- #
# Verification policy
# --------------------------------------------------------------------------- #
def test_fully_supported_claims_become_verified() -> None:
    for record in _project(drift=_clean_drift()).candidate_records:
        assert record.verification_state is VerificationState.VERIFIED


def test_metadata_warning_downgrades_metadata_claims_to_partially_verified() -> None:
    snapshot = _snapshot(
        warnings=[
            ObserverWarning(
                warning_id="w-meta",
                category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
                summary="Git metadata was unavailable for part of the observation.",
            )
        ]
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["current_branch"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )
    assert claims["working_tree_state"].verification_state is (
        VerificationState.VERIFIED
    )


def test_unverified_identity_never_promotes_any_claim() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(status=RepositoryIdentityStatus.UNVERIFIED)
    )
    for record in _project(snapshot=snapshot).candidate_records:
        assert record.verification_state is VerificationState.UNVERIFIED


def test_missing_git_metadata_identity_never_promotes_any_claim() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(
            status=RepositoryIdentityStatus.MISSING_GIT_METADATA
        )
    )
    for record in _project(snapshot=snapshot).candidate_records:
        assert record.verification_state is VerificationState.UNVERIFIED


def test_partial_drift_downgrades_drift_claims() -> None:
    drift = _drifted_drift(
        drift_status=RepositoryDriftStatus.PARTIAL,
        completeness=SnapshotCompleteness.PARTIAL,
    )
    claims = _claims(_project(drift=drift))
    assert claims["drift_status"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )


def test_confidence_is_never_set() -> None:
    for record in _project(drift=_clean_drift()).candidate_records:
        assert record.confidence is None


def test_identity_mismatch_cannot_produce_falsely_verified_candidates() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(status=RepositoryIdentityStatus.MISMATCHED_REMOTE)
    )
    with pytest.raises(ProjectionIdentityError):
        _project(snapshot=snapshot)


# --------------------------------------------------------------------------- #
# Bounds and overflow
# --------------------------------------------------------------------------- #
def test_evidence_overflow_omits_only_unreferenced_evidence() -> None:
    # 4 candidate-referenced anchors + 6 unreferenced observer items. A limit
    # above the referenced count overflows only unreferenced evidence, never
    # support a retained candidate cites.
    snapshot = _snapshot(
        evidence=[_observer_evidence(f"ev-{index}") for index in range(6)]
    )
    limits = RepositoryEvidenceProjectionLimits(max_evidence_records=6)
    result = _project(snapshot=snapshot, limits=limits)
    assert len(result.evidence_records) == 6
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.EVIDENCE_RECORD_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].observed_count == 10  # 4 anchors + 6 observer items
    assert entries[0].omitted_count == 4  # only unreferenced observer items
    assert result.completeness is SnapshotCompleteness.PARTIAL
    # Referential integrity: every retained candidate's evidence survives.
    evidence_ids = {record.evidence_id for record in result.evidence_records}
    for record in result.candidate_records:
        assert set(record.evidence_ids) <= evidence_ids


@pytest.mark.parametrize("max_evidence_records", [1, 2, 3])
def test_evidence_limit_below_referenced_count_is_fatal(max_evidence_records) -> None:
    # The default snapshot has 4 candidate-referenced anchors (snapshot, commit,
    # branch, remote). A limit below that cannot retain them without producing
    # dangling references, so projection fails closed instead.
    limits = RepositoryEvidenceProjectionLimits(
        max_evidence_records=max_evidence_records
    )
    with pytest.raises(ProjectionLimitError):
        _project(limits=limits)


def test_evidence_limit_exactly_referenced_count_retains_all_support() -> None:
    limits = RepositoryEvidenceProjectionLimits(max_evidence_records=4)
    result = _project(limits=limits)
    assert len(result.evidence_records) == 4
    evidence_ids = {record.evidence_id for record in result.evidence_records}
    for record in result.candidate_records:
        assert set(record.evidence_ids) <= evidence_ids
    assert not [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.EVIDENCE_RECORD_COUNT
    ]


def test_default_bounds_retain_all_evidence_and_candidate_support() -> None:
    result = _project(drift=_clean_drift())
    evidence_ids = {record.evidence_id for record in result.evidence_records}
    for record in result.candidate_records:
        assert record.evidence_ids
        assert set(record.evidence_ids) <= evidence_ids
    assert not result.overflow


def test_candidate_overflow_retains_documented_priority_order() -> None:
    limits = RepositoryEvidenceProjectionLimits(max_candidate_records=3)
    result = _project(limits=limits)
    predicates = [record.claim.predicate for record in result.candidate_records]
    assert predicates == ["identity_status", "current_commit", "current_branch"]
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.CANDIDATE_RECORD_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].retained_count == 3
    assert entries[0].omitted_count >= 1


def test_warning_overflow_is_explicit() -> None:
    snapshot = _snapshot(
        warnings=[
            ObserverWarning(
                warning_id=f"w-{index}",
                category=ObserverWarningCategory.PARTIAL_SNAPSHOT,
                summary=f"warning {index}",
            )
            for index in range(4)
        ],
        completeness=SnapshotCompleteness.PARTIAL,
    )
    limits = RepositoryEvidenceProjectionLimits(max_warnings=1)
    result = _project(snapshot=snapshot, limits=limits)
    assert len(result.warnings) == 1
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.WARNING_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].omitted_count == 3


def test_skipped_observation_overflow_is_explicit() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(
            current_commit=None,
            current_branch=None,
            upstream_reference=None,
            default_branch=None,
        ),
        branch=None,
        commit=None,
    )
    limits = RepositoryEvidenceProjectionLimits(max_skipped_observations=2)
    result = _project(snapshot=snapshot, limits=limits)
    assert len(result.skipped_observations) == 2
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.SKIPPED_OBSERVATION_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].omitted_count >= 1


def test_file_path_summary_is_bounded_with_explicit_overflow() -> None:
    files = [
        FileObservationSummary(
            file_id=f"f-{index}",
            repository_relative_path=f"src/file_{index:02d}.py",
            normalized_path=f"src/file_{index:02d}.py",
        )
        for index in range(20)
    ]
    limits = RepositoryEvidenceProjectionLimits(max_file_path_summary_items=5)
    result = _project(snapshot=_snapshot(changed_files=files), limits=limits)
    anchor = next(
        record
        for record in result.evidence_records
        if record.reference.reference_kind is EvidenceReferenceKind.SOURCE_RECORD_ID
    )
    assert len(anchor.metadata["changed_file_paths"]) == 5
    assert anchor.metadata["changed_file_paths_omitted"] == 15
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.FILE_PATH_SUMMARY_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].omitted_count == 15


def test_no_per_file_memory_record_flood() -> None:
    files = [
        FileObservationSummary(
            file_id=f"f-{index}",
            repository_relative_path=f"src/file_{index:03d}.py",
            normalized_path=f"src/file_{index:03d}.py",
        )
        for index in range(200)
    ]
    result = _project(snapshot=_snapshot(changed_files=files))
    baseline = _project()
    assert len(result.candidate_records) == len(baseline.candidate_records)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
def test_blank_project_id_is_rejected_at_the_contract_edge() -> None:
    with pytest.raises(ValidationError):
        RepositoryEvidenceProjectionRequest(project_id="   ", snapshot=_snapshot())


def test_unsafe_repository_identity_is_fatal() -> None:
    snapshot = _snapshot(
        repository_identity=_identity(status=RepositoryIdentityStatus.UNSAFE_LOCATION)
    )
    with pytest.raises(ProjectionIdentityError):
        _project(snapshot=snapshot)


def test_incompatible_snapshot_and_drift_repositories_are_fatal() -> None:
    drift = _clean_drift(repository_identity=_identity(repository_id="other-repo"))
    with pytest.raises(ProjectionInputMismatchError):
        _project(drift=drift)


def test_duplicate_generated_evidence_id_is_fatal() -> None:
    snapshot = _snapshot(
        evidence=[_observer_evidence("ev-dup"), _observer_evidence("ev-dup")]
    )
    with pytest.raises(ProjectionDuplicateIdError):
        _project(snapshot=snapshot)


def test_duplicate_generated_candidate_id_is_fatal(monkeypatch) -> None:
    original = projection_module._stable_id

    def collide(prefix: str, payload) -> str:
        if prefix == "candidate":
            return "candidate-fixed"
        return original(prefix, payload)

    monkeypatch.setattr(projection_module, "_stable_id", collide)
    with pytest.raises(ProjectionDuplicateIdError):
        _project()


def test_missing_required_observation_timestamp_is_fatal() -> None:
    broken = _snapshot().model_copy(update={"observed_at": None})
    with pytest.raises(ProjectionTimestampError):
        _project(snapshot=broken)


def test_contract_version_mismatch_is_fatal() -> None:
    with pytest.raises(ProjectionContractVersionError):
        _project(snapshot=_snapshot(contract_version="repo-observer.v2"))
    with pytest.raises(ProjectionContractVersionError):
        _project(drift=_clean_drift(contract_version="repo-observer.v2"))


# --------------------------------------------------------------------------- #
# Isolation
# --------------------------------------------------------------------------- #
def test_projection_never_invokes_subprocess(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("projection invoked a subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert _project(drift=_drifted_drift()).read_only is True


def test_projection_never_opens_files(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("projection accessed the filesystem")

    monkeypatch.setattr(builtins, "open", forbidden)
    assert _project(drift=_drifted_drift()).read_only is True


def test_source_contains_no_prohibited_runtime_behavior() -> None:
    source = inspect.getsource(projection_module)
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "uuid",
        "subprocess",
        "os.system",
        "os.environ",
        "Path.read",
        "Path.write",
        "open(",
        "ActiveMemoryStore",
        "app.store",
        "httpx",
        "socket",
    ):
        assert token not in source, f"prohibited token in projection service: {token}"


def test_module_level_helper_matches_service_output() -> None:
    request = _request()
    assert (
        project_repository_evidence(request).model_dump_json()
        == RepositoryEvidenceProjectionService().project(request).model_dump_json()
    )


# --------------------------------------------------------------------------- #
# Candidate lifecycle (Phase 39A §2)
# --------------------------------------------------------------------------- #
def test_every_projected_candidate_is_inactive() -> None:
    result = _project(drift=_drifted_drift())
    assert result.candidate_records
    for record in result.candidate_records:
        assert record.lifecycle_state is LifecycleState.INACTIVE


# --------------------------------------------------------------------------- #
# Recorded timestamp contract (Phase 39A §3)
# --------------------------------------------------------------------------- #
def test_recorded_at_is_created_at_distinct_from_observed_at() -> None:
    result = _project(drift=_clean_drift())
    for record in result.candidate_records:
        assert record.observed_at == OBSERVED_AT
        assert record.created_at == RECORDED_AT
    assert OBSERVED_AT != RECORDED_AT


def test_aware_timestamps_are_accepted_and_serialize_stably() -> None:
    observed = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    recorded = datetime(2026, 7, 18, 12, 5, tzinfo=timezone.utc)
    snapshot = _snapshot(observed_at=observed)
    drift = _clean_drift(observed_at=observed)
    first = RepositoryEvidenceProjectionService().project(
        _request(snapshot=snapshot, drift=drift, recorded_at=recorded)
    )
    second = RepositoryEvidenceProjectionService().project(
        _request(snapshot=snapshot, drift=drift, recorded_at=recorded)
    )
    assert first.model_dump_json() == second.model_dump_json()
    for record in first.candidate_records:
        assert record.created_at == recorded


def test_mixed_awareness_timestamps_are_fatal() -> None:
    aware = datetime(2026, 7, 18, 12, 5, tzinfo=timezone.utc)
    with pytest.raises(ProjectionTimestampError):
        _project(recorded_at=aware)  # naive snapshot + aware recorded_at


def test_recorded_at_before_observation_is_fatal() -> None:
    with pytest.raises(ProjectionTimestampError):
        _project(recorded_at=OBSERVED_AT - timedelta(minutes=1))


def test_drift_observed_before_snapshot_observed_is_fatal() -> None:
    drift = _clean_drift(observed_at=OBSERVED_AT - timedelta(minutes=1))
    with pytest.raises(ProjectionTimestampError):
        _project(drift=drift)


def test_recorded_at_before_drift_observation_is_fatal() -> None:
    later = OBSERVED_AT + timedelta(hours=1)
    snapshot = _snapshot(observed_at=OBSERVED_AT)
    drift = _clean_drift(observed_at=later)
    # recorded_at sits between the two observations: valid vs the snapshot but
    # earlier than the drift observation it records.
    with pytest.raises(ProjectionTimestampError):
        _project(
            snapshot=snapshot,
            drift=drift,
            recorded_at=OBSERVED_AT + timedelta(minutes=1),
        )


# --------------------------------------------------------------------------- #
# Stable identity inputs (Phase 39A §4)
# --------------------------------------------------------------------------- #
def test_different_limits_produce_different_projection_ids() -> None:
    wide = _project()
    narrow = _project(limits=RepositoryEvidenceProjectionLimits(max_candidate_records=5))
    assert wide.projection_id != narrow.projection_id


def test_different_snapshot_ids_produce_different_candidate_ids() -> None:
    first = _claims(_project(snapshot=_snapshot(snapshot_id="snapshot-1")))
    second = _claims(_project(snapshot=_snapshot(snapshot_id="snapshot-2")))
    assert (
        first["identity_status"].record_id != second["identity_status"].record_id
    )


def test_changed_verification_standing_changes_candidate_id() -> None:
    # Same working_tree_state value ("clean") and same snapshot id, but a
    # different completeness changes the verification standing — and therefore
    # the candidate id.
    complete = _claims(
        _project(snapshot=_snapshot(completeness=SnapshotCompleteness.COMPLETE))
    )["working_tree_state"]
    partial = _claims(
        _project(snapshot=_snapshot(completeness=SnapshotCompleteness.PARTIAL))
    )["working_tree_state"]
    assert complete.claim.value == partial.claim.value == "clean"
    assert complete.verification_state is not partial.verification_state
    assert complete.record_id != partial.record_id


def test_different_recorded_at_changes_candidate_id() -> None:
    early = _claims(_project(recorded_at=RECORDED_AT))["identity_status"]
    late = _claims(
        _project(recorded_at=RECORDED_AT + timedelta(hours=1))
    )["identity_status"]
    assert early.record_id != late.record_id


# --------------------------------------------------------------------------- #
# Trust / limitation policy (Phase 39A §5)
# --------------------------------------------------------------------------- #
def _drift_warning(category=ObserverWarningCategory.GIT_METADATA_UNAVAILABLE):
    return ObserverWarning(warning_id="dw-1", category=category, summary="drift warning")


def _drift_limitation(category=ObserverLimitationCategory.UNAVAILABLE_INFORMATION):
    return ObserverLimitation(
        limitation_id="dl-1", category=category, summary="drift limitation"
    )


def test_complete_drift_with_material_warning_is_not_verified() -> None:
    drift = _clean_drift(warnings=[_drift_warning()])
    claims = _claims(_project(drift=drift))
    assert claims["drift_status"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )


def test_complete_drift_with_material_limitation_is_not_verified() -> None:
    drift = _clean_drift(limitations=[_drift_limitation()])
    claims = _claims(_project(drift=drift))
    assert claims["drift_status"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )


def test_truncated_drift_is_not_verified() -> None:
    overflow = OverflowMetadata(
        overflow_id="drift-of-1",
        limit_kind=OverflowLimitKind.FILE_COUNT,
        truncated=True,
        configured_limit=1,
        observed_count=5,
        retained_count=1,
        omitted_count=4,
        deterministic_cutoff="first N by path",
        snapshot_partial=True,
    )
    drift = _drifted_drift(
        drift_status=RepositoryDriftStatus.PARTIAL,
        completeness=SnapshotCompleteness.PARTIAL,
        overflow=[overflow],
    )
    claims = _claims(_project(drift=drift))
    assert claims["drift_status"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )


def test_snapshot_material_limitation_downgrades_working_tree_claims() -> None:
    snapshot = _snapshot(
        limitations=[
            ObserverLimitation(
                limitation_id="sl-1",
                category=ObserverLimitationCategory.UNAVAILABLE_INFORMATION,
                summary="snapshot limitation",
            )
        ]
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )
    assert claims["current_branch"].verification_state is (
        VerificationState.PARTIALLY_VERIFIED
    )


def test_unrelated_warning_does_not_degrade_unrelated_claims() -> None:
    snapshot = _snapshot(
        warnings=[
            ObserverWarning(
                warning_id="w-binary",
                category=ObserverWarningCategory.BINARY_CONTENT_OMITTED,
                summary="a binary file's content was omitted",
            )
        ]
    )
    claims = _claims(_project(snapshot=snapshot))
    assert claims["working_tree_state"].verification_state is VerificationState.VERIFIED
    assert claims["current_branch"].verification_state is VerificationState.VERIFIED


def test_limitations_are_projected_as_skipped_observations() -> None:
    snapshot = _snapshot(
        limitations=[
            ObserverLimitation(
                limitation_id="sl-9",
                category=ObserverLimitationCategory.BOUNDED_COLLECTION,
                summary="bounded collection",
            )
        ]
    )
    result = _project(snapshot=snapshot)
    assert any(
        "snapshot-limitation sl-9" in item for item in result.skipped_observations
    )


# --------------------------------------------------------------------------- #
# Snapshot/drift identity consistency (Phase 39A §6)
# --------------------------------------------------------------------------- #
def test_same_repo_id_but_different_root_is_fatal() -> None:
    drift = _clean_drift(
        repository_identity=_identity(normalized_root="c:/other/root")
    )
    with pytest.raises(ProjectionInputMismatchError):
        _project(drift=drift)


def test_same_repo_id_but_different_remote_is_fatal() -> None:
    drift = _clean_drift(
        repository_identity=_identity(
            primary_remote_url="https://github.com/example/other.git"
        )
    )
    with pytest.raises(ProjectionInputMismatchError):
        _project(drift=drift)


def test_identity_mismatch_error_never_echoes_remote_secret() -> None:
    drift = _clean_drift(
        repository_identity=_identity(
            primary_remote_url="https://user:topsecret@github.com/example/other.git"
        )
    )
    snapshot = _snapshot(
        repository_identity=_identity(
            primary_remote_url="https://user:othersecret@github.com/example/hive-mind.git"
        )
    )
    with pytest.raises(ProjectionInputMismatchError) as excinfo:
        _project(snapshot=snapshot, drift=drift)
    assert "topsecret" not in str(excinfo.value)
    assert "othersecret" not in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Remote reference safety (Phase 39A §7)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "url,expected_safe",
    [
        ("https://user:secret@github.com/example/hive-mind.git", False),
        ("https://github.com/example/hive-mind.git?token=abc", False),
        ("https://github.com/example/hive-mind.git#tok", False),
        ("https://user%40evil@github.com/example/hive-mind.git", False),
        ("https://token@github.com/example/hive-mind.git", False),
        ("https://github.com/example/hive-mind.git", True),
        ("git@github.com:example/hive-mind.git", True),
        ("ssh://git@github.com/example/hive-mind.git", True),
    ],
)
def test_remote_reference_safety_classification(url, expected_safe) -> None:
    assert _remote_reference_is_safe(url) is expected_safe


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@github.com/example/hive-mind.git",
        "https://github.com/example/hive-mind.git?token=secret",
        "https://github.com/example/hive-mind.git#secret",
        "https://user%40secret@github.com/example/hive-mind.git",
    ],
)
def test_adversarial_remotes_are_never_projected(url) -> None:
    result = _project(snapshot=_snapshot(repository_identity=_identity(primary_remote_url=url)))
    assert all("secret" not in record.reference.value for record in result.evidence_records)
    assert all("secret" not in item for item in result.skipped_observations)
    assert any("configured_remote" in item for item in result.skipped_observations)


def test_safe_ssh_remote_is_projected() -> None:
    result = _project(
        snapshot=_snapshot(
            repository_identity=_identity(
                primary_remote_url="git@github.com:example/hive-mind.git"
            )
        )
    )
    remotes = [
        record
        for record in result.evidence_records
        if record.reference.reference_kind is EvidenceReferenceKind.EXTERNAL_SOURCE_ID
    ]
    assert len(remotes) == 1
    assert remotes[0].reference.value == "git@github.com:example/hive-mind.git"


# --------------------------------------------------------------------------- #
# Aggregate drift claims (Phase 39A §8)
# --------------------------------------------------------------------------- #
def test_drift_aggregate_claims_are_projected() -> None:
    summary = RepositoryDriftSummary(
        total_changed_files=4,
        retained_file_count=4,
        unstaged_count=4,
        added_count=1,
        modified_count=1,
        deleted_count=1,
        renamed_count=0,
        copied_count=0,
        type_changed_count=1,
        unknown_count=0,
    )
    files = [
        RepositoryDriftFile(
            file_id=f"df-{i}",
            change_kind=FileChangeKind.MODIFIED,
            current_path=f"src/f{i}.py",
            normalized_path=f"src/f{i}.py",
            unstaged=True,
            evidence_ids=["ev-git-status"],
        )
        for i in range(4)
    ]
    drift = RepositoryDriftAnalysis(
        drift_id="drift-agg",
        repository_identity=_identity(),
        observed_at=OBSERVED_AT,
        baseline_reference="HEAD",
        baseline_commit_hash=COMMIT,
        drift_status=RepositoryDriftStatus.DRIFTED,
        summary=summary,
        files=files,
        evidence=[_observer_evidence()],
        completeness=SnapshotCompleteness.COMPLETE,
    )
    result = _project(drift=drift)
    claims = _claims(result)
    assert claims["drift_baseline_commit"].claim.value == COMMIT
    assert claims["drift_baseline_commit"].claim.value_kind is ClaimValueKind.IDENTIFIER
    assert claims["added_count"].claim.value == "1"
    assert claims["modified_count"].claim.value == "1"
    assert claims["deleted_count"].claim.value == "1"
    assert claims["renamed_count"].claim.value == "0"
    assert claims["copied_count"].claim.value == "0"
    assert claims["type_changed_count"].claim.value == "1"
    assert claims["unknown_count"].claim.value == "0"
    # Aggregate claims cite the drift evidence anchor and reference retained
    # evidence only (no dangling ids, no per-file records).
    evidence_ids = {record.evidence_id for record in result.evidence_records}
    for key in ("added_count", "modified_count", "type_changed_count"):
        assert claims[key].claim.value_kind is ClaimValueKind.INTEGER
        assert claims[key].evidence_ids
        assert set(claims[key].evidence_ids) <= evidence_ids


def test_missing_baseline_commit_is_omitted_not_serialized_none() -> None:
    drift = _clean_drift(baseline_commit_hash=None)
    result = _project(drift=drift)
    claims = _claims(result)
    assert "drift_baseline_commit" not in claims
    assert all(record.claim.value != "None" for record in result.candidate_records)
    assert any(
        "drift_baseline_commit" in item for item in result.skipped_observations
    )


def test_default_candidate_limit_holds_full_drift_claim_set() -> None:
    result = _project(drift=_drifted_drift())
    predicates = {record.claim.predicate for record in result.candidate_records}
    for expected in (
        "drift_status",
        "drift_baseline_commit",
        "drifted_file_count",
        "added_count",
        "modified_count",
        "deleted_count",
        "renamed_count",
        "copied_count",
        "type_changed_count",
        "unknown_count",
    ):
        assert expected in predicates
    assert not [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.CANDIDATE_RECORD_COUNT
    ]


# --------------------------------------------------------------------------- #
# Limit contracts (Phase 39A §9)
# --------------------------------------------------------------------------- #
def test_oversized_limit_is_rejected_at_the_contract_edge() -> None:
    with pytest.raises(ValidationError):
        RepositoryEvidenceProjectionLimits(max_evidence_records=100_000)
