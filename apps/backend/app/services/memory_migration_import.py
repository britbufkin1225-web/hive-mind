"""Publish-last coordinator for human-approved migration imports."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from app.models.active_memory import LifecycleState, MemoryRecord, VerificationState
from app.models.memory_migration_projection import MemoryMigrationCandidate, derive_candidate_content_digest
from app.models.memory_migration_candidate_assessment import MigrationCandidateAssessmentReport
from app.models.memory_migration_import import *
from app.services.active_memory_snapshot_store import ActiveMemorySnapshotStore
from app.services.active_memory_store_holder import AuthoritativeActiveMemoryStoreHolder
from app.services.memory_migration_import_store import MigrationImportStore
from app.services.migration_import_lock import MigrationImportLock
from app.store.active_memory_store import DuplicateRecordError, InMemoryActiveMemoryStore

@dataclass(frozen=True)
class ImportResult:
    receipt: VerifiedImportReceipt
    replayed: bool = False

class MemoryMigrationImportService:
    def __init__(self, ledger_store: MigrationImportStore, snapshot_store: ActiveMemorySnapshotStore, holder: AuthoritativeActiveMemoryStoreHolder, *, lock: MigrationImportLock | None=None, clock: TrustedClock | None=None) -> None:
        self.ledger_store=ledger_store; self.snapshot_store=snapshot_store; self.holder=holder
        self.lock=lock or MigrationImportLock(); self.clock=clock or SystemUtcClock()

    def initialize(self) -> None:
        self.lock.acquire("startup")
        try:
            ledger_exists=self.ledger_store.exists(); snapshot_exists=self.snapshot_store.exists()
            if not ledger_exists and not snapshot_exists:
                empty=self.ledger_store.empty(); self.ledger_store.persist(empty)
                self.snapshot_store.persist(InMemoryActiveMemoryStore(), 0)
                self.holder.clear_quarantine(); return
            if ledger_exists != snapshot_exists:
                self._quarantine(ImportDiagnosticCode.GENERATION_MISMATCH, "only one durable artifact exists")
            ledger=self.ledger_store.load(); snap=self.snapshot_store.load()
            if ledger.commit_generation != snap.commit_generation:
                self._quarantine(ImportDiagnosticCode.GENERATION_MISMATCH, "durable generations do not match")
            # Startup publishes an equal-generation snapshot without exposing the raw store.
            current=self.holder.current_generation()
            if current < snap.commit_generation:
                self.holder.publish(snap.store, current, snap.commit_generation) if snap.commit_generation == current+1 else self._quarantine(ImportDiagnosticCode.GENERATION_MISMATCH,"live generation cannot be advanced safely")
            self.holder.clear_quarantine()
        finally: self.lock.release()

    def import_reviewed_candidate(self, *, candidate: MemoryMigrationCandidate, assessment: MigrationCandidateAssessmentReport, decision: MigrationReviewDecision, specification: ReviewedImportSpecification, authorization: ProjectScopeAuthorizationContext) -> ImportResult:
        key=derive_idempotency_key(candidate_id=candidate.candidate_id,content_digest=candidate.content_digest,assessment_report_id=assessment.report_id,assessment_version=assessment.assessment_version,review_decision_id=decision.review_decision_id,specification_digest=specification.specification_digest,authorization_context_id=authorization.authorization_context_id)
        self.lock.acquire(key)
        try:
            ledger, loaded=self._load_pair()
            if ledger.quarantined or self.holder.quarantine_state().quarantined:
                raise MemoryMigrationImportError(ImportDiagnosticCode.IMPORT_SERVICE_QUARANTINED,"reviewed import is quarantined")
            existing=next((r for r in ledger.receipts if r.idempotency_key==key),None)
            if existing:
                if existing.receipt_integrity_digest != derive_receipt_integrity_digest(existing): self._quarantine(ImportDiagnosticCode.RECEIPT_INTEGRITY_FAILURE,"stored receipt integrity failed")
                return ImportResult(existing, True)
            self._validate(candidate,assessment,decision,specification,authorization,ledger)
            record=self._record(decision,specification)
            sequence=1+sum(a.idempotency_key==key for a in ledger.attempts)
            now=self.clock.now()
            attempt=MigrationImportAttempt(import_attempt_id=derive_import_attempt_id(key,sequence),idempotency_key=key,attempt_sequence=sequence,review_decision_id=decision.review_decision_id,candidate_id=candidate.candidate_id,content_digest=candidate.content_digest,assessment_report_id=assessment.report_id,assessment_version=assessment.assessment_version,specification_digest=specification.specification_digest,authorization_context_id=authorization.authorization_context_id,target_record_id=record.record_id,intent_state=ImportIntentState.INTENDED,commit_generation=ledger.commit_generation,attempt_timestamp=now)
            ledger=self.ledger_store.replace(ledger,review_decisions=self._append_unique(ledger.review_decisions,decision,"review_decision_id"),authorization_contexts=self._append_unique(ledger.authorization_contexts,authorization,"authorization_context_id"),specifications=self._append_unique(ledger.specifications,specification,"specification_digest"),attempts=[*ledger.attempts,attempt])
            candidate_store=InMemoryActiveMemoryStore.restore(loaded.store.serialize())
            try: candidate_store.insert(record)
            except DuplicateRecordError:
                if candidate_store.get(record.record_id).model_dump(mode="json") != record.model_dump(mode="json"):
                    raise MemoryMigrationImportError(ImportDiagnosticCode.RECORD_IDENTITY_COLLISION,"record identity collides with different content")
            generation=ledger.commit_generation+1
            self.snapshot_store.persist(candidate_store,generation)
            receipt=self._receipt(candidate,assessment,decision,specification,authorization,attempt,record,generation,now)
            committed=attempt.model_copy(update={"intent_state":ImportIntentState.COMMITTED})
            attempts=[committed if a.import_attempt_id==attempt.import_attempt_id else a for a in ledger.attempts]
            ledger=self.ledger_store.replace(ledger,attempts=attempts,receipts=[*ledger.receipts,receipt],commit_generation=generation)
            check_ledger, check_snapshot=self._load_pair()
            if check_ledger.commit_generation!=generation or check_snapshot.store.find(record.record_id).model_dump(mode="json")!=record.model_dump(mode="json"):
                self._quarantine(ImportDiagnosticCode.UNCERTAIN_COMMIT_RESULT,"durable commit linkage could not be verified")
            try: self.holder.publish(check_snapshot.store,generation-1,generation)
            except MemoryMigrationImportError:
                self._quarantine(ImportDiagnosticCode.LIVE_STORE_REPLACEMENT_FAILURE,"durable commit succeeded but live publication failed")
            return ImportResult(receipt)
        except MemoryMigrationImportError: raise
        except Exception as exc:
            raise MemoryMigrationImportError(ImportDiagnosticCode.PERSISTENCE_FAILURE,"reviewed import failed before verified publication") from exc
        finally: self.lock.release()

    def revoke_authorization(self, context: ProjectScopeAuthorizationContext, *, principal_id: str, reason: str, replacement_id: str|None=None) -> AuthorizationRevocationEntry:
        self.lock.acquire(context.authorization_context_id)
        try:
            ledger,_=self._load_pair(); now=self.clock.now()
            raw={"authorization_context_id":context.authorization_context_id,"issuance_revision":context.issuance_revision,"revoking_principal_id":principal_id,"revocation_reason":reason,"replacement_authorization_context_id":replacement_id,"revoked_at":now}
            raw["authorization_revocation_id"]=derive_authorization_revocation_id(raw)
            entry=AuthorizationRevocationEntry.model_validate(raw)
            if not any(x.authorization_revocation_id==entry.authorization_revocation_id for x in ledger.authorization_revocations):
                self.ledger_store.replace(ledger,authorization_revocations=[*ledger.authorization_revocations,entry])
            return entry
        finally: self.lock.release()

    def _load_pair(self):
        if not self.ledger_store.exists() and not self.snapshot_store.exists():
            ledger=self.ledger_store.empty(); self.ledger_store.persist(ledger); self.snapshot_store.persist(InMemoryActiveMemoryStore(),0)
        if self.ledger_store.exists()!=self.snapshot_store.exists(): self._quarantine(ImportDiagnosticCode.GENERATION_MISMATCH,"durable artifacts are incomplete")
        ledger=self.ledger_store.load(); snap=self.snapshot_store.load()
        if snap.commit_generation == ledger.commit_generation + 1:
            ledger = self._recover_uncertain(ledger, snap)
        elif ledger.commit_generation!=snap.commit_generation:
            self._quarantine(ImportDiagnosticCode.GENERATION_MISMATCH,"durable generations do not match")
        return ledger,snap

    def _recover_uncertain(self, ledger, snap):
        """Finalize only the single integrity-verified N/N+1 intent state."""
        intended=[a for a in ledger.attempts if a.intent_state==ImportIntentState.INTENDED and a.commit_generation==ledger.commit_generation]
        if len(intended)!=1:
            self._quarantine(ImportDiagnosticCode.UNCERTAIN_COMMIT_RESULT,"N/N+1 recovery has no unique durable intent")
        attempt=intended[0]; record=snap.store.find(attempt.target_record_id)
        spec=next((x for x in ledger.specifications if x.specification_digest==attempt.specification_digest),None)
        auth=next((x for x in ledger.authorization_contexts if x.authorization_context_id==attempt.authorization_context_id),None)
        decision=next((x for x in ledger.review_decisions if x.review_decision_id==attempt.review_decision_id),None)
        if record is None or spec is None or auth is None or decision is None:
            self._quarantine(ImportDiagnosticCode.MISSING_LINKED_MEMORY_RECORD,"uncertain commit linkage is incomplete")
        revoked={x.authorization_context_id for x in ledger.authorization_revocations}
        ProjectScopeAuthorizationValidator(self.clock).validate(auth,spec,revoked)
        expected=self._record(decision,spec)
        if expected.model_dump(mode="json")!=record.model_dump(mode="json"):
            self._quarantine(ImportDiagnosticCode.RECORD_IDENTITY_COLLISION,"uncertain commit record content differs")
        raw={"receipt_version":IMPORT_VERSION,"candidate_id":attempt.candidate_id,"content_digest":attempt.content_digest,"assessment_report_id":attempt.assessment_report_id,"assessment_version":attempt.assessment_version,"review_decision_id":attempt.review_decision_id,"specification_digest":spec.specification_digest,"authorization_context_id":auth.authorization_context_id,"authorization_context_digest":auth.authorization_context_digest,"idempotency_key":attempt.idempotency_key,"import_attempt_id":attempt.import_attempt_id,"record_id":record.record_id,"record_supersedes":spec.supersession_refs[0].target_record_id if spec.supersession_refs else None,"supersession_refs":spec.supersession_refs,"commit_generation":snap.commit_generation,"verification_status":"verified_import","attempt_timestamp":attempt.attempt_timestamp,"verification_timestamp":self.clock.now(),"receipt_id":"","receipt_integrity_digest":""}
        raw["receipt_id"]=derive_receipt_id(raw); raw["receipt_integrity_digest"]=derive_receipt_integrity_digest(raw)
        receipt=VerifiedImportReceipt.model_validate(raw)
        committed=attempt.model_copy(update={"intent_state":ImportIntentState.COMMITTED})
        attempts=[committed if x.import_attempt_id==attempt.import_attempt_id else x for x in ledger.attempts]
        updated=self.ledger_store.replace(ledger,attempts=attempts,receipts=[*ledger.receipts,receipt],commit_generation=snap.commit_generation)
        if self.holder.current_generation()==ledger.commit_generation:
            self.holder.publish(snap.store,ledger.commit_generation,snap.commit_generation)
        return updated

    def _validate(self,candidate,assessment,decision,specification,authorization,ledger):
        if derive_candidate_content_digest(candidate.content)!=candidate.content_digest or candidate.content_digest!=decision.content_digest:
            raise MemoryMigrationImportError(ImportDiagnosticCode.CANDIDATE_INTEGRITY_FAILURE,"candidate content integrity failed")
        if candidate.candidate_id!=decision.candidate_id or assessment.report_id!=decision.assessment_report_id or assessment.assessment_version!=decision.assessment_version:
            raise MemoryMigrationImportError(ImportDiagnosticCode.ASSESSMENT_MISMATCH,"candidate or assessment binding changed")
        if not decision.reviewer_id or not decision.reason or not decision.evidence_references:
            raise MemoryMigrationImportError(ImportDiagnosticCode.INCOMPLETE_REVIEW_PROVENANCE,"review provenance is incomplete")
        if decision.status != ReviewDecisionStatus.APPROVED:
            raise MemoryMigrationImportError(ImportDiagnosticCode.REVIEW_NOT_APPROVED,"review decision is not approved")
        binding=("candidate_id","content_digest","review_decision_id")
        if any(getattr(specification,x)!=getattr(decision,x) for x in binding) or specification.assessment_report_id!=assessment.report_id or specification.assessment_version!=assessment.assessment_version:
            raise MemoryMigrationImportError(ImportDiagnosticCode.SPECIFICATION_BINDING_MISMATCH,"reviewed specification binding does not match")
        KindClaimCompatibilityValidator().validate(specification)
        revoked={x.authorization_context_id for x in ledger.authorization_revocations}
        ProjectScopeAuthorizationValidator(self.clock).validate(authorization,specification,revoked)

    def _record(self,decision,spec):
        provenance=MigrationProvenance(candidate_id=spec.candidate_id,content_digest=spec.content_digest,assessment_report_id=spec.assessment_report_id,assessment_version=spec.assessment_version)
        content={"kind":spec.target_kind,"claim":spec.claim,"project_id":spec.project_id,"scope":spec.scope,"source":spec.source_provenance,"verification_state":VerificationState.UNVERIFIED,"lifecycle_state":LifecycleState.INACTIVE,"confidence":None,"evidence_ids":[],"verification":None,"supersession_refs":list(spec.supersession_refs),"observed_at":spec.observed_at,"created_at":decision.decision_timestamp,"metadata":{"migration_provenance":provenance.model_dump(mode="json")}}
        json_content={k:(v.model_dump(mode="json") if isinstance(v,BaseModel) else [x.model_dump(mode="json") for x in v] if isinstance(v,list) and v and isinstance(v[0],BaseModel) else v) for k,v in content.items()}
        return MemoryRecord(record_id=derive_record_id(json_content),**content)

    def _receipt(self,candidate,assessment,decision,spec,auth,attempt,record,generation,now):
        raw={"candidate_id":candidate.candidate_id,"content_digest":candidate.content_digest,"assessment_report_id":assessment.report_id,"assessment_version":assessment.assessment_version,"review_decision_id":decision.review_decision_id,"specification_digest":spec.specification_digest,"authorization_context_id":auth.authorization_context_id,"authorization_context_digest":auth.authorization_context_digest,"idempotency_key":attempt.idempotency_key,"import_attempt_id":attempt.import_attempt_id,"record_id":record.record_id,"record_supersedes":spec.supersession_refs[0].target_record_id if spec.supersession_refs else None,"supersession_refs":spec.supersession_refs,"commit_generation":generation,"attempt_timestamp":attempt.attempt_timestamp,"verification_timestamp":now,"receipt_id":"","receipt_integrity_digest":""}
        raw["receipt_version"] = IMPORT_VERSION
        raw["verification_status"] = "verified_import"
        raw["receipt_id"]=derive_receipt_id(raw); raw["receipt_integrity_digest"]=derive_receipt_integrity_digest(raw)
        return VerifiedImportReceipt.model_validate(raw)

    @staticmethod
    def _append_unique(items,item,key):
        old=next((x for x in items if getattr(x,key)==getattr(item,key)),None)
        if old and old.model_dump(mode="json")!=item.model_dump(mode="json"):
            raise MemoryMigrationImportError(ImportDiagnosticCode.CONFLICTING_REPLAY,"immutable workflow identity has conflicting material")
        return list(items) if old else [*items,item]

    def _quarantine(self,code,message):
        self.holder.quarantine(code.value)
        try:
            if self.ledger_store.exists():
                ledger=self.ledger_store.load(); self.ledger_store.replace(ledger,quarantined=True,quarantine_reason=code.value)
        except Exception: pass
        raise MemoryMigrationImportError(ImportDiagnosticCode.IMPORT_SERVICE_QUARANTINED,message)
