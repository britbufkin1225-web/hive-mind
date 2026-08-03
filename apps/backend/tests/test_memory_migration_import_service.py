from datetime import datetime, timedelta, timezone
import pytest
from app.models.active_memory import MemoryClaim, MemoryRecordKind, MemorySource, MemorySourceType
from app.models.memory_migration import MigrationArtifactFormat, MigrationContainerKind, MigrationCustodyKind, MigrationDigestAlgorithm
from app.models.memory_migration_projection import MemoryMigrationCandidate, MigrationCandidateProvenance, MigrationCandidateRole, derive_candidate_content_digest, derive_candidate_id
from app.models.memory_migration_import import *
from app.services.memory_migration_candidate_assessment import assess_memory_migration_candidates
from app.services.memory_migration_import import MemoryMigrationImportService
from app.services.memory_migration_import_store import MigrationImportStore
from app.services.active_memory_snapshot_store import ActiveMemorySnapshotStore
from app.services.active_memory_store_holder import AuthoritativeActiveMemoryStoreHolder
from app.services.migration_import_lock import MigrationImportLock

NOW=datetime(2026,1,1,tzinfo=timezone.utc)
class Clock:
    def now(self): return NOW

def candidate(text="reviewed text"):
    provenance=MigrationCandidateProvenance(bundle_id="bundle",bundle_fingerprint="mm-bundle-"+"0"*24,source_artifact_id="artifact",source_artifact_fingerprint="mm-artifact-"+"0"*24,source_artifact_format=MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,source_container=MigrationContainerKind.SINGLE_FILE,observed_digest_algorithm=MigrationDigestAlgorithm.SHA256,observed_digest_value="c"*64,custody=MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,source=MemorySource(source_type=MemorySourceType.CHATGPT,source_id="source"),source_local_id="conversation:1",source_role=MigrationCandidateRole.USER)
    digest=derive_candidate_content_digest(text)
    cid=derive_candidate_id(bundle_fingerprint=provenance.bundle_fingerprint,artifact_fingerprint=provenance.source_artifact_fingerprint,source_local_id=provenance.source_local_id,role=provenance.source_role.value,source_sequence_index=0,chunk_index=0,content_digest=digest)
    return MemoryMigrationCandidate(candidate_id=cid,content=text,content_digest=digest,chunk_index=0,chunk_count=1,source_sequence_index=0,provenance=provenance)

def workflow(c, report, status=ReviewDecisionStatus.APPROVED, reason="reviewed", evidence=True):
    d=dict(schema_version=IMPORT_VERSION,review_decision_id="",review_policy_version="review.v1",reviewer_id="human",decision_timestamp=NOW,status=status,reason=reason,notes=None,candidate_id=c.candidate_id,content_digest=c.content_digest,assessment_report_id=report.report_id,assessment_version=report.assessment_version,evidence_references=([{"kind":"assessment","ref_id":report.report_id}] if evidence else []),supersedes_decision_id=None,renewal_revision=0); d["review_decision_id"]=derive_review_decision_id(d); decision=MigrationReviewDecision.model_validate(d)
    a=dict(authorization_context_version=IMPORT_VERSION,authorization_policy_version="auth.v1",authorization_context_id="",authorization_context_digest="",authorized_project_id="project",authorized_scopes=[],project_level_authorized=True,authorizing_principal_id="human",review_decision_id=decision.review_decision_id,candidate_id=c.candidate_id,content_digest=c.content_digest,assessment_report_id=report.report_id,assessment_version=report.assessment_version,issuance_revision=0,supersedes_authorization_context_id=None,issued_at=NOW,expires_at=NOW+timedelta(days=1)); a["authorization_context_id"]=derive_authorization_context_id(a); a["authorization_context_digest"]=derive_authorization_context_digest(a); auth=ProjectScopeAuthorizationContext.model_validate(a)
    s=dict(schema_version=IMPORT_VERSION,candidate_id=c.candidate_id,content_digest=c.content_digest,assessment_report_id=report.report_id,assessment_version=report.assessment_version,review_decision_id=decision.review_decision_id,target_kind=MemoryRecordKind.PROJECT_FACT,claim=MemoryClaim(subject="project",predicate="status",value="ready"),observed_at=None,kind_claim_policy_version=KIND_CLAIM_COMPATIBILITY_POLICY_VERSION,project_id="project",scope=None,authorization_context_id=auth.authorization_context_id,authorization_context_digest=auth.authorization_context_digest,evidence_references=[],source_type=MemorySourceType.IMPORTED_DOCUMENT,source_provenance=MemorySource(source_type=MemorySourceType.IMPORTED_DOCUMENT,source_id=c.candidate_id),supersession_refs=[],specification_digest=""); s["specification_digest"]=derive_specification_digest(s)
    return decision,auth,ReviewedImportSpecification.model_validate(s)

def service(tmp_path):
    return MemoryMigrationImportService(MigrationImportStore(tmp_path/"ledger.json"),ActiveMemorySnapshotStore(tmp_path/"snapshot.json"),AuthoritativeActiveMemoryStoreHolder(),lock=MigrationImportLock(tmp_path/"lock",timeout=.1),clock=Clock())

def test_success_and_exact_replay_have_one_effect_and_one_receipt(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report); svc=service(tmp_path)
    first=svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    replay=svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert not first.replayed and replay.replayed and replay.receipt==first.receipt
    assert len(svc.holder.list_records())==1 and len(svc.ledger_store.load().receipts)==1

def test_non_approved_review_never_mutates_live_store(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report,ReviewDecisionStatus.REJECTED); svc=service(tmp_path)
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.REVIEW_NOT_APPROVED and svc.holder.list_records()==[]

def test_deferred_review_never_mutates_live_store(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report,ReviewDecisionStatus.DEFERRED); svc=service(tmp_path)
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.REVIEW_NOT_APPROVED and svc.holder.list_records()==[]

def test_incomplete_review_provenance_fails_closed(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); svc=service(tmp_path)
    d,a,s=workflow(c,report,reason="")
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.INCOMPLETE_REVIEW_PROVENANCE and svc.holder.list_records()==[]
    d,a,s=workflow(c,report,evidence=False)
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.INCOMPLETE_REVIEW_PROVENANCE and svc.holder.list_records()==[]

def test_changed_candidate_bytes_invalidate_approval(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report); svc=service(tmp_path)
    tampered=candidate("tampered bytes")
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=tampered,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.CANDIDATE_INTEGRITY_FAILURE and svc.holder.list_records()==[]

def test_changed_assessment_invalidates_authorization(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report); svc=service(tmp_path)
    other_report=assess_memory_migration_candidates([candidate("alpha"),candidate("beta")])
    assert other_report.report_id!=report.report_id
    with pytest.raises(MemoryMigrationImportError) as exc: svc.import_reviewed_candidate(candidate=c,assessment=other_report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.ASSESSMENT_MISMATCH and svc.holder.list_records()==[]

def test_two_distinct_approved_imports_advance_generation_without_rewrite(tmp_path):
    svc=service(tmp_path)
    c1=candidate("first fact"); r1=assess_memory_migration_candidates([c1]); d1,a1,s1=workflow(c1,r1)
    c2=candidate("second fact"); r2=assess_memory_migration_candidates([c2]); d2,a2,s2=workflow(c2,r2)
    first=svc.import_reviewed_candidate(candidate=c1,assessment=r1,decision=d1,specification=s1,authorization=a1)
    second=svc.import_reviewed_candidate(candidate=c2,assessment=r2,decision=d2,specification=s2,authorization=a2)
    assert first.receipt.commit_generation==1 and second.receipt.commit_generation==2
    ids={first.receipt.record_id,second.receipt.record_id}
    assert len(ids)==2 and {r.record_id for r in svc.holder.list_records()}==ids
    assert len(svc.ledger_store.load().receipts)==2

def test_uncertain_n_n1_commit_recovers_deterministically_and_publishes_once(tmp_path):
    c=candidate(); report=assess_memory_migration_candidates([c]); d,a,s=workflow(c,report)
    svc=service(tmp_path)
    # Simulate a crash after the durable N+1 snapshot but before the receipt/ledger commit.
    calls={"n":0}; real=svc.ledger_store.replace
    def flaky(ledger,**changes):
        calls["n"]+=1
        if calls["n"]==2: raise RuntimeError("crash after durable snapshot, before receipt")
        return real(ledger,**changes)
    svc.ledger_store.replace=flaky
    with pytest.raises(MemoryMigrationImportError) as exc:
        svc.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert exc.value.code==ImportDiagnosticCode.PERSISTENCE_FAILURE
    assert svc.holder.list_records()==[]  # authoritative live store never advanced
    # Durable state is exactly N/N+1: snapshot at generation 1, ledger still at 0 with a lone INTENDED attempt, no receipt.
    assert svc.snapshot_store.load().commit_generation==1
    mid=svc.ledger_store.load()
    assert mid.commit_generation==0 and len(mid.receipts)==0
    assert [x.intent_state for x in mid.attempts]==[ImportIntentState.INTENDED]
    # A fresh process recovers on load: finalizes exactly one receipt, advances the ledger, and publishes the verified snapshot.
    recovered=service(tmp_path)
    result=recovered.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert result.replayed  # the durable commit was finalized by recovery; caller gets the deterministic receipt
    assert len(recovered.holder.list_records())==1
    led=recovered.ledger_store.load()
    assert led.commit_generation==1 and len(led.receipts)==1
    assert result.receipt.commit_generation==1 and led.receipts[0]==result.receipt
    assert recovered.holder.find_record(result.receipt.record_id) is not None
    # Recovery is idempotent under repeated replay: no second version, same receipt.
    again=recovered.import_reviewed_candidate(candidate=c,assessment=report,decision=d,specification=s,authorization=a)
    assert again.replayed and again.receipt==result.receipt
    assert len(recovered.holder.list_records())==1 and len(recovered.ledger_store.load().receipts)==1
