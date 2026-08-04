"""Phase 40K.5 — genuinely read-only production migration preflight.

This service is the read-only orchestration seam Phase 40K identified as missing
(runbook §2, §7, §12). It deterministically evaluates a
:class:`~app.models.migration_readiness.MigrationReadinessManifest` and returns a
bounded, non-secret :class:`PreflightReport` with a ``pass`` / ``blocked`` /
``fail_closed`` outcome.

It is read-only *by construction*, not merely by description:

* It imports and touches **no** store, holder, ledger, snapshot, lock, attempt,
  receipt, authorization registry, or filesystem/network resource. Its only
  dependency is an injected :class:`~app.models.memory_migration_import.TrustedClock`
  used to evaluate declared expiry/staleness through the established boundary —
  never ambient ``datetime.now``.
* ``evaluate`` is a pure function of ``(manifest, clock)``: identical inputs
  always yield an identical report, so the evidence is reproducible and diffable.
* Nothing here can promote a field-state, authorize execution, or mutate anything.

Outcome discipline (the phase's "reject rather than normalize ambiguity" rule):

* ``not_supplied`` / ``unverified`` / ``blocked`` field-states are honest
  not-ready signals → **blocked**.
* A supplied value that is a placeholder/fixture/demonstration or is secret-like,
  a malformed declared timestamp, or a weak dataset digest algorithm is a
  *deceptive or dangerous* input → **fail_closed** (rejected), never blocked.
* ``pass`` requires every execution-required check ``verified`` **and** no active
  stop condition. A passing preflight is a *repository/readiness* result only; it
  never authorizes production execution (that is the separate execution gate).
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.memory_migration_import import SystemUtcClock, TrustedClock
from app.models.migration_readiness import (
    FieldState,
    MigrationReadinessManifest,
    is_supplied,
    looks_like_placeholder,
    looks_like_secret,
)

TOOL_VERSION = "migration-readiness-preflight.v1"
# Declared trusted evidence older than this (relative to the injected clock) is
# treated as stale. One rollback-window-friendly day; the runbook leaves the true
# retention window to the human owner, this only guards against clearly-stale
# preflight evidence being reused.
DEFAULT_MAX_EVIDENCE_AGE_SECONDS = 24 * 60 * 60
MAX_REPORT_ITEMS = 128


class PreflightOutcome(StrEnum):
    PASS = "pass"
    BLOCKED = "blocked"
    FAIL_CLOSED = "fail_closed"


class CheckState(StrEnum):
    """Per-check result. ``rejected`` is the fail-closed, deceptive-input state."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    NOT_SUPPLIED = "not_supplied"
    BLOCKED = "blocked"
    CONFLICTING = "conflicting"
    REJECTED = "rejected"


class ReadinessCheckId(StrEnum):
    REPOSITORY_IMPLEMENTATION_IDENTITY = "repository_implementation_identity"
    DATASET_FINGERPRINT = "dataset_fingerprint"
    DATASET_FINGERPRINT_CONFLICT = "dataset_fingerprint_conflict"
    DATASET_DIGEST_ALGORITHM = "dataset_digest_algorithm"
    PIPELINE_IDENTITY = "pipeline_identity"
    DESTINATION_REVISION = "destination_revision"
    DESTINATION_REVISION_VERIFICATION = "destination_revision_verification"
    DESTINATION_REVISION_CONFLICT = "destination_revision_conflict"
    DESTINATION_CAPACITY = "destination_capacity"
    WRITER_EXCLUSION = "writer_exclusion"
    BACKUP_IDENTITY = "backup_identity"
    BACKUP_VERIFICATION = "backup_verification"
    RESTORATION_READINESS = "restoration_readiness"
    AUTHORIZATION_PRESENCE = "authorization_presence"
    AUTHORIZATION_INTEGRITY = "authorization_integrity"
    AUTHORIZATION_SCOPE = "authorization_scope"
    AUTHORIZATION_EXPIRY = "authorization_expiry"
    AUTHORIZATION_REVOCATION = "authorization_revocation"
    TRUSTED_TIME = "trusted_time"
    EXPECTED_COUNTS = "expected_counts"
    COUNT_CONSISTENCY = "count_consistency"
    EXPECTED_RECEIPT_IDENTITY = "expected_receipt_identity"
    EVIDENCE_DESTINATION = "evidence_destination"
    RECOVERY_MATERIALS = "recovery_materials"
    STALE_EVIDENCE = "stale_evidence"
    STOP_CONDITIONS = "stop_conditions"
    PLACEHOLDER_INPUTS = "placeholder_inputs"
    SECRET_LEAKAGE = "secret_leakage"
    PRODUCTION_ORCHESTRATION = "production_read_only_orchestration"


class ReadinessBlockedCode(StrEnum):
    MANIFEST_MALFORMED = "manifest_malformed"
    REQUIRED_STATE_NOT_VERIFIED = "required_state_not_verified"
    OPERATIONAL_VALUE_NOT_SUPPLIED = "operational_value_not_supplied"
    DATASET_FINGERPRINT_CONFLICT = "dataset_fingerprint_conflict"
    DATASET_DIGEST_ALGORITHM_WEAK = "dataset_digest_algorithm_weak"
    DESTINATION_REVISION_CONFLICT = "destination_revision_conflict"
    DESTINATION_REVISION_UNVERIFIED = "destination_revision_unverified"
    BACKUP_UNVERIFIED = "backup_unverified"
    RESTORATION_UNVERIFIED = "restoration_unverified"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_SCOPE_UNVERIFIED = "authorization_scope_unverified"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_REVOKED = "authorization_revoked"
    AUTHORIZATION_REVOCATION_UNVERIFIED = "authorization_revocation_unverified"
    TRUSTED_TIME_UNTRUSTED = "trusted_time_untrusted"
    COUNT_MISMATCH = "count_mismatch"
    STALE_EVIDENCE = "stale_evidence"
    MALFORMED_TIMESTAMP = "malformed_timestamp"
    STOP_CONDITION_ACTIVE = "stop_condition_active"
    PLACEHOLDER_VALUE_REJECTED = "placeholder_value_rejected"
    SECRET_LIKE_VALUE_REJECTED = "secret_like_value_rejected"
    PRODUCTION_ORCHESTRATION_BLOCKED = "production_read_only_orchestration_blocked"


class PreflightCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    check_id: ReadinessCheckId
    state: CheckState
    blocked_reason: ReadinessBlockedCode | None = None
    detail: str = Field(default="", max_length=256)


class PreflightEvidence(BaseModel):
    """Bounded, non-secret evidence suitable for a shareable review packet."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest_identity: str
    schema_version: str
    runbook_version: str
    tool_version: str
    repository_baseline_commit: str
    repository_execution_commit: str
    destination_revision: str
    authorization_identifier: str
    backup_identifier: str
    expected_counts: dict[str, int] = Field(default_factory=dict)
    supplied_field_summary: dict[str, str] = Field(default_factory=dict)
    active_stop_conditions: tuple[str, ...] = ()


class PreflightReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    outcome: PreflightOutcome
    manifest_identity: str
    tool_version: str = TOOL_VERSION
    evaluated_at: datetime | None = None
    checks: tuple[PreflightCheckResult, ...] = ()
    blocked_reasons: tuple[ReadinessBlockedCode, ...] = ()
    active_stop_conditions: tuple[str, ...] = ()
    evidence: PreflightEvidence | None = None

    @property
    def is_pass(self) -> bool:
        return self.outcome is PreflightOutcome.PASS


_REDACTED = "[redacted]"


def _safe_identifier(value: str) -> str:
    """Pass a declared non-secret id through, redacting anything secret-shaped."""
    if is_supplied(value) and looks_like_secret(value):
        return _REDACTED
    return value


class MigrationReadinessPreflight:
    """Deterministic, read-only readiness evaluator (a dedicated domain boundary)."""

    def __init__(
        self,
        *,
        clock: TrustedClock | None = None,
        max_evidence_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
    ) -> None:
        self._clock = clock or SystemUtcClock()
        self._max_age = max_evidence_age_seconds

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def evaluate_mapping(self, raw: object) -> PreflightReport:
        """Parse an untrusted mapping and evaluate it; malformed → fail_closed."""
        try:
            manifest = MigrationReadinessManifest.model_validate(raw)
        except ValidationError as exc:
            return self._malformed_report(str(exc))
        return self.evaluate(manifest)

    def evaluate(self, manifest: MigrationReadinessManifest) -> PreflightReport:
        now = self._trusted_now()
        checks: list[PreflightCheckResult] = []
        checks.extend(self._structural_checks(manifest, now))
        checks.extend(self._deception_checks(manifest))
        checks.append(self._stop_condition_check(manifest))

        rejected = [c for c in checks if c.state is CheckState.REJECTED]
        not_verified = [c for c in checks if c.state not in (CheckState.VERIFIED,)]
        active = manifest.stop_conditions.active_conditions

        if rejected:
            outcome = PreflightOutcome.FAIL_CLOSED
        elif not not_verified and not active:
            outcome = PreflightOutcome.PASS
        else:
            outcome = PreflightOutcome.BLOCKED

        blocked_reasons = tuple(
            dict.fromkeys(c.blocked_reason for c in checks if c.blocked_reason)
        )[:MAX_REPORT_ITEMS]
        return PreflightReport(
            outcome=outcome,
            manifest_identity=manifest.identity(),
            evaluated_at=now,
            checks=tuple(checks[:MAX_REPORT_ITEMS]),
            blocked_reasons=blocked_reasons,
            active_stop_conditions=active,
            evidence=self._evidence(manifest, active),
        )

    # ------------------------------------------------------------------ #
    # Structural (state/consistency) checks
    # ------------------------------------------------------------------ #
    def _structural_checks(
        self, m: MigrationReadinessManifest, now: datetime | None
    ) -> list[PreflightCheckResult]:
        out: list[PreflightCheckResult] = []

        out.append(self._state_check(
            ReadinessCheckId.REPOSITORY_IMPLEMENTATION_IDENTITY,
            m.repository.implementation_identity_state,
            supplied=is_supplied(m.repository.execution_commit),
        ))
        out.append(self._state_check(
            ReadinessCheckId.DATASET_FINGERPRINT,
            m.preflight.dataset_fingerprint_state,
            supplied=is_supplied(m.source_dataset.digest),
        ))
        out.append(self._dataset_conflict_check(m))
        out.append(self._dataset_algorithm_check(m))
        out.append(self._state_check(
            ReadinessCheckId.PIPELINE_IDENTITY, m.pipeline.state,
            supplied=is_supplied(m.pipeline.parser_identity),
        ))
        out.append(self._state_check(
            ReadinessCheckId.DESTINATION_REVISION, m.preflight.destination_revision_state,
            supplied=is_supplied(m.destination.ledger_revision),
        ))
        out.append(self._destination_revision_verification_check(m))
        out.append(self._destination_revision_conflict_check(m))
        out.append(self._state_check(
            ReadinessCheckId.DESTINATION_CAPACITY, m.destination.capacity_state,
        ))
        out.append(self._state_check(
            ReadinessCheckId.WRITER_EXCLUSION,
            m.destination.concurrent_writer_exclusion_state,
        ))
        out.append(self._state_check(
            ReadinessCheckId.BACKUP_IDENTITY, m.backup.state,
            supplied=is_supplied(m.backup.non_secret_backup_id),
            reason=ReadinessBlockedCode.BACKUP_UNVERIFIED,
        ))
        out.append(self._backup_verification_check(m))
        out.append(self._state_check(
            ReadinessCheckId.RESTORATION_READINESS,
            m.backup.isolated_restoration_rehearsal_state,
            reason=ReadinessBlockedCode.RESTORATION_UNVERIFIED,
        ))
        out.append(self._state_check(
            ReadinessCheckId.AUTHORIZATION_PRESENCE, m.authorization.state,
            supplied=is_supplied(m.authorization.non_secret_authorization_id),
            reason=ReadinessBlockedCode.AUTHORIZATION_MISSING,
        ))
        out.append(self._authorization_integrity_check(m))
        out.append(self._authorization_scope_check(m))
        out.append(self._authorization_expiry_check(m, now))
        out.append(self._authorization_revocation_check(m))
        out.append(self._trusted_time_check(m, now))
        out.append(self._state_check(
            ReadinessCheckId.EXPECTED_COUNTS, m.expected_counts.state,
        ))
        out.append(self._count_consistency_check(m))
        out.append(self._state_check(
            ReadinessCheckId.EXPECTED_RECEIPT_IDENTITY, m.preflight.expected_write_set_state,
            supplied=is_supplied(m.preflight.expected_receipt_identity),
        ))
        out.append(self._state_check(
            ReadinessCheckId.EVIDENCE_DESTINATION, m.preflight.evidence_destination_state,
        ))
        out.append(self._state_check(
            ReadinessCheckId.RECOVERY_MATERIALS, m.preflight.recovery_materials_state,
        ))
        out.append(self._stale_evidence_check(m, now))
        out.append(self._production_orchestration_check(m))
        return out

    def _state_check(
        self,
        check_id: ReadinessCheckId,
        state: FieldState,
        *,
        supplied: bool = True,
        reason: ReadinessBlockedCode = ReadinessBlockedCode.REQUIRED_STATE_NOT_VERIFIED,
    ) -> PreflightCheckResult:
        if state is FieldState.VERIFIED and supplied:
            return PreflightCheckResult(check_id=check_id, state=CheckState.VERIFIED)
        if state is FieldState.CONFLICTING:
            return PreflightCheckResult(
                check_id=check_id, state=CheckState.CONFLICTING, blocked_reason=reason,
            )
        if not supplied or state is FieldState.NOT_SUPPLIED:
            return PreflightCheckResult(
                check_id=check_id, state=CheckState.NOT_SUPPLIED,
                blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
            )
        if state is FieldState.BLOCKED:
            return PreflightCheckResult(
                check_id=check_id, state=CheckState.BLOCKED, blocked_reason=reason,
            )
        return PreflightCheckResult(
            check_id=check_id, state=CheckState.UNVERIFIED, blocked_reason=reason,
        )

    def _dataset_conflict_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.DATASET_FINGERPRINT_CONFLICT
        d, r = m.source_dataset.digest, m.source_dataset.reviewed_digest
        if is_supplied(d) and is_supplied(r) and d != r:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.CONFLICTING,
                blocked_reason=ReadinessBlockedCode.DATASET_FINGERPRINT_CONFLICT,
                detail="declared digest differs from reviewed digest",
            )
        if is_supplied(d) and is_supplied(r):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.NOT_SUPPLIED,
            blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
        )

    def _dataset_algorithm_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        from app.models.migration_readiness import ACCEPTED_DIGEST_ALGORITHMS
        cid = ReadinessCheckId.DATASET_DIGEST_ALGORITHM
        algo = m.source_dataset.digest_algorithm.strip().lower()
        if algo not in ACCEPTED_DIGEST_ALGORITHMS:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.REJECTED,
                blocked_reason=ReadinessBlockedCode.DATASET_DIGEST_ALGORITHM_WEAK,
                detail="dataset digest algorithm is too weak",
            )
        # Strong algorithm named, but only meaningful once a digest is present.
        if is_supplied(m.source_dataset.digest):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.NOT_SUPPLIED,
            blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
        )

    def _destination_revision_verification_check(
        self, m: MigrationReadinessManifest
    ) -> PreflightCheckResult:
        return self._state_check(
            ReadinessCheckId.DESTINATION_REVISION_VERIFICATION,
            m.destination.revision_verification_state,
            reason=ReadinessBlockedCode.DESTINATION_REVISION_UNVERIFIED,
        )

    def _destination_revision_conflict_check(
        self, m: MigrationReadinessManifest
    ) -> PreflightCheckResult:
        cid = ReadinessCheckId.DESTINATION_REVISION_CONFLICT
        exp, obs = m.destination.ledger_revision, m.destination.observed_ledger_revision
        if is_supplied(exp) and is_supplied(obs) and exp != obs:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.CONFLICTING,
                blocked_reason=ReadinessBlockedCode.DESTINATION_REVISION_CONFLICT,
                detail="observed destination revision differs from expected",
            )
        if is_supplied(exp) and is_supplied(obs):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.NOT_SUPPLIED,
            blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
        )

    def _backup_verification_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.BACKUP_VERIFICATION
        if (m.backup.integrity_state is FieldState.VERIFIED
                and m.backup.readability_state is FieldState.VERIFIED):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.BACKUP_UNVERIFIED,
        )

    def _authorization_integrity_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.AUTHORIZATION_INTEGRITY
        if (m.authorization.integrity_state is FieldState.VERIFIED
                and m.authorization.issuance_lineage_state is FieldState.VERIFIED):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.AUTHORIZATION_MISSING,
        )

    def _authorization_scope_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.AUTHORIZATION_SCOPE
        if (m.authorization.project_binding_state is FieldState.VERIFIED
                and m.authorization.scope_binding_state is FieldState.VERIFIED):
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.AUTHORIZATION_SCOPE_UNVERIFIED,
        )

    def _authorization_expiry_check(
        self, m: MigrationReadinessManifest, now: datetime | None
    ) -> PreflightCheckResult:
        cid = ReadinessCheckId.AUTHORIZATION_EXPIRY
        raw = m.authorization.expires_at
        if not is_supplied(raw):
            return PreflightCheckResult(
                check_id=cid, state=CheckState.NOT_SUPPLIED,
                blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
            )
        parsed = _parse_trusted_timestamp(raw)
        if parsed is None:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.REJECTED,
                blocked_reason=ReadinessBlockedCode.MALFORMED_TIMESTAMP,
                detail="authorization expiry is not a trusted UTC timestamp",
            )
        if now is None:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.TRUSTED_TIME_UNTRUSTED,
            )
        if now >= parsed:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.AUTHORIZATION_EXPIRED,
                detail="authorization is expired at the trusted evaluation time",
            )
        if m.authorization.expiration_state is FieldState.VERIFIED:
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.REQUIRED_STATE_NOT_VERIFIED,
        )

    def _authorization_revocation_check(
        self, m: MigrationReadinessManifest
    ) -> PreflightCheckResult:
        cid = ReadinessCheckId.AUTHORIZATION_REVOCATION
        state = m.authorization.revocation_state
        if state is FieldState.VERIFIED:
            # Verified absent from the durable revocation registry.
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        if state is FieldState.BLOCKED:
            # Present in the revocation registry — the authorization is revoked.
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.AUTHORIZATION_REVOKED,
                detail="authorization is recorded as revoked",
            )
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.AUTHORIZATION_REVOCATION_UNVERIFIED,
        )

    def _trusted_time_check(
        self, m: MigrationReadinessManifest, now: datetime | None
    ) -> PreflightCheckResult:
        cid = ReadinessCheckId.TRUSTED_TIME
        if now is None:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.TRUSTED_TIME_UNTRUSTED,
                detail="trusted clock is unavailable or not timezone-aware",
            )
        return self._state_check(
            cid, m.authorization.trusted_clock_state,
            reason=ReadinessBlockedCode.TRUSTED_TIME_UNTRUSTED,
        )

    def _count_consistency_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.COUNT_CONSISTENCY
        c = m.expected_counts
        fields = [c.projected, c.approved_for_import, c.imported, c.skipped,
                  c.rejected, c.excluded, c.unresolved]
        if not all(isinstance(v, int) for v in fields):
            return PreflightCheckResult(
                check_id=cid, state=CheckState.NOT_SUPPLIED,
                blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
            )
        projected, approved, imported, skipped, rejected, excluded, unresolved = fields
        disposition_total = approved + rejected + skipped + excluded + unresolved
        if disposition_total != projected or imported > approved:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.CONFLICTING,
                blocked_reason=ReadinessBlockedCode.COUNT_MISMATCH,
                detail="expected counts do not reconcile",
            )
        if c.state is FieldState.VERIFIED:
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.UNVERIFIED,
            blocked_reason=ReadinessBlockedCode.REQUIRED_STATE_NOT_VERIFIED,
        )

    def _stale_evidence_check(
        self, m: MigrationReadinessManifest, now: datetime | None
    ) -> PreflightCheckResult:
        cid = ReadinessCheckId.STALE_EVIDENCE
        stamps = [m.source_dataset.captured_at_trusted_utc, m.backup.created_at_trusted_utc]
        supplied = [s for s in stamps if is_supplied(s)]
        if not supplied:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.NOT_SUPPLIED,
                blocked_reason=ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED,
            )
        if now is None:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.TRUSTED_TIME_UNTRUSTED,
            )
        for raw in supplied:
            parsed = _parse_trusted_timestamp(raw)
            if parsed is None:
                return PreflightCheckResult(
                    check_id=cid, state=CheckState.REJECTED,
                    blocked_reason=ReadinessBlockedCode.MALFORMED_TIMESTAMP,
                    detail="a trusted evidence timestamp is malformed",
                )
            age = (now - parsed).total_seconds()
            if age > self._max_age or age < 0:
                return PreflightCheckResult(
                    check_id=cid, state=CheckState.BLOCKED,
                    blocked_reason=ReadinessBlockedCode.STALE_EVIDENCE,
                    detail="readiness evidence is stale or future-dated",
                )
        return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)

    def _production_orchestration_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.PRODUCTION_ORCHESTRATION
        state = m.preflight.production_read_only_orchestration_state
        if state is FieldState.VERIFIED:
            return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)
        return PreflightCheckResult(
            check_id=cid, state=CheckState.BLOCKED,
            blocked_reason=ReadinessBlockedCode.PRODUCTION_ORCHESTRATION_BLOCKED,
            detail="production read-only orchestration over real data is not wired",
        )

    # ------------------------------------------------------------------ #
    # Deception checks (placeholder / secret-like values)
    # ------------------------------------------------------------------ #
    def _deception_checks(self, m: MigrationReadinessManifest) -> list[PreflightCheckResult]:
        placeholder_hit = False
        secret_hit = False
        for value in _operational_values(m):
            if looks_like_secret(value):
                secret_hit = True
            elif looks_like_placeholder(value):
                placeholder_hit = True
        placeholder = PreflightCheckResult(
            check_id=ReadinessCheckId.PLACEHOLDER_INPUTS,
            state=CheckState.REJECTED if placeholder_hit else CheckState.VERIFIED,
            blocked_reason=(ReadinessBlockedCode.PLACEHOLDER_VALUE_REJECTED
                            if placeholder_hit else None),
            detail="placeholder/fixture value used operationally" if placeholder_hit else "",
        )
        secret = PreflightCheckResult(
            check_id=ReadinessCheckId.SECRET_LEAKAGE,
            state=CheckState.REJECTED if secret_hit else CheckState.VERIFIED,
            blocked_reason=(ReadinessBlockedCode.SECRET_LIKE_VALUE_REJECTED
                            if secret_hit else None),
            detail="secret-like value present in manifest" if secret_hit else "",
        )
        return [placeholder, secret]

    def _stop_condition_check(self, m: MigrationReadinessManifest) -> PreflightCheckResult:
        cid = ReadinessCheckId.STOP_CONDITIONS
        if m.stop_conditions.active_conditions:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.BLOCKED,
                blocked_reason=ReadinessBlockedCode.STOP_CONDITION_ACTIVE,
                detail="one or more runbook stop conditions are active",
            )
        if not m.stop_conditions.all_acknowledged:
            return PreflightCheckResult(
                check_id=cid, state=CheckState.UNVERIFIED,
                blocked_reason=ReadinessBlockedCode.STOP_CONDITION_ACTIVE,
                detail="stop conditions not all acknowledged",
            )
        return PreflightCheckResult(check_id=cid, state=CheckState.VERIFIED)

    # ------------------------------------------------------------------ #
    # Evidence + helpers
    # ------------------------------------------------------------------ #
    def _evidence(
        self, m: MigrationReadinessManifest, active: tuple[str, ...]
    ) -> PreflightEvidence:
        counts = {
            k: v for k, v in {
                "projected": m.expected_counts.projected,
                "approved_for_import": m.expected_counts.approved_for_import,
                "imported": m.expected_counts.imported,
                "skipped": m.expected_counts.skipped,
                "rejected": m.expected_counts.rejected,
                "excluded": m.expected_counts.excluded,
                "unresolved": m.expected_counts.unresolved,
            }.items() if isinstance(v, int)
        }
        summary = {
            "source_dataset": m.source_dataset.state.value,
            "pipeline": m.pipeline.state.value,
            "destination": m.destination.state.value,
            "backup": m.backup.state.value,
            "authorization": m.authorization.state.value,
            "preflight": m.preflight.state.value,
            "execution": m.execution.status.value,
            "production_orchestration": m.preflight.production_read_only_orchestration_state.value,
        }
        return PreflightEvidence(
            manifest_identity=m.identity(),
            schema_version=m.schema_version,
            runbook_version=m.runbook_version,
            tool_version=TOOL_VERSION,
            repository_baseline_commit=m.repository.baseline_commit,
            repository_execution_commit=m.repository.execution_commit,
            destination_revision=m.destination.ledger_revision,
            authorization_identifier=_safe_identifier(m.authorization.non_secret_authorization_id),
            backup_identifier=_safe_identifier(m.backup.non_secret_backup_id),
            expected_counts=counts,
            supplied_field_summary=summary,
            active_stop_conditions=active,
        )

    def _malformed_report(self, _detail: str) -> PreflightReport:
        # Deliberately bounded and non-secret: the raw validation text can echo
        # supplied values, so it is never surfaced. Only a typed check is emitted.
        return PreflightReport(
            outcome=PreflightOutcome.FAIL_CLOSED,
            manifest_identity="mm-readiness-unparsed",
            evaluated_at=self._trusted_now(),
            checks=(PreflightCheckResult(
                check_id=ReadinessCheckId.REPOSITORY_IMPLEMENTATION_IDENTITY,
                state=CheckState.REJECTED,
                blocked_reason=ReadinessBlockedCode.MANIFEST_MALFORMED,
                detail="readiness manifest did not satisfy the contract",
            ),),
            blocked_reasons=(ReadinessBlockedCode.MANIFEST_MALFORMED,),
        )

    def _trusted_now(self) -> datetime | None:
        """Read the injected trusted clock; an untrusted (naive) time is refused."""
        try:
            now = self._clock.now()
        except Exception:
            return None
        if not isinstance(now, datetime) or now.tzinfo is None:
            return None
        return now


def _operational_values(m: MigrationReadinessManifest) -> list[str]:
    """Every supplied operational value string subject to deception scanning.

    Repository origin/baseline and the ``digest_algorithm`` selectors are excluded:
    they are repository/format identity, not operator-supplied operational facts.
    """
    values: list[str] = [m.repository.execution_commit]
    for section, skip in (
        (m.source_dataset, {"digest_algorithm"}),
        (m.pipeline, set()),
        (m.destination, set()),
        (m.backup, {"digest_algorithm"}),
        (m.authorization, set()),
        (m.evidence, set()),
        (m.execution, set()),
        (m.human_decisions, set()),
    ):
        for name, value in section.model_dump().items():
            if name in skip:
                continue
            if isinstance(value, str) and is_supplied(value):
                values.append(value)
    return [v for v in values if is_supplied(v)]


def _parse_trusted_timestamp(raw: str) -> datetime | None:
    """Parse a declared timezone-aware ISO-8601 UTC timestamp, else ``None``."""
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed
