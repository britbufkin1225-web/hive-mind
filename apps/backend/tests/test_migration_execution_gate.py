"""Phase 40K.5 — fail-closed reviewed-migration execution gate tests.

Every refusal case wires a spy executor and asserts it is NEVER called: that is
the concrete proof that an invalid execution request produces no attempt,
receipt, ledger, holder, or Active Memory effect (the gate never reaches a
mutating dispatch on refusal).
"""
from __future__ import annotations

import pytest

from app.models.migration_readiness import MigrationReadinessManifest
from app.services.migration_execution_gate import (
    ExecutionDecisionState,
    ExecutionRefusalCode,
    OperationalExecutionAuthorization,
    ReviewedMigrationExecutionGate,
)
from app.services.migration_readiness_preflight import (
    MigrationReadinessPreflight,
    PreflightOutcome,
)
from test_migration_readiness_preflight import FixedClock, verified_manifest_dict


class SpyExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, manifest, auth):
        self.calls.append((manifest, auth))
        return "dispatched"


def manifest_from(raw: dict) -> MigrationReadinessManifest:
    return MigrationReadinessManifest.model_validate(raw)


def gate(executor=None) -> ReviewedMigrationExecutionGate:
    return ReviewedMigrationExecutionGate(
        MigrationReadinessPreflight(clock=FixedClock()), executor=executor
    )


def op_auth(identity: str, **over) -> OperationalExecutionAuthorization:
    data = dict(
        authorized_manifest_identity=identity,
        issuer_principal_id="devdevbuilds",
        devdevbuilds_go_reference="go-record-2026-08-03",
        operational=True,
        fixture=False,
        demonstration=False,
        devdevbuilds_go=True,
    )
    data.update(over)
    return OperationalExecutionAuthorization.model_validate(data)


# --------------------------------------------------------------------------- #
# Refusals — spy executor must never be called
# --------------------------------------------------------------------------- #
def test_missing_authorization_refuses_even_on_passing_preflight():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(m, None)
    assert decision.refused
    assert decision.refusal_code is ExecutionRefusalCode.MISSING_OPERATIONAL_AUTHORIZATION
    # The preflight for this exact manifest passes, proving a pass never authorizes.
    assert decision.preflight_outcome is PreflightOutcome.PASS
    assert spy.calls == []


def test_fixture_authorization_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(m, op_auth(m.identity(), fixture=True))
    assert decision.refusal_code is ExecutionRefusalCode.FIXTURE_AUTHORIZATION_REJECTED
    assert spy.calls == []


def test_demonstration_or_non_operational_authorization_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    g = gate(spy)
    d1 = g.request_execution(m, op_auth(m.identity(), fixture=False, demonstration=True))
    d2 = g.request_execution(m, op_auth(m.identity(), fixture=False, operational=False))
    assert d1.refusal_code is ExecutionRefusalCode.FIXTURE_AUTHORIZATION_REJECTED
    assert d2.refusal_code is ExecutionRefusalCode.FIXTURE_AUTHORIZATION_REJECTED
    assert spy.calls == []


def test_placeholder_authorization_text_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(
        m, op_auth(m.identity(), devdevbuilds_go_reference="changeme")
    )
    assert decision.refusal_code is ExecutionRefusalCode.PLACEHOLDER_AUTHORIZATION_REJECTED
    assert spy.calls == []


def test_secret_like_authorization_text_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(
        m, op_auth(m.identity(), issuer_principal_id="bearer sk-000111222333444555")
    )
    assert decision.refusal_code is ExecutionRefusalCode.SECRET_LIKE_AUTHORIZATION_REJECTED
    assert spy.calls == []


def test_absent_devdevbuilds_go_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(m, op_auth(m.identity(), devdevbuilds_go=False))
    assert decision.refusal_code is ExecutionRefusalCode.DEVDEVBUILDS_GO_ABSENT
    assert spy.calls == []


def test_manifest_identity_mismatch_refused():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(m, op_auth("mm-readiness-000000000000000000000000"))
    assert decision.refusal_code is ExecutionRefusalCode.AUTHORIZATION_MANIFEST_MISMATCH
    assert spy.calls == []


def test_blocked_preflight_with_valid_authorization_refused():
    spy = SpyExecutor()
    raw = verified_manifest_dict()
    raw["backup"]["integrity_state"] = "unverified"  # forces preflight -> blocked
    m = manifest_from(raw)
    decision = gate(spy).request_execution(m, op_auth(m.identity()))
    assert decision.refusal_code is ExecutionRefusalCode.PREFLIGHT_NOT_PASSED
    assert decision.preflight_outcome is PreflightOutcome.BLOCKED
    assert spy.calls == []


# --------------------------------------------------------------------------- #
# Cleared — only with the full, exact combination
# --------------------------------------------------------------------------- #
def test_full_combination_clears_and_dispatches_to_injected_executor_only():
    spy = SpyExecutor()
    m = manifest_from(verified_manifest_dict())
    decision = gate(spy).request_execution(m, op_auth(m.identity()))
    assert decision.state is ExecutionDecisionState.CLEARED_FOR_EXECUTION
    assert decision.dispatched is True
    assert len(spy.calls) == 1 and spy.calls[0][0] is m


def test_cleared_without_wired_executor_performs_no_dispatch():
    m = manifest_from(verified_manifest_dict())
    decision = gate(executor=None).request_execution(m, op_auth(m.identity()))
    assert decision.state is ExecutionDecisionState.CLEARED_FOR_EXECUTION
    assert decision.dispatched is False


def test_executor_exception_is_redacted_and_never_reported_as_success():
    class FailingExecutor:
        def __call__(self, manifest, auth):
            raise RuntimeError("bearer sk-sensitive-secret")

    m = manifest_from(verified_manifest_dict())
    decision = gate(FailingExecutor()).request_execution(m, op_auth(m.identity()))
    assert decision.state is ExecutionDecisionState.EXECUTION_FAILED
    assert decision.refusal_code is ExecutionRefusalCode.EXECUTOR_FAILED
    assert decision.dispatched is True
    assert "sensitive" not in decision.detail


def test_default_gate_has_no_wired_executor():
    # A gate constructed without an explicit executor can never mutate: even a
    # cleared decision dispatches nothing. This is the Phase 40K.5 posture.
    m = manifest_from(verified_manifest_dict())
    decision = ReviewedMigrationExecutionGate(
        MigrationReadinessPreflight(clock=FixedClock())
    ).request_execution(m, op_auth(m.identity()))
    assert decision.state is ExecutionDecisionState.CLEARED_FOR_EXECUTION
    assert decision.dispatched is False


def test_authorization_flags_reject_non_bool():
    with pytest.raises(Exception):
        OperationalExecutionAuthorization.model_validate(
            dict(
                authorized_manifest_identity="mm-readiness-x",
                issuer_principal_id="p",
                devdevbuilds_go_reference="r",
                operational=1,  # not a bool
                fixture=False,
                demonstration=False,
                devdevbuilds_go=True,
            )
        )
