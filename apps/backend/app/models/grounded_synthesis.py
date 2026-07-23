"""Phase 40B — Grounded Synthesis Layer contract types (``grounded-synthesis.v1``).

Contract and schema foundation only. These are the stable **wire shapes** for the
Grounded Synthesis Layer designed in Phase 40A
(``docs/create-layer-architecture.md`` and
``docs/planning/phase-40a-create-layer-foundation-project-cohesion.md``). This
module adds **NO** synthesis behavior: no producer, no grounding assembly, no
evidence lookup, no policy engine, no endpoint, no persistence, no repository or
graph mutation, no Active Memory insertion, and no AI/LLM provider integration.
It defines *shapes* and their bounded validation only — exactly as Phase 37B
defined the ``active-memory.v1`` contracts before any logic ran, and Phase 37I
defined ``repo-observer.v1``.

Conventions (kept identical to ``active_memory.py`` / ``repository_workspace.py``
so all four contract layers read the same):

* Enums are :class:`enum.StrEnum` with ``UPPER_SNAKE`` member names whose
  serialized value is the ``snake_case`` string literal. Because these are
  ``StrEnum``, the serialized value *is* that literal — it is the stable wire
  contract.
* Every model sets ``model_config = ConfigDict(extra="forbid")`` (the Phase
  37I/39B convention). Unknown fields are rejected rather than silently
  absorbed, which is what keeps a provider-specific field (``model``,
  ``temperature``, ``api_key``, a prompt template) from ever leaking into a
  request through a permissive schema.
* Client-supplied free text and every collection carry defensive upper bounds
  (``MAX_SYNTHESIS_*``), matching the Phase 18B / 37B bounded-field discipline:
  oversized or unbounded input is rejected at the contract edge.
* Existing vocabularies are **reused, not duplicated**. Evidence typing,
  evidence pointers, source identity, scope, confidence bands, and contradiction
  severity come from ``app.models.active_memory``; re-declaring them here would
  create two vocabularies that could drift apart (Phase 40A §3.4, §6).

Design rationale for every significant decision is recorded inline. The headline
decisions:

* **Deterministic by construction.** Nothing in this module reads a clock,
  generates a random identifier, touches the filesystem, runs Git, queries a
  store, or calls a network/model provider. Every timestamp and identifier is
  *caller-supplied*; :func:`derive_grounded_synthesis_id` derives an id solely
  from explicitly normalized inputs using the existing repository hashing
  convention (``repository_evidence_projection._stable_id``).
* **Proposed, never accepted.** :class:`GroundedSynthesisArtifact` is a
  *proposal*. There is deliberately no ``approved``/``accepted``/``canonical``/
  ``committed``/``applied`` state anywhere in
  :class:`SynthesisReadinessStatus`, and ``human_review_required`` /
  ``read_only`` are pinned ``True`` rather than being caller-settable
  (Phase 40A §7, §8).
* **Provenance is mandatory for a grounded artifact.** An artifact carries a
  required :class:`SynthesisProvenance`; a ``proposed`` artifact must cite
  evidence, and every citation must appear in the provenance's used-evidence
  set. A grounded claim can never outrun its recorded grounding
  (Phase 40A §6).
* **Insufficient evidence is a first-class outcome, never a silent success.**
  :class:`SynthesisReadinessStatus` and :class:`SynthesisValidationIssueCode`
  both carry ``insufficient_evidence``, and the cross-field validators refuse to
  let an ungrounded packet or artifact call itself ``ready``/``proposed``
  (Phase 40A §9).

No Grounded Synthesis runtime exists after this phase. Declaring a shape is not
producing an output; nothing here synthesizes, assembles, validates policy,
persists, exports, or approves anything — those are later phases (40C onward)
built on top of these contracts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.active_memory import (
    ConfidenceBand,
    ContradictionSeverity,
    EvidenceReference,
    EvidenceType,
    MemoryScope,
    MemorySource,
)
from app.services.validation import assert_within_nesting_depth

# --------------------------------------------------------------------------- #
# Contract version.
#
# A stable *wire* version for the whole grounded-synthesis contract family,
# decoupled from the application/package version so the type contract can evolve
# on its own cadence — the same decision recorded for
# ``ACTIVE_MEMORY_CONTRACT_VERSION``. It is a fixed literal, not derived from a
# package version, so a client can pin against it deterministically. Every
# top-level record carries it and rejects any other value rather than guessing
# (Phase 40A §12: explicit version discriminator, no silent coercion).
# --------------------------------------------------------------------------- #
GROUNDED_SYNTHESIS_CONTRACT_VERSION = "grounded-synthesis.v1"


# --------------------------------------------------------------------------- #
# Bounded free-text / collection / metadata limits.
#
# Defensive upper bounds for caller-supplied fields, mirroring the Phase 18B and
# 37B rationale: they reject pathologically large input at the contract boundary
# without constraining any realistic value, and they satisfy the Phase 40A §10
# "bounded everything" security principle. Collection bounds are deliberately
# *smaller* than the Active Memory ceiling (1024): a grounding packet is a
# curated, human-reviewable selection, not a dump of every record in the store.
# --------------------------------------------------------------------------- #
MAX_SYNTHESIS_ID_LENGTH = 256
MAX_SYNTHESIS_LABEL_LENGTH = 512
MAX_SYNTHESIS_SUMMARY_LENGTH = 2048
MAX_SYNTHESIS_OBJECTIVE_LENGTH = 4096
MAX_SYNTHESIS_SECTION_HEADING_LENGTH = 512
MAX_SYNTHESIS_SECTION_BODY_LENGTH = 16_384
MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH = 65_536

MAX_SYNTHESIS_COLLECTION_ITEMS = 256
MAX_SYNTHESIS_EVIDENCE_REFERENCES = 128
MAX_SYNTHESIS_CONTEXT_SUMMARIES = 128
MAX_SYNTHESIS_ARTIFACT_SECTIONS = 64
MAX_SYNTHESIS_CITATIONS = 128
MAX_SYNTHESIS_WARNINGS = 64
MAX_SYNTHESIS_CONFLICTS = 64
MAX_SYNTHESIS_MISSING_CONTEXT_ITEMS = 64
MAX_SYNTHESIS_UNRESOLVED_CLAIMS = 64
MAX_SYNTHESIS_VALIDATION_ISSUES = 64

MAX_SYNTHESIS_METADATA_ENTRIES = 32
MAX_SYNTHESIS_METADATA_KEY_LENGTH = 128
MAX_SYNTHESIS_METADATA_VALUE_LENGTH = 1024
# Metadata is a shallow, inspectable bag — never an arbitrary nested document.
# Four levels covers every realistic annotation while rejecting the
# recursion-shaped payloads Phase 18D named (see ``assert_within_nesting_depth``).
MAX_SYNTHESIS_METADATA_DEPTH = 4

MAX_SYNTHESIS_DIGEST_LENGTH = 128


# =========================================================================== #
# Enumerations (closed wire vocabularies)
# =========================================================================== #
class GroundedSynthesisMode(StrEnum):
    """The capability *within* the Grounded Synthesis Layer a request invokes.

    These are **capabilities, not layers** (Phase 40A §0, §1.2). ``musings`` is
    the low-authority exploratory capability; ``loom`` is the capability that
    assembles evidence, context, constraints, and intent into a coherent
    synthesis output. Neither is a name for the architecture.

    A closed enum (not free text) because every downstream boundary — allowed
    artifact categories, readiness rules, review requirements — branches on mode.
    An unsupported value fails validation explicitly rather than defaulting.
    """

    MUSINGS = "musings"
    LOOM = "loom"


class SynthesisArtifactCategory(StrEnum):
    """Closed catalog of *proposed* output categories (Phase 40A §1.1, §12.1).

    Every member names a proposal, draft, plan, packet, or bounded artifact. No
    member names an applied change: ``patch_proposal`` is an artifact
    *describing* a change, never an applied one (Phase 40A §8). ``musing`` is
    included as the lowest-authority category produced by
    :attr:`GroundedSynthesisMode.MUSINGS`.
    """

    MUSING = "musing"
    IMPLEMENTATION_PROPOSAL = "implementation_proposal"
    WORK_PACKET = "work_packet"
    ARCHITECTURE_DRAFT = "architecture_draft"
    CODE_CHANGE_PLAN = "code_change_plan"
    DOCUMENTATION_DRAFT = "documentation_draft"
    TEST_PLAN = "test_plan"
    ISSUE_DRAFT = "issue_draft"
    PULL_REQUEST_DRAFT = "pull_request_draft"
    DESIGN_BRIEF = "design_brief"
    PATCH_PROPOSAL = "patch_proposal"
    AGENT_CONTRIBUTION_PACKET = "agent_contribution_packet"


class GroundingEvidenceKind(StrEnum):
    """Which existing Hive|Mind grounding source an evidence reference points at.

    This is the one genuinely *new* vocabulary in this family: it names the
    Intelligence-Layer producer of a piece of grounding, which no existing enum
    captures. It is deliberately closed to sources that already exist in the
    repository (Phase 40A §3, §6) so a reference can never claim a grounding
    source Hive|Mind cannot actually produce.

    It is orthogonal to :class:`~app.models.active_memory.EvidenceType`, which
    describes *what kind of proof* the evidence is; this describes *which
    Hive|Mind subsystem holds it*.
    """

    REPOSITORY_OBSERVATION = "repository_observation"
    REPOSITORY_DRIFT_FINDING = "repository_drift_finding"
    ACTIVE_MEMORY_RECORD = "active_memory_record"
    ACTIVE_MEMORY_EVIDENCE_RECORD = "active_memory_evidence_record"
    CONTRADICTION_RECORD = "contradiction_record"
    CONTEXT_PACKET_ENTRY = "context_packet_entry"
    KNOWLEDGE_GRAPH_NODE = "knowledge_graph_node"
    SOURCE_REGISTRY_ENTRY = "source_registry_entry"
    QUERY_TRAIL = "query_trail"


class SynthesisReadinessStatus(StrEnum):
    """Bounded readiness/lifecycle state for a request, packet, or artifact.

    A *status vocabulary*, not an execution state machine: this module defines
    no transition table, no scheduler, and no autonomous advancement. Nothing
    here advances a status; a caller declares one and the cross-field validators
    check it is consistent with the evidence actually present.

    Deliberately **absent**: any state implying content was written, merged,
    published, applied, accepted, or committed. The strongest state a Grounded
    Synthesis output can reach in this contract family is ``proposed``
    (Phase 40A §7, §8). Human acceptance is a separate, later, human-gated
    concern (Phase 40F) and is not representable here.
    """

    DRAFT = "draft"
    CONTEXT_REQUIRED = "context_required"
    READY = "ready"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED = "blocked"
    PROPOSED = "proposed"
    VALIDATION_FAILED = "validation_failed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class SynthesisGenerationMethod(StrEnum):
    """How a proposed artifact was produced.

    A single-member enum, on purpose. Phase 40A §11 pins the near-term Grounded
    Synthesis phases to a **deterministic-only** core; any future generative step
    is a separately-gated addition that must extend this vocabulary explicitly
    and be re-reviewed. Encoding that as a one-value closed enum means a
    model-backed producer cannot be recorded as legitimate provenance without a
    deliberate contract change.
    """

    DETERMINISTIC = "deterministic"


class SynthesisWarningCode(StrEnum):
    """Closed vocabulary of "do not rely on this" signals.

    Bounded codes rather than free prose so a consumer (and a future reviewer
    UI) can route on the reason. Mirrors the Active Memory
    :class:`~app.models.active_memory.PacketWarning` discipline: a warning is a
    reference plus a reason, never an inlined dump.
    """

    STALE_BASELINE = "stale_baseline"
    MISSING_CONTEXT = "missing_context"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    COVERAGE_GAP = "coverage_gap"
    CONSTRAINT_LIMITED = "constraint_limited"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    BOUNDS_EXCEEDED = "bounds_exceeded"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class SynthesisValidationStatus(StrEnum):
    """Overall validation verdict: valid or invalid.

    Only two values, because a validation result must never be *partially*
    valid. Detail lives in :class:`SynthesisValidationIssue`; the verdict itself
    stays binary so no consumer can read a degraded result as a passing one.
    """

    VALID = "valid"
    INVALID = "invalid"


class SynthesisValidationSubject(StrEnum):
    """Which contract a validation result describes."""

    REQUEST = "request"
    CONTEXT_PACKET = "context_packet"
    ARTIFACT = "artifact"
    PROVENANCE = "provenance"


class SynthesisValidationIssueCode(StrEnum):
    """Closed taxonomy of why validation failed (Phase 40A §9).

    Each member is a *typed failure outcome*, not an overloaded success. A
    malformed or unsupported input surfaces the specific code; it is never
    coerced into a valid state.
    """

    INVALID_REQUEST = "invalid_request"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED_MODE = "unsupported_mode"
    UNSUPPORTED_ARTIFACT_CATEGORY = "unsupported_artifact_category"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CONSTRAINT_VIOLATION = "constraint_violation"
    MALFORMED_REFERENCE = "malformed_reference"
    MISSING_PROVENANCE = "missing_provenance"
    DUPLICATE_EVIDENCE_REFERENCE = "duplicate_evidence_reference"
    BOUNDS_EXCEEDED = "bounds_exceeded"


# =========================================================================== #
# Shared bounded-validation helpers
#
# Small, pure, reusable checks so every model in the family enforces the same
# rules with the same error text. None of them reads external state.
# =========================================================================== #
def _reject_bool(value: Any) -> Any:
    """Reject a ``bool`` supplied where an integer is expected.

    Pydantic's lax mode happily reads ``True`` as ``1``. For bounded limits that
    silently turns a nonsense value into a limit of one, so the contract edge
    rejects it outright — the Phase 18B "reject at the edge, never coerce"
    discipline applied to the one coercion Pydantic would otherwise allow.
    """

    if isinstance(value, bool):
        raise ValueError("integer field must not be a boolean")
    return value


def _require_bool(value: Any) -> Any:
    """Reject a non-``bool`` supplied where a flag is expected.

    The mirror of :func:`_reject_bool`: ``0``/``1`` must not become a policy
    flag, because these flags carry safety meaning (``prohibit_repository_writes``
    et al.) and must be explicit.
    """

    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


def _clean_required_text(value: str, label: str) -> str:
    """Strip and reject blank/whitespace-only required text."""

    text = value.strip()
    if not text:
        raise ValueError(f"{label} must not be empty or whitespace-only")
    return text


def _clean_unique_ids(values: list[str], label: str) -> list[str]:
    """Strip, reject blanks/over-long entries, and reject duplicate identifiers.

    Duplicate identifiers are rejected rather than de-duplicated: silently
    collapsing them would hide a caller bug in which two different evidence
    items were assigned the same id, and would make citation/provenance
    cross-checks unsound.
    """

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_required_text(item, f"{label} entry")
        if len(text) > MAX_SYNTHESIS_ID_LENGTH:
            raise ValueError(
                f"{label} entry exceeds the {MAX_SYNTHESIS_ID_LENGTH} character limit"
            )
        if text in seen:
            raise ValueError(f"duplicate {label} entry {text!r}")
        seen.add(text)
        cleaned.append(text)
    return cleaned


def _validate_bounded_metadata(value: dict[str, Any]) -> dict[str, Any]:
    """Bound a free-form metadata bag: entries, key length, value length, depth.

    Metadata stays the forward-compatible escape hatch used across the API, but
    it is never an unbounded or deeply nested document (Phase 40A §10).
    """

    if len(value) > MAX_SYNTHESIS_METADATA_ENTRIES:
        raise ValueError(
            f"metadata exceeds the {MAX_SYNTHESIS_METADATA_ENTRIES} entry limit"
        )
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("metadata keys must be non-empty strings")
        if len(key) > MAX_SYNTHESIS_METADATA_KEY_LENGTH:
            raise ValueError(
                "metadata key exceeds the "
                f"{MAX_SYNTHESIS_METADATA_KEY_LENGTH} character limit"
            )
        if isinstance(item, str) and len(item) > MAX_SYNTHESIS_METADATA_VALUE_LENGTH:
            raise ValueError(
                "metadata value exceeds the "
                f"{MAX_SYNTHESIS_METADATA_VALUE_LENGTH} character limit"
            )
    assert_within_nesting_depth(value, MAX_SYNTHESIS_METADATA_DEPTH)
    return value


def _validate_contract_version(value: str) -> str:
    """Reject any schema version other than the one this module implements."""

    if value != GROUNDED_SYNTHESIS_CONTRACT_VERSION:
        raise ValueError(
            f"unsupported schema_version {value!r}; "
            f"expected {GROUNDED_SYNTHESIS_CONTRACT_VERSION!r}"
        )
    return value


def derive_grounded_synthesis_id(prefix: str, *parts: str) -> str:
    """Derive a stable identifier from explicitly-normalized caller inputs.

    Follows the existing repository convention
    (``repository_evidence_projection._stable_id``): a unit-separator join, a
    SHA-256 digest, and a bounded hex suffix behind a readable prefix. It is a
    pure function of its arguments — no clock, no randomness, no environment —
    so the same inputs always yield the same id. Callers that already own an
    identifier should keep using it; this exists only so a caller that needs a
    derived one does not invent an ad hoc (or random) scheme.
    """

    clean_prefix = _clean_required_text(prefix, "identifier prefix")
    if not parts:
        raise ValueError("identifier derivation requires at least one input part")
    normalized = [_clean_required_text(part, "identifier part") for part in parts]
    digest = hashlib.sha256("\x1f".join(normalized).encode("utf-8")).hexdigest()[:24]
    return f"{clean_prefix}-{digest}"


class _GroundedSynthesisModel(BaseModel):
    """Shared config for every model in the family.

    ``extra="forbid"`` is the load-bearing setting: it is what guarantees a
    provider-specific field (``model``, ``temperature``, ``max_tokens``,
    ``prompt``, ``api_key``) or an execution directive cannot ride into a
    contract on an unknown key (Phase 40A §2, §8).
    """

    model_config = ConfigDict(extra="forbid")


# =========================================================================== #
# Constraints
# =========================================================================== #
class SynthesisConstraints(_GroundedSynthesisModel):
    """Bounded constraints a future synthesis service must honor (Phase 40A §7–§10).

    Deliberately a *fixed set of declared limits and safety flags*, not a policy
    engine: there is no rule language, no expression evaluation, and no
    caller-supplied predicate. Phase 40A §14 rejected a broad policy engine for
    the foundation, so this stays a flat, inspectable, serializable record.

    The four ``prohibit_*``/``require_human_review`` flags are pinned to their
    safe value and reject being turned off. That is the contract-level
    expression of Phase 40A §8 "no silent authority escalation": a request
    cannot negotiate away the repository-write prohibition, the graph-mutation
    prohibition, or the human review gate.
    """

    max_evidence_references: int = Field(
        default=MAX_SYNTHESIS_EVIDENCE_REFERENCES,
        ge=1,
        le=MAX_SYNTHESIS_EVIDENCE_REFERENCES,
    )
    max_context_summaries: int = Field(
        default=MAX_SYNTHESIS_CONTEXT_SUMMARIES,
        ge=1,
        le=MAX_SYNTHESIS_CONTEXT_SUMMARIES,
    )
    max_artifact_sections: int = Field(
        default=MAX_SYNTHESIS_ARTIFACT_SECTIONS,
        ge=1,
        le=MAX_SYNTHESIS_ARTIFACT_SECTIONS,
    )
    max_artifact_content_length: int = Field(
        default=MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH,
        ge=1,
        le=MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH,
    )
    allowed_artifact_categories: list[SynthesisArtifactCategory] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_COLLECTION_ITEMS
    )
    require_evidence_citations: bool = True
    reject_unsupported_claims: bool = True
    surface_unresolved_conflicts: bool = True
    refuse_on_insufficient_grounding: bool = True
    require_human_review: bool = True
    prohibit_repository_writes: bool = True
    prohibit_graph_mutation: bool = True

    @field_validator(
        "max_evidence_references",
        "max_context_summaries",
        "max_artifact_sections",
        "max_artifact_content_length",
        mode="before",
    )
    @classmethod
    def _limits_are_integers(cls, value: Any) -> Any:
        return _reject_bool(value)

    @field_validator(
        "require_evidence_citations",
        "reject_unsupported_claims",
        "surface_unresolved_conflicts",
        "refuse_on_insufficient_grounding",
        "require_human_review",
        "prohibit_repository_writes",
        "prohibit_graph_mutation",
        mode="before",
    )
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("allowed_artifact_categories")
    @classmethod
    def _categories_unique(
        cls, value: list[SynthesisArtifactCategory]
    ) -> list[SynthesisArtifactCategory]:
        seen: set[SynthesisArtifactCategory] = set()
        for category in value:
            if category in seen:
                raise ValueError(
                    f"duplicate allowed artifact category {category.value!r}"
                )
            seen.add(category)
        return value

    @model_validator(mode="after")
    def _safety_flags_cannot_be_disabled(self) -> "SynthesisConstraints":
        # These are not tunables. Disabling any of them would let a request
        # declare itself exempt from the Phase 40A boundary, which is exactly
        # the silent authority escalation the architecture forbids.
        if not self.require_human_review:
            raise ValueError("require_human_review must remain True")
        if not self.prohibit_repository_writes:
            raise ValueError("prohibit_repository_writes must remain True")
        if not self.prohibit_graph_mutation:
            raise ValueError("prohibit_graph_mutation must remain True")
        return self

    def permits_category(self, category: SynthesisArtifactCategory) -> bool:
        """Whether ``category`` is allowed.

        An empty ``allowed_artifact_categories`` means "not narrowed" rather
        than "nothing allowed": narrowing is opt-in, and an empty allowlist is
        the natural default for a request that does not restrict its output.
        """

        return not self.allowed_artifact_categories or (
            category in self.allowed_artifact_categories
        )


# =========================================================================== #
# Grounding evidence
# =========================================================================== #
class GroundingEvidenceReference(_GroundedSynthesisModel):
    """A normalized, bounded pointer at one piece of existing Hive|Mind evidence.

    A *reference*, never the evidence itself and never a loader: constructing
    one performs no filesystem read, no Git command, no store query, no graph
    traversal, and no network access (Phase 40A §6, §8). It records where the
    evidence lives and what it is, so a future service can resolve it under its
    own bounded rules.

    Reuse is deliberate: ``evidence_type`` (the claim-relative strength
    hierarchy), ``reference`` (the bounded, never-executable pointer),
    ``source``, ``scope``, and ``confidence`` all come from ``active-memory.v1``
    rather than being re-declared, so grounded synthesis and Active Memory can
    never disagree about what a commit reference or a confidence band means.
    """

    evidence_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    grounding_kind: GroundingEvidenceKind
    reference: EvidenceReference
    evidence_type: EvidenceType | None = None
    source: MemorySource | None = None
    source_record_id: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_ID_LENGTH
    )
    scope: MemoryScope | None = None
    observed_at: datetime | None = None
    confidence: ConfidenceBand | None = None
    label: str | None = Field(default=None, max_length=MAX_SYNTHESIS_LABEL_LENGTH)
    summary: str | None = Field(default=None, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    content_digest: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_DIGEST_LENGTH
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id")
    @classmethod
    def _evidence_id_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "evidence_id")

    @field_validator("source_record_id", "label", "summary")
    @classmethod
    def _optional_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "optional text field")

    @field_validator("content_digest")
    @classmethod
    def _digest_is_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = _clean_required_text(value, "content_digest")
        # A digest is an integrity reference, not a free-form label. Requiring
        # lowercase hex keeps it comparable byte-for-byte across producers and
        # stops arbitrary text riding in under an integrity-sounding name.
        if not all(char in "0123456789abcdef" for char in text):
            raise ValueError("content_digest must be lowercase hexadecimal")
        return text

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)


class SynthesisContextSummary(_GroundedSynthesisModel):
    """A bounded, already-produced contextual summary carried into a packet.

    Contract only: nothing here summarizes anything. A summary must name the
    evidence it came from (``evidence_ids``), so a packet can never carry an
    unattributed narrative alongside its attributed evidence.
    """

    summary_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    label: str = Field(min_length=1, max_length=MAX_SYNTHESIS_LABEL_LENGTH)
    summary: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES
    )
    confidence: ConfidenceBand | None = None

    @field_validator("summary_id", "label", "summary")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "context summary field")

    @field_validator("evidence_ids")
    @classmethod
    def _evidence_ids_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "evidence_ids")


class SynthesisEvidenceConflict(_GroundedSynthesisModel):
    """An identified conflict between grounding evidence items.

    Surfaced, never resolved. Like
    :class:`~app.models.active_memory.ContradictionRecord`, a conflict requires
    at least two participants and carries no "winner" field — the Grounded
    Synthesis Layer must not pick one (Phase 40A §9 ``contradiction_blocked``).
    """

    conflict_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    summary: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    evidence_ids: list[str] = Field(max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES)
    severity: ContradictionSeverity | None = None
    contradiction_record_id: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_ID_LENGTH
    )

    @field_validator("conflict_id", "summary")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "conflict field")

    @field_validator("evidence_ids")
    @classmethod
    def _at_least_two_participants(cls, value: list[str]) -> list[str]:
        cleaned = _clean_unique_ids(value, "conflict evidence_ids")
        if len(cleaned) < 2:
            raise ValueError("a conflict must involve at least two evidence ids")
        return cleaned


class SynthesisMissingContext(_GroundedSynthesisModel):
    """An explicit gap: context the packet knows it does not have.

    Missing context is *data*, not an absence. Phase 40A §9 requires
    insufficient grounding to be visible rather than inferred from an empty
    collection, so a gap names itself and the evidence kinds that would close it.
    """

    gap_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    required_evidence_kinds: list[GroundingEvidenceKind] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_COLLECTION_ITEMS
    )

    @field_validator("gap_id", "description")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "missing-context field")

    @field_validator("required_evidence_kinds")
    @classmethod
    def _kinds_unique(
        cls, value: list[GroundingEvidenceKind]
    ) -> list[GroundingEvidenceKind]:
        seen: set[GroundingEvidenceKind] = set()
        for kind in value:
            if kind in seen:
                raise ValueError(f"duplicate required evidence kind {kind.value!r}")
            seen.add(kind)
        return value


class SynthesisSourceCoverage(_GroundedSynthesisModel):
    """How much of one grounding source class a packet actually drew on.

    ``referenced_count`` is a plain count of references of that kind; it is
    metadata about coverage, not a quality score. Counts are caller-supplied —
    nothing is computed here.
    """

    grounding_kind: GroundingEvidenceKind
    referenced_count: int = Field(ge=0)
    confidence: ConfidenceBand | None = None
    note: str | None = Field(default=None, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)

    @field_validator("referenced_count", mode="before")
    @classmethod
    def _count_is_integer(cls, value: Any) -> Any:
        return _reject_bool(value)

    @field_validator("note")
    @classmethod
    def _note_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "coverage note")


class SynthesisWarning(_GroundedSynthesisModel):
    """A bounded "do not rely on this" entry with a closed reason code."""

    code: SynthesisWarningCode
    message: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_SYNTHESIS_ID_LENGTH)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "warning message")

    @field_validator("subject_id")
    @classmethod
    def _subject_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "warning subject_id")


# =========================================================================== #
# Synthesis context packet
# =========================================================================== #
class SynthesisContextPacket(_GroundedSynthesisModel):
    """The stable input boundary: already-produced grounding, assembled.

    A **passive data structure** (Phase 40A §12.2 ``GroundingPacket``). It
    performs no repository inspection, no evidence gathering, no selection, and
    no policy evaluation — those are Phase 40C/40D. It only holds what a caller
    has already produced, in a bounded and checkable shape.

    Cross-field rules make grounding honest rather than assumed:

    * a packet with no evidence cannot claim ``ready``;
    * a packet with open gaps cannot claim ``ready``;
    * every conflict, summary, and coverage entry must reference evidence the
      packet actually carries — a dangling reference is a malformed packet, not
      a warning.

    Ordering is caller-preserved (a caller may have a meaningful order); use
    :meth:`normalized` for the deterministic canonical ordering, mirroring
    ``RepositoryWorkspaceConfig.normalized()``.
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    packet_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    request_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    correlation_id: str | None = Field(default=None, max_length=MAX_SYNTHESIS_ID_LENGTH)
    mode: GroundedSynthesisMode
    readiness: SynthesisReadinessStatus = SynthesisReadinessStatus.CONTEXT_REQUIRED
    evidence_references: list[GroundingEvidenceReference] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES
    )
    context_summaries: list[SynthesisContextSummary] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_CONTEXT_SUMMARIES
    )
    conflicts: list[SynthesisEvidenceConflict] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_CONFLICTS
    )
    missing_context: list[SynthesisMissingContext] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_MISSING_CONTEXT_ITEMS
    )
    source_coverage: list[SynthesisSourceCoverage] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_COLLECTION_ITEMS
    )
    warnings: list[SynthesisWarning] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_WARNINGS
    )
    assembled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("packet_id", "request_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "packet identifier")

    @field_validator("correlation_id")
    @classmethod
    def _correlation_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "correlation_id")

    @field_validator("read_only", mode="before")
    @classmethod
    def _read_only_is_boolean(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    @model_validator(mode="after")
    def _validate_packet(self) -> "SynthesisContextPacket":
        if not self.read_only:
            # The packet is an input boundary, never a write channel
            # (Phase 40A §8). There is no mode in which it is not read-only.
            raise ValueError("read_only must remain True")

        evidence_ids = [item.evidence_id for item in self.evidence_references]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence_references contain duplicate evidence_id values")
        known = set(evidence_ids)

        for summary in self.context_summaries:
            unknown = [item for item in summary.evidence_ids if item not in known]
            if unknown:
                raise ValueError(
                    f"context summary {summary.summary_id!r} references unknown "
                    f"evidence ids {sorted(unknown)!r}"
                )
        for conflict in self.conflicts:
            unknown = [item for item in conflict.evidence_ids if item not in known]
            if unknown:
                raise ValueError(
                    f"conflict {conflict.conflict_id!r} references unknown "
                    f"evidence ids {sorted(unknown)!r}"
                )

        seen_kinds: set[GroundingEvidenceKind] = set()
        for coverage in self.source_coverage:
            if coverage.grounding_kind in seen_kinds:
                raise ValueError(
                    "duplicate source_coverage entry for "
                    f"{coverage.grounding_kind.value!r}"
                )
            seen_kinds.add(coverage.grounding_kind)

        # Readiness must match the evidence actually present. An empty or
        # gap-bearing packet calling itself "ready" is precisely the silent
        # insufficient-evidence failure Phase 40A §9 forbids.
        if self.readiness is SynthesisReadinessStatus.READY:
            if not self.evidence_references:
                raise ValueError(
                    "a packet with no evidence references cannot be 'ready'; "
                    "use 'context_required' or 'insufficient_evidence'"
                )
            if self.missing_context:
                raise ValueError(
                    "a packet with unresolved missing context cannot be 'ready'"
                )
        return self

    def normalized(self) -> "SynthesisContextPacket":
        """Return a copy with every bounded collection deterministically ordered.

        Ordering keys are the entries' own stable identifiers (or, for coverage,
        the closed enum value), so the result is byte-stable across runs and
        independent of insertion order.
        """

        return SynthesisContextPacket(
            schema_version=self.schema_version,
            packet_id=self.packet_id,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            mode=self.mode,
            readiness=self.readiness,
            evidence_references=sorted(
                self.evidence_references, key=lambda item: item.evidence_id
            ),
            context_summaries=sorted(
                self.context_summaries, key=lambda item: item.summary_id
            ),
            conflicts=sorted(self.conflicts, key=lambda item: item.conflict_id),
            missing_context=sorted(self.missing_context, key=lambda item: item.gap_id),
            source_coverage=sorted(
                self.source_coverage, key=lambda item: item.grounding_kind.value
            ),
            warnings=sorted(
                self.warnings, key=lambda item: (item.code.value, item.message)
            ),
            assembled_at=self.assembled_at,
            metadata=self.metadata,
            read_only=self.read_only,
        )


# =========================================================================== #
# Request
# =========================================================================== #
class GroundedSynthesisRequest(_GroundedSynthesisModel):
    """A typed, versioned request for a future Grounded Synthesis capability.

    Carries *intent and grounding*, never *execution configuration*. There is
    deliberately no model name, provider, temperature, token budget, prompt
    template, credential, or agent directive — and ``extra="forbid"`` means one
    cannot be smuggled in as an unknown field (Phase 40A §2, §11).

    Grounding may be supplied either by reference (``context_packet_id``) or
    embedded (``context_packet``). Supplying both is allowed only when they
    agree; disagreeing identifiers are rejected rather than silently preferring
    one, because either choice would misrepresent what the request was grounded
    on.
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    request_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    mode: GroundedSynthesisMode
    objective: str = Field(min_length=1, max_length=MAX_SYNTHESIS_OBJECTIVE_LENGTH)
    requested_category: SynthesisArtifactCategory | None = None
    context_packet_id: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_ID_LENGTH
    )
    context_packet: SynthesisContextPacket | None = None
    evidence_references: list[GroundingEvidenceReference] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES
    )
    constraints: SynthesisConstraints = Field(default_factory=SynthesisConstraints)
    scope: MemoryScope | None = None
    requesting_source: MemorySource | None = None
    correlation_id: str | None = Field(default=None, max_length=MAX_SYNTHESIS_ID_LENGTH)
    submitted_at: datetime | None = None
    status: SynthesisReadinessStatus = SynthesisReadinessStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("request_id")
    @classmethod
    def _request_id_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "request_id")

    @field_validator("objective")
    @classmethod
    def _objective_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "objective")

    @field_validator("context_packet_id", "correlation_id")
    @classmethod
    def _optional_identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "identifier")

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    @model_validator(mode="after")
    def _validate_request(self) -> "GroundedSynthesisRequest":
        evidence_ids = [item.evidence_id for item in self.evidence_references]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence_references contain duplicate evidence_id values")
        if len(self.evidence_references) > self.constraints.max_evidence_references:
            raise ValueError(
                f"evidence reference count {len(self.evidence_references)} exceeds "
                f"the declared limit {self.constraints.max_evidence_references}"
            )

        if self.requested_category is not None and not self.constraints.permits_category(
            self.requested_category
        ):
            raise ValueError(
                f"requested_category {self.requested_category.value!r} is not in "
                "the declared allowed_artifact_categories"
            )

        if self.context_packet is not None:
            if self.context_packet.request_id != self.request_id:
                raise ValueError(
                    "embedded context_packet.request_id must match request_id"
                )
            if self.context_packet.mode is not self.mode:
                raise ValueError("embedded context_packet.mode must match request mode")
            if (
                self.context_packet_id is not None
                and self.context_packet_id != self.context_packet.packet_id
            ):
                raise ValueError(
                    "context_packet_id disagrees with the embedded "
                    "context_packet.packet_id"
                )

        # A request that has neither grounding reference nor grounding evidence
        # is not "ready" for anything; it must say so rather than imply it.
        has_grounding = bool(
            self.context_packet_id or self.context_packet or self.evidence_references
        )
        if not has_grounding and self.status not in (
            SynthesisReadinessStatus.DRAFT,
            SynthesisReadinessStatus.CONTEXT_REQUIRED,
            SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE,
            SynthesisReadinessStatus.BLOCKED,
        ):
            raise ValueError(
                f"status {self.status.value!r} requires a grounding reference, an "
                "embedded context packet, or evidence references"
            )
        return self


# =========================================================================== #
# Provenance
# =========================================================================== #
class SynthesisProvenance(_GroundedSynthesisModel):
    """How a proposed artifact is grounded — mandatory, never optional.

    Phase 40A §6 makes "evidence before synthesis" a mandatory principle, so
    :class:`GroundedSynthesisArtifact` carries this as a **required** field
    rather than an optional annotation: an artifact cannot exist without a
    record of what grounded it.

    It records exclusions as well as inclusions. Evidence that was considered
    and rejected is part of the audit trail (Phase 40A §17); dropping it would
    make a narrow result indistinguishable from a thorough one.
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    request_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    context_packet_id: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_ID_LENGTH
    )
    used_evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES
    )
    excluded_evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_EVIDENCE_REFERENCES
    )
    source_coverage: list[SynthesisSourceCoverage] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_COLLECTION_ITEMS
    )
    unresolved_conflict_ids: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_CONFLICTS
    )
    validation_warnings: list[SynthesisWarning] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_WARNINGS
    )
    generation_method: SynthesisGenerationMethod = (
        SynthesisGenerationMethod.DETERMINISTIC
    )
    transformation_version: str = Field(
        min_length=1, max_length=MAX_SYNTHESIS_LABEL_LENGTH
    )
    producer: MemorySource | None = None
    parent_artifact_id: str | None = Field(
        default=None, max_length=MAX_SYNTHESIS_ID_LENGTH
    )

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("request_id", "transformation_version")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "provenance field")

    @field_validator("context_packet_id", "parent_artifact_id")
    @classmethod
    def _optional_identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "provenance identifier")

    @field_validator("used_evidence_ids")
    @classmethod
    def _used_ids_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "used_evidence_ids")

    @field_validator("excluded_evidence_ids")
    @classmethod
    def _excluded_ids_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "excluded_evidence_ids")

    @field_validator("unresolved_conflict_ids")
    @classmethod
    def _conflict_ids_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "unresolved_conflict_ids")

    @model_validator(mode="after")
    def _validate_provenance(self) -> "SynthesisProvenance":
        overlap = set(self.used_evidence_ids) & set(self.excluded_evidence_ids)
        if overlap:
            # The same evidence cannot be both the basis of a claim and
            # deliberately excluded from it; that would make the audit trail
            # unreadable.
            raise ValueError(
                "evidence ids appear in both used and excluded sets: "
                f"{sorted(overlap)!r}"
            )
        if self.parent_artifact_id is not None and not self.parent_artifact_id:
            raise ValueError("parent_artifact_id must not be blank")
        return self


# =========================================================================== #
# Proposed artifact
# =========================================================================== #
# The statuses a produced artifact may legitimately hold. Anything describing an
# in-flight request (``draft`` / ``context_required`` / ``ready``) is not an
# artifact state, and no acceptance state exists in the vocabulary at all.
PROPOSED_ARTIFACT_STATUSES: frozenset[SynthesisReadinessStatus] = frozenset(
    {
        SynthesisReadinessStatus.PROPOSED,
        SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE,
        SynthesisReadinessStatus.BLOCKED,
        SynthesisReadinessStatus.VALIDATION_FAILED,
        SynthesisReadinessStatus.HUMAN_REVIEW_REQUIRED,
    }
)


class GroundedSynthesisArtifactSection(_GroundedSynthesisModel):
    """One bounded section of a proposed artifact's structured content."""

    section_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    heading: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SECTION_HEADING_LENGTH)
    body: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SECTION_BODY_LENGTH)
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_CITATIONS
    )

    @field_validator("section_id", "heading", "body")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "artifact section field")

    @field_validator("evidence_ids")
    @classmethod
    def _evidence_ids_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "section evidence_ids")


class GroundedSynthesisArtifact(_GroundedSynthesisModel):
    """A **proposed** synthesis output — never accepted repository or graph state.

    The distinction is structural, not conventional:

    * ``status`` is drawn from the proposal-only subset of
      :class:`SynthesisReadinessStatus`; ``draft``/``context_required``/``ready``
      describe an in-flight request, not a produced artifact, and are rejected
      here. No accepted/approved/committed value exists at all.
    * ``human_review_required`` and ``read_only`` are pinned ``True`` and reject
      being turned off (Phase 40A §7).
    * ``provenance`` is required, and a ``proposed`` artifact must cite evidence
      that its provenance actually records as used.

    The artifact writes nothing. It has no path to disk, the knowledge graph,
    Active Memory, a database, or a repository; constructing one performs no I/O
    (Phase 40A §8, §19).
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    artifact_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    request_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    mode: GroundedSynthesisMode
    category: SynthesisArtifactCategory
    status: SynthesisReadinessStatus = SynthesisReadinessStatus.PROPOSED
    sections: list[GroundedSynthesisArtifactSection] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_ARTIFACT_SECTIONS
    )
    citations: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_CITATIONS
    )
    provenance: SynthesisProvenance
    warnings: list[SynthesisWarning] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_WARNINGS
    )
    unresolved_claims: list[str] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_UNRESOLVED_CLAIMS
    )
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    human_review_required: bool = True
    read_only: bool = True

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("artifact_id", "request_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "artifact identifier")

    @field_validator("citations")
    @classmethod
    def _citations_unique(cls, value: list[str]) -> list[str]:
        return _clean_unique_ids(value, "citations")

    @field_validator("unresolved_claims")
    @classmethod
    def _claims_bounded(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for claim in value:
            text = _clean_required_text(claim, "unresolved claim")
            if len(text) > MAX_SYNTHESIS_SUMMARY_LENGTH:
                raise ValueError(
                    "unresolved claim exceeds the "
                    f"{MAX_SYNTHESIS_SUMMARY_LENGTH} character limit"
                )
            cleaned.append(text)
        return cleaned

    @field_validator("human_review_required", "read_only", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    @model_validator(mode="after")
    def _validate_artifact(self) -> "GroundedSynthesisArtifact":
        if not self.human_review_required:
            raise ValueError("human_review_required must remain True")
        if not self.read_only:
            raise ValueError("read_only must remain True")

        if self.status not in PROPOSED_ARTIFACT_STATUSES:
            raise ValueError(
                f"status {self.status.value!r} is not a proposed-artifact status; "
                "an artifact is a proposal awaiting human review"
            )

        if self.provenance.request_id != self.request_id:
            raise ValueError("provenance.request_id must match the artifact request_id")

        section_ids = [section.section_id for section in self.sections]
        if len(set(section_ids)) != len(section_ids):
            raise ValueError("sections contain duplicate section_id values")

        total_content = sum(len(section.body) for section in self.sections)
        if total_content > MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH:
            raise ValueError(
                f"artifact content length {total_content} exceeds the "
                f"{MAX_SYNTHESIS_ARTIFACT_CONTENT_LENGTH} character limit"
            )

        used = set(self.provenance.used_evidence_ids)
        unrecorded = [item for item in self.citations if item not in used]
        if unrecorded:
            # A citation the provenance does not record as used would let an
            # artifact claim grounding its audit trail cannot support.
            raise ValueError(
                "citations not recorded in provenance.used_evidence_ids: "
                f"{sorted(unrecorded)!r}"
            )
        for section in self.sections:
            unrecorded_section = [
                item for item in section.evidence_ids if item not in used
            ]
            if unrecorded_section:
                raise ValueError(
                    f"section {section.section_id!r} cites evidence not recorded in "
                    f"provenance.used_evidence_ids: {sorted(unrecorded_section)!r}"
                )

        if self.status is SynthesisReadinessStatus.PROPOSED:
            if not used:
                raise ValueError(
                    "a 'proposed' artifact requires provenance evidence; use "
                    "'insufficient_evidence' when nothing grounds it"
                )
            if not self.citations:
                raise ValueError(
                    "a 'proposed' artifact must cite the evidence supporting it"
                )
        return self


# =========================================================================== #
# Validation result
# =========================================================================== #
class SynthesisValidationIssue(_GroundedSynthesisModel):
    """One typed validation failure with a bounded, secret-free message."""

    code: SynthesisValidationIssueCode
    message: str = Field(min_length=1, max_length=MAX_SYNTHESIS_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_SYNTHESIS_ID_LENGTH)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "validation message")

    @field_validator("subject_id")
    @classmethod
    def _subject_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "validation subject_id")


class SynthesisValidationResult(_GroundedSynthesisModel):
    """An explicit, non-coercing validation verdict over one contract instance.

    The invariant that makes it trustworthy: ``status`` is ``valid`` **if and
    only if** ``issues`` is empty. There is no "valid with problems" state, so a
    consumer can never read a degraded result as a passing one, and a producer
    can never file issues under a passing verdict (Phase 40A §9 — failures are
    typed outcomes, not overloaded successes).

    ``human_review_required`` is a separate axis from validity: a structurally
    valid artifact still requires review, and marking it so is not a failure.
    """

    schema_version: str = Field(default=GROUNDED_SYNTHESIS_CONTRACT_VERSION)
    subject: SynthesisValidationSubject
    subject_id: str = Field(min_length=1, max_length=MAX_SYNTHESIS_ID_LENGTH)
    status: SynthesisValidationStatus
    issues: list[SynthesisValidationIssue] = Field(
        default_factory=list, max_length=MAX_SYNTHESIS_VALIDATION_ISSUES
    )
    human_review_required: bool = True

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("subject_id")
    @classmethod
    def _subject_id_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "subject_id")

    @field_validator("human_review_required", mode="before")
    @classmethod
    def _flag_is_boolean(cls, value: Any) -> Any:
        return _require_bool(value)

    @model_validator(mode="after")
    def _status_matches_issues(self) -> "SynthesisValidationResult":
        if self.status is SynthesisValidationStatus.VALID and self.issues:
            raise ValueError("a 'valid' result must carry no issues")
        if self.status is SynthesisValidationStatus.INVALID and not self.issues:
            raise ValueError("an 'invalid' result must carry at least one issue")
        return self
