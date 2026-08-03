"""Phase 40I reviewed-persistence and verified-import contracts.

All identities use one versioned, domain-separated canonical JSON rule.  The
workflow models are frozen and forbid extra fields so caller assertions cannot
silently become authorization material.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.active_memory import (
    MemoryClaim, MemoryRecordKind, MemoryScope, MemorySource,
    MemorySourceType, SupersessionReference,
)

IMPORT_VERSION = "memory-migration-import.v1"
LEDGER_VERSION = "memory-migration-import-ledger.v1"
SNAPSHOT_VERSION = "active-memory-snapshot.v1"
KIND_CLAIM_COMPATIBILITY_POLICY_VERSION = "memory-kind-claim-policy.v1"
MAX_IMPORT_RECORDS = 4096
MAX_IMPORT_DIAGNOSTICS = 128
MAX_IMPORT_FILE_BYTES = 16 * 1024 * 1024
MAX_TEXT = 2048


def canonical_json(value: Any) -> str:
    """Return the one lossless canonical wire representation used by Phase 40I."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    def encode(item: Any) -> Any:
        if isinstance(item, BaseModel):
            return item.model_dump(mode="json")
        if isinstance(item, datetime):
            rendered = item.isoformat()
            return rendered[:-6] + "Z" if rendered.endswith("+00:00") else rendered
        raise TypeError(f"unsupported canonical value: {type(item).__name__}")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=encode)


def canonical_digest(domain: str, value: Any) -> str:
    payload = canonical_json({"domain": domain, "version": IMPORT_VERSION, "value": value})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _without(value: BaseModel | dict[str, Any], *keys: str) -> dict[str, Any]:
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for key in keys:
        data.pop(key, None)
    return data


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReviewDecisionStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ImportIntentState(StrEnum):
    INTENDED = "intended"
    COMMITTED = "committed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


class ImportDiagnosticCode(StrEnum):
    MISSING_REVIEW_DECISION = "missing_review_decision"
    REVIEW_NOT_APPROVED = "review_not_approved"
    STALE_APPROVAL = "stale_approval"
    INCOMPLETE_REVIEW_PROVENANCE = "incomplete_review_provenance"
    REVIEW_DECISION_COLLISION = "review_decision_collision"
    SUPERSESSION_TIE = "supersession_tie"
    SUPERSESSION_CYCLE = "supersession_cycle"
    MISSING_REVIEWED_SPECIFICATION = "missing_reviewed_specification"
    INVALID_REVIEWED_SPECIFICATION = "invalid_reviewed_specification"
    MISSING_CLAIM = "missing_claim"
    MALFORMED_CLAIM = "malformed_claim"
    UNSUPPORTED_CLAIM_KIND = "unsupported_claim_kind"
    KIND_CLAIM_INCOMPATIBLE = "kind_claim_incompatible"
    KIND_CLAIM_POLICY_VERSION_MISMATCH = "kind_claim_policy_version_mismatch"
    SPECIFICATION_BINDING_MISMATCH = "specification_binding_mismatch"
    SPECIFICATION_INTEGRITY_FAILURE = "specification_integrity_failure"
    MISSING_AUTHORIZATION = "missing_authorization"
    MALFORMED_AUTHORIZATION = "malformed_authorization"
    PROJECT_AUTHORIZATION_MISMATCH = "project_authorization_mismatch"
    UNAUTHORIZED_PROJECT_SCOPE = "unauthorized_project_scope"
    AUTHORIZATION_CONTEXT_MISMATCH = "authorization_context_mismatch"
    AUTHORIZATION_CONTEXT_INTEGRITY_FAILURE = "authorization_context_integrity_failure"
    AUTHORIZATION_CONTEXT_REVOKED = "authorization_context_revoked"
    AUTHORIZATION_CONTEXT_EXPIRED = "authorization_context_expired"
    INCOMPLETE_AUTHORIZATION_LINEAGE = "incomplete_authorization_lineage"
    AUTHORIZATION_LINEAGE_TIE = "authorization_lineage_tie"
    AUTHORIZATION_LINEAGE_CYCLE = "authorization_lineage_cycle"
    CANDIDATE_INTEGRITY_FAILURE = "candidate_integrity_failure"
    ASSESSMENT_MISMATCH = "assessment_mismatch"
    CONFLICTING_REPLAY = "conflicting_replay"
    RECORD_IDENTITY_COLLISION = "record_identity_collision"
    RECEIPT_INTEGRITY_FAILURE = "receipt_integrity_failure"
    CORRUPT_LEDGER = "corrupt_ledger"
    CORRUPT_ACTIVE_MEMORY_SNAPSHOT = "corrupt_active_memory_snapshot"
    SNAPSHOT_MISSING = "snapshot_missing"
    GENERATION_MISMATCH = "generation_mismatch"
    PERSISTENCE_FAILURE = "persistence_failure"
    PARTIAL_WRITE_DETECTED = "partial_write_detected"
    LOCK_UNAVAILABLE = "lock_unavailable"
    STALE_LOCK_AMBIGUOUS = "stale_lock_ambiguous"
    MALFORMED_LOCK_METADATA = "malformed_lock_metadata"
    LOCK_RELEASE_FAILURE = "lock_release_failure"
    REVISION_CONFLICT = "revision_conflict"
    UNCERTAIN_COMMIT_RESULT = "uncertain_commit_result"
    MISSING_LINKED_ATTEMPT = "missing_linked_attempt"
    MISSING_LINKED_MEMORY_RECORD = "missing_linked_memory_record"
    LIVE_STORE_REPLACEMENT_FAILURE = "live_store_replacement_failure"
    IMPORT_SERVICE_QUARANTINED = "import_service_quarantined"
    UNSUPPORTED_VERSION = "unsupported_version"
    BOUNDED_INPUT_EXCEEDED = "bounded_input_exceeded"


class ImportDiagnostic(ImportModel):
    code: ImportDiagnosticCode
    message: str = Field(max_length=512)


class MemoryMigrationImportError(Exception):
    def __init__(self, code: ImportDiagnosticCode, message: str) -> None:
        self.code = code
        self.diagnostic = ImportDiagnostic(code=code, message=message[:512])
        super().__init__(self.diagnostic.message)


class ReviewEvidenceReference(ImportModel):
    kind: str = Field(min_length=1, max_length=128)
    ref_id: str = Field(min_length=1, max_length=512)


class MigrationReviewDecision(ImportModel):
    schema_version: str = IMPORT_VERSION
    review_decision_id: str
    review_policy_version: str
    reviewer_id: str
    decision_timestamp: datetime
    status: ReviewDecisionStatus
    reason: str
    notes: str | None = None
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str
    evidence_references: tuple[ReviewEvidenceReference, ...] = ()
    supersedes_decision_id: str | None = None
    renewal_revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def integrity(self) -> "MigrationReviewDecision":
        if self.schema_version != IMPORT_VERSION or self.review_decision_id != derive_review_decision_id(self):
            raise ValueError("review decision identity mismatch")
        return self


def derive_review_decision_id(value: MigrationReviewDecision | dict[str, Any]) -> str:
    data = _without(value, "review_decision_id", "decision_timestamp", "schema_version")
    return canonical_digest("migration-import/review-decision", data)


class ProjectScopeAuthorizationContext(ImportModel):
    authorization_context_version: str = IMPORT_VERSION
    authorization_policy_version: str
    authorization_context_id: str
    authorization_context_digest: str
    authorized_project_id: str
    authorized_scopes: tuple[str, ...] = ()
    project_level_authorized: bool = False
    authorizing_principal_id: str
    review_decision_id: str
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str
    issuance_revision: int = Field(ge=0)
    supersedes_authorization_context_id: str | None = None
    issued_at: datetime
    expires_at: datetime | None = None

    @field_validator("authorized_scopes")
    @classmethod
    def scopes_are_set(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not x or len(x) > 512 for x in value) or len(value) != len(set(value)):
            raise ValueError("authorized_scopes must be a bounded unique set")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def integrity(self) -> "ProjectScopeAuthorizationContext":
        if self.authorization_context_version != IMPORT_VERSION:
            raise ValueError("unsupported authorization version")
        if self.authorization_context_id != derive_authorization_context_id(self):
            raise ValueError("authorization context identity mismatch")
        if self.authorization_context_digest != derive_authorization_context_digest(self):
            raise ValueError("authorization context integrity mismatch")
        return self


def derive_authorization_context_id(value: ProjectScopeAuthorizationContext | dict[str, Any]) -> str:
    data = _without(value, "authorization_context_id", "authorization_context_digest", "issued_at", "authorization_context_version")
    return canonical_digest("migration-import/authorization-context", data)


def derive_authorization_context_digest(value: ProjectScopeAuthorizationContext | dict[str, Any]) -> str:
    return canonical_digest("migration-import/authorization-context-integrity", _without(value, "authorization_context_digest"))


class AuthorizationRevocationEntry(ImportModel):
    authorization_revocation_id: str
    authorization_context_id: str
    issuance_revision: int = Field(ge=0)
    revoking_principal_id: str
    revocation_reason: str
    replacement_authorization_context_id: str | None = None
    revoked_at: datetime

    @model_validator(mode="after")
    def identity(self) -> "AuthorizationRevocationEntry":
        if self.authorization_revocation_id != derive_authorization_revocation_id(self):
            raise ValueError("authorization revocation identity mismatch")
        return self


def derive_authorization_revocation_id(value: AuthorizationRevocationEntry | dict[str, Any]) -> str:
    return canonical_digest("migration-import/authorization-revocation", _without(value, "authorization_revocation_id", "revoked_at"))


class MigrationProvenance(ImportModel):
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str


class ReviewedImportSpecification(ImportModel):
    schema_version: str = IMPORT_VERSION
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str
    review_decision_id: str
    target_kind: MemoryRecordKind
    claim: MemoryClaim
    observed_at: datetime | None = None
    kind_claim_policy_version: str = KIND_CLAIM_COMPATIBILITY_POLICY_VERSION
    project_id: str
    scope: MemoryScope | None = None
    authorization_context_id: str
    authorization_context_digest: str
    evidence_references: tuple[ReviewEvidenceReference, ...] = ()
    source_type: MemorySourceType = MemorySourceType.IMPORTED_DOCUMENT
    source_provenance: MemorySource
    supersession_refs: tuple[SupersessionReference, ...] = ()
    specification_digest: str

    @model_validator(mode="after")
    def integrity(self) -> "ReviewedImportSpecification":
        if self.schema_version != IMPORT_VERSION or self.source_type != MemorySourceType.IMPORTED_DOCUMENT:
            raise ValueError("invalid reviewed specification version or source")
        if self.specification_digest != derive_specification_digest(self):
            raise ValueError("specification integrity mismatch")
        return self


def derive_specification_digest(value: ReviewedImportSpecification | dict[str, Any]) -> str:
    return canonical_digest("migration-import/specification", _without(value, "specification_digest"))


def derive_idempotency_key(*, candidate_id: str, content_digest: str, assessment_report_id: str, assessment_version: str, review_decision_id: str, specification_digest: str, authorization_context_id: str) -> str:
    return canonical_digest("migration-import/reviewed-input", locals())


def derive_import_attempt_id(idempotency_key: str, attempt_sequence: int) -> str:
    return canonical_digest("migration-import/attempt", {"idempotency_key": idempotency_key, "attempt_sequence": attempt_sequence})


class MigrationImportAttempt(ImportModel):
    import_attempt_id: str
    idempotency_key: str
    attempt_sequence: int = Field(ge=1)
    review_decision_id: str
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str
    specification_digest: str
    authorization_context_id: str
    target_record_id: str
    intent_state: ImportIntentState
    commit_generation: int = Field(ge=0)
    attempt_timestamp: datetime


class VerifiedImportReceipt(ImportModel):
    receipt_version: str = IMPORT_VERSION
    receipt_id: str
    candidate_id: str
    content_digest: str
    assessment_report_id: str
    assessment_version: str
    review_decision_id: str
    specification_digest: str
    authorization_context_id: str
    authorization_context_digest: str
    idempotency_key: str
    import_attempt_id: str
    record_id: str
    record_supersedes: str | None = None
    supersession_refs: tuple[SupersessionReference, ...] = ()
    commit_generation: int = Field(ge=1)
    verification_status: str = "verified_import"
    attempt_timestamp: datetime
    verification_timestamp: datetime
    receipt_integrity_digest: str

    @model_validator(mode="after")
    def integrity(self) -> "VerifiedImportReceipt":
        if self.receipt_version != IMPORT_VERSION or self.receipt_id != derive_receipt_id(self) or self.receipt_integrity_digest != derive_receipt_integrity_digest(self):
            raise ValueError("receipt identity or integrity mismatch")
        return self


def derive_receipt_id(value: VerifiedImportReceipt | dict[str, Any]) -> str:
    d = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    members = {k: d.get(k) for k in ("idempotency_key", "import_attempt_id", "record_id", "record_supersedes", "authorization_context_id", "commit_generation")}
    return canonical_digest("migration-import/receipt", members)


def derive_receipt_integrity_digest(value: VerifiedImportReceipt | dict[str, Any]) -> str:
    return canonical_digest("migration-import/receipt-integrity", _without(value, "receipt_integrity_digest"))


def derive_record_id(record_content: dict[str, Any]) -> str:
    return canonical_digest("migration-import/record", record_content)


def derive_ledger_integrity_digest(value: BaseModel | dict[str, Any]) -> str:
    return canonical_digest("migration-import/ledger-integrity", _without(value, "ledger_integrity_digest"))


def derive_snapshot_integrity_digest(value: BaseModel | dict[str, Any]) -> str:
    return canonical_digest("migration-import/snapshot-integrity", _without(value, "snapshot_integrity_digest"))


class MigrationImportLedger(ImportModel):
    envelope_type: str = "migration-import-ledger"
    schema_version: str = LEDGER_VERSION
    ledger_revision: int = Field(default=0, ge=0)
    commit_generation: int = Field(default=0, ge=0)
    review_decisions: tuple[MigrationReviewDecision, ...] = ()
    authorization_contexts: tuple[ProjectScopeAuthorizationContext, ...] = ()
    authorization_revocations: tuple[AuthorizationRevocationEntry, ...] = ()
    specifications: tuple[ReviewedImportSpecification, ...] = ()
    attempts: tuple[MigrationImportAttempt, ...] = ()
    receipts: tuple[VerifiedImportReceipt, ...] = ()
    quarantined: bool = False
    quarantine_reason: str | None = None
    ledger_integrity_digest: str

    @model_validator(mode="after")
    def integrity(self) -> "MigrationImportLedger":
        if self.schema_version != LEDGER_VERSION or self.ledger_integrity_digest != derive_ledger_integrity_digest(self):
            raise ValueError("ledger integrity mismatch")
        return self


class ActiveMemorySnapshotEnvelope(ImportModel):
    envelope_type: str = "active-memory-snapshot"
    schema_version: str = SNAPSHOT_VERSION
    commit_generation: int = Field(ge=0)
    active_memory: dict[str, Any]
    snapshot_integrity_digest: str

    @model_validator(mode="after")
    def integrity(self) -> "ActiveMemorySnapshotEnvelope":
        if self.schema_version != SNAPSHOT_VERSION or self.snapshot_integrity_digest != derive_snapshot_integrity_digest(self):
            raise ValueError("snapshot integrity mismatch")
        return self


class TrustedClock(Protocol):
    def now(self) -> datetime: ...


class SystemUtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class KindClaimCompatibilityValidator:
    """Closed v1 policy; claim shape is already enforced by MemoryClaim."""
    def validate(self, specification: ReviewedImportSpecification) -> None:
        if specification.kind_claim_policy_version != KIND_CLAIM_COMPATIBILITY_POLICY_VERSION:
            raise MemoryMigrationImportError(ImportDiagnosticCode.KIND_CLAIM_POLICY_VERSION_MISMATCH, "kind/claim policy version is unsupported")
        # Current Active Memory kinds all accept its single bounded scalar claim shape.
        if specification.target_kind not in set(MemoryRecordKind):
            raise MemoryMigrationImportError(ImportDiagnosticCode.UNSUPPORTED_CLAIM_KIND, "claim kind is unsupported")


class ProjectScopeAuthorizationValidator:
    def __init__(self, clock: TrustedClock) -> None:
        self.clock = clock

    def validate(self, context: ProjectScopeAuthorizationContext, specification: ReviewedImportSpecification, revoked_ids: set[str]) -> None:
        if context.authorized_project_id != specification.project_id:
            raise MemoryMigrationImportError(ImportDiagnosticCode.PROJECT_AUTHORIZATION_MISMATCH, "authorization project does not match specification")
        if context.authorization_context_id in revoked_ids:
            raise MemoryMigrationImportError(ImportDiagnosticCode.AUTHORIZATION_CONTEXT_REVOKED, "authorization context is revoked")
        now = self.clock.now()
        if now.tzinfo is None or (context.expires_at is not None and (context.expires_at.tzinfo is None or now >= context.expires_at)):
            raise MemoryMigrationImportError(ImportDiagnosticCode.AUTHORIZATION_CONTEXT_EXPIRED, "authorization context is expired or has an invalid timestamp")
        if specification.scope is None:
            if not context.project_level_authorized:
                raise MemoryMigrationImportError(ImportDiagnosticCode.UNAUTHORIZED_PROJECT_SCOPE, "project-level import is not authorized")
        elif canonical_json(specification.scope.model_dump(mode="json")) not in context.authorized_scopes:
            raise MemoryMigrationImportError(ImportDiagnosticCode.UNAUTHORIZED_PROJECT_SCOPE, "requested scope is not an exact authorized member")
        bindings = ("review_decision_id", "candidate_id", "content_digest", "assessment_report_id", "assessment_version")
        if any(getattr(context, name) != getattr(specification, name) for name in bindings):
            raise MemoryMigrationImportError(ImportDiagnosticCode.AUTHORIZATION_CONTEXT_MISMATCH, "authorization binding does not match reviewed specification")
        if context.authorization_context_id != specification.authorization_context_id or context.authorization_context_digest != specification.authorization_context_digest:
            raise MemoryMigrationImportError(ImportDiagnosticCode.AUTHORIZATION_CONTEXT_MISMATCH, "authorization identity does not match reviewed specification")
