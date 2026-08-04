"""Phase 40K.5 — production migration readiness-manifest contract.

This module reconciles the checked-in fail-closed readiness template
(``docs/operations/phase-40k-readiness.template.json``, ``phase-40k-readiness.v1``)
into a bounded, deterministically validated Pydantic contract. It adds **no**
migration behavior: it reads no dataset, opens no store, publishes no holder,
creates no attempt/receipt/ledger material, and reaches no authorization
decision on its own. It defines the *shapes and field-state vocabulary* the
read-only preflight service (:mod:`app.services.migration_readiness_preflight`)
and the fail-closed execution gate
(:mod:`app.services.migration_execution_gate`) evaluate.

Design rationale (the headline decisions, matching the migration-track house
style established by ``memory_migration.py`` / ``memory_migration_import.py``):

* **Declared field-states, never derived truth.** Every operational field is a
  *declaration* about real-world material this repository cannot see. The
  :class:`FieldState` vocabulary distinguishes ``not_supplied`` (absent),
  ``unverified`` (supplied but not independently confirmed), ``verified``
  (independently confirmed by an operator/reviewer), ``blocked``, and
  ``conflicting`` (a detected contradiction). Nothing here can promote a state;
  promotion is an operator act recorded outside Git.
* **Absence is honest; deception is rejected.** ``not_supplied`` /
  ``unverified`` / ``blocked`` are legitimate "not ready" states and drive a
  ``blocked`` preflight. A *placeholder, fixture, demonstration, or secret-like*
  value dressed up as a real operational fact is a different, dangerous thing and
  is **rejected** (fail-closed), never normalized.
* **Strict scalars.** Booleans and integers reject the lax coercions (``0``/``1``
  → bool, ``"3"``/``3.0`` → int) that Pydantic allows by default, because these
  fields carry readiness claims and must be exactly what the operator declared —
  the same discipline ``memory_migration.py`` applies with ``_require_bool`` /
  ``_require_int``.
* **Deterministic identity.** :func:`derive_readiness_manifest_identity` folds the
  canonical manifest content (identity field excluded) through the one Phase 40I
  canonical-JSON rule and a domain-separated SHA-256, so identical declarations
  always yield the same manifest identity and evidence is reproducible.

The contract is faithful to the template: every template key is a known field.
A small number of *optional* companion fields (``reviewed_digest``,
``observed_ledger_revision``, ``revision_verification_state``) default to the
``not_supplied`` sentinel and let the preflight represent the runbook's
conflict/mismatch stop conditions without inventing real values; a template that
omits them still validates.
"""
from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Reuse the single Phase 40I canonical-JSON serializer rather than defining a
# second one — identity/serialization logic must not be duplicated across the
# migration track (see ``memory_migration_import.canonical_json``).
from app.models.memory_migration_import import canonical_json

READINESS_CONTRACT_VERSION = "memory-migration-readiness.v1"
READINESS_RUNBOOK_VERSION = "phase-40k-runbook.v1"
READINESS_TEMPLATE_SCHEMA_VERSION = "phase-40k-readiness.v1"

# Bounded free-text / collection limits. Readiness fields are short safe
# identifiers, states, and aliases — never payloads — so the ceilings are tight.
MAX_READINESS_TEXT = 512
MAX_READINESS_ACTIVE_CONDITIONS = 64
MAX_READINESS_COUNT = 1_000_000_000

# The absent-value sentinel the checked-in template uses everywhere.
NOT_SUPPLIED = "not_supplied"

# Digest algorithms strong enough to anchor a dataset/backup fingerprint. Mirrors
# the runbook §3 rule (SHA-256/512 accepted; MD5/SHA-1 rejected as weak).
ACCEPTED_DIGEST_ALGORITHMS = frozenset({"sha256", "sha512"})

# Substrings that mark a value as a placeholder/fixture/demonstration rather than
# a real operational fact. Detected only in operational value fields; a match is
# a fail-closed rejection, not a blocked state, because the value is pretending to
# be real. ``not_supplied`` is deliberately absent — honest absence is not deceit.
PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "fixture",
    "demo",
    "dummy",
    "sample",
    "changeme",
    "todo",
    "tbd",
    "your-",
    "xxx",
    "<",
    ">",
    "lorem",
    "test-",
    "test_",
)

# Substrings/shapes that mark a value as secret-like. A match is rejected so a
# credential, token, or key never lands in a reviewable evidence packet.
SECRET_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "bearer ",
    "authorization:",
    "private key",
    "-----begin",
    "sk-",
    "aws_secret",
    "access_key",
    "refresh_token",
    "session_token",
    "client_secret",
)


class FieldState(StrEnum):
    """The closed field-state vocabulary for one readiness fact.

    ``verified`` is the only state that clears an execution-required check.
    ``conflicting`` is produced by the preflight when two supplied values that
    must agree do not; it is never authored directly by a well-formed template.
    """

    NOT_SUPPLIED = "not_supplied"
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    CONFLICTING = "conflicting"


def _require_bool(value: Any) -> Any:
    """Reject a non-``bool`` where a flag is expected (no ``0``/``1`` coercion)."""
    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


def _require_count(value: Any) -> Any:
    """Require the ``not_supplied`` sentinel or a bounded non-negative integer.

    Booleans and integral floats/strings are rejected: a count is a safety input,
    and silently converting ``True`` or ``"3"`` into ``1``/``3`` would let the
    consistency check judge a value the operator never declared.
    """
    if value == NOT_SUPPLIED:
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("count field must be an integer or 'not_supplied'")
    if value < 0 or value > MAX_READINESS_COUNT:
        raise ValueError("count field is out of the accepted bounds")
    return value


class _ReadinessModel(BaseModel):
    """Shared config: reject unknown keys, freeze after construction.

    ``extra='forbid'`` is load-bearing — it is what stops a credential-shaped or
    payload-shaped key riding into a readiness declaration on an unknown field.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


def _bounded_text(default: Any = ...) -> Any:
    return Field(default, min_length=1, max_length=MAX_READINESS_TEXT)


class RepositorySection(_ReadinessModel):
    origin: str = _bounded_text()
    baseline_commit: str = _bounded_text()
    execution_commit: str = _bounded_text(NOT_SUPPLIED)
    implementation_identity_state: FieldState = FieldState.UNVERIFIED


class SourceDatasetSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    non_secret_locator: str = _bounded_text(NOT_SUPPLIED)
    format: str = _bounded_text(NOT_SUPPLIED)
    byte_size: str = _bounded_text(NOT_SUPPLIED)
    object_count: str = _bounded_text(NOT_SUPPLIED)
    digest_algorithm: str = _bounded_text("sha256")
    digest: str = _bounded_text(NOT_SUPPLIED)
    # Optional companion: the fingerprint recorded at authorization review. A
    # mismatch against ``digest`` is the runbook's "conflicting dataset
    # fingerprints" stop condition.
    reviewed_digest: str = _bounded_text(NOT_SUPPLIED)
    captured_at_trusted_utc: str = _bounded_text(NOT_SUPPLIED)
    source_revision_or_export_id: str = _bounded_text(NOT_SUPPLIED)
    custody_notes_reference: str = _bounded_text(NOT_SUPPLIED)
    operator_acknowledgement: str = _bounded_text(NOT_SUPPLIED)
    reviewer_acknowledgement: str = _bounded_text(NOT_SUPPLIED)


class PipelineSection(_ReadinessModel):
    parser_identity: str = _bounded_text(NOT_SUPPLIED)
    projection_identity: str = _bounded_text(NOT_SUPPLIED)
    assessment_identity: str = _bounded_text(NOT_SUPPLIED)
    reviewed_specification_identity: str = _bounded_text(NOT_SUPPLIED)
    state: FieldState = FieldState.UNVERIFIED


class DestinationSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    non_secret_identity: str = _bounded_text(NOT_SUPPLIED)
    project_id: str = _bounded_text(NOT_SUPPLIED)
    scope: str = _bounded_text(NOT_SUPPLIED)
    ledger_revision: str = _bounded_text(NOT_SUPPLIED)
    # Optional companion: the revision observed read-only at preflight. A mismatch
    # against ``ledger_revision`` is the "destination revision mismatch" stop.
    observed_ledger_revision: str = _bounded_text(NOT_SUPPLIED)
    revision_verification_state: FieldState = FieldState.UNVERIFIED
    commit_generation: str = _bounded_text(NOT_SUPPLIED)
    capacity_state: FieldState = FieldState.UNVERIFIED
    concurrent_writer_exclusion_state: FieldState = FieldState.UNVERIFIED


class ExpectedCountsSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    projected: str | int = NOT_SUPPLIED
    approved_for_import: str | int = NOT_SUPPLIED
    imported: str | int = NOT_SUPPLIED
    skipped: str | int = NOT_SUPPLIED
    rejected: str | int = NOT_SUPPLIED
    excluded: str | int = NOT_SUPPLIED
    unresolved: str | int = NOT_SUPPLIED

    @field_validator(
        "projected", "approved_for_import", "imported", "skipped",
        "rejected", "excluded", "unresolved", mode="before",
    )
    @classmethod
    def _counts_bounded(cls, value: Any) -> Any:
        return _require_count(value)


class BackupSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    non_secret_backup_id: str = _bounded_text(NOT_SUPPLIED)
    digest_algorithm: str = _bounded_text("sha256")
    ledger_digest: str = _bounded_text(NOT_SUPPLIED)
    snapshot_digest: str = _bounded_text(NOT_SUPPLIED)
    source_generation: str = _bounded_text(NOT_SUPPLIED)
    created_at_trusted_utc: str = _bounded_text(NOT_SUPPLIED)
    integrity_state: FieldState = FieldState.UNVERIFIED
    readability_state: FieldState = FieldState.UNVERIFIED
    isolated_restoration_rehearsal_state: FieldState = FieldState.UNVERIFIED
    retention_and_access_reference: str = _bounded_text(NOT_SUPPLIED)


class AuthorizationSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    non_secret_authorization_id: str = _bounded_text(NOT_SUPPLIED)
    integrity_state: FieldState = FieldState.UNVERIFIED
    issuance_lineage_state: FieldState = FieldState.UNVERIFIED
    expires_at: str = _bounded_text(NOT_SUPPLIED)
    expiration_state: FieldState = FieldState.UNVERIFIED
    revocation_state: FieldState = FieldState.UNVERIFIED
    project_binding_state: FieldState = FieldState.UNVERIFIED
    scope_binding_state: FieldState = FieldState.UNVERIFIED
    trusted_clock_state: FieldState = FieldState.UNVERIFIED
    operator_context_state: FieldState = FieldState.UNVERIFIED


class PreflightSection(_ReadinessModel):
    state: FieldState = FieldState.BLOCKED
    # Repository tooling readiness: the read-only preflight interface now exists
    # (Phase 40K.5). Operational orchestration over the real source/destination is
    # a separately authorized concern (40K.6+) and stays blocked until wired.
    production_read_only_orchestration_state: FieldState = FieldState.BLOCKED
    dataset_fingerprint_state: FieldState = FieldState.UNVERIFIED
    pipeline_state: FieldState = FieldState.UNVERIFIED
    destination_revision_state: FieldState = FieldState.UNVERIFIED
    backup_state: FieldState = FieldState.UNVERIFIED
    authorization_state: FieldState = FieldState.UNVERIFIED
    expected_write_set_state: FieldState = FieldState.UNVERIFIED
    expected_receipt_identity: str = _bounded_text(NOT_SUPPLIED)
    storage_capacity_state: FieldState = FieldState.UNVERIFIED
    evidence_destination_state: FieldState = FieldState.UNVERIFIED
    recovery_materials_state: FieldState = FieldState.UNVERIFIED


class StopConditionsSection(_ReadinessModel):
    state: FieldState = FieldState.BLOCKED
    all_acknowledged: bool = False
    active_conditions: tuple[str, ...] = ()

    @field_validator("all_acknowledged", mode="before")
    @classmethod
    def _flag_is_bool(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("active_conditions")
    @classmethod
    def _conditions_bounded(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) > MAX_READINESS_ACTIVE_CONDITIONS:
            raise ValueError("active_conditions exceeds the bound")
        if any(not item or len(item) > MAX_READINESS_TEXT for item in value):
            raise ValueError("each active condition must be bounded, non-empty text")
        return value


class EvidenceSection(_ReadinessModel):
    state: FieldState = FieldState.NOT_SUPPLIED
    preflight_packet: str = _bounded_text(NOT_SUPPLIED)
    authorization_packet: str = _bounded_text(NOT_SUPPLIED)
    backup_packet: str = _bounded_text(NOT_SUPPLIED)
    execution_packet: str = _bounded_text(NOT_SUPPLIED)
    receipt_packet: str = _bounded_text(NOT_SUPPLIED)
    post_run_packet: str = _bounded_text(NOT_SUPPLIED)
    recovery_packet: str = _bounded_text(NOT_SUPPLIED)


class ExecutionSection(_ReadinessModel):
    status: FieldState = FieldState.BLOCKED
    approved_command_identity: str = _bounded_text(NOT_SUPPLIED)
    attempt_id: str = _bounded_text(NOT_SUPPLIED)
    receipt_id: str = _bounded_text(NOT_SUPPLIED)
    final_ledger_revision: str = _bounded_text(NOT_SUPPLIED)
    final_commit_generation: str = _bounded_text(NOT_SUPPLIED)
    final_disposition: FieldState = FieldState.BLOCKED


class HumanDecisionsSection(_ReadinessModel):
    operator: str = _bounded_text(NOT_SUPPLIED)
    independent_reviewer: str = _bounded_text(NOT_SUPPLIED)
    authorization_issuer: str = _bounded_text(NOT_SUPPLIED)
    recovery_decision_maker: str = _bounded_text(NOT_SUPPLIED)
    devdevbuilds_go_no_go: str = _bounded_text(NOT_SUPPLIED)
    acceptance: str = _bounded_text(NOT_SUPPLIED)


class MigrationReadinessManifest(_ReadinessModel):
    """The complete, deterministically validated readiness manifest.

    Parses the checked-in ``phase-40k-readiness.v1`` template unchanged. Every
    section defaults to its fail-closed (``not_supplied`` / ``unverified`` /
    ``blocked``) state so an empty or partial manifest is representable and
    evaluated as not-ready rather than rejected outright.
    """

    schema_version: str = READINESS_TEMPLATE_SCHEMA_VERSION
    runbook_version: str = READINESS_RUNBOOK_VERSION
    repository: RepositorySection
    source_dataset: SourceDatasetSection = Field(default_factory=SourceDatasetSection)
    pipeline: PipelineSection = Field(default_factory=PipelineSection)
    destination: DestinationSection = Field(default_factory=DestinationSection)
    expected_counts: ExpectedCountsSection = Field(default_factory=ExpectedCountsSection)
    backup: BackupSection = Field(default_factory=BackupSection)
    authorization: AuthorizationSection = Field(default_factory=AuthorizationSection)
    preflight: PreflightSection = Field(default_factory=PreflightSection)
    stop_conditions: StopConditionsSection = Field(default_factory=StopConditionsSection)
    evidence: EvidenceSection = Field(default_factory=EvidenceSection)
    execution: ExecutionSection = Field(default_factory=ExecutionSection)
    human_decisions: HumanDecisionsSection = Field(default_factory=HumanDecisionsSection)

    @field_validator("schema_version")
    @classmethod
    def _schema_supported(cls, value: str) -> str:
        if value != READINESS_TEMPLATE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported readiness schema_version {value!r}; "
                f"expected {READINESS_TEMPLATE_SCHEMA_VERSION!r}"
            )
        return value

    def identity(self) -> str:
        return derive_readiness_manifest_identity(self)


def derive_readiness_manifest_identity(manifest: MigrationReadinessManifest) -> str:
    """Deterministic, domain-separated identity for a readiness manifest.

    Folds the canonical manifest content through SHA-256 under a version-scoped
    domain, so identical declarations always fingerprint identically. Pure — no
    clock, randomness, or environment read.
    """
    payload = canonical_json(
        {
            "domain": "migration-readiness/manifest",
            "version": READINESS_CONTRACT_VERSION,
            "value": manifest.model_dump(mode="json"),
        }
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"mm-readiness-{digest[:24]}"


def is_supplied(value: str) -> bool:
    """A value field is *supplied* when it is not the ``not_supplied`` sentinel."""
    return value != NOT_SUPPLIED


def looks_like_placeholder(value: str) -> bool:
    """True when a *supplied* value is a placeholder/fixture rather than real."""
    if not is_supplied(value):
        return False
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def looks_like_secret(value: str) -> bool:
    """True when a supplied value carries a credential/token/key shape.

    A pure lowercase-hex digest of the length the accepted algorithms produce is
    explicitly exempt: those are legitimate non-secret fingerprints, not tokens.
    """
    if not is_supplied(value):
        return False
    text = value.strip()
    lowered = text.lower()
    if any(marker in lowered for marker in SECRET_MARKERS):
        return True
    # Pure hexadecimal of any meaningful length is a fingerprint, digest, or
    # commit SHA — a legitimate non-secret identifier, never a token.
    if len(text) >= 16 and all(c in "0123456789abcdef" for c in lowered):
        return False
    # A long, unbroken, high-alphabet run with no whitespace is token-shaped.
    return len(text) >= 40 and " " not in text and not text.isdigit()
