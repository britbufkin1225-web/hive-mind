"""Phase 40D — Grounded Synthesis validation report contracts.

The typed **result** shapes for the Phase 40D guardrail layer: a closed
diagnostic taxonomy, a binary severity axis, one bounded diagnostic record, and
the packet validation report that carries an explicit synthesis-readiness
determination.

Deliberately a *separate module* rather than an extension of
``app.models.grounded_synthesis``:

* Phase 40D must not alter the stable Phase 40B ``grounded-synthesis.v1``
  contracts to make validation easier. The packet, evidence reference,
  provenance, artifact and request shapes are reused **unchanged**; nothing here
  redefines, mirrors, or narrows any of them.
* A validation report is a *new* shape describing an existing contract, the same
  way ``repository_observer_api`` describes ``repository_observer`` records
  without re-declaring them.

What this module deliberately does **not** add:

* No second context-packet model, evidence-record hierarchy, or provenance
  contract. :class:`SynthesisPacketValidationReport` refers to a packet by
  identifier and never embeds or restates one.
* No synthesis output, generated text, or repaired packet. A report describes; it
  never produces or corrects.
* No I/O, clock read, or randomness. Every field is caller-supplied and every
  derived value is a pure function of the model's own fields.

The load-bearing structural decisions:

* **Severity is a property of the code, not of the caller.**
  :data:`DIAGNOSTIC_SEVERITY` maps every :class:`GroundingDiagnosticCode` to a
  fixed :class:`GroundingDiagnosticSeverity`, and
  :class:`GroundingValidationDiagnostic` fills it in — rejecting a supplied
  severity that disagrees. A blocking condition therefore cannot be filed as
  advisory by a producer that would rather not block, which is the Phase 40D
  equivalent of the Phase 40B "no silent authority escalation" rule.
* **Diagnostics are canonically ordered and unique.** Determinism is contractual
  in Phase 40D, so the ordering rule lives in the model rather than in the
  producing service alone: an out-of-order or duplicated diagnostic list is a
  malformed report, not a cosmetic difference.
* **Readiness cannot outrun the diagnostics.** A report carrying any blocking
  diagnostic must assess ``blocked``, and ``synthesis_ready`` is true if and only
  if the assessment is ``ready``. A consumer can therefore branch on one boolean
  without re-deriving the rule.
* **It reconciles with the canonical Phase 40B verdict.**
  :meth:`SynthesisPacketValidationReport.to_validation_result` projects the
  report onto the existing :class:`SynthesisValidationResult`, so a consumer that
  already speaks ``grounded-synthesis.v1`` needs no new vocabulary to learn
  whether a packet is valid.

Phase 40D validates evidence; it still generates no Grounded Synthesis output.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.grounded_synthesis import (
    GROUNDED_SYNTHESIS_CONTRACT_VERSION,
    MAX_SYNTHESIS_COLLECTION_ITEMS,
    MAX_SYNTHESIS_ID_LENGTH,
    MAX_SYNTHESIS_SUMMARY_LENGTH,
    MAX_SYNTHESIS_VALIDATION_ISSUES,
    GroundedSynthesisMode,
    GroundingEvidenceKind,
    SynthesisReadinessStatus,
    SynthesisValidationIssue,
    SynthesisValidationIssueCode,
    SynthesisValidationResult,
    SynthesisValidationStatus,
    SynthesisValidationSubject,
)

# --------------------------------------------------------------------------- #
# Validation policy version.
#
# A stable identifier for the *ruleset*, deliberately separate from
# ``GROUNDED_SYNTHESIS_CONTRACT_VERSION`` (the wire shape) and from
# ``GROUNDING_CONTEXT_ASSEMBLY_VERSION`` (the assembly policy) — the same
# three-way separation Phase 40C established. The wire contract can stay
# ``grounded-synthesis.v1`` while the guardrail rules evolve, and a consumer can
# tell which ruleset produced a verdict without inferring it from the codes.
# --------------------------------------------------------------------------- #
GROUNDED_SYNTHESIS_VALIDATION_VERSION = "grounded-synthesis-validation.v1"

# A report may legitimately carry more diagnostics than the Phase 40B
# ``SynthesisValidationResult`` carries issues, because it also carries advisory
# entries that are not issues at all. It reuses the existing collection ceiling
# rather than declaring a new bound.
MAX_VALIDATION_DIAGNOSTICS = MAX_SYNTHESIS_COLLECTION_ITEMS


class GroundingDiagnosticSeverity(StrEnum):
    """Blocking vs advisory — the only two severities Phase 40D recognizes.

    Two values on purpose. A third ("error-ish but not really") would invite the
    exact ambiguity the Phase 40B :class:`SynthesisValidationStatus` avoided by
    staying binary: every diagnostic either prevents synthesis readiness or it
    does not, and a consumer must never have to guess which.
    """

    BLOCKING = "blocking"
    ADVISORY = "advisory"


class GroundingDiagnosticCode(StrEnum):
    """Closed taxonomy of Phase 40D packet guardrail findings.

    Finer-grained than :class:`SynthesisValidationIssueCode` on purpose: the
    Phase 40B codes are the stable *wire* taxonomy a validation result speaks,
    while these name the specific guardrail that fired, so a future review,
    export, or API surface can route on the actual condition.
    :data:`DIAGNOSTIC_ISSUE_CODE` maps each one back onto the canonical
    vocabulary, so the two never drift into competing taxonomies.
    """

    # Contract and policy version.
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    UNSUPPORTED_ASSEMBLY_VERSION = "unsupported_assembly_version"

    # Evidence identity.
    UNSUPPORTED_GROUNDING_KIND = "unsupported_grounding_kind"
    DUPLICATE_EVIDENCE_IDENTIFIER = "duplicate_evidence_identifier"
    CONFLICTING_EVIDENCE_IDENTITY = "conflicting_evidence_identity"
    CONFLICTING_SOURCE_IDENTITY = "conflicting_source_identity"
    REDUNDANT_EVIDENCE_IDENTITY = "redundant_evidence_identity"

    # Provenance.
    MISSING_PROVENANCE_REFERENCE = "missing_provenance_reference"
    MISSING_PROVENANCE_SOURCE = "missing_provenance_source"
    MALFORMED_PROVENANCE_IDENTIFIER = "malformed_provenance_identifier"
    UNEXPECTED_PROVENANCE_REFERENCE_KIND = "unexpected_provenance_reference_kind"
    DANGLING_EVIDENCE_REFERENCE = "dangling_evidence_reference"
    UNGROUNDED_CONTEXT_SUMMARY = "ungrounded_context_summary"
    UNEXPECTED_CONTEXT_SUMMARY = "unexpected_context_summary"

    # Source and repository safety.
    UNSAFE_SOURCE_REFERENCE = "unsafe_source_reference"
    UNSAFE_REPOSITORY_IDENTITY = "unsafe_repository_identity"

    # Packet self-consistency.
    EVIDENCE_COUNT_MISMATCH = "evidence_count_mismatch"
    COVERAGE_COUNT_MISMATCH = "coverage_count_mismatch"
    MISSING_COVERAGE_ENTRY = "missing_coverage_entry"
    CONFLICT_COUNT_MISMATCH = "conflict_count_mismatch"
    READINESS_CLAIM_UNSUPPORTED = "readiness_claim_unsupported"
    PACKET_IDENTITY_MISMATCH = "packet_identity_mismatch"
    NON_CANONICAL_ORDERING = "non_canonical_ordering"

    # Bounds, truncation and overflow.
    PACKET_BOUND_EXCEEDED = "packet_bound_exceeded"
    FAMILY_BOUND_EXCEEDED = "family_bound_exceeded"
    OVERSIZED_PACKET_FIELD = "oversized_packet_field"
    INVALID_TRUNCATION_CLAIM = "invalid_truncation_claim"
    UNDECLARED_TRUNCATION = "undeclared_truncation"
    UNKNOWN_CRITICAL_EVIDENCE = "unknown_critical_evidence"

    # Grounding sufficiency.
    NO_GROUNDING_EVIDENCE = "no_grounding_evidence"


# --------------------------------------------------------------------------- #
# Fixed severity per code.
#
# Blocking is the default posture: a condition is advisory only when it leaves
# the packet's grounding fully trustworthy and traceable.
#
# The four advisory members, with reasons:
#
# * ``redundant_evidence_identity`` — the same evidence recorded twice with
#   *identical* material. Wasteful, but nothing about it is untrue, and blocking
#   it would punish a packet that is merely repetitive.
# * ``unexpected_provenance_reference_kind`` — the pointer kind is outside the
#   set Hive|Mind's own grounding producers emit for that family. The Phase 37A
#   contract permits every pointer kind, so this is "may not resolve", not
#   "cannot be trusted".
# * ``non_canonical_ordering`` — ordering is presentation, not grounding.
#   Reordering a packet changes no claim and drops no evidence.
# * ``no_grounding_evidence`` — an empty packet is a legitimate, honestly
#   declared outcome (Phase 40B forbids it from claiming ``ready`` at all), so
#   the emptiness is surfaced rather than treated as a failure.
# --------------------------------------------------------------------------- #
DIAGNOSTIC_SEVERITY: dict[GroundingDiagnosticCode, GroundingDiagnosticSeverity] = {
    GroundingDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNSUPPORTED_ASSEMBLY_VERSION: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNSUPPORTED_GROUNDING_KIND: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.DUPLICATE_EVIDENCE_IDENTIFIER: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.CONFLICTING_SOURCE_IDENTITY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.REDUNDANT_EVIDENCE_IDENTITY: (
        GroundingDiagnosticSeverity.ADVISORY
    ),
    GroundingDiagnosticCode.MISSING_PROVENANCE_REFERENCE: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.MISSING_PROVENANCE_SOURCE: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.MALFORMED_PROVENANCE_IDENTIFIER: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNEXPECTED_PROVENANCE_REFERENCE_KIND: (
        GroundingDiagnosticSeverity.ADVISORY
    ),
    GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNGROUNDED_CONTEXT_SUMMARY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNEXPECTED_CONTEXT_SUMMARY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.COVERAGE_COUNT_MISMATCH: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.MISSING_COVERAGE_ENTRY: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.CONFLICT_COUNT_MISMATCH: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.NON_CANONICAL_ORDERING: (
        GroundingDiagnosticSeverity.ADVISORY
    ),
    GroundingDiagnosticCode.PACKET_BOUND_EXCEEDED: GroundingDiagnosticSeverity.BLOCKING,
    GroundingDiagnosticCode.FAMILY_BOUND_EXCEEDED: GroundingDiagnosticSeverity.BLOCKING,
    GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD: GroundingDiagnosticSeverity.BLOCKING,
    GroundingDiagnosticCode.INVALID_TRUNCATION_CLAIM: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.UNDECLARED_TRUNCATION: GroundingDiagnosticSeverity.BLOCKING,
    GroundingDiagnosticCode.UNKNOWN_CRITICAL_EVIDENCE: (
        GroundingDiagnosticSeverity.BLOCKING
    ),
    GroundingDiagnosticCode.NO_GROUNDING_EVIDENCE: GroundingDiagnosticSeverity.ADVISORY,
}

# --------------------------------------------------------------------------- #
# Projection onto the canonical Phase 40B issue taxonomy.
#
# Every Phase 40D code maps onto exactly one existing
# ``SynthesisValidationIssueCode``, so a report can be expressed as a
# ``SynthesisValidationResult`` without inventing a second wire vocabulary. The
# mapping is many-to-one by design: the Phase 40B codes name *what kind of
# failure* a consumer is looking at, which is coarser than naming which guardrail
# fired, and widening the Phase 40B enum to restore a one-to-one mapping would be
# exactly the contract change Phase 40D must not make.
# --------------------------------------------------------------------------- #
DIAGNOSTIC_ISSUE_CODE: dict[GroundingDiagnosticCode, SynthesisValidationIssueCode] = {
    GroundingDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION: (
        SynthesisValidationIssueCode.INVALID_REQUEST
    ),
    GroundingDiagnosticCode.UNSUPPORTED_ASSEMBLY_VERSION: (
        SynthesisValidationIssueCode.INVALID_REQUEST
    ),
    GroundingDiagnosticCode.UNSUPPORTED_GROUNDING_KIND: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.DUPLICATE_EVIDENCE_IDENTIFIER: (
        SynthesisValidationIssueCode.DUPLICATE_EVIDENCE_REFERENCE
    ),
    GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY: (
        SynthesisValidationIssueCode.CONFLICTING_EVIDENCE
    ),
    GroundingDiagnosticCode.CONFLICTING_SOURCE_IDENTITY: (
        SynthesisValidationIssueCode.CONFLICTING_EVIDENCE
    ),
    GroundingDiagnosticCode.REDUNDANT_EVIDENCE_IDENTITY: (
        SynthesisValidationIssueCode.DUPLICATE_EVIDENCE_REFERENCE
    ),
    GroundingDiagnosticCode.MISSING_PROVENANCE_REFERENCE: (
        SynthesisValidationIssueCode.MISSING_PROVENANCE
    ),
    GroundingDiagnosticCode.MISSING_PROVENANCE_SOURCE: (
        SynthesisValidationIssueCode.MISSING_PROVENANCE
    ),
    GroundingDiagnosticCode.MALFORMED_PROVENANCE_IDENTIFIER: (
        SynthesisValidationIssueCode.MALFORMED_REFERENCE
    ),
    GroundingDiagnosticCode.UNEXPECTED_PROVENANCE_REFERENCE_KIND: (
        SynthesisValidationIssueCode.MALFORMED_REFERENCE
    ),
    GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE: (
        SynthesisValidationIssueCode.MALFORMED_REFERENCE
    ),
    GroundingDiagnosticCode.UNGROUNDED_CONTEXT_SUMMARY: (
        SynthesisValidationIssueCode.MISSING_PROVENANCE
    ),
    GroundingDiagnosticCode.UNEXPECTED_CONTEXT_SUMMARY: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.COVERAGE_COUNT_MISMATCH: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.MISSING_COVERAGE_ENTRY: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.CONFLICT_COUNT_MISMATCH: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.NON_CANONICAL_ORDERING: (
        SynthesisValidationIssueCode.CONSTRAINT_VIOLATION
    ),
    GroundingDiagnosticCode.PACKET_BOUND_EXCEEDED: (
        SynthesisValidationIssueCode.BOUNDS_EXCEEDED
    ),
    GroundingDiagnosticCode.FAMILY_BOUND_EXCEEDED: (
        SynthesisValidationIssueCode.BOUNDS_EXCEEDED
    ),
    GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD: (
        SynthesisValidationIssueCode.BOUNDS_EXCEEDED
    ),
    GroundingDiagnosticCode.INVALID_TRUNCATION_CLAIM: (
        SynthesisValidationIssueCode.BOUNDS_EXCEEDED
    ),
    GroundingDiagnosticCode.UNDECLARED_TRUNCATION: (
        SynthesisValidationIssueCode.BOUNDS_EXCEEDED
    ),
    GroundingDiagnosticCode.UNKNOWN_CRITICAL_EVIDENCE: (
        SynthesisValidationIssueCode.INSUFFICIENT_EVIDENCE
    ),
    GroundingDiagnosticCode.NO_GROUNDING_EVIDENCE: (
        SynthesisValidationIssueCode.INSUFFICIENT_EVIDENCE
    ),
}


def _require_int(value: Any) -> Any:
    """Reject a ``bool`` supplied where a count is expected.

    The Phase 40B ``_reject_bool`` rule, restated locally rather than imported
    from a sibling module's private surface: each contract module in this family
    owns its own edge guards so no module depends on another's internals.
    """

    if isinstance(value, bool):
        raise ValueError("integer field must not be a boolean")
    return value


def _require_flag(value: Any) -> Any:
    """Reject a non-``bool`` supplied where a flag is expected."""

    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


def _clean_text(value: str, label: str) -> str:
    """Strip and reject blank/whitespace-only required text."""

    text = value.strip()
    if not text:
        raise ValueError(f"{label} must not be empty or whitespace-only")
    return text


class _ValidationModel(BaseModel):
    """Shared config: unknown fields are rejected, never absorbed.

    Same rationale as the Phase 40B ``_GroundedSynthesisModel``: a report is
    consumed by future API, review and export surfaces, and ``extra="forbid"`` is
    what stops a provider-specific or execution-shaped field riding into one on
    an unknown key.
    """

    model_config = ConfigDict(extra="forbid")


class GroundingValidationDiagnostic(_ValidationModel):
    """One bounded, secret-free guardrail finding.

    ``severity`` is derived from ``code`` through :data:`DIAGNOSTIC_SEVERITY`. It
    may be omitted entirely, and supplying one that disagrees with the code is
    rejected rather than honored — the classification belongs to the taxonomy, so
    a blocking condition cannot be downgraded at the call site.

    ``subject_id`` names the packet-local record the finding is about (an
    evidence id, conflict id, gap id, or the packet id itself) and
    ``grounding_kind`` names the evidence family when the finding is
    family-scoped. Both are optional because a finding may legitimately concern
    the packet as a whole.

    ``message`` is bounded, human-readable, and carries only counts, closed-enum
    literals, and packet-local identifiers — never a filesystem path, remote URL,
    credential, command output, or copied provider payload. Phase 40C established
    that raw provider material never enters a packet; Phase 40D must not
    reintroduce it through a diagnostic.
    """

    code: GroundingDiagnosticCode
    severity: GroundingDiagnosticSeverity | None = None
    message: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_SYNTHESIS_ID_LENGTH)
    grounding_kind: GroundingEvidenceKind | None = None

    @model_validator(mode="before")
    @classmethod
    def _severity_follows_code(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "code" not in data:
            return data
        try:
            code = GroundingDiagnosticCode(data["code"])
        except ValueError:
            # Let the field validator report the unknown code with its own
            # message rather than masking it with a lookup failure.
            return data
        expected = DIAGNOSTIC_SEVERITY[code]
        supplied = data.get("severity")
        if supplied is None:
            return {**data, "severity": expected}
        if GroundingDiagnosticSeverity(supplied) is not expected:
            raise ValueError(
                f"diagnostic {code.value!r} is {expected.value!r}; "
                "severity is fixed by the code and cannot be reclassified"
            )
        return data

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_text(value, "diagnostic message")

    @field_validator("subject_id")
    @classmethod
    def _subject_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_text(value, "diagnostic subject_id")

    @property
    def blocking(self) -> bool:
        """Whether this finding prevents synthesis readiness."""

        return self.severity is GroundingDiagnosticSeverity.BLOCKING

    def sort_key(self) -> tuple[str, str, str, str]:
        """The canonical ordering key for a diagnostic list.

        Code first so related findings group together, then the family and
        subject so a per-record view is contiguous, then the message as the final
        deterministic tie-break. Severity is deliberately *not* in the key: it is
        a pure function of the code, so including it would add nothing and would
        make the order look as though it could vary independently.
        """

        return (
            self.code.value,
            "" if self.grounding_kind is None else self.grounding_kind.value,
            self.subject_id or "",
            self.message,
        )


class SynthesisPacketValidationReport(_ValidationModel):
    """The deterministic verdict over one :class:`SynthesisContextPacket`.

    A **passive result record**. It holds no packet, repairs nothing, and carries
    no synthesis output; it names the packet it describes by identifier and
    records what the guardrails found.

    Cross-field rules make the verdict impossible to misread:

    * any blocking diagnostic forces ``assessed_readiness`` to ``blocked``;
    * ``synthesis_ready`` is true if and only if ``assessed_readiness`` is
      ``ready``, so the boolean can never disagree with the status;
    * a ``ready`` assessment requires the packet to have carried evidence — the
      Phase 40B rule that an empty packet cannot be ready, restated where the
      readiness decision is actually made;
    * diagnostics are unique and canonically ordered, because Phase 40D promises
      identical output for identical semantic input.
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    validation_version: str = Field(default=GROUNDED_SYNTHESIS_VALIDATION_VERSION)
    packet_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    request_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    mode: GroundedSynthesisMode
    declared_readiness: SynthesisReadinessStatus
    assessed_readiness: SynthesisReadinessStatus
    synthesis_ready: bool
    evidence_count: int = Field(ge=0)
    family_count: int = Field(ge=0)
    diagnostics: list[GroundingValidationDiagnostic] = Field(
        default_factory=list, max_length=MAX_VALIDATION_DIAGNOSTICS
    )
    read_only: bool = True

    @field_validator("schema_version")
    @classmethod
    def _contract_version_supported(cls, value: str) -> str:
        if value != GROUNDED_SYNTHESIS_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {GROUNDED_SYNTHESIS_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("validation_version")
    @classmethod
    def _validation_version_supported(cls, value: str) -> str:
        if value != GROUNDED_SYNTHESIS_VALIDATION_VERSION:
            raise ValueError(
                f"unsupported validation_version {value!r}; "
                f"expected {GROUNDED_SYNTHESIS_VALIDATION_VERSION!r}"
            )
        return value

    @field_validator("packet_id", "request_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_text(value, "report identifier")

    @field_validator("evidence_count", "family_count", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("synthesis_ready", "read_only", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_flag(value)

    @model_validator(mode="after")
    def _validate_report(self) -> "SynthesisPacketValidationReport":
        if not self.read_only:
            # A report describes a packet; there is no mode in which producing
            # one grants write authority (Phase 40A §8).
            raise ValueError("read_only must remain True")

        seen: set[tuple[str, str, str, str]] = set()
        previous: tuple[str, str, str, str] | None = None
        for diagnostic in self.diagnostics:
            key = diagnostic.sort_key()
            if key in seen:
                raise ValueError(
                    f"duplicate diagnostic {diagnostic.code.value!r}; a finding is "
                    "reported once per subject"
                )
            if previous is not None and key < previous:
                raise ValueError(
                    "diagnostics must be in canonical order "
                    "(code, grounding_kind, subject_id, message)"
                )
            seen.add(key)
            previous = key

        if any(item.blocking for item in self.diagnostics):
            if self.assessed_readiness is not SynthesisReadinessStatus.BLOCKED:
                raise ValueError(
                    "a report carrying a blocking diagnostic must assess "
                    "'blocked' readiness"
                )
        if self.synthesis_ready is not (
            self.assessed_readiness is SynthesisReadinessStatus.READY
        ):
            raise ValueError(
                "synthesis_ready must be True if and only if assessed_readiness "
                "is 'ready'"
            )
        if (
            self.assessed_readiness is SynthesisReadinessStatus.READY
            and self.evidence_count == 0
        ):
            raise ValueError("a packet with no evidence cannot be assessed 'ready'")
        if self.family_count > self.evidence_count:
            raise ValueError(
                f"family_count {self.family_count} exceeds evidence_count "
                f"{self.evidence_count}"
            )
        return self

    @property
    def blocking_diagnostics(self) -> list[GroundingValidationDiagnostic]:
        """Findings that prevent synthesis readiness, in canonical order."""

        return [item for item in self.diagnostics if item.blocking]

    @property
    def advisory_diagnostics(self) -> list[GroundingValidationDiagnostic]:
        """Findings that are visible but do not prevent readiness."""

        return [item for item in self.diagnostics if not item.blocking]

    def to_validation_result(self) -> SynthesisValidationResult:
        """Project the report onto the canonical Phase 40B validation verdict.

        Only *blocking* diagnostics become issues: the Phase 40B contract makes a
        result valid if and only if it carries no issues, so filing an advisory
        finding as an issue would turn every merely-repetitive packet into an
        invalid one.

        The Phase 40B issue list is bounded at
        :data:`MAX_SYNTHESIS_VALIDATION_ISSUES`. When more blocking findings
        exist, the tail is replaced with one explicit ``bounds_exceeded`` issue
        rather than silently dropped — the same "represent the truncation"
        discipline Phase 40C applied to warnings. The full set always remains on
        the report itself.
        """

        blocking = self.blocking_diagnostics
        kept = (
            blocking
            if len(blocking) <= MAX_SYNTHESIS_VALIDATION_ISSUES
            else blocking[: MAX_SYNTHESIS_VALIDATION_ISSUES - 1]
        )
        issues = [
            SynthesisValidationIssue(
                code=DIAGNOSTIC_ISSUE_CODE[item.code],
                message=item.message,
                subject_id=item.subject_id,
            )
            for item in kept
        ]
        if len(kept) < len(blocking):
            issues.append(
                SynthesisValidationIssue(
                    code=SynthesisValidationIssueCode.BOUNDS_EXCEEDED,
                    message=(
                        f"{len(blocking) - len(kept)} additional blocking "
                        f"diagnostic(s) omitted to satisfy the "
                        f"{MAX_SYNTHESIS_VALIDATION_ISSUES} issue bound"
                    ),
                    subject_id=self.packet_id,
                )
            )
        return SynthesisValidationResult(
            subject=SynthesisValidationSubject.CONTEXT_PACKET,
            subject_id=self.packet_id,
            status=(
                SynthesisValidationStatus.INVALID
                if issues
                else SynthesisValidationStatus.VALID
            ),
            issues=issues,
            human_review_required=True,
        )
