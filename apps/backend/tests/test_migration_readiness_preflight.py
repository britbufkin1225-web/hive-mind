"""Phase 40K.5 — read-only readiness preflight + manifest contract tests."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models.migration_readiness import (
    MigrationReadinessManifest,
    derive_readiness_manifest_identity,
    looks_like_placeholder,
    looks_like_secret,
)
from app.services.migration_readiness_preflight import (
    CheckState,
    MigrationReadinessPreflight,
    PreflightOutcome,
    ReadinessBlockedCode,
    ReadinessCheckId,
)

NOW = datetime(2026, 8, 3, tzinfo=timezone.utc)
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs" / "operations" / "phase-40k-readiness.template.json"
)


class FixedClock:
    def __init__(self, now: datetime | None = NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        if self._now is None:
            raise RuntimeError("trusted clock unavailable")
        return self._now


class NaiveClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 3)  # tz-naive → untrusted


def preflight(clock: object | None = None, **kwargs) -> MigrationReadinessPreflight:
    return MigrationReadinessPreflight(clock=clock or FixedClock(), **kwargs)


def verified_manifest_dict() -> dict:
    """A fully verified, internally consistent synthetic manifest → PASS.

    This is a hand-authored TEST fixture. Its ``verified`` states describe the
    fixture only; they are never a claim about any real dataset, backup, or
    authorization. Individual tests degrade one field to prove fail-closed paths.
    """
    digest = "a" * 64
    return {
        "schema_version": "phase-40k-readiness.v1",
        "runbook_version": "phase-40k-runbook.v1",
        "repository": {
            "origin": "https://github.com/britbufkin1225-web/hive-mind.git",
            "baseline_commit": "3d38f2b403b68d654dd5a9aadd62eef714738080",
            "execution_commit": "3d38f2b403b68d654dd5a9aadd62eef714738080",
            "implementation_identity_state": "verified",
        },
        "source_dataset": {
            "state": "verified",
            "non_secret_locator": "reviewed-export-object",
            "format": "chatgpt_conversations_json",
            "byte_size": "1024",
            "object_count": "1",
            "digest_algorithm": "sha256",
            "digest": digest,
            "reviewed_digest": digest,
            "captured_at_trusted_utc": "2026-08-02T12:00:00Z",
            "source_revision_or_export_id": "export-2026-08-02",
            "custody_notes_reference": "custody-packet-01",
            "operator_acknowledgement": "ack-op",
            "reviewer_acknowledgement": "ack-rev",
        },
        "pipeline": {
            "parser_identity": "memory_migration_parser.v1",
            "projection_identity": "memory_migration_projection.v1",
            "assessment_identity": "assessment-report-01",
            "reviewed_specification_identity": "spec-01",
            "state": "verified",
        },
        "destination": {
            "state": "verified",
            "non_secret_identity": "authoritative-active-memory",
            "project_id": "project-01",
            "scope": "scope-01",
            "ledger_revision": "7",
            "observed_ledger_revision": "7",
            "revision_verification_state": "verified",
            "commit_generation": "7",
            "capacity_state": "verified",
            "concurrent_writer_exclusion_state": "verified",
        },
        "expected_counts": {
            "state": "verified",
            "projected": 10,
            "approved_for_import": 6,
            "imported": 6,
            "skipped": 1,
            "rejected": 2,
            "excluded": 1,
            "unresolved": 0,
        },
        "backup": {
            "state": "verified",
            "non_secret_backup_id": "backup-01",
            "digest_algorithm": "sha256",
            "ledger_digest": "b" * 64,
            "snapshot_digest": "c" * 64,
            "source_generation": "7",
            "created_at_trusted_utc": "2026-08-02T12:00:00Z",
            "integrity_state": "verified",
            "readability_state": "verified",
            "isolated_restoration_rehearsal_state": "verified",
            "retention_and_access_reference": "retention-01",
        },
        "authorization": {
            "state": "verified",
            "non_secret_authorization_id": "authz-01",
            "integrity_state": "verified",
            "issuance_lineage_state": "verified",
            "expires_at": "2026-08-04T00:00:00Z",
            "expiration_state": "verified",
            "revocation_state": "verified",
            "project_binding_state": "verified",
            "scope_binding_state": "verified",
            "trusted_clock_state": "verified",
            "operator_context_state": "verified",
        },
        "preflight": {
            "state": "verified",
            "production_read_only_orchestration_state": "verified",
            "dataset_fingerprint_state": "verified",
            "pipeline_state": "verified",
            "destination_revision_state": "verified",
            "backup_state": "verified",
            "authorization_state": "verified",
            "expected_write_set_state": "verified",
            "expected_receipt_identity": "receipt-identity-01",
            "storage_capacity_state": "verified",
            "evidence_destination_state": "verified",
            "recovery_materials_state": "verified",
        },
        "stop_conditions": {
            "state": "verified",
            "all_acknowledged": True,
            "active_conditions": [],
        },
        "evidence": {
            "state": "verified",
            "preflight_packet": "packet-pre",
            "authorization_packet": "packet-auth",
            "backup_packet": "packet-backup",
            "execution_packet": "packet-exec",
            "receipt_packet": "packet-receipt",
            "post_run_packet": "packet-post",
            "recovery_packet": "packet-recovery",
        },
        "execution": {
            "status": "verified",
            "approved_command_identity": "command-01",
            "attempt_id": "not_supplied",
            "receipt_id": "not_supplied",
            "final_ledger_revision": "not_supplied",
            "final_commit_generation": "not_supplied",
            "final_disposition": "verified",
        },
        "human_decisions": {
            "operator": "operator-alpha",
            "independent_reviewer": "reviewer-beta",
            "authorization_issuer": "issuer-gamma",
            "recovery_decision_maker": "recovery-delta",
            "devdevbuilds_go_no_go": "go",
            "acceptance": "accepted",
        },
    }


def evaluate(raw: dict, clock: object | None = None):
    return preflight(clock=clock).evaluate_mapping(raw)


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
def test_checked_in_template_parses_and_is_blocked():
    raw = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    report = evaluate(raw)
    assert report.outcome is PreflightOutcome.BLOCKED
    assert report.evidence.manifest_identity == report.manifest_identity


def test_manifest_identity_is_deterministic_and_content_derived():
    m = MigrationReadinessManifest.model_validate(verified_manifest_dict())
    assert m.identity() == derive_readiness_manifest_identity(m)
    changed = verified_manifest_dict()
    changed["destination"]["ledger_revision"] = "8"
    changed["destination"]["observed_ledger_revision"] = "8"
    other = MigrationReadinessManifest.model_validate(changed)
    assert other.identity() != m.identity()


def test_unknown_schema_version_rejected():
    raw = verified_manifest_dict()
    raw["schema_version"] = "phase-40k-readiness.v2"
    report = evaluate(raw)
    assert report.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.MANIFEST_MALFORMED in report.blocked_reasons


def test_unknown_field_and_ambiguous_bool_rejected():
    raw = verified_manifest_dict()
    raw["unexpected_key"] = "x"
    assert evaluate(raw).outcome is PreflightOutcome.FAIL_CLOSED
    raw2 = verified_manifest_dict()
    raw2["stop_conditions"]["all_acknowledged"] = 1  # not a real bool
    assert evaluate(raw2).outcome is PreflightOutcome.FAIL_CLOSED


def test_count_coercion_rejected():
    raw = verified_manifest_dict()
    raw["expected_counts"]["projected"] = "10"  # numeric string, not int
    assert evaluate(raw).outcome is PreflightOutcome.FAIL_CLOSED


# --------------------------------------------------------------------------- #
# Baseline outcomes
# --------------------------------------------------------------------------- #
def test_empty_manifest_missing_required_repository_is_fail_closed():
    assert evaluate({}).outcome is PreflightOutcome.FAIL_CLOSED


def test_all_operational_fields_not_supplied_is_blocked():
    raw = {"repository": {
        "origin": "https://example.invalid/repo.git",
        "baseline_commit": "3d38f2b403b68d654dd5a9aadd62eef714738080",
    }}
    report = evaluate(raw)
    assert report.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED in report.blocked_reasons


def test_fully_verified_manifest_passes():
    report = evaluate(verified_manifest_dict())
    assert report.outcome is PreflightOutcome.PASS, [
        (c.check_id.value, c.state.value) for c in report.checks
        if c.state is not CheckState.VERIFIED
    ]
    assert report.blocked_reasons == ()


def test_repeated_evaluation_is_deterministic():
    raw = verified_manifest_dict()
    a = evaluate(raw)
    b = evaluate(raw)
    assert a.model_dump() == b.model_dump()


# --------------------------------------------------------------------------- #
# Individual fail-closed / blocked cases (degrade one field at a time)
# --------------------------------------------------------------------------- #
def _blocked_when(mutate) -> "tuple":
    raw = verified_manifest_dict()
    mutate(raw)
    report = evaluate(raw)
    return report


def test_conflicting_dataset_fingerprints_fail_closed():
    r = _blocked_when(lambda raw: raw["source_dataset"].__setitem__("reviewed_digest", "d" * 64))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.DATASET_FINGERPRINT_CONFLICT in r.blocked_reasons


def test_weak_dataset_digest_algorithm_is_fail_closed():
    r = _blocked_when(lambda raw: raw["source_dataset"].__setitem__("digest_algorithm", "md5"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.DATASET_DIGEST_ALGORITHM_WEAK in r.blocked_reasons


def test_destination_revision_mismatch_fails_closed():
    r = _blocked_when(lambda raw: raw["destination"].__setitem__("observed_ledger_revision", "9"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.DESTINATION_REVISION_CONFLICT in r.blocked_reasons


def test_missing_destination_revision_verification_blocks():
    r = _blocked_when(lambda raw: raw["destination"].__setitem__("revision_verification_state", "unverified"))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.DESTINATION_REVISION_UNVERIFIED in r.blocked_reasons


def test_backup_missing_blocks():
    def mutate(raw):
        raw["backup"]["state"] = "not_supplied"
        raw["backup"]["non_secret_backup_id"] = "not_supplied"
    r = _blocked_when(mutate)
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED in r.blocked_reasons


def test_backup_unverified_blocks():
    r = _blocked_when(lambda raw: raw["backup"].__setitem__("integrity_state", "unverified"))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.BACKUP_UNVERIFIED in r.blocked_reasons


def test_restoration_unverified_blocks():
    r = _blocked_when(lambda raw: raw["backup"].__setitem__("isolated_restoration_rehearsal_state", "unverified"))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.RESTORATION_UNVERIFIED in r.blocked_reasons


def test_authorization_missing_blocks():
    def mutate(raw):
        raw["authorization"]["state"] = "not_supplied"
        raw["authorization"]["non_secret_authorization_id"] = "not_supplied"
    r = _blocked_when(mutate)
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.OPERATIONAL_VALUE_NOT_SUPPLIED in r.blocked_reasons


def test_authorization_scope_mismatch_blocks():
    r = _blocked_when(lambda raw: raw["authorization"].__setitem__("scope_binding_state", "blocked"))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.AUTHORIZATION_SCOPE_UNVERIFIED in r.blocked_reasons


def test_authorization_expired_fails_closed():
    r = _blocked_when(lambda raw: raw["authorization"].__setitem__("expires_at", "2026-08-02T00:00:00Z"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.AUTHORIZATION_EXPIRED in r.blocked_reasons


def test_malformed_authorization_expiry_is_fail_closed():
    r = _blocked_when(lambda raw: raw["authorization"].__setitem__("expires_at", "not-a-timestamp!"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.MALFORMED_TIMESTAMP in r.blocked_reasons


def test_authorization_revoked_fails_closed():
    r = _blocked_when(lambda raw: raw["authorization"].__setitem__("revocation_state", "blocked"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.AUTHORIZATION_REVOKED in r.blocked_reasons


def test_untrusted_time_blocks():
    report = preflight(clock=NaiveClock()).evaluate_mapping(verified_manifest_dict())
    assert report.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.TRUSTED_TIME_UNTRUSTED in report.blocked_reasons


def test_expected_count_mismatch_fails_closed():
    r = _blocked_when(lambda raw: raw["expected_counts"].__setitem__("imported", 9))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.COUNT_MISMATCH in r.blocked_reasons


def test_stale_evidence_fails_closed():
    r = _blocked_when(lambda raw: raw["source_dataset"].__setitem__("captured_at_trusted_utc", "2020-01-01T00:00:00Z"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.STALE_EVIDENCE in r.blocked_reasons


@pytest.mark.parametrize("digest", ["abc", "A" * 64, "g" * 64, "a" * 63])
def test_noncanonical_dataset_digest_fails_closed(digest):
    def mutate(raw):
        raw["source_dataset"]["digest"] = digest
        raw["source_dataset"]["reviewed_digest"] = digest
    assert _blocked_when(mutate).outcome is PreflightOutcome.FAIL_CLOSED


def test_noncanonical_backup_digest_or_algorithm_fails_closed():
    assert _blocked_when(
        lambda raw: raw["backup"].__setitem__("ledger_digest", "abc")
    ).outcome is PreflightOutcome.FAIL_CLOSED
    assert _blocked_when(
        lambda raw: raw["backup"].__setitem__("digest_algorithm", "SHA256")
    ).outcome is PreflightOutcome.FAIL_CLOSED


def test_whitespace_only_operational_value_fails_closed():
    r = _blocked_when(
        lambda raw: raw["destination"].__setitem__("non_secret_identity", "   ")
    )
    assert r.outcome is PreflightOutcome.FAIL_CLOSED


def test_triggered_stop_condition_blocks():
    r = _blocked_when(lambda raw: raw["stop_conditions"].__setitem__("active_conditions", ["destination_revision_changed"]))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.STOP_CONDITION_ACTIVE in r.blocked_reasons


def test_placeholder_value_rejected():
    r = _blocked_when(lambda raw: raw["destination"].__setitem__("non_secret_identity", "example-destination"))
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.PLACEHOLDER_VALUE_REJECTED in r.blocked_reasons


def test_secret_like_value_rejected_and_redacted():
    def mutate(raw):
        raw["authorization"]["non_secret_authorization_id"] = "bearer sk-supersecrettoken0000"
    r = _blocked_when(mutate)
    assert r.outcome is PreflightOutcome.FAIL_CLOSED
    assert ReadinessBlockedCode.SECRET_LIKE_VALUE_REJECTED in r.blocked_reasons
    assert r.evidence.authorization_identifier == "[redacted]"


def test_production_orchestration_blocked_state():
    r = _blocked_when(lambda raw: raw["preflight"].__setitem__("production_read_only_orchestration_state", "blocked"))
    assert r.outcome is PreflightOutcome.BLOCKED
    assert ReadinessBlockedCode.PRODUCTION_ORCHESTRATION_BLOCKED in r.blocked_reasons


def test_non_secret_evidence_never_exposes_secretish_values():
    report = evaluate(verified_manifest_dict())
    dumped = json.dumps(report.evidence.model_dump(mode="json"))
    assert "bearer" not in dumped.lower()
    assert "token" not in dumped.lower()


# --------------------------------------------------------------------------- #
# Read-only guarantee: the preflight touches no persistence surface.
# --------------------------------------------------------------------------- #
def test_preflight_performs_no_persistent_mutation(tmp_path, monkeypatch):
    # There is nothing to mutate: assert the service imports/holds no store,
    # holder, ledger, or snapshot attribute, and evaluation does not write files.
    svc = preflight()
    for forbidden in ("ledger_store", "snapshot_store", "holder", "lock", "_store"):
        assert not hasattr(svc, forbidden)
    before = set(Path(tmp_path).iterdir())
    monkeypatch.chdir(tmp_path)
    evaluate(verified_manifest_dict())
    assert set(Path(tmp_path).iterdir()) == before


def test_helpers_reject_placeholder_and_secret_shapes():
    assert looks_like_placeholder("changeme-please")
    assert not looks_like_placeholder("not_supplied")
    assert looks_like_secret("password=hunter2")
    assert not looks_like_secret("a" * 64)  # hex digest is non-secret


def test_evaluate_mapping_and_evaluate_agree():
    raw = verified_manifest_dict()
    from_map = evaluate(raw)
    from_model = preflight().evaluate(MigrationReadinessManifest.model_validate(raw))
    assert from_map.outcome is from_model.outcome
    assert from_map.manifest_identity == from_model.manifest_identity
    # sanity: copy stability of dict fixture
    assert raw == copy.deepcopy(raw)
