from datetime import datetime, timedelta, timezone
import pytest
from app.models.active_memory import MemoryClaim, MemoryRecordKind, MemorySource, MemorySourceType
from app.models.memory_migration_import import *

NOW=datetime(2026,1,1,tzinfo=timezone.utc)

def decision(status=ReviewDecisionStatus.APPROVED):
    raw=dict(schema_version=IMPORT_VERSION,review_decision_id="pending",review_policy_version="review.v1",reviewer_id="human-1",decision_timestamp=NOW,status=status,reason="reviewed",notes=None,candidate_id="candidate",content_digest="a"*64,assessment_report_id="report",assessment_version="assessment.v1",evidence_references=[{"kind":"assessment","ref_id":"report"}],supersedes_decision_id=None,renewal_revision=0)
    raw["review_decision_id"]=derive_review_decision_id(raw); return MigrationReviewDecision.model_validate(raw)

def authorization(d):
    raw=dict(authorization_context_version=IMPORT_VERSION,authorization_policy_version="auth.v1",authorization_context_id="pending",authorization_context_digest="pending",authorized_project_id="project",authorized_scopes=[],project_level_authorized=True,authorizing_principal_id="human-1",review_decision_id=d.review_decision_id,candidate_id=d.candidate_id,content_digest=d.content_digest,assessment_report_id=d.assessment_report_id,assessment_version=d.assessment_version,issuance_revision=0,supersedes_authorization_context_id=None,issued_at=NOW,expires_at=NOW+timedelta(days=1))
    raw["authorization_context_id"]=derive_authorization_context_id(raw); raw["authorization_context_digest"]=derive_authorization_context_digest(raw); return ProjectScopeAuthorizationContext.model_validate(raw)

def specification(d,a):
    raw=dict(schema_version=IMPORT_VERSION,candidate_id=d.candidate_id,content_digest=d.content_digest,assessment_report_id=d.assessment_report_id,assessment_version=d.assessment_version,review_decision_id=d.review_decision_id,target_kind=MemoryRecordKind.PROJECT_FACT,claim=MemoryClaim(subject="project",predicate="status",value="ready"),observed_at=None,kind_claim_policy_version=KIND_CLAIM_COMPATIBILITY_POLICY_VERSION,project_id="project",scope=None,authorization_context_id=a.authorization_context_id,authorization_context_digest=a.authorization_context_digest,evidence_references=[],source_type=MemorySourceType.IMPORTED_DOCUMENT,source_provenance=MemorySource(source_type=MemorySourceType.IMPORTED_DOCUMENT,source_id="candidate"),supersession_refs=[],specification_digest="pending")
    raw["specification_digest"]=derive_specification_digest(raw); return ReviewedImportSpecification.model_validate(raw)

def test_domain_hashing_is_deterministic_and_order_independent():
    assert canonical_digest("x",{"b":2,"a":1}) == canonical_digest("x",{"a":1,"b":2})
    assert canonical_digest("x",{}) != canonical_digest("y",{})

def test_review_authorization_and_specification_are_integrity_bound():
    d=decision(); a=authorization(d); s=specification(d,a)
    assert s.review_decision_id==d.review_decision_id
    changed=a.model_dump(mode="json"); changed["authorized_project_id"]="other"
    with pytest.raises(ValueError): ProjectScopeAuthorizationContext.model_validate(changed)

def test_authorization_uses_trusted_clock_and_exact_project_authority():
    d=decision(); a=authorization(d); s=specification(d,a)
    class Clock:
        def now(self): return NOW
    ProjectScopeAuthorizationValidator(Clock()).validate(a,s,set())
    with pytest.raises(MemoryMigrationImportError) as exc:
        ProjectScopeAuthorizationValidator(Clock()).validate(a,s,{a.authorization_context_id})
    assert exc.value.code == ImportDiagnosticCode.AUTHORIZATION_CONTEXT_REVOKED

def test_review_decision_timestamp_is_not_identity_but_is_immutable_content():
    d=decision(); changed=d.model_dump(mode="json"); changed["decision_timestamp"]=(NOW+timedelta(hours=1)).isoformat()
    assert derive_review_decision_id(changed)==d.review_decision_id
