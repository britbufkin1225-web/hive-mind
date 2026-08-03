"""Phase 40J disposable end-to-end reviewed migration rehearsal."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.active_memory import MemoryClaim, MemoryRecordKind, MemorySource, MemorySourceType
from app.models.memory_migration import (
    DeclaredArtifactDigest, MemoryMigrationBundle, MigrationArtifactDescriptor,
    MigrationArtifactFormat, MigrationContainerKind, MigrationCustodyKind,
    MigrationDigestAlgorithm, MigrationEntryKind, MigrationProvenance as IntakeProvenance,
)
from app.models.memory_migration_import import *
from app.services.active_memory_snapshot_store import ActiveMemorySnapshotStore
from app.services.active_memory_store_holder import AuthoritativeActiveMemoryStoreHolder
from app.services.memory_migration_candidate_assessment import assess_memory_migration_candidates
from app.services.memory_migration_import import MemoryMigrationImportService
from app.services.memory_migration_import_store import MigrationImportStore
from app.services.memory_migration_intake import assess_memory_migration_intake
from app.services.memory_migration_parser import InMemoryArtifactByteSource, parse_and_project
from app.services.memory_migration_rehearsal import MigrationRehearsalPaths
from app.services.migration_import_lock import MigrationImportLock

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


class Clock:
    def now(self): return NOW


def export_bytes():
    def node(node_id, role, text, parent, children):
        return {"id": node_id, "parent": parent, "children": children, "message": {"id": node_id, "author": {"role": role}, "create_time": 1.0, "content": {"content_type": "text", "parts": [text]}}}
    value = [{"conversation_id": "synthetic-1", "create_time": 1.0, "mapping": {
        "root": {"id": "root", "message": None, "parent": None, "children": ["accepted"]},
        "accepted": node("accepted", "user", "Synthetic accepted project fact", "root", ["rejected"]),
        "rejected": node("rejected", "assistant", "Synthetic rejected contradiction", "accepted", ["unreviewed"]),
        "unreviewed": node("unreviewed", "user", "Synthetic unreviewed candidate", "rejected", []),
    }}]
    return json.dumps(value, sort_keys=True).encode()


def projected_candidates():
    payload = export_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    artifact = MigrationArtifactDescriptor(
        artifact_id="synthetic-artifact", declared_relative_path="conversations.json",
        entry_kind=MigrationEntryKind.FILE,
        artifact_format=MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        container=MigrationContainerKind.SINGLE_FILE, declared_byte_size=len(payload),
        declared_digest=DeclaredArtifactDigest(algorithm=MigrationDigestAlgorithm.SHA256, value=digest),
    )
    bundle = MemoryMigrationBundle(
        bundle_id="synthetic-rehearsal-bundle",
        provenance=IntakeProvenance(
            custody=MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
            source=MemorySource(source_type=MemorySourceType.CHATGPT, source_id="synthetic-export"),
            declared_exported_at=NOW,
        ), artifacts=[artifact],
    )
    result = parse_and_project(bundle, assess_memory_migration_intake(bundle), InMemoryArtifactByteSource({artifact.artifact_id: payload}))
    assert result.gate_permitted and result.artifacts_read == 1 and result.candidate_count == 3
    return result.candidates


def workflow(candidate, report, status=ReviewDecisionStatus.APPROVED, *, project="project", expires=NOW + timedelta(days=1)):
    decision_raw = dict(schema_version=IMPORT_VERSION, review_decision_id="", review_policy_version="review.v1", reviewer_id="human-reviewer", decision_timestamp=NOW, status=status, reason="synthetic human decision", notes=None, candidate_id=candidate.candidate_id, content_digest=candidate.content_digest, assessment_report_id=report.report_id, assessment_version=report.assessment_version, evidence_references=[{"kind": "assessment", "ref_id": report.report_id}], supersedes_decision_id=None, renewal_revision=0)
    decision_raw["review_decision_id"] = derive_review_decision_id(decision_raw)
    decision = MigrationReviewDecision.model_validate(decision_raw)
    auth_raw = dict(authorization_context_version=IMPORT_VERSION, authorization_policy_version="auth.v1", authorization_context_id="", authorization_context_digest="", authorized_project_id=project, authorized_scopes=[], project_level_authorized=True, authorizing_principal_id="human-authorizer", review_decision_id=decision.review_decision_id, candidate_id=candidate.candidate_id, content_digest=candidate.content_digest, assessment_report_id=report.report_id, assessment_version=report.assessment_version, issuance_revision=0, supersedes_authorization_context_id=None, issued_at=NOW, expires_at=expires)
    auth_raw["authorization_context_id"] = derive_authorization_context_id(auth_raw)
    auth_raw["authorization_context_digest"] = derive_authorization_context_digest(auth_raw)
    auth = ProjectScopeAuthorizationContext.model_validate(auth_raw)
    spec_raw = dict(schema_version=IMPORT_VERSION, candidate_id=candidate.candidate_id, content_digest=candidate.content_digest, assessment_report_id=report.report_id, assessment_version=report.assessment_version, review_decision_id=decision.review_decision_id, target_kind=MemoryRecordKind.PROJECT_FACT, claim=MemoryClaim(subject="project", predicate="rehearsal_status", value="ready"), observed_at=None, kind_claim_policy_version=KIND_CLAIM_COMPATIBILITY_POLICY_VERSION, project_id="project", scope=None, authorization_context_id=auth.authorization_context_id, authorization_context_digest=auth.authorization_context_digest, evidence_references=[], source_type=MemorySourceType.IMPORTED_DOCUMENT, source_provenance=MemorySource(source_type=MemorySourceType.IMPORTED_DOCUMENT, source_id=candidate.candidate_id), supersession_refs=[], specification_digest="")
    spec_raw["specification_digest"] = derive_specification_digest(spec_raw)
    return decision, auth, ReviewedImportSpecification.model_validate(spec_raw)


def service(paths):
    return MemoryMigrationImportService(MigrationImportStore(paths.ledger), ActiveMemorySnapshotStore(paths.snapshot), AuthoritativeActiveMemoryStoreHolder(), lock=MigrationImportLock(paths.lock, timeout=.1), clock=Clock())


def assert_no_success(svc):
    assert svc.holder.list_records() == []
    assert not svc.ledger_store.exists() or len(svc.ledger_store.load().receipts) == 0


def test_disposable_complete_workflow_and_clean_deterministic_rerun(tmp_path):
    paths = MigrationRehearsalPaths.isolated(tmp_path / "phase-40j")
    identities = []
    for run in range(2):
        candidates = projected_candidates()
        report = assess_memory_migration_candidates(candidates)
        svc = service(paths)
        approved, rejected, unreviewed = candidates
        decision, auth, spec = workflow(approved, report)
        first = svc.import_reviewed_candidate(candidate=approved, assessment=report, decision=decision, specification=spec, authorization=auth)
        replay = svc.import_reviewed_candidate(candidate=approved, assessment=report, decision=decision, specification=spec, authorization=auth)
        assert not first.replayed and replay.replayed and replay.receipt == first.receipt
        assert first.receipt.receipt_integrity_digest == derive_receipt_integrity_digest(first.receipt)
        ledger = svc.ledger_store.load(); snapshot = svc.snapshot_store.load()
        assert ledger.commit_generation == snapshot.commit_generation == svc.holder.current_generation() == 1
        assert len(ledger.attempts) == len(ledger.receipts) == len(svc.holder.list_records()) == 1
        assert approved.candidate_id in json.dumps(snapshot.store.serialize())
        assert rejected.content not in json.dumps(snapshot.store.serialize()) and unreviewed.content not in json.dumps(snapshot.store.serialize())
        rejected_decision, rejected_auth, rejected_spec = workflow(rejected, report, ReviewDecisionStatus.REJECTED)
        with pytest.raises(MemoryMigrationImportError) as exc:
            svc.import_reviewed_candidate(candidate=rejected, assessment=report, decision=rejected_decision, specification=rejected_spec, authorization=rejected_auth)
        assert exc.value.code == ImportDiagnosticCode.REVIEW_NOT_APPROVED and len(svc.holder.list_records()) == 1
        identities.append((first.receipt.receipt_id, first.receipt.receipt_integrity_digest, first.receipt.record_id))
        paths.reset()
        assert not paths.root.exists()
    assert identities[0] == identities[1]


@pytest.mark.parametrize("case, expected", [
    ("expired", ImportDiagnosticCode.AUTHORIZATION_CONTEXT_EXPIRED),
    ("wrong_project", ImportDiagnosticCode.PROJECT_AUTHORIZATION_MISMATCH),
    ("changed_spec", ImportDiagnosticCode.AUTHORIZATION_CONTEXT_MISMATCH),
])
def test_authorization_boundaries_fail_without_side_effects(tmp_path, case, expected):
    candidate = projected_candidates()[0]; report = assess_memory_migration_candidates([candidate])
    decision, auth, spec = workflow(candidate, report, expires=NOW if case == "expired" else NOW + timedelta(days=1))
    if case == "wrong_project": decision, auth, spec = workflow(candidate, report, project="other-project")
    if case == "changed_spec":
        raw = spec.model_dump(mode="json"); raw.update(authorization_context_id="changed-authorization", specification_digest=""); raw["specification_digest"] = derive_specification_digest(raw); spec = ReviewedImportSpecification.model_validate(raw)
    svc = service(MigrationRehearsalPaths.isolated(tmp_path / case))
    with pytest.raises(MemoryMigrationImportError) as exc:
        svc.import_reviewed_candidate(candidate=candidate, assessment=report, decision=decision, specification=spec, authorization=auth)
    assert exc.value.code == expected; assert_no_success(svc)


def test_revocation_and_authorization_reuse_fail_closed(tmp_path):
    candidates = projected_candidates(); report = assess_memory_migration_candidates(candidates)
    decision, auth, spec = workflow(candidates[0], report); svc = service(MigrationRehearsalPaths.isolated(tmp_path / "revoked"))
    svc.revoke_authorization(auth, principal_id="human-authorizer", reason="rehearsal revocation")
    with pytest.raises(MemoryMigrationImportError) as exc:
        svc.import_reviewed_candidate(candidate=candidates[0], assessment=report, decision=decision, specification=spec, authorization=auth)
    assert exc.value.code == ImportDiagnosticCode.AUTHORIZATION_CONTEXT_REVOKED; assert_no_success(svc)
    other = candidates[1]
    with pytest.raises(MemoryMigrationImportError):
        svc.import_reviewed_candidate(candidate=other, assessment=report, decision=decision, specification=spec, authorization=auth)
    assert_no_success(svc)


def test_missing_authorization_fails_with_stable_diagnostic_and_no_side_effects(tmp_path):
    candidate = projected_candidates()[0]
    report = assess_memory_migration_candidates([candidate])
    decision, _authorization, specification = workflow(candidate, report)
    svc = service(MigrationRehearsalPaths.isolated(tmp_path / "missing-authorization"))
    with pytest.raises(MemoryMigrationImportError) as exc:
        svc.import_reviewed_candidate(
            candidate=candidate,
            assessment=report,
            decision=decision,
            specification=specification,
            authorization=None,  # type: ignore[arg-type] - exercises the runtime boundary
        )
    assert exc.value.code == ImportDiagnosticCode.MISSING_AUTHORIZATION
    assert_no_success(svc)


def test_tampered_ledger_snapshot_and_stale_revision_are_detected(tmp_path):
    paths = MigrationRehearsalPaths.isolated(tmp_path / "integrity"); svc = service(paths)
    candidate = projected_candidates()[0]; report = assess_memory_migration_candidates([candidate]); decision, auth, spec = workflow(candidate, report)
    svc.import_reviewed_candidate(candidate=candidate, assessment=report, decision=decision, specification=spec, authorization=auth)
    ledger = svc.ledger_store.load()
    with pytest.raises(MemoryMigrationImportError) as exc: svc.ledger_store.persist(ledger, expected_revision=ledger.ledger_revision - 1)
    assert exc.value.code == ImportDiagnosticCode.REVISION_CONFLICT and svc.holder.current_generation() == 1
    raw = json.loads(paths.ledger.read_text()); raw["commit_generation"] = 99; paths.ledger.write_text(json.dumps(raw))
    with pytest.raises(MemoryMigrationImportError) as exc: service(paths).initialize()
    assert exc.value.code in {ImportDiagnosticCode.CORRUPT_LEDGER, ImportDiagnosticCode.IMPORT_SERVICE_QUARANTINED}


def test_n_n1_uncertain_commit_recovery_uses_durable_state(tmp_path):
    paths = MigrationRehearsalPaths.isolated(tmp_path / "recovery"); svc = service(paths)
    candidate = projected_candidates()[0]; report = assess_memory_migration_candidates([candidate]); decision, auth, spec = workflow(candidate, report)
    calls = 0; real = svc.ledger_store.replace
    def fail_after_effect(ledger, **changes):
        nonlocal calls; calls += 1
        if calls == 2: raise RuntimeError("injected crash after durable effect")
        return real(ledger, **changes)
    svc.ledger_store.replace = fail_after_effect
    with pytest.raises(MemoryMigrationImportError) as exc:
        svc.import_reviewed_candidate(candidate=candidate, assessment=report, decision=decision, specification=spec, authorization=auth)
    assert exc.value.code == ImportDiagnosticCode.PERSISTENCE_FAILURE and svc.holder.list_records() == []
    assert svc.ledger_store.load().commit_generation == 0 and svc.snapshot_store.load().commit_generation == 1
    recovered = service(paths); result = recovered.import_reviewed_candidate(candidate=candidate, assessment=report, decision=decision, specification=spec, authorization=auth)
    assert result.replayed and recovered.holder.current_generation() == 1 and len(recovered.ledger_store.load().receipts) == 1


def test_rehearsal_path_guard_rejects_environment_override(monkeypatch, tmp_path):
    root = tmp_path / "collision"
    monkeypatch.setenv("HIVEMIND_MIGRATION_IMPORT_PATH", str(root / "migration-import-ledger.json"))
    monkeypatch.setenv("HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH", str(root / "active-memory-snapshot.json"))
    monkeypatch.setenv("HIVEMIND_MIGRATION_IMPORT_LOCK_PATH", str(root / "migration-import.lock"))
    with pytest.raises(MemoryMigrationImportError) as exc: MigrationRehearsalPaths.isolated(root)
    assert exc.value.code == ImportDiagnosticCode.PERSISTENCE_FAILURE and not root.exists()
