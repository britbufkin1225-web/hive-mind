"""Phase 39A — deterministic Repository Evidence Projection tests.

Hermetic: every test runs over directly-constructed contract fixtures. Mocks
appear only to prove prohibited dependencies (subprocess, filesystem, store)
are never invoked.
"""

from __future__ import annotations

import builtins
import inspect
import subprocess
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.active_memory import (
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
    ObserverWarning,
    ObserverWarningCategory,
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
    ProjectionTimestampError,
    RepositoryEvidenceProjectionService,
    project_repository_evidence,
)

OBSERVED_AT = datetime(2026, 7, 18, 12, 0, 0)
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
) -> RepositoryEvidenceProjectionRequest:
    return RepositoryEvidenceProjectionRequest(
        project_id=project_id,
        snapshot=snapshot or _snapshot(),
        drift_analysis=drift,
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
        assert record.lifecycle_state is LifecycleState.ACTIVE
        assert record.confidence is None
        assert record.observed_at == OBSERVED_AT
        assert record.created_at == OBSERVED_AT


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
def test_evidence_overflow_is_explicit_and_prioritizes_anchors() -> None:
    snapshot = _snapshot(
        evidence=[_observer_evidence(f"ev-{index}") for index in range(6)]
    )
    limits = RepositoryEvidenceProjectionLimits(max_evidence_records=3)
    result = _project(snapshot=snapshot, limits=limits)
    assert len(result.evidence_records) == 3
    entries = [
        item
        for item in result.overflow
        if item.kind is ProjectionOverflowKind.EVIDENCE_RECORD_COUNT
    ]
    assert len(entries) == 1
    assert entries[0].observed_count == 10  # 4 anchors + 6 observer items
    assert entries[0].omitted_count == 7
    assert result.completeness is SnapshotCompleteness.PARTIAL


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
