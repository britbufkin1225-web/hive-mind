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

def candidate():
    provenance=MigrationCandidateProvenance(bundle_id="bundle",bundle_fingerprint="mm-bundle-"+"0"*24,source_artifact_id="artifact",source_artifact_fingerprint="mm-artifact-"+"0"*24,source_artifact_format=MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,source_container=MigrationContainerKind.SINGLE_FILE,observed_digest_algorithm=MigrationDigestAlgorithm.SHA256,observed_digest_value="c"*64,custody=MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,source=MemorySource(source_type=MemorySourceType.CHATGPT,source_id="source"),source_local_id="conversation:1",source_role=MigrationCandidateRole.USER)
    digest=derive_candidate_content_digest("reviewed text")
    cid=derive_candidate_id(bundle_fingerprint=provenance.bundle_fingerprint,artifact_fingerprint=provenance.source_artifact_fingerprint,source_local_id=provenance.source_local_id,role=provenance.source_role.value,source_sequence_index=0,chunk_index=0,content_digest=digest)
    return MemoryMigrationCandidate(candidate_id=cid,content="reviewed text",content_digest=digest,chunk_index=0,chunk_count=1,source_sequence_index=0,provenance=provenance)

def workflow(c, report, status=ReviewDecisionStatus.APPROVED):
    d=dict(schema_version=IMPORT_VERSION,review_decision_id="",review_policy_version="review.v1",reviewer_id="human",decision_timestamp=NOW,status=status,reason="reviewed",notes=None,candidate_id=c.candidate_id,content_digest=c.content_digest,assessment_report_id=report.report_id,assessment_version=report.assessment_version,evidence_references=[{"kind":"assessment","ref_id":report.report_id}],supersedes_decision_id=None,renewal_revision=0); d["review_decision_id"]=derive_review_decision_id(d); decision=MigrationReviewDecision.model_validate(d)
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
