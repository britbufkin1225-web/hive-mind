"""Phase 40K.5 — fail-closed reviewed-migration execution gate.

Phase 40K's runbook forbids ad-hoc execution ("Directly importing backend classes
from an ad-hoc shell is prohibited", §2) and records that no reviewed production
execution entry point exists (§7, §12). This module supplies that entry point as a
**decision boundary**, separate from the read-only preflight, that defaults to
refusal and can only clear execution when supplied exact, independently verified
authorization *and* readiness.

The gate is deliberately not a second migration engine. When (and only when) a
request clears every gate, dispatch is delegated to an injected ``executor`` — in
a separately authorized Phase 40L that executor is
``MemoryMigrationImportService.import_reviewed_candidate`` (the Phase 40I
publish-last coordinator). No executor is wired in Phase 40K.5, so a cleared
decision performs no work here: the gate reuses and hardens the existing 40I
boundary rather than competing with it.

Guarantees the gate upholds:

* **Defaults to refusal.** A missing operational authorization is refused before
  anything else — a passing preflight never *implies* authorization.
* **No fixtures/placeholders.** An authorization flagged fixture/demonstration/
  non-operational, or carrying placeholder text, is refused.
* **Exact binding.** The authorization must name the exact manifest identity it
  authorizes; a stale or mismatched binding is refused.
* **Verified readiness required.** Execution additionally requires a ``pass``
  preflight; a ``blocked`` / ``fail_closed`` manifest is refused.
* **No silent dry-run downgrade, no mutation on refusal.** A refused request
  never reaches the executor, so it can create no attempt, receipt, ledger,
  holder, or Active Memory effect.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.migration_readiness import (
    MAX_READINESS_TEXT,
    MigrationReadinessManifest,
    is_supplied,
    looks_like_placeholder,
    looks_like_secret,
)
from app.services.migration_readiness_preflight import (
    MigrationReadinessPreflight,
    PreflightOutcome,
    PreflightReport,
)

GATE_VERSION = "migration-execution-gate.v1"


def _require_bool(value: Any) -> Any:
    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


class OperationalExecutionAuthorization(BaseModel):
    """An explicit, out-of-band operational go supplied to the execution gate.

    Distinct from the Phase 40I ``ProjectScopeAuthorizationContext`` (runtime
    import authorization): this is the *operator-facing* attestation that the
    reviewed readiness packet for one exact manifest received a devdevbuilds go.
    The fixture/demonstration flags are representable **on purpose** so the gate
    can name and refuse them — exactly as the intake contracts represent the
    custody kinds they refuse.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    authorized_manifest_identity: str = Field(min_length=1, max_length=MAX_READINESS_TEXT)
    issuer_principal_id: str = Field(min_length=1, max_length=MAX_READINESS_TEXT)
    devdevbuilds_go_reference: str = Field(min_length=1, max_length=MAX_READINESS_TEXT)
    operational: bool = False
    fixture: bool = True
    demonstration: bool = True
    devdevbuilds_go: bool = False

    @field_validator(
        "operational", "fixture", "demonstration", "devdevbuilds_go", mode="before"
    )
    @classmethod
    def _flags_are_bool(cls, value: Any) -> Any:
        return _require_bool(value)


class ExecutionDecisionState(StrEnum):
    REFUSED = "refused"
    CLEARED_FOR_EXECUTION = "cleared_for_execution"


class ExecutionRefusalCode(StrEnum):
    MISSING_OPERATIONAL_AUTHORIZATION = "missing_operational_authorization"
    FIXTURE_AUTHORIZATION_REJECTED = "fixture_authorization_rejected"
    PLACEHOLDER_AUTHORIZATION_REJECTED = "placeholder_authorization_rejected"
    SECRET_LIKE_AUTHORIZATION_REJECTED = "secret_like_authorization_rejected"
    DEVDEVBUILDS_GO_ABSENT = "devdevbuilds_go_absent"
    AUTHORIZATION_MANIFEST_MISMATCH = "authorization_manifest_mismatch"
    PREFLIGHT_NOT_PASSED = "preflight_not_passed"


class ExecutionGateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    state: ExecutionDecisionState
    gate_version: str = GATE_VERSION
    manifest_identity: str
    refusal_code: ExecutionRefusalCode | None = None
    detail: str = Field(default="", max_length=256)
    dispatched: bool = False
    preflight_outcome: PreflightOutcome

    @property
    def refused(self) -> bool:
        return self.state is ExecutionDecisionState.REFUSED


class ReviewedMigrationExecutionGate:
    """Execution-facing decision boundary. Reuses the read-only preflight."""

    def __init__(
        self,
        preflight: MigrationReadinessPreflight | None = None,
        *,
        executor: Callable[
            [MigrationReadinessManifest, OperationalExecutionAuthorization], Any
        ] | None = None,
    ) -> None:
        self._preflight = preflight or MigrationReadinessPreflight()
        # Optional Phase 40L dispatch target. None in Phase 40K.5 → a cleared
        # decision never performs work here.
        self._executor = executor

    def request_execution(
        self,
        manifest: MigrationReadinessManifest,
        operational_authorization: OperationalExecutionAuthorization | None = None,
    ) -> ExecutionGateDecision:
        report: PreflightReport = self._preflight.evaluate(manifest)
        identity = manifest.identity()

        # 1. Default to refusal: authorization is required and is NEVER inferred
        #    from a passing preflight.
        if operational_authorization is None:
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.MISSING_OPERATIONAL_AUTHORIZATION,
                "no operational authorization was supplied",
            )
        auth = operational_authorization

        # 2. Reject fixture / demonstration / non-operational authorizations.
        if auth.fixture or auth.demonstration or not auth.operational:
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.FIXTURE_AUTHORIZATION_REJECTED,
                "authorization is fixture/demonstration or not marked operational",
            )

        # 3. Reject placeholder / secret-like authorization text.
        auth_text = (auth.issuer_principal_id, auth.devdevbuilds_go_reference)
        if any(looks_like_secret(v) for v in auth_text):
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.SECRET_LIKE_AUTHORIZATION_REJECTED,
                "authorization carries secret-like text",
            )
        if any(looks_like_placeholder(v) for v in auth_text):
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.PLACEHOLDER_AUTHORIZATION_REJECTED,
                "authorization carries placeholder text",
            )

        # 4. Require an explicit devdevbuilds go.
        if not auth.devdevbuilds_go or not is_supplied(auth.devdevbuilds_go_reference):
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.DEVDEVBUILDS_GO_ABSENT,
                "explicit devdevbuilds go is absent",
            )

        # 5. Exact binding: the authorization must name this exact manifest.
        if auth.authorized_manifest_identity != identity:
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.AUTHORIZATION_MANIFEST_MISMATCH,
                "authorization does not bind this exact manifest identity",
            )

        # 6. Verified readiness required (in addition to, never in place of, auth).
        if report.outcome is not PreflightOutcome.PASS:
            return self._refuse(
                identity, report,
                ExecutionRefusalCode.PREFLIGHT_NOT_PASSED,
                "readiness preflight did not pass",
            )

        # Cleared. Dispatch only if an executor is wired (Phase 40L); otherwise the
        # decision is returned without performing any work.
        dispatched = False
        if self._executor is not None:
            self._executor(manifest, auth)
            dispatched = True
        return ExecutionGateDecision(
            state=ExecutionDecisionState.CLEARED_FOR_EXECUTION,
            manifest_identity=identity,
            detail="cleared; execution belongs to separately authorized Phase 40L",
            dispatched=dispatched,
            preflight_outcome=report.outcome,
        )

    @staticmethod
    def _refuse(
        identity: str,
        report: PreflightReport,
        code: ExecutionRefusalCode,
        detail: str,
    ) -> ExecutionGateDecision:
        return ExecutionGateDecision(
            state=ExecutionDecisionState.REFUSED,
            manifest_identity=identity,
            refusal_code=code,
            detail=detail,
            dispatched=False,
            preflight_outcome=report.outcome,
        )
