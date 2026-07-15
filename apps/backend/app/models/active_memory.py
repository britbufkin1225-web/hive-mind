"""Phase 37B — Active Agent Memory + Verification Layer contract types.

Contract/schema-alignment only. These are the stable **wire models** for the
future Active Agent Memory + Verification Layer designed in Phase 37A
(``docs/planning/phase-37a-active-agent-memory-verification-layer-planning.md``
and the reusable ``docs/active-agent-memory-verification-layer.md``). This module
adds **NO** persistence, store, service, router, endpoint, ingestion,
contradiction detection, active-state calculation, context-packet generation, or
AI/LLM logic. It defines *shapes* only — exactly as Phase 10B defined the
intelligence contracts before any logic ran (see ``hive_models.py`` Phase 10B
section).

Conventions (kept identical to ``hive_models.py`` so the two contract layers read
the same):

* Enums are :class:`enum.StrEnum` with ``UPPER_SNAKE`` member names whose
  serialized value is the ``snake_case`` string literal. Because these are
  ``StrEnum``, the serialized API value *is* that literal — so the literals here
  are the stable wire contract that the frontend union types
  (``apps/frontend/src/types/api.ts``) mirror exactly.
* Free-form, forward-compatible data rides in ``metadata: dict[str, Any]``
  (``Field(default_factory=dict)``), matching the ``metadata.evidence`` pattern
  used across the API rather than premature typed fields.
* Client-supplied free-text fields carry defensive upper bounds
  (``MAX_MEMORY_*``), matching the Phase 18B bounded-field discipline: oversized
  input is rejected at the contract edge, every realistic value stays valid.

Design rationale for every significant decision is recorded inline and, in
prose, in ``docs/active-agent-memory-verification-layer.md`` (§ "Phase 37B —
settled contract decisions").

No runtime memory system exists after this phase. Storing a claim is not
endorsing it; nothing here verifies, supersedes, contradicts, or activates
anything — those are later phases (37C–37H) built on top of these contracts.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------- #
# Bounded free-text / collection limits.
#
# Defensive upper bounds for client-supplied fields on the future write surface,
# mirroring the Phase 18B rationale (``MAX_CONSOLE_COMMAND_LENGTH`` et al.): they
# reject pathologically large input at the contract boundary without constraining
# any realistic value, and they support the Phase 37A §13 "bounded payloads"
# security principle (contradiction-flooding / DoS resistance). Identifiers stay
# generous but finite; claim values are bounded scalars (see ``MemoryClaim``),
# never unbounded prose blobs. Collections are capped so a context packet or an
# evidence set can never balloon into an unbounded dump.
# --------------------------------------------------------------------------- #
MAX_MEMORY_ID_LENGTH = 256
MAX_MEMORY_SUBJECT_LENGTH = 512
MAX_MEMORY_PREDICATE_LENGTH = 256
MAX_MEMORY_VALUE_LENGTH = 2048
MAX_MEMORY_SUMMARY_LENGTH = 2048
MAX_MEMORY_LABEL_LENGTH = 512
MAX_MEMORY_REFERENCE_LENGTH = 2048
MAX_MEMORY_COLLECTION_ITEMS = 1024


# --------------------------------------------------------------------------- #
# Contract version.
#
# A stable *wire* version for the whole active-memory contract family, decoupled
# from the application/package version so the type contract can evolve on its own
# cadence (Phase 37A §16.1(13) parity requirement). It is a fixed literal, not
# derived from a package version, so a client can pin against it deterministically.
# --------------------------------------------------------------------------- #
ACTIVE_MEMORY_CONTRACT_VERSION = "active-memory.v1"


# =========================================================================== #
# Enumerations (closed wire vocabularies)
# =========================================================================== #
class MemoryRecordKind(StrEnum):
    """Closed set of memory-record categories (Phase 37A §4).

    A closed enum (not free text) because contradiction rules (37D) and the
    active-state calculation (37C) branch on record kind; an open string would
    let a typo silently create an uncomputable category. These six mirror the
    Phase 37A conceptual record types exactly.
    """

    PROJECT_FACT = "project_fact"
    PROJECT_DECISION = "project_decision"
    PROJECT_CONSTRAINT = "project_constraint"
    PHASE_STATUS = "phase_status"
    REPOSITORY_STATE = "repository_state"
    CAPABILITY = "capability"


class VerificationState(StrEnum):
    """How strongly a claim is currently believed given its evidence (Phase 37A §7).

    This is the **belief axis**, kept strictly separate from
    :class:`LifecycleState` (the "is it in force?" axis). Phase 37A §7 warned that
    overloading both into one enum makes ``superseded`` (a lifecycle fact) and
    ``contradicted`` (a truth signal) ambiguous; Phase 37B settles that by moving
    ``superseded``/``retracted``/``stale`` onto the lifecycle axis only and
    keeping this axis to belief states. ``contradicted`` stays here because it is
    a statement about *believability* (this record lost a deterministic conflict),
    while the record's *in-force* consequence is carried by lifecycle.
    """

    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    HUMAN_CONFIRMED = "human_confirmed"
    CONTRADICTED = "contradicted"
    UNRESOLVABLE = "unresolvable"


class LifecycleState(StrEnum):
    """Where a record sits in its life — the **in-force axis** (Phase 37A §9).

    Separate from :class:`VerificationState` so "believe it?" and "is it current?"
    never collapse into one overloaded value. ``superseded``/``retracted``/
    ``stale`` live here (not on the belief axis): they describe why a record left
    the active baseline while remaining stored, queryable history.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    STALE = "stale"
    ARCHIVED = "archived"


class ConfidenceBand(StrEnum):
    """Qualitative confidence band — strength of support, kept **separate** from
    verification state (Phase 37A §3, §16.1(5)).

    A closed qualitative enum rather than a float: a numeric confidence invites
    false precision and tempts silent averaging of evidence, which Phase 37A §6.3
    explicitly forbids ("discordant evidence produces a contradiction, not an
    average"). Three stable bands are inspectable, comparable across heterogeneous
    sources, and cannot be mistaken for a computed probability. Confidence is
    always optional; no confidence is *calculated* in this phase.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimValueKind(StrEnum):
    """How to interpret a claim's bounded scalar ``value`` (see :class:`MemoryClaim`).

    A claim value is stored as a bounded *string* for a stable, serializable wire
    shape; this tag tells a consumer whether that string denotes a boolean, an
    integer, a timestamp, an identifier, etc. It exists so the future
    deterministic contradiction rules (37D) can compare like-with-like (e.g.
    ``merged`` boolean vs. a status string) instead of guessing from prose. No
    coercion is performed here — the tag is contract metadata only.
    """

    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    TIMESTAMP = "timestamp"
    IDENTIFIER = "identifier"
    ENUM = "enum"


class MemoryScopeType(StrEnum):
    """Closed scope axis a record/evidence applies to (Phase 37A §10.1, §16.1(11)).

    Named ``MemoryScopeType`` (not bare ``ScopeType``) to stay unambiguous
    alongside the existing ``SourceType``/``RegistrySourceType`` families in
    ``hive_models.py``. Scope is a closed enum + a bounded id so the active-state
    calculation can be computed *per scope* (a decision active for one phase need
    not be active globally). No scope inheritance is implemented in this phase.
    """

    PROJECT = "project"
    REPOSITORY = "repository"
    BRANCH = "branch"
    PHASE = "phase"
    FEATURE = "feature"
    COMPONENT = "component"
    SESSION = "session"


class MemorySourceType(StrEnum):
    """Identity category of who/what asserted a record (Phase 37A §5, §16.1(10)).

    Named ``MemorySourceType`` to avoid colliding with the existing graph
    ``SourceType``. This types the *identity* of a source; it deliberately carries
    **no trust flag**. Phase 37A §5 makes trust a domain-aware *policy over
    evidence*, computed later — a recognized source type never implies the source
    is trusted, so no ``trusted`` field exists on :class:`MemorySource`.
    """

    HUMAN = "human"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    CHATGPT = "chatgpt"
    CLI_REPORT = "cli_report"
    REPOSITORY_OBSERVER = "repository_observer"
    CI_SYSTEM = "ci_system"
    IMPORTED_DOCUMENT = "imported_document"
    UNKNOWN = "unknown"


class EvidenceType(StrEnum):
    """Closed set of evidence categories (Phase 37A §6).

    Ordered strongest-to-weakest for the *claim-relative* hierarchy in Phase 37A
    §6.1 (enum order is documentation only; it is not the wire value). Evidence
    types are intentionally **not equal**: a screenshot proves visible UI state,
    not merge status; a conversational summary is weak as evidence. Future
    evidence-strength/authority metadata rides in ``metadata`` rather than a
    premature typed score, so no trust calculation is implied here.
    """

    HUMAN_CONFIRMATION = "human_confirmation"
    REPOSITORY_COMMAND_OUTPUT = "repository_command_output"
    COMMIT = "commit"
    BRANCH = "branch"
    PULL_REQUEST = "pull_request"
    TEST_OUTPUT = "test_output"
    CI_OUTPUT = "ci_output"
    RUNTIME_API_RESPONSE = "runtime_api_response"
    SOURCE_CODE = "source_code"
    SOURCE_CONTROLLED_DOC = "source_controlled_doc"
    STRUCTURED_CLI_REPORT = "structured_cli_report"
    STRUCTURED_AGENT_REPORT = "structured_agent_report"
    SCREENSHOT = "screenshot"
    VIDEO = "video"
    CONVERSATIONAL_SUMMARY = "conversational_summary"
    INFERRED_CONTEXT = "inferred_context"


class EvidenceReferenceKind(StrEnum):
    """Closed set of *bounded, inspectable* evidence-reference pointer kinds
    (Phase 37A §4.7, §13; prompt §6).

    Every value denotes a safe, bounded reference — a commit hash, a branch name,
    a PR number, a repository-relative path, a symbol/line reference, a captured
    command/test-run identifier, a stored record/artifact id, or an explicitly
    allowed external source id. There is deliberately **no** "raw command" or
    "arbitrary filesystem path" kind: a reference is never executable content and
    never a secret-bearing payload (Phase 37A §13). References point *at* evidence;
    they are not the evidence's contents.
    """

    COMMIT_HASH = "commit_hash"
    BRANCH_NAME = "branch_name"
    PULL_REQUEST_NUMBER = "pull_request_number"
    FILE_PATH = "file_path"
    SYMBOL_REFERENCE = "symbol_reference"
    COMMAND_ID = "command_id"
    TEST_RUN_ID = "test_run_id"
    SOURCE_RECORD_ID = "source_record_id"
    ARTIFACT_ID = "artifact_id"
    EXTERNAL_SOURCE_ID = "external_source_id"


class SupersessionKind(StrEnum):
    """Directional link kinds for supersession and retraction (Phase 37A §9,
    §16.1(6)).

    Only ``supersedes`` and ``retracts`` are ever **stored** — a record points
    *forward* from the newer/authoring record to the older/target record it
    replaces or withdraws (one canonical stored direction). ``superseded_by`` and
    ``retracted_by`` are the **derived inverses**: a later read/traversal phase
    (37C) computes them; they are reserved here so the wire vocabulary is complete
    and an inverse view can serialize, but nothing authors them directly. This
    single-stored-direction choice keeps supersession chains acyclic and lets the
    "head of chain" be derived deterministically without reconciling two
    independently-written link sets.
    """

    SUPERSEDES = "supersedes"
    SUPERSEDED_BY = "superseded_by"
    RETRACTS = "retracts"
    RETRACTED_BY = "retracted_by"


class ContradictionClass(StrEnum):
    """Deterministic contradiction taxonomy — the five Phase 37D MVP classes
    (Phase 37A §8.1).

    Closed and stable so 37D can route handling by class. These five are the only
    classes 37D will implement; later classes (Phase 37A §8.2) are intentionally
    omitted until scoped, so the contract does not advertise detection it will not
    ship.
    """

    DUPLICATE_PHASE_STATUS = "duplicate_phase_status"
    PENDING_VS_MERGED = "pending_vs_merged"
    FRONTEND_ONLY_VS_BACKEND_MODIFICATION = "frontend_only_vs_backend_modification"
    CURRENT_VS_SUPERSEDED_DECISION = "current_vs_superseded_decision"
    CLEAN_VS_DIRTY_WORKING_TREE = "clean_vs_dirty_working_tree"


class ContradictionResolutionState(StrEnum):
    """Resolution lifecycle of a contradiction (Phase 37A §4.8).

    ``open → resolved → archived``. A contradiction is **never** auto-resolved by
    the layer picking a winner (Phase 37A §1.5, §13); resolution happens by human
    decision, supersession, or retraction, and the mechanism is captured by the
    optional ``resolution_record_id``/``resolution_source`` on
    :class:`ContradictionRecord` rather than by inflating this enum.
    """

    OPEN = "open"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ContradictionSeverity(StrEnum):
    """Optional impact band for a contradiction (Phase 37A §4.8, "severity where
    justified").

    Justified because contradictions differ in how much they should block action:
    a stale ``clean_vs_dirty_working_tree`` conflict is informational, whereas a
    ``pending_vs_merged`` conflict with no merge evidence can invalidate an
    agent's entire baseline. Optional; no severity is *calculated* here.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActiveStateResult(StrEnum):
    """Result of the future per-slot active-state calculation (Phase 37A §10,
    §16.1; prompt §11).

    A dedicated enum — **not** a boolean — because uncertainty is first-class data
    (Phase 37A §10.2). ``unresolved`` (a live contradiction the layer must not
    silently pick a winner for) and ``no_eligible_record`` (nothing verified/fresh
    to select) are distinct outcomes that must never be flattened into ``false``.
    No active state is computed in this phase.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNRESOLVED = "unresolved"
    NO_ELIGIBLE_RECORD = "no_eligible_record"


# =========================================================================== #
# Value / identity building blocks
# =========================================================================== #
class MemoryScope(BaseModel):
    """A single scope coordinate: a closed type plus a bounded identifier.

    Records carry a mandatory coarse ``project_id`` plus an optional *narrower*
    ``MemoryScope`` (branch/phase/feature/…) so active-state can be computed per
    scope (Phase 37A §10.1). Contract only: ``scope_id`` is a declared value, not
    a verified location; no scope inheritance is resolved here.
    """

    scope_type: MemoryScopeType
    scope_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)

    @field_validator("scope_id")
    @classmethod
    def _scope_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("scope_id must not be empty")
        return value.strip()


class MemorySource(BaseModel):
    """Identity of who/what asserted a record or evidence item (Phase 37A §5).

    Carries the source *type* + a stable ``source_id`` + an optional display label
    and an optional session/run identifier. It deliberately carries **no trust
    signal** — trust is a later domain-aware policy over evidence, not a stored
    property of identity (Phase 37A §5, §13 "agent/observer identity spoofing":
    unidentified sources get the weakest treatment *by policy*, not by a flag
    here).
    """

    source_type: MemorySourceType
    source_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    display_label: str | None = Field(default=None, max_length=MAX_MEMORY_LABEL_LENGTH)
    session_id: str | None = Field(default=None, max_length=MAX_MEMORY_ID_LENGTH)

    @field_validator("source_id")
    @classmethod
    def _source_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("source_id must not be empty")
        return value.strip()


class MemoryClaim(BaseModel):
    """The single proposition a record asserts: a bounded subject/predicate/value
    triple plus an optional human-readable summary (Phase 37A §3, §16.1(2)).

    A claim is **structured, not prose-only**: subject + predicate + a bounded
    scalar ``value`` (tagged by :class:`ClaimValueKind`). Rationale — a free prose
    paragraph cannot be compared deterministically, so the future contradiction
    rules (37D) and dedup/identity keying (subject+predicate) would be impossible
    over prose. A bounded scalar triple is comparable, serializable, and cannot
    grow into an unbounded recursive object. ``summary`` is an optional
    human-readable gloss only; it never replaces the structured triple.
    """

    subject: str = Field(max_length=MAX_MEMORY_SUBJECT_LENGTH)
    predicate: str = Field(max_length=MAX_MEMORY_PREDICATE_LENGTH)
    value: str = Field(max_length=MAX_MEMORY_VALUE_LENGTH)
    value_kind: ClaimValueKind = ClaimValueKind.STRING
    summary: str | None = Field(default=None, max_length=MAX_MEMORY_SUMMARY_LENGTH)

    @field_validator("subject", "predicate")
    @classmethod
    def _identity_part_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("claim subject and predicate must not be empty")
        return value.strip()


class EvidenceReference(BaseModel):
    """A bounded, inspectable pointer *at* a piece of evidence — never its
    contents (Phase 37A §4.7, §13; prompt §6).

    ``value`` is the primary bounded reference (a commit hash, branch name, PR
    number as a string, repository-relative path, record/artifact id, …) and
    ``detail`` is an optional bounded qualifier (e.g. a line range ``L10-L42`` for
    a ``file_path``, or a symbol name). By construction a reference is not
    executable content and carries no secret payload; runtime redaction/validation
    of submitted evidence is deferred to the store phase (37C).
    """

    reference_kind: EvidenceReferenceKind
    value: str = Field(max_length=MAX_MEMORY_REFERENCE_LENGTH)
    detail: str | None = Field(default=None, max_length=MAX_MEMORY_REFERENCE_LENGTH)

    @field_validator("value")
    @classmethod
    def _reference_value_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("evidence reference value must not be empty")
        return value.strip()


class SupersessionReference(BaseModel):
    """A forward supersession/retraction link authored on the newer record
    (Phase 37A §9, §16.1(6)).

    Canonical stored direction only: ``kind`` is ``supersedes`` or ``retracts``
    and ``target_record_id`` is the older/withdrawn record. Authoring the
    inverse (``superseded_by``/``retracted_by``) is rejected here — those are
    *derived* by a later traversal phase, not stored — which keeps chains
    single-directional and their head deterministically computable.
    """

    kind: SupersessionKind
    target_record_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    reason: str | None = Field(default=None, max_length=MAX_MEMORY_SUMMARY_LENGTH)
    created_at: datetime

    @field_validator("target_record_id")
    @classmethod
    def _target_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("target_record_id must not be empty")
        return value.strip()

    @field_validator("kind")
    @classmethod
    def _only_canonical_direction_stored(cls, value: SupersessionKind) -> SupersessionKind:
        # Only the forward directions are ever authored/stored; the inverses are
        # derived (Phase 37A §9.2). Reserving them in the enum keeps the wire
        # vocabulary complete without allowing a second, independently-written
        # link set that could disagree with the canonical one.
        if value in (SupersessionKind.SUPERSEDED_BY, SupersessionKind.RETRACTED_BY):
            raise ValueError(
                "only 'supersedes'/'retracts' are stored; "
                "'superseded_by'/'retracted_by' are derived inverses"
            )
        return value


class VerificationMetadata(BaseModel):
    """The latest verification *event* over a record — checker, time, and the
    evidence weighed (Phase 37A §4.9; prompt §2(3)).

    Optional on a record. The record's authoritative current belief is its
    top-level ``verification_state``; this captures *how* that head state was last
    reached (which deterministic rule or which human checked it, when, and against
    which :class:`EvidenceRecord` ids) for auditability. It records a verification
    outcome; it computes none.
    """

    state: VerificationState
    checked_at: datetime | None = None
    checker: MemorySource | None = None
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    note: str | None = Field(default=None, max_length=MAX_MEMORY_SUMMARY_LENGTH)


# =========================================================================== #
# First-class records
# =========================================================================== #
class EvidenceRecord(BaseModel):
    """A first-class record *of a piece of evidence* so multiple claims can
    reference the same evidence and its freshness can be tracked centrally
    (Phase 37A §4.7).

    Carries the evidence ``type``, a bounded :class:`EvidenceReference`, optional
    scope/source, and a ``captured_at`` timestamp distinct from any record's
    creation time (Phase 37A §13 timestamps). ``valid_until`` is an optional
    freshness window (contract only — no freshness/invalidation is *computed*
    here). Future evidence-strength or authority signals ride in ``metadata``,
    keeping the contract additive without implying a trust calculation.
    """

    evidence_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    evidence_type: EvidenceType
    reference: EvidenceReference
    scope: MemoryScope | None = None
    source: MemorySource | None = None
    captured_at: datetime
    valid_until: datetime | None = None
    summary: str | None = Field(default=None, max_length=MAX_MEMORY_SUMMARY_LENGTH)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_id")
    @classmethod
    def _evidence_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("evidence_id must not be empty")
        return value.strip()


class MemoryRecord(BaseModel):
    """The atomic stored unit: one structured claim plus its standing
    (Phase 37A §3, §4).

    Identity is explicit and never derived from display text (Phase 37A §16.1(1)):
    ``record_id`` + the claim's subject/predicate + ``project_id`` + optional
    narrower ``scope`` + ``source`` + ``created_at``. Belief and in-force are two
    **separate** fields (``verification_state`` vs. ``lifecycle_state``).
    Evidence, supersession, and verification detail attach by **reference**
    (``evidence_ids``, ``supersession_refs``, ``verification``) — the record is
    conceptually immutable and its full history is not inlined. No deduplication,
    verification, or activation logic runs in this phase.

    Timestamps are distinct and never substituted for one another (Phase 37A §13):
    ``observed_at`` is the claimed observation time; ``created_at`` is when the
    record was recorded. Evidence-capture / verification / supersession times live
    on their own models.
    """

    record_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    kind: MemoryRecordKind
    claim: MemoryClaim
    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    scope: MemoryScope | None = None
    source: MemorySource
    verification_state: VerificationState = VerificationState.UNVERIFIED
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    confidence: ConfidenceBand | None = None
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    verification: VerificationMetadata | None = None
    supersession_refs: list[SupersessionReference] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    observed_at: datetime | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("record_id", "project_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("record_id and project_id must not be empty")
        return value.strip()


class ContradictionRecord(BaseModel):
    """A detected incompatibility between records under a deterministic rule
    (Phase 37A §4.8, §8).

    Supports every field the Phase 37D MVP needs: the fired ``contradiction_class``
    (one of the five MVP classes), the ``involved_record_ids`` (at least two — a
    contradiction is inherently between records), a ``summary``, the detecting
    ``detection_source`` and ``detected_at`` time, a ``resolution_state`` that is
    never auto-advanced to a winner, an optional resolution record/source,
    supporting ``evidence_ids``, and an optional ``severity``. Detection itself is
    Phase 37D; this is the shape only.
    """

    contradiction_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    contradiction_class: ContradictionClass
    involved_record_ids: list[str] = Field(max_length=MAX_MEMORY_COLLECTION_ITEMS)
    summary: str = Field(max_length=MAX_MEMORY_SUMMARY_LENGTH)
    detection_source: MemorySource
    detected_at: datetime
    resolution_state: ContradictionResolutionState = ContradictionResolutionState.OPEN
    resolution_record_id: str | None = Field(
        default=None, max_length=MAX_MEMORY_ID_LENGTH
    )
    resolution_source: MemorySource | None = None
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    severity: ContradictionSeverity | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contradiction_id")
    @classmethod
    def _contradiction_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("contradiction_id must not be empty")
        return value.strip()

    @field_validator("involved_record_ids")
    @classmethod
    def _at_least_two_records(cls, value: list[str]) -> list[str]:
        # A contradiction is, by definition, between two or more records
        # (Phase 37A §8.1). A structurally incomplete contradiction (0/1 record)
        # is rejected at the contract edge rather than stored as a degenerate one.
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) < 2:
            raise ValueError("a contradiction must involve at least two record ids")
        return cleaned


# =========================================================================== #
# Read-only context-packet response contract
# =========================================================================== #
class VerificationSummary(BaseModel):
    """Deterministic per-state counts of the records in a context packet
    (Phase 37A §11.1 "verification summary").

    Mirrors the ``IntelligenceReportSummary`` counts pattern: a compact rollup so a
    consumer can show "N verified / M unverified" without walking every record.
    Counts only; nothing is verified here.
    """

    verified_count: int = 0
    human_confirmed_count: int = 0
    partially_verified_count: int = 0
    unverified_count: int = 0
    contradicted_count: int = 0
    unresolvable_count: int = 0


class RepositoryBaseline(BaseModel):
    """The freshest, explicitly-timestamped repository baseline for a packet
    (Phase 37A §11.1 "current repository baseline").

    ``working_tree_clean`` is ``bool | None`` where **``None`` means "unknown"**,
    never ``False`` — Phase 37A §10.2 requires uncertainty to be represented as
    data, not silently collapsed to a negative. Evidence for the baseline attaches
    by reference (``evidence_ids``); nothing is observed or computed in this phase.
    """

    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    branch: str | None = Field(default=None, max_length=MAX_MEMORY_LABEL_LENGTH)
    head_commit: str | None = Field(default=None, max_length=MAX_MEMORY_ID_LENGTH)
    working_tree_clean: bool | None = None
    observed_at: datetime | None = None
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("project_id must not be empty")
        return value.strip()


class PacketWarning(BaseModel):
    """A bounded "do not rely on this" entry for the packet's warnings section
    (Phase 37A §11.1 "stale / superseded warnings").

    References the affected record by id and states its lifecycle reason — the
    packet never inlines the full superseded/stale record or its history, keeping
    the warning section bounded (Phase 37A §11.2 "references rather than inlines").
    """

    record_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    lifecycle_state: LifecycleState
    reason: str = Field(max_length=MAX_MEMORY_SUMMARY_LENGTH)


class ContextPacket(BaseModel):
    """The read-only, bounded, deterministic pre-action baseline bundle
    (Phase 37A §4.10, §11).

    Sections mirror Phase 37A §11.1 exactly. Active records are carried inline as
    bounded, kind-partitioned lists (facts / decisions / constraints /
    capabilities) so an agent or the future read-only inspector (37F) can read the
    baseline without a second fetch — but **only active records** enter these
    sections. Bulky/derivable data is carried by *reference*: evidence as bounded
    :class:`EvidenceReference` pointers, stale/superseded items as
    :class:`PacketWarning`s (id + reason, never full history), contradictions as
    their own first-class section. ``prohibited_assumptions`` makes "do not assume
    X" explicit. Every collection is length-bounded (Phase 37A §13). This is a
    *derived view* contract; **no packet is generated in this phase** — generation
    (37E) must never mutate anything.
    """

    packet_version: str = ACTIVE_MEMORY_CONTRACT_VERSION
    generated_at: datetime
    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    repository_baseline: RepositoryBaseline | None = None
    active_track: str | None = Field(default=None, max_length=MAX_MEMORY_LABEL_LENGTH)
    active_phase: str | None = Field(default=None, max_length=MAX_MEMORY_LABEL_LENGTH)
    active_facts: list[MemoryRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    active_decisions: list[MemoryRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    active_constraints: list[MemoryRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    known_capabilities: list[MemoryRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    unresolved_contradictions: list[ContradictionRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    warnings: list[PacketWarning] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    evidence_references: list[EvidenceReference] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    verification_summary: VerificationSummary = Field(default_factory=VerificationSummary)
    prohibited_assumptions: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    read_only: bool = True

    @field_validator("project_id")
    @classmethod
    def _project_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("project_id must not be empty")
        return value.strip()
