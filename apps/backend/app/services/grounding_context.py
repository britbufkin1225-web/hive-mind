"""Phase 40C — deterministic Grounding Context Assembly service.

The first backend service of the Grounded Synthesis Layer. It answers exactly
one question:

    Given an eligible grounding request and the evidence Hive|Mind already
    holds, what bounded, traceable :class:`SynthesisContextPacket` should a
    future synthesis stage receive?

It is a pure, read-only transformation over *already-produced* records from
existing Hive|Mind providers into the canonical Phase 40B
``grounded-synthesis.v1`` contracts. It generates nothing: no summary spanning
several records, no recommendation, no drafted content, no inferred answer. The
packet **is** the deliverable.

This module never: reads a clock, generates a random identifier, calls a
network or model provider, runs Git, touches the filesystem, enumerates a
directory, queries a store, persists anything, caches a packet, mutates a
repository/graph/memory record, or resolves a contradiction. Every timestamp is
caller-supplied and every identifier is content-derived through the Phase 40B
:func:`~app.models.grounded_synthesis.derive_grounded_synthesis_id` helper.

Headline design decisions, with rationale (Phase 40A §6, §8, §9, §10):

* **Assembly is separated from synthesis.** Collecting, filtering, ranking and
  packaging evidence is a deterministic, auditable transformation; producing
  prose from that evidence is not. Keeping them in different phases means the
  grounded input boundary can be reviewed, tested, and trusted *before* anything
  is ever generated from it — and a future generative stage cannot quietly
  widen its own grounding, because it does not assemble it.
* **The core is pure.** :meth:`GroundingContextAssemblyService.assemble` takes
  the request, an explicit :class:`GroundingEvidenceSources` bundle of records
  the caller has already obtained from the existing read-only providers, and an
  explicit ``assembled_at``. Provider *access* stays with the caller; provider
  *interpretation* lives here and is independently testable from fixtures. A
  service that reached into stores itself could not be proven deterministic.
* **The provider set is deliberately narrow.** Only the five evidence families
  that already carry the Phase 40B/37A grounding vocabulary — evidence type,
  bounded evidence reference, source identity, scope, confidence band,
  contradiction severity — are supported. Families that would need an *invented*
  mapping to fit are deferred rather than approximated (see
  :data:`SUPPORTED_GROUNDING_KINDS` and the module docs).
* **Nothing is summarized.** ``context_summaries`` is always empty. A summary
  spanning multiple evidence records is synthesis; emitting one here would make
  Phase 40C generative and would put an unattributed narrative inside the
  grounded input boundary.
* **Raw provider payloads are never copied.** Bounded excerpts, absolute
  repository roots, remote URLs, command output, and free-form provider metadata
  bags stay where they are. Packet metadata carries only closed-enum scalars and
  counts, so a credential or a machine-specific path has no route into a packet.
* **Failure is visible, never silent.** Unsafe repository identity, an
  unrepresentable critical conflict, and truncation of critical evidence all
  block readiness. Raw candidate overflow fails closed with a domain error
  rather than clipping evidence before its criticality is known — the same
  choice Phase 37E made in
  :class:`~app.services.active_memory_context_packet.ContextPacketTruncationUnsupportedError`.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Sequence

from app.models.active_memory import (
    ConfidenceBand,
    ContradictionRecord,
    ContradictionResolutionState,
    ContradictionSeverity,
    EvidenceRecord,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceType,
    LifecycleState,
    MemoryRecord,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models.grounded_synthesis import (
    MAX_SYNTHESIS_CONFLICTS,
    MAX_SYNTHESIS_DIGEST_LENGTH,
    MAX_SYNTHESIS_EVIDENCE_REFERENCES,
    MAX_SYNTHESIS_LABEL_LENGTH,
    MAX_SYNTHESIS_MISSING_CONTEXT_ITEMS,
    MAX_SYNTHESIS_SUMMARY_LENGTH,
    MAX_SYNTHESIS_WARNINGS,
    GroundedSynthesisMode,
    GroundedSynthesisRequest,
    GroundingEvidenceKind,
    GroundingEvidenceReference,
    SynthesisContextPacket,
    SynthesisEvidenceConflict,
    SynthesisMissingContext,
    SynthesisReadinessStatus,
    SynthesisSourceCoverage,
    SynthesisWarning,
    SynthesisWarningCode,
    derive_grounded_synthesis_id,
)
from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    RepositoryDriftAnalysis,
    RepositoryEvidence,
    RepositoryIdentityStatus,
    RepositorySnapshot,
    TruncationState,
)

# --------------------------------------------------------------------------- #
# Assembly version.
#
# A stable identifier for the *transformation*, deliberately separate from
# ``GROUNDED_SYNTHESIS_CONTRACT_VERSION`` (the wire shape). The contract can stay
# ``grounded-synthesis.v1`` while the assembly policy — ranking, eligibility,
# bounds — evolves; folding this into the packet identifier means a packet
# produced under different assembly rules can never collide with one produced
# under these rules, even from byte-identical evidence.
# --------------------------------------------------------------------------- #
GROUNDING_CONTEXT_ASSEMBLY_VERSION = "grounding-context-assembly.v1"


# --------------------------------------------------------------------------- #
# Supported evidence families.
#
# Chosen because each already carries the Phase 37A / 40B grounding vocabulary
# and therefore normalizes without inventing anything:
#
# * ``active_memory_evidence_record`` — an ``EvidenceRecord`` already *is* a
#   typed evidence reference (``EvidenceType`` + ``EvidenceReference`` + scope +
#   source + capture time). It is the closest existing analogue of the Phase 40B
#   grounding reference, so it normalizes one-to-one.
# * ``repository_observation`` / ``repository_drift_finding`` — Repository
#   Observer ``RepositoryEvidence`` items are bounded, deterministic, digest-
#   bearing observations with a declared ``EvidenceAuthority``, which supplies a
#   real authority axis rather than a guessed one.
# * ``contradiction_record`` — the only family that can make a packet *unsafe*
#   to synthesize from. Excluding it would let a packet look cleaner than the
#   evidence actually is, which Phase 40A §9 forbids.
# * ``active_memory_record`` — the project's own claims. Weakest as grounding
#   (a claim is not proof of itself) but indispensable as context, so it is
#   included and ranked last among provider families.
#
# Deliberately deferred, with reasons, rather than approximated:
#
# * ``context_packet_entry`` — the Phase 37E ``ContextPacket`` is an aggregate of
#   the memory and contradiction records already covered above. Admitting it
#   would enter the same underlying records twice under a second identity, which
#   deduplication cannot collapse (different canonical source identity) and which
#   would inflate coverage counts.
# * ``knowledge_graph_node`` / ``source_registry_entry`` / ``query_trail`` —
#   ``HiveGraphNode``, ``SourceRecord`` and ``QueryTrailEntry`` carry no evidence
#   type, no bounded evidence reference, no scope, no confidence band, and no
#   verification standing. Normalizing them would require inventing every one of
#   those mappings, which is precisely the fabricated-grounding failure the
#   Grounded Synthesis Layer exists to prevent. They remain available to a later
#   phase that first gives them evidence semantics.
#
# Dreaming suggestions, decay statuses and provenance chains are likewise
# deferred: they are *derived advisory views* over graph records rather than
# observations, and ``GroundingEvidenceKind`` has no member for them — adding one
# would be a Phase 40B contract expansion, not a Phase 40C assembly concern.
# --------------------------------------------------------------------------- #
SUPPORTED_GROUNDING_KINDS: frozenset[GroundingEvidenceKind] = frozenset(
    {
        GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
        GroundingEvidenceKind.REPOSITORY_OBSERVATION,
        GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING,
        GroundingEvidenceKind.CONTRADICTION_RECORD,
        GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
    }
)

# Request statuses from which grounding may legitimately be assembled. The
# remaining members describe a *produced artifact* (``proposed``,
# ``validation_failed``, ``human_review_required``), not an in-flight request;
# assembling grounding for one would mean re-grounding something already
# produced.
ASSEMBLABLE_REQUEST_STATUSES: frozenset[SynthesisReadinessStatus] = frozenset(
    {
        SynthesisReadinessStatus.DRAFT,
        SynthesisReadinessStatus.CONTEXT_REQUIRED,
        SynthesisReadinessStatus.READY,
        SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE,
        SynthesisReadinessStatus.BLOCKED,
    }
)

# Repository identity statuses that make an observation untrustworthy to ground
# on. Identical to the Phase 39A fatal set: projecting or grounding under an
# unverified scope fabricates authority.
_UNSAFE_IDENTITY_STATUSES: frozenset[RepositoryIdentityStatus] = frozenset(
    {
        RepositoryIdentityStatus.UNSAFE_LOCATION,
        RepositoryIdentityStatus.MISMATCHED_ROOT,
        RepositoryIdentityStatus.MISMATCHED_REMOTE,
    }
)

# Only ``active`` memory records ground synthesis. Superseded/stale/retracted
# records are explicitly *not* the current baseline, and Phase 39A projects every
# repository-derived candidate as ``inactive`` — grounding on those would treat
# an unactivated projection as accepted project truth.
_GROUNDABLE_LIFECYCLE_STATES: frozenset[LifecycleState] = frozenset(
    {LifecycleState.ACTIVE}
)

# ``unresolvable`` means no evidence can settle the claim, so it can ground
# nothing. ``contradicted`` is deliberately *kept*: dropping it would remove one
# side of a conflict the packet is required to surface.
_UNGROUNDABLE_VERIFICATION_STATES: frozenset[VerificationState] = frozenset(
    {VerificationState.UNRESOLVABLE}
)

# Observer authorities that assert the absence of evidence rather than evidence.
_UNGROUNDABLE_OBSERVER_AUTHORITIES: frozenset[EvidenceAuthority] = frozenset(
    {
        EvidenceAuthority.UNSUPPORTED_ASSUMPTION,
        EvidenceAuthority.UNAVAILABLE_INFORMATION,
    }
)


class GroundingExclusionReason(StrEnum):
    """Closed, bounded vocabulary for *why* a candidate did not enter the packet.

    A closed vocabulary rather than free prose so diagnostics can be counted,
    compared across runs, and rendered by a future reviewer surface — and so an
    exclusion message can never carry a path, a remote URL, or provider text.
    """

    UNSUPPORTED_EVIDENCE_KIND = "unsupported_evidence_kind"
    OUT_OF_SCOPE = "out_of_scope"
    MISSING_GROUNDING_FIELDS = "missing_grounding_fields"
    NOT_ACTIVE_LIFECYCLE = "not_active_lifecycle"
    UNRESOLVABLE_VERIFICATION = "unresolvable_verification"
    UNSAFE_REPOSITORY_IDENTITY = "unsafe_repository_identity"
    UNGROUNDED_AUTHORITY = "ungrounded_authority"
    OMITTED_CONTENT = "omitted_content"
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    BOUNDS_EXCEEDED = "bounds_exceeded"


# --------------------------------------------------------------------------- #
# Domain errors
# --------------------------------------------------------------------------- #
class GroundingContextAssemblyError(Exception):
    """Base class for fatal assembly failures."""


class GroundingRequestNotAssemblableError(GroundingContextAssemblyError):
    """Raised when the request itself cannot legitimately be grounded.

    Service-level, cross-record validation that Pydantic cannot express: a
    request already carrying assembled grounding, or one in an artifact status,
    is not a request awaiting context assembly.
    """


class GroundingCandidateOverflowError(GroundingContextAssemblyError):
    """Raised when raw candidate volume exceeds the configured guard.

    Fails closed rather than clipping. Discarding raw candidates *before*
    eligibility and criticality are known could silently remove a critical
    conflict, so the caller is told to narrow the request instead.
    """


class GroundingEvidenceIdentityError(GroundingContextAssemblyError):
    """Raised when two distinct candidates derive the same evidence identifier.

    Practically unreachable (SHA-256 over distinct canonical material), but a
    collision would silently drop evidence inside the contract's uniqueness rule,
    so it is surfaced rather than absorbed.
    """


class GroundingPacketIdentityError(GroundingContextAssemblyError):
    """Raised when the request names a packet id the assembly does not produce.

    ``context_packet_id`` is the caller's declaration of which grounding the
    request is based on. Returning a differently-identified packet under that
    declaration would misrepresent what the request was grounded on.
    """


# --------------------------------------------------------------------------- #
# Bounds
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GroundingAssemblyLimits:
    """Assembly-specific bounds layered *under* the Phase 40B contract ceilings.

    Every default is at or below its Phase 40B counterpart, so a packet built
    with the defaults can never be rejected for exceeding a contract bound; these
    exist to bound *assembly work* and packet composition, not to re-declare the
    contract.

    ``max_raw_candidates`` guards total collection volume. ``max_items_per_kind``
    stops one evidence family consuming the whole packet: a packet dominated by
    128 repository observations is not grounded context, it is a repository dump,
    and it would push every contradiction and every project claim out of the
    packet on count alone. The cap is lifted when only one family produced
    eligible evidence, because there is then nothing for it to crowd out — that
    is the scoping case, expressed through the evidence actually available rather
    than through a request field the Phase 40B contract does not define.
    """

    max_raw_candidates: int = 1024
    max_evidence_items: int = MAX_SYNTHESIS_EVIDENCE_REFERENCES
    max_items_per_kind: int = 48
    max_conflicts: int = MAX_SYNTHESIS_CONFLICTS
    max_missing_context: int = MAX_SYNTHESIS_MISSING_CONTEXT_ITEMS
    max_warnings: int = MAX_SYNTHESIS_WARNINGS
    max_label_length: int = MAX_SYNTHESIS_LABEL_LENGTH
    max_summary_length: int = MAX_SYNTHESIS_SUMMARY_LENGTH

    def __post_init__(self) -> None:
        for name, ceiling in (
            ("max_evidence_items", MAX_SYNTHESIS_EVIDENCE_REFERENCES),
            ("max_conflicts", MAX_SYNTHESIS_CONFLICTS),
            ("max_missing_context", MAX_SYNTHESIS_MISSING_CONTEXT_ITEMS),
            ("max_warnings", MAX_SYNTHESIS_WARNINGS),
            ("max_label_length", MAX_SYNTHESIS_LABEL_LENGTH),
            ("max_summary_length", MAX_SYNTHESIS_SUMMARY_LENGTH),
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
            if value > ceiling:
                raise ValueError(
                    f"{name}={value} exceeds the Phase 40B contract ceiling {ceiling}"
                )
        for name in ("max_raw_candidates", "max_items_per_kind"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


# --------------------------------------------------------------------------- #
# Evidence sources
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GroundingEvidenceSources:
    """Already-obtained records from the existing read-only providers.

    A plain frozen container, deliberately **not** a new Pydantic contract: it is
    an in-process service input, not a wire shape, and adding a second
    packet-adjacent model would start a vocabulary that could drift from
    ``grounded-synthesis.v1``. Sequences are copied into tuples so a caller
    mutating its own list after the call cannot alter a later assembly.
    """

    memory_records: Sequence[MemoryRecord] = ()
    evidence_records: Sequence[EvidenceRecord] = ()
    contradictions: Sequence[ContradictionRecord] = ()
    repository_snapshots: Sequence[RepositorySnapshot] = ()
    repository_drift_analyses: Sequence[RepositoryDriftAnalysis] = ()

    def __post_init__(self) -> None:
        for name in (
            "memory_records",
            "evidence_records",
            "contradictions",
            "repository_snapshots",
            "repository_drift_analyses",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def total_records(self) -> int:
        return (
            len(self.memory_records)
            + len(self.evidence_records)
            + len(self.contradictions)
            + len(self.repository_snapshots)
            + len(self.repository_drift_analyses)
        )


# --------------------------------------------------------------------------- #
# Authority ranking.
#
# ``authority_rank`` is ``family_base + within_family_offset``; lower is
# stronger. Every input is a *declared field on a real record* — never a computed
# score, never a heuristic, never a clock- or environment-derived value.
#
# Family bases (spaced by 20 so a family's own offsets can never cross into the
# next family's band):
#
# * evidence records first, because ``EvidenceType`` **is** the repository's
#   canonical claim-relative strength hierarchy (Phase 37A §6.1) and reusing it
#   avoids inventing a second, competing one;
# * repository observations next — direct, re-verifiable, digest-bearing;
# * drift findings after observations, because drift is derived *from* an
#   observation against a baseline;
# * contradiction records next: structural signals *about* other evidence rather
#   than observations of the world (criticality is handled ahead of authority in
#   the sort key, so a critical conflict still leads the packet);
# * memory records last among providers: a claim is context, not proof of itself;
# * caller-supplied request references last overall, so that when a provider also
#   holds the record the verified provider normalization always wins the
#   duplicate contest.
# --------------------------------------------------------------------------- #
_FAMILY_BASE: dict[GroundingEvidenceKind, int] = {
    GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD: 0,
    GroundingEvidenceKind.REPOSITORY_OBSERVATION: 20,
    GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING: 40,
    GroundingEvidenceKind.CONTRADICTION_RECORD: 60,
    GroundingEvidenceKind.ACTIVE_MEMORY_RECORD: 80,
}

_REQUESTED_REFERENCE_BASE = 160

# ``EvidenceType`` is declared strongest-to-weakest; enum iteration preserves
# declaration order, so the index is the documented hierarchy position.
_EVIDENCE_TYPE_OFFSET: dict[EvidenceType, int] = {
    member: index for index, member in enumerate(EvidenceType)
}
_UNTYPED_EVIDENCE_OFFSET = len(_EVIDENCE_TYPE_OFFSET)

_OBSERVER_AUTHORITY_OFFSET: dict[EvidenceAuthority, int] = {
    EvidenceAuthority.DIRECT_GIT_OUTPUT: 0,
    EvidenceAuthority.DIRECT_FILESYSTEM_METADATA: 2,
    EvidenceAuthority.PARSED_REPOSITORY_DOCUMENT: 4,
    EvidenceAuthority.VALIDATED_EXECUTION_SOURCE: 6,
    EvidenceAuthority.USER_SUPPLIED_STATEMENT: 10,
    EvidenceAuthority.AGENT_GENERATED_SUMMARY: 12,
}

_VERIFICATION_OFFSET: dict[VerificationState, int] = {
    VerificationState.HUMAN_CONFIRMED: 0,
    VerificationState.VERIFIED: 2,
    VerificationState.PARTIALLY_VERIFIED: 6,
    VerificationState.UNVERIFIED: 10,
    VerificationState.CONTRADICTED: 14,
}

_SEVERITY_OFFSET: dict[ContradictionSeverity | None, int] = {
    ContradictionSeverity.CRITICAL: 0,
    ContradictionSeverity.WARNING: 4,
    ContradictionSeverity.INFO: 8,
    None: 8,
}

_CONFIDENCE_RANK: dict[ConfidenceBand | None, int] = {
    ConfidenceBand.HIGH: 0,
    ConfidenceBand.MEDIUM: 1,
    ConfidenceBand.LOW: 2,
    None: 3,
}

# Final canonical tie-break between families, before the lexical identifier.
_KIND_ORDER: tuple[GroundingEvidenceKind, ...] = (
    GroundingEvidenceKind.CONTRADICTION_RECORD,
    GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
    GroundingEvidenceKind.REPOSITORY_OBSERVATION,
    GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING,
    GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
)
_KIND_RANK: dict[GroundingEvidenceKind, int] = {
    kind: index for index, kind in enumerate(_KIND_ORDER)
}

# Documented, explicit mapping from a Repository Observer evidence *category* to
# the Active Memory evidence hierarchy. Categories with no honest counterpart map
# to ``None`` rather than to a plausible-looking neighbour: an unknown evidence
# type is better than a wrong one.
_OBSERVER_CATEGORY_EVIDENCE_TYPE: dict[EvidenceCategory, EvidenceType | None] = {
    EvidenceCategory.GIT_METADATA: EvidenceType.REPOSITORY_COMMAND_OUTPUT,
    EvidenceCategory.WORKING_TREE_METADATA: EvidenceType.REPOSITORY_COMMAND_OUTPUT,
    EvidenceCategory.REPOSITORY_CONFIGURATION: EvidenceType.REPOSITORY_COMMAND_OUTPUT,
    EvidenceCategory.FILE_METADATA: EvidenceType.SOURCE_CODE,
    EvidenceCategory.BOUNDED_TEXT_EXCERPT: EvidenceType.SOURCE_CONTROLLED_DOC,
    EvidenceCategory.VALIDATION_RESULT: EvidenceType.STRUCTURED_CLI_REPORT,
    EvidenceCategory.EXCLUSION_RECORD: None,
    EvidenceCategory.EXTERNALLY_SUPPLIED_CLAIM: None,
    EvidenceCategory.UNSUPPORTED_DATA: None,
}

_EPOCH = datetime(1, 1, 1)
_HEX_DIGITS = frozenset("0123456789abcdef")


# --------------------------------------------------------------------------- #
# Small deterministic helpers
# --------------------------------------------------------------------------- #
def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def _instant(value: datetime) -> int:
    """Exact integer microseconds, comparable across naive and aware inputs.

    Aware datetimes normalize through UTC; naive datetimes are used as-is and are
    never reinterpreted through the host-local timezone (the Phase 39A rule).
    Integer arithmetic avoids float rounding, so ordering is exact.
    """

    naive = (
        value.astimezone(timezone.utc).replace(tzinfo=None) if _is_aware(value) else value
    )
    delta = naive - _EPOCH
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _freshness_key(value: datetime | None) -> tuple[int, int]:
    """Newest first; undated evidence sorts after every dated item."""

    if value is None:
        return (1, 0)
    return (0, -_instant(value))


def _canonical_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _normalize_identity(value: str) -> str:
    """NFC-normalize and strip an identifier used as a canonical identity key.

    Without this, two Unicode-equivalent spellings of the same record id would
    form two duplicate-free candidates and two different derived evidence ids.
    """

    return unicodedata.normalize("NFC", value).strip()


def _bounded_text(value: str | None, limit: int) -> tuple[str | None, bool]:
    """Strip, drop blanks, and deterministically truncate over-long text.

    Returns ``(text, truncated)``. Truncation keeps the leading characters and
    marks the cut with a single ellipsis so the result is stable and visibly
    incomplete rather than silently shortened.
    """

    if value is None:
        return None, False
    text = value.strip()
    if not text:
        return None, False
    if len(text) <= limit:
        return text, False
    return text[: limit - 1] + "…", True


def _bounded_digest(value: str | None) -> str | None:
    """Accept a digest only if it satisfies the Phase 40B lowercase-hex rule."""

    if value is None:
        return None
    text = value.strip().lower()
    if not text or len(text) > MAX_SYNTHESIS_DIGEST_LENGTH:
        return None
    if not all(char in _HEX_DIGITS for char in text):
        return None
    return text


def _scope_key(scope: MemoryScope | None) -> tuple[str, str] | None:
    if scope is None:
        return None
    return (scope.scope_type.value, scope.scope_id)


def _reference_material(reference: EvidenceReference) -> list[str | None]:
    return [reference.reference_kind.value, reference.value, reference.detail]


def _source_material(source: MemorySource | None) -> list[str | None] | None:
    if source is None:
        return None
    return [
        source.source_type.value,
        source.source_id,
        source.display_label,
        source.session_id,
    ]


# --------------------------------------------------------------------------- #
# Internal candidate
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Candidate:
    """One normalized, not-yet-filtered grounding candidate."""

    kind: GroundingEvidenceKind
    source_record_id: str
    reference: EvidenceReference
    evidence_type: EvidenceType | None
    source: MemorySource | None
    scope: MemoryScope | None
    observed_at: datetime | None
    confidence: ConfidenceBand | None
    label: str | None
    summary: str | None
    content_digest: str | None
    metadata: tuple[tuple[str, str], ...]
    authority_rank: int
    requested: bool
    # The provider's own record id, used only to map contradiction membership
    # back to included evidence. ``None`` when the family has no such linkage.
    origin_record_id: str | None = None
    text_truncated: bool = False

    def identity_key(self) -> tuple[str, str]:
        return (self.kind.value, self.source_record_id)

    def dedup_precedence(self, critical: bool) -> tuple[int, int, int, tuple[int, int], str]:
        """Documented duplicate-winner precedence.

        Criticality first (a conflicted record must not lose to a quieter copy of
        itself), then declared provider authority, then confidence band, then
        freshness, then the canonical hash material as a stable lexical
        tie-break.
        """

        return (
            0 if critical else 1,
            self.authority_rank,
            _CONFIDENCE_RANK[self.confidence],
            _freshness_key(self.observed_at),
            self.hash_material(),
        )

    def hash_material(self) -> str:
        """Canonical JSON of everything that materially defines this candidate."""

        payload: dict[str, Any] = {
            "kind": self.kind.value,
            "source_record_id": self.source_record_id,
            "reference": _reference_material(self.reference),
            "evidence_type": None if self.evidence_type is None else self.evidence_type.value,
            "source": _source_material(self.source),
            "scope": list(_scope_key(self.scope)) if self.scope is not None else None,
            "observed_at": _canonical_datetime(self.observed_at),
            "confidence": None if self.confidence is None else self.confidence.value,
            "label": self.label,
            "summary": self.summary,
            "content_digest": self.content_digest,
            "metadata": [list(pair) for pair in self.metadata],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def evidence_id(self) -> str:
        return derive_grounded_synthesis_id("gs-ev", self.hash_material())

    def to_reference(self, evidence_id: str) -> GroundingEvidenceReference:
        return GroundingEvidenceReference(
            evidence_id=evidence_id,
            grounding_kind=self.kind,
            reference=self.reference,
            evidence_type=self.evidence_type,
            source=self.source,
            source_record_id=self.source_record_id,
            scope=self.scope,
            observed_at=self.observed_at,
            confidence=self.confidence,
            label=self.label,
            summary=self.summary,
            content_digest=self.content_digest,
            metadata=dict(self.metadata),
        )


@dataclass
class _Diagnostics:
    """Bounded, secret-free counters accumulated during one assembly."""

    inspected: int = 0
    accepted: int = 0
    duplicates_removed: int = 0
    truncated_items: int = 0
    text_truncations: int = 0
    exclusions: dict[GroundingExclusionReason, int] = field(default_factory=dict)
    unsupported_kinds: set[str] = field(default_factory=set)

    def exclude(self, reason: GroundingExclusionReason, count: int = 1) -> None:
        self.exclusions[reason] = self.exclusions.get(reason, 0) + count

    @property
    def excluded(self) -> int:
        return sum(self.exclusions.values())


# --------------------------------------------------------------------------- #
# The service
# --------------------------------------------------------------------------- #
class GroundingContextAssemblyService:
    """Assemble existing evidence into a bounded ``SynthesisContextPacket``.

    Stateless between calls: the limits are the only configuration, nothing is
    retained, nothing is cached, and every returned model is freshly constructed,
    so a caller mutating one result cannot influence the next assembly. The
    service is therefore safe to share, and — because it holds no packet history
    — it adds no persistence surface.
    """

    def __init__(self, *, limits: GroundingAssemblyLimits | None = None) -> None:
        self._limits = limits or GroundingAssemblyLimits()

    @property
    def limits(self) -> GroundingAssemblyLimits:
        return self._limits

    # ----------------------------------------------------------------- #
    # Public entry point
    # ----------------------------------------------------------------- #
    def assemble(
        self,
        request: GroundedSynthesisRequest,
        *,
        evidence: GroundingEvidenceSources,
        assembled_at: datetime | None = None,
    ) -> SynthesisContextPacket:
        """Build the packet for ``request`` from ``evidence``.

        ``assembled_at`` is caller-supplied and optional; the service never reads
        a clock. It is folded into the packet identifier because two assemblies
        of identical evidence at different declared times are two different
        packets and must not share an id.
        """

        self._validate_request(request)

        limits = self._limits
        diagnostics = _Diagnostics()
        blocking_reasons: list[str] = []
        warnings: list[SynthesisWarning] = []

        candidates = self._collect(request, evidence, diagnostics, warnings, blocking_reasons)
        diagnostics.inspected = len(candidates)
        if diagnostics.inspected > limits.max_raw_candidates:
            raise GroundingCandidateOverflowError(
                f"collected {diagnostics.inspected} raw candidates, exceeding the "
                f"max_raw_candidates guard of {limits.max_raw_candidates}; narrow the "
                "request scope or the supplied evidence rather than dropping "
                "candidates before their criticality is known"
            )

        eligible = self._filter(request, candidates, diagnostics)
        critical_ids = self._critical_source_ids(evidence)
        deduplicated = self._deduplicate(eligible, critical_ids, diagnostics)
        ranked = self._rank(deduplicated, critical_ids)
        selected, dropped = self._apply_bounds(request, ranked, diagnostics, warnings)

        included, by_evidence_id = self._build_references(selected)
        diagnostics.accepted = len(included)

        conflicts, conflict_warnings, conflict_blockers = self._build_conflicts(
            evidence, by_evidence_id
        )
        warnings.extend(conflict_warnings)
        blocking_reasons.extend(conflict_blockers)

        dropped_critical = [
            candidate
            for candidate in dropped
            if self._is_critical(candidate, critical_ids)
        ]
        if dropped_critical:
            blocking_reasons.append("critical_evidence_truncated")
            warnings.append(
                SynthesisWarning(
                    code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                    message=(
                        f"{len(dropped_critical)} evidence item(s) participating in a "
                        "critical contradiction were removed by packet bounds"
                    ),
                )
            )

        missing_context = self._build_missing_context(request, selected, dropped, limits)
        if diagnostics.text_truncations:
            warnings.append(
                SynthesisWarning(
                    code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                    message=(
                        f"{diagnostics.text_truncations} evidence label(s) or "
                        "summary/summaries were truncated to the contract text bounds"
                    ),
                )
            )
        if diagnostics.unsupported_kinds:
            warnings.append(
                SynthesisWarning(
                    code=SynthesisWarningCode.COVERAGE_GAP,
                    message=(
                        "unsupported grounding evidence kind(s) excluded: "
                        + ", ".join(sorted(diagnostics.unsupported_kinds))
                    ),
                )
            )

        coverage = self._build_coverage(candidates, included)
        readiness, readiness_reason = self._evaluate_readiness(
            included=included,
            conflicts=conflicts,
            missing_context=missing_context,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        )

        ordered_warnings = self._bound_warnings(warnings, limits)
        metadata = self._build_metadata(
            request=request,
            diagnostics=diagnostics,
            conflicts=conflicts,
            readiness_reason=readiness_reason,
        )

        packet_id = self._derive_packet_id(
            request=request,
            readiness=readiness,
            included=included,
            conflicts=conflicts,
            missing_context=missing_context,
            coverage=coverage,
            warnings=ordered_warnings,
            assembled_at=assembled_at,
        )
        if (
            request.context_packet_id is not None
            and request.context_packet_id != packet_id
        ):
            raise GroundingPacketIdentityError(
                f"request context_packet_id {request.context_packet_id!r} does not match "
                f"the assembled packet identifier {packet_id!r}"
            )

        return SynthesisContextPacket(
            packet_id=packet_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            mode=request.mode,
            readiness=readiness,
            evidence_references=included,
            # Deliberately empty: producing a summary spanning several evidence
            # records is synthesis, which Phase 40C does not perform. An
            # unattributed narrative has no place inside the grounded input
            # boundary (Phase 40A §6).
            context_summaries=[],
            conflicts=conflicts,
            missing_context=missing_context,
            source_coverage=coverage,
            warnings=ordered_warnings,
            assembled_at=assembled_at,
            metadata=metadata,
            read_only=True,
        )

    # ----------------------------------------------------------------- #
    # 1. Request validation (cross-record only)
    # ----------------------------------------------------------------- #
    def _validate_request(self, request: GroundedSynthesisRequest) -> None:
        """Enforce the invariants Pydantic cannot see.

        Field-level bounds, enum membership, metadata safety, evidence-reference
        uniqueness and request/packet consistency are already guaranteed by the
        Phase 40B model; re-checking them here would duplicate validation and
        create a second place for the rules to drift.
        """

        if request.status not in ASSEMBLABLE_REQUEST_STATUSES:
            raise GroundingRequestNotAssemblableError(
                f"request status {request.status.value!r} is not an assemblable "
                "request status; it describes a produced artifact"
            )
        if request.context_packet is not None:
            raise GroundingRequestNotAssemblableError(
                "request already carries an embedded context_packet; re-assembling "
                "would silently replace the grounding the request declares"
            )

    # ----------------------------------------------------------------- #
    # 2. Collection + normalization
    # ----------------------------------------------------------------- #
    def _collect(
        self,
        request: GroundedSynthesisRequest,
        evidence: GroundingEvidenceSources,
        diagnostics: _Diagnostics,
        warnings: list[SynthesisWarning],
        blocking_reasons: list[str],
    ) -> list[_Candidate]:
        limits = self._limits
        candidates: list[_Candidate] = []
        requested_keys = {
            (item.grounding_kind.value, _normalize_identity(item.source_record_id))
            for item in request.evidence_references
            if item.source_record_id is not None
        }

        for record in evidence.evidence_records:
            candidate = self._normalize_evidence_record(record, limits, diagnostics)
            if candidate is not None:
                candidates.append(candidate)

        for snapshot in evidence.repository_snapshots:
            if snapshot.repository_identity.status in _UNSAFE_IDENTITY_STATUSES:
                diagnostics.exclude(
                    GroundingExclusionReason.UNSAFE_REPOSITORY_IDENTITY,
                    len(snapshot.evidence),
                )
                blocking_reasons.append("unsafe_repository_identity")
                warnings.append(
                    SynthesisWarning(
                        code=SynthesisWarningCode.CONSTRAINT_LIMITED,
                        message=(
                            "repository observation excluded: identity status "
                            f"{snapshot.repository_identity.status.value!r} is not safe "
                            "to ground on"
                        ),
                        subject_id=snapshot.snapshot_id,
                    )
                )
                continue
            for item in snapshot.evidence:
                candidate = self._normalize_observer_evidence(
                    item,
                    kind=GroundingEvidenceKind.REPOSITORY_OBSERVATION,
                    container_id=snapshot.snapshot_id,
                    repository_id=snapshot.repository_identity.repository_id,
                    observer_version=snapshot.observer_version,
                    fallback_observed_at=snapshot.observed_at,
                    fallback_reference=self._snapshot_fallback_reference(snapshot),
                    extra_metadata=(("snapshot_completeness", snapshot.completeness.value),),
                    limits=limits,
                    diagnostics=diagnostics,
                )
                if candidate is not None:
                    candidates.append(candidate)

        for drift in evidence.repository_drift_analyses:
            if drift.repository_identity.status in _UNSAFE_IDENTITY_STATUSES:
                diagnostics.exclude(
                    GroundingExclusionReason.UNSAFE_REPOSITORY_IDENTITY,
                    len(drift.evidence),
                )
                blocking_reasons.append("unsafe_repository_identity")
                warnings.append(
                    SynthesisWarning(
                        code=SynthesisWarningCode.CONSTRAINT_LIMITED,
                        message=(
                            "repository drift finding excluded: identity status "
                            f"{drift.repository_identity.status.value!r} is not safe to "
                            "ground on"
                        ),
                        subject_id=drift.drift_id,
                    )
                )
                continue
            for item in drift.evidence:
                candidate = self._normalize_observer_evidence(
                    item,
                    kind=GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING,
                    container_id=drift.drift_id,
                    repository_id=drift.repository_identity.repository_id,
                    observer_version=drift.observer_version,
                    fallback_observed_at=drift.observed_at,
                    fallback_reference=self._drift_fallback_reference(drift),
                    extra_metadata=(("drift_status", drift.drift_status.value),),
                    limits=limits,
                    diagnostics=diagnostics,
                )
                if candidate is not None:
                    candidates.append(candidate)

        for contradiction in evidence.contradictions:
            candidate = self._normalize_contradiction(contradiction, limits, diagnostics)
            if candidate is not None:
                candidates.append(candidate)

        for record in evidence.memory_records:
            candidate = self._normalize_memory_record(record, limits, diagnostics)
            if candidate is not None:
                candidates.append(candidate)

        for reference in request.evidence_references:
            candidate = self._normalize_requested_reference(reference, limits, diagnostics)
            if candidate is not None:
                candidates.append(candidate)

        # Mark provider candidates the request named explicitly. Doing this after
        # collection keeps the "directly requested" flag a property of the
        # request/candidate *pair* rather than of the collection order.
        if not requested_keys:
            return candidates
        return [
            candidate
            if candidate.requested or candidate.identity_key() not in requested_keys
            else _replace_requested(candidate)
            for candidate in candidates
        ]

    def _normalize_evidence_record(
        self,
        record: EvidenceRecord,
        limits: GroundingAssemblyLimits,
        diagnostics: _Diagnostics,
    ) -> _Candidate | None:
        source_id = _normalize_identity(record.evidence_id)
        if not source_id:
            diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
            return None
        label, label_cut = _bounded_text(
            f"{record.evidence_type.value} evidence {source_id}", limits.max_label_length
        )
        summary, summary_cut = _bounded_text(record.summary, limits.max_summary_length)
        if label_cut or summary_cut:
            diagnostics.text_truncations += 1
        return _Candidate(
            kind=GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD,
            source_record_id=source_id,
            # The record already carries a bounded, non-executable
            # ``EvidenceReference``; reusing it verbatim is the whole reason this
            # family normalizes one-to-one.
            reference=record.reference,
            evidence_type=record.evidence_type,
            source=record.source,
            scope=record.scope,
            observed_at=record.captured_at,
            confidence=None,
            label=label,
            summary=summary,
            content_digest=None,
            metadata=(("reference_kind", record.reference.reference_kind.value),),
            authority_rank=(
                _FAMILY_BASE[GroundingEvidenceKind.ACTIVE_MEMORY_EVIDENCE_RECORD]
                + _EVIDENCE_TYPE_OFFSET[record.evidence_type]
            ),
            requested=False,
            origin_record_id=source_id,
            text_truncated=label_cut or summary_cut,
        )

    def _normalize_memory_record(
        self,
        record: MemoryRecord,
        limits: GroundingAssemblyLimits,
        diagnostics: _Diagnostics,
    ) -> _Candidate | None:
        source_id = _normalize_identity(record.record_id)
        if not source_id:
            diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
            return None
        label, label_cut = _bounded_text(
            f"{record.claim.subject} {record.claim.predicate}", limits.max_label_length
        )
        summary_text = record.claim.summary or (
            f"{record.claim.subject} {record.claim.predicate} {record.claim.value}"
        )
        summary, summary_cut = _bounded_text(summary_text, limits.max_summary_length)
        if label_cut or summary_cut:
            diagnostics.text_truncations += 1
        return _Candidate(
            kind=GroundingEvidenceKind.ACTIVE_MEMORY_RECORD,
            source_record_id=source_id,
            # A memory record has no ``EvidenceReference`` of its own; the stable,
            # non-executable pointer at it is its own record id.
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID,
                value=source_id,
            ),
            # Deliberately ``None``: a claim is not itself evidence, and choosing
            # any ``EvidenceType`` for it would assert proof the record does not
            # carry.
            evidence_type=None,
            source=record.source,
            scope=record.scope,
            observed_at=record.observed_at or record.created_at,
            confidence=record.confidence,
            label=label,
            summary=summary,
            content_digest=None,
            metadata=(
                ("lifecycle_state", record.lifecycle_state.value),
                ("record_kind", record.kind.value),
                ("verification_state", record.verification_state.value),
            ),
            authority_rank=(
                _FAMILY_BASE[GroundingEvidenceKind.ACTIVE_MEMORY_RECORD]
                + _VERIFICATION_OFFSET.get(record.verification_state, 14)
            ),
            requested=False,
            origin_record_id=source_id,
            text_truncated=label_cut or summary_cut,
        )

    def _normalize_contradiction(
        self,
        record: ContradictionRecord,
        limits: GroundingAssemblyLimits,
        diagnostics: _Diagnostics,
    ) -> _Candidate | None:
        source_id = _normalize_identity(record.contradiction_id)
        if not source_id:
            diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
            return None
        label, label_cut = _bounded_text(
            f"Contradiction {record.contradiction_class.value}", limits.max_label_length
        )
        summary, summary_cut = _bounded_text(record.summary, limits.max_summary_length)
        if label_cut or summary_cut:
            diagnostics.text_truncations += 1
        metadata: list[tuple[str, str]] = [
            ("contradiction_class", record.contradiction_class.value),
            ("resolution_state", record.resolution_state.value),
        ]
        if record.severity is not None:
            metadata.append(("severity", record.severity.value))
        return _Candidate(
            kind=GroundingEvidenceKind.CONTRADICTION_RECORD,
            source_record_id=source_id,
            reference=EvidenceReference(
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID,
                value=source_id,
            ),
            evidence_type=None,
            source=record.detection_source,
            scope=None,
            observed_at=record.detected_at,
            confidence=None,
            label=label,
            summary=summary,
            content_digest=None,
            metadata=tuple(sorted(metadata)),
            authority_rank=(
                _FAMILY_BASE[GroundingEvidenceKind.CONTRADICTION_RECORD]
                + _SEVERITY_OFFSET[record.severity]
            ),
            requested=False,
            origin_record_id=source_id,
            text_truncated=label_cut or summary_cut,
        )

    def _normalize_observer_evidence(
        self,
        item: RepositoryEvidence,
        *,
        kind: GroundingEvidenceKind,
        container_id: str,
        repository_id: str,
        observer_version: str,
        fallback_observed_at: datetime,
        fallback_reference: EvidenceReference | None,
        extra_metadata: tuple[tuple[str, str], ...],
        limits: GroundingAssemblyLimits,
        diagnostics: _Diagnostics,
    ) -> _Candidate | None:
        if item.authority in _UNGROUNDABLE_OBSERVER_AUTHORITIES:
            diagnostics.exclude(GroundingExclusionReason.UNGROUNDED_AUTHORITY)
            return None
        if item.truncation_state is TruncationState.OMITTED:
            diagnostics.exclude(GroundingExclusionReason.OMITTED_CONTENT)
            return None

        source_id = _normalize_identity(f"{container_id}:{item.evidence_id}")
        reference = self._observer_reference(item, fallback_reference)
        if reference is None:
            diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
            return None

        label, label_cut = _bounded_text(item.source, limits.max_label_length)
        summary, summary_cut = _bounded_text(item.summary, limits.max_summary_length)
        if label_cut or summary_cut:
            diagnostics.text_truncations += 1

        metadata = tuple(
            sorted(
                (
                    ("authority", item.authority.value),
                    ("evidence_category", item.category.value),
                    ("truncation_state", item.truncation_state.value),
                    *extra_metadata,
                )
            )
        )
        return _Candidate(
            kind=kind,
            source_record_id=source_id,
            reference=reference,
            evidence_type=_OBSERVER_CATEGORY_EVIDENCE_TYPE[item.category],
            # Reuses the exact Phase 39A observer source convention so grounded
            # synthesis and evidence projection name the same producer.
            source=MemorySource(
                source_type=MemorySourceType.REPOSITORY_OBSERVER,
                source_id=f"repository-observer:{observer_version}",
            ),
            scope=MemoryScope(
                scope_type=MemoryScopeType.REPOSITORY, scope_id=repository_id
            ),
            observed_at=item.captured_at or fallback_observed_at,
            # No confidence is *calculated* anywhere in Hive|Mind (Phase 37A §6.3,
            # Phase 39A); inventing one here would be a computed trust score.
            confidence=None,
            label=label,
            summary=summary,
            content_digest=_bounded_digest(item.digest),
            metadata=metadata,
            authority_rank=(
                _FAMILY_BASE[kind] + _OBSERVER_AUTHORITY_OFFSET.get(item.authority, 12)
            ),
            requested=False,
            origin_record_id=None,
            text_truncated=label_cut or summary_cut,
        )

    def _normalize_requested_reference(
        self,
        reference: GroundingEvidenceReference,
        limits: GroundingAssemblyLimits,
        diagnostics: _Diagnostics,
    ) -> _Candidate | None:
        """Admit a caller-supplied reference as a candidate in its own right.

        It is already a valid Phase 40B grounding reference, so re-deriving it
        would be pointless; it flows through the same filter, dedup and ranking
        stages as everything else, and ranks below every provider family so a
        provider-held copy always wins the duplicate contest.
        """

        source_id = _normalize_identity(
            reference.source_record_id or reference.evidence_id
        )
        if not source_id:
            diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
            return None
        label, label_cut = _bounded_text(reference.label, limits.max_label_length)
        summary, summary_cut = _bounded_text(reference.summary, limits.max_summary_length)
        if label_cut or summary_cut:
            diagnostics.text_truncations += 1
        offset = (
            _UNTYPED_EVIDENCE_OFFSET
            if reference.evidence_type is None
            else _EVIDENCE_TYPE_OFFSET[reference.evidence_type]
        )
        return _Candidate(
            kind=reference.grounding_kind,
            source_record_id=source_id,
            reference=reference.reference,
            evidence_type=reference.evidence_type,
            source=reference.source,
            scope=reference.scope,
            observed_at=reference.observed_at,
            confidence=reference.confidence,
            label=label,
            summary=summary,
            content_digest=_bounded_digest(reference.content_digest),
            # The caller's own metadata bag is deliberately *not* carried over.
            # It has already passed Phase 40B bounds, but copying an arbitrary
            # caller bag into assembled output would make the packet's metadata a
            # pass-through channel rather than assembly-controlled diagnostics.
            metadata=(("origin", "requested_reference"),),
            authority_rank=_REQUESTED_REFERENCE_BASE + offset,
            requested=True,
            origin_record_id=source_id,
            text_truncated=label_cut or summary_cut,
        )

    @staticmethod
    def _observer_reference(
        item: RepositoryEvidence, fallback: EvidenceReference | None
    ) -> EvidenceReference | None:
        """Pick the strongest bounded pointer the observer evidence supports.

        A repository-relative path is preferred because it is the most specific
        safe pointer. Absolute roots and remote URLs are never used — they are
        machine-specific and can carry credentials.
        """

        if item.repository_relative_path:
            return EvidenceReference(
                reference_kind=EvidenceReferenceKind.FILE_PATH,
                value=item.repository_relative_path,
            )
        return fallback

    @staticmethod
    def _snapshot_fallback_reference(
        snapshot: RepositorySnapshot,
    ) -> EvidenceReference | None:
        if snapshot.commit:
            return EvidenceReference(
                reference_kind=EvidenceReferenceKind.COMMIT_HASH, value=snapshot.commit
            )
        if snapshot.branch:
            return EvidenceReference(
                reference_kind=EvidenceReferenceKind.BRANCH_NAME, value=snapshot.branch
            )
        return EvidenceReference(
            reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value=snapshot.snapshot_id
        )

    @staticmethod
    def _drift_fallback_reference(
        drift: RepositoryDriftAnalysis,
    ) -> EvidenceReference | None:
        if drift.baseline_commit_hash:
            return EvidenceReference(
                reference_kind=EvidenceReferenceKind.COMMIT_HASH,
                value=drift.baseline_commit_hash,
            )
        return EvidenceReference(
            reference_kind=EvidenceReferenceKind.ARTIFACT_ID, value=drift.drift_id
        )

    # ----------------------------------------------------------------- #
    # 3. Eligibility filtering
    # ----------------------------------------------------------------- #
    def _filter(
        self,
        request: GroundedSynthesisRequest,
        candidates: Sequence[_Candidate],
        diagnostics: _Diagnostics,
    ) -> list[_Candidate]:
        """Apply the explicit, deterministic inclusion rules.

        Lifecycle and verification gating happen here rather than during
        normalization so that an excluded record is still *counted* as inspected:
        a narrow packet must be distinguishable from a thorough one.
        """

        request_scope = _scope_key(request.scope)
        eligible: list[_Candidate] = []
        for candidate in candidates:
            if candidate.kind not in SUPPORTED_GROUNDING_KINDS:
                diagnostics.exclude(GroundingExclusionReason.UNSUPPORTED_EVIDENCE_KIND)
                diagnostics.unsupported_kinds.add(candidate.kind.value)
                continue
            if not candidate.source_record_id or not candidate.reference.value.strip():
                diagnostics.exclude(GroundingExclusionReason.MISSING_GROUNDING_FIELDS)
                continue
            candidate_scope = _scope_key(candidate.scope)
            # Absence of a declared scope is *not* evidence of being out of scope.
            # Contradiction records carry no scope at all; excluding them under a
            # scoped request would hide exactly the conflicts a scoped packet most
            # needs to surface.
            if (
                request_scope is not None
                and candidate_scope is not None
                and candidate_scope != request_scope
            ):
                diagnostics.exclude(GroundingExclusionReason.OUT_OF_SCOPE)
                continue
            # Lifecycle/verification standing is read from the candidate's own
            # normalized metadata, never from a shared index: a caller-supplied
            # reference that happens to reuse a provider record id must not
            # inherit that provider record's standing.
            values = dict(candidate.metadata)
            lifecycle = values.get("lifecycle_state")
            if lifecycle is not None and LifecycleState(lifecycle) not in (
                _GROUNDABLE_LIFECYCLE_STATES
            ):
                diagnostics.exclude(GroundingExclusionReason.NOT_ACTIVE_LIFECYCLE)
                continue
            verification = values.get("verification_state")
            if verification is not None and VerificationState(verification) in (
                _UNGROUNDABLE_VERIFICATION_STATES
            ):
                diagnostics.exclude(GroundingExclusionReason.UNRESOLVABLE_VERIFICATION)
                continue
            eligible.append(candidate)
        return eligible

    # ----------------------------------------------------------------- #
    # 4. Deduplication
    # ----------------------------------------------------------------- #
    @staticmethod
    def _critical_source_ids(evidence: GroundingEvidenceSources) -> frozenset[str]:
        """Provider record ids participating in an *open, critical* contradiction.

        Only ``open`` contradictions count: a resolved or archived contradiction
        is history, and treating it as a live blocker would make every packet
        permanently blocked once any conflict had ever existed.
        """

        ids: set[str] = set()
        for contradiction in evidence.contradictions:
            if contradiction.resolution_state is not ContradictionResolutionState.OPEN:
                continue
            if contradiction.severity is not ContradictionSeverity.CRITICAL:
                continue
            ids.add(_normalize_identity(contradiction.contradiction_id))
            ids.update(
                _normalize_identity(record_id)
                for record_id in contradiction.involved_record_ids
            )
        return frozenset(ids)

    @staticmethod
    def _is_critical(candidate: _Candidate, critical_ids: frozenset[str]) -> bool:
        return candidate.source_record_id in critical_ids

    def _deduplicate(
        self,
        candidates: Sequence[_Candidate],
        critical_ids: frozenset[str],
        diagnostics: _Diagnostics,
    ) -> list[_Candidate]:
        """Collapse candidates sharing a canonical source identity.

        The key is ``(grounding_kind, NFC-normalized source record id)`` — the
        provider's own stable identity, never Python object identity, never
        ``hash()``, never set iteration order, and never a serialized blob whose
        representation could shift. Cross-family collapsing is deliberately *not*
        attempted: two families referring to the same underlying fact do so under
        different evidence semantics, and merging them would be an invented
        equivalence.
        """

        winners: dict[tuple[str, str], _Candidate] = {}
        for candidate in candidates:
            key = candidate.identity_key()
            existing = winners.get(key)
            if existing is None:
                winners[key] = candidate
                continue
            diagnostics.duplicates_removed += 1
            diagnostics.exclude(GroundingExclusionReason.DUPLICATE_EVIDENCE)
            challenger_key = candidate.dedup_precedence(
                self._is_critical(candidate, critical_ids)
            )
            incumbent_key = existing.dedup_precedence(
                self._is_critical(existing, critical_ids)
            )
            if challenger_key < incumbent_key:
                winners[key] = candidate
        # Sorting by the canonical key makes the output independent of dict
        # insertion order, which is the only place input order could otherwise
        # leak into the result.
        return [winners[key] for key in sorted(winners)]

    # ----------------------------------------------------------------- #
    # 5. Ranking
    # ----------------------------------------------------------------- #
    def _rank(
        self, candidates: Sequence[_Candidate], critical_ids: frozenset[str]
    ) -> list[_Candidate]:
        """Order the packet deterministically.

        The key, in order:

        1. participation in an open critical contradiction — a blocker must lead
           the packet and must never be the item bounds remove;
        2. whether the request named the evidence directly;
        3. declared provider authority (see :data:`_FAMILY_BASE`);
        4. confidence band, where the record declares one;
        5. freshness, newest first, undated last;
        6. canonical evidence family;
        7. the derived evidence identifier — a pure function of the candidate's
           canonical material, so the final tie-break is stable across processes
           and never depends on ``hash()`` randomization or input order.
        """

        return sorted(
            candidates,
            key=lambda candidate: (
                0 if self._is_critical(candidate, critical_ids) else 1,
                0 if candidate.requested else 1,
                candidate.authority_rank,
                _CONFIDENCE_RANK[candidate.confidence],
                _freshness_key(candidate.observed_at),
                _KIND_RANK.get(candidate.kind, len(_KIND_ORDER)),
                candidate.evidence_id(),
            ),
        )

    # ----------------------------------------------------------------- #
    # 6. Bounds
    # ----------------------------------------------------------------- #
    def _apply_bounds(
        self,
        request: GroundedSynthesisRequest,
        ranked: Sequence[_Candidate],
        diagnostics: _Diagnostics,
        warnings: list[SynthesisWarning],
    ) -> tuple[list[_Candidate], list[_Candidate]]:
        limits = self._limits
        # The request's own declared ceiling always wins when it is stricter: a
        # caller may narrow the packet, never widen it past the contract.
        item_limit = min(
            limits.max_evidence_items, request.constraints.max_evidence_references
        )
        distinct_kinds = {candidate.kind for candidate in ranked}
        # With a single contributing family there is nothing for it to crowd out,
        # so the per-family cap has no purpose and is lifted.
        per_kind_limit = (
            item_limit if len(distinct_kinds) <= 1 else limits.max_items_per_kind
        )

        selected: list[_Candidate] = []
        dropped: list[_Candidate] = []
        per_kind_counts: dict[GroundingEvidenceKind, int] = {}
        per_kind_dropped: dict[GroundingEvidenceKind, int] = {}
        total_dropped = 0

        for candidate in ranked:
            count = per_kind_counts.get(candidate.kind, 0)
            if count >= per_kind_limit or len(selected) >= item_limit:
                dropped.append(candidate)
                total_dropped += 1
                if count >= per_kind_limit and len(selected) < item_limit:
                    per_kind_dropped[candidate.kind] = (
                        per_kind_dropped.get(candidate.kind, 0) + 1
                    )
                continue
            per_kind_counts[candidate.kind] = count + 1
            selected.append(candidate)

        if total_dropped:
            diagnostics.truncated_items = total_dropped
            diagnostics.exclude(GroundingExclusionReason.BOUNDS_EXCEEDED, total_dropped)
            warnings.append(
                SynthesisWarning(
                    code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                    message=(
                        f"{total_dropped} eligible evidence item(s) omitted to satisfy "
                        f"the packet limit of {item_limit} item(s)"
                    ),
                )
            )
            for kind in sorted(per_kind_dropped, key=lambda item: item.value):
                warnings.append(
                    SynthesisWarning(
                        code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                        message=(
                            f"{per_kind_dropped[kind]} item(s) omitted to satisfy the "
                            f"per-family limit of {per_kind_limit} item(s)"
                        ),
                        subject_id=kind.value,
                    )
                )
        return selected, dropped

    # ----------------------------------------------------------------- #
    # 7. Packet construction helpers
    # ----------------------------------------------------------------- #
    def _build_references(
        self, selected: Sequence[_Candidate]
    ) -> tuple[list[GroundingEvidenceReference], dict[str, str]]:
        """Materialize references and index provider record id -> evidence id."""

        references: list[GroundingEvidenceReference] = []
        by_source: dict[str, str] = {}
        seen: dict[str, _Candidate] = {}
        for candidate in selected:
            evidence_id = candidate.evidence_id()
            previous = seen.get(evidence_id)
            if previous is not None:
                raise GroundingEvidenceIdentityError(
                    f"derived evidence id {evidence_id!r} collides between "
                    f"{previous.identity_key()!r} and {candidate.identity_key()!r}"
                )
            seen[evidence_id] = candidate
            references.append(candidate.to_reference(evidence_id))
            if candidate.origin_record_id is not None:
                by_source.setdefault(candidate.origin_record_id, evidence_id)
        return references, by_source

    def _build_conflicts(
        self,
        evidence: GroundingEvidenceSources,
        by_source: dict[str, str],
    ) -> tuple[list[SynthesisEvidenceConflict], list[SynthesisWarning], list[str]]:
        """Surface open contradictions over evidence the packet actually carries.

        Conflicts are *surfaced, never resolved*: no winner is chosen and no
        participant is dropped. A contradiction whose participants are not both
        present cannot be expressed as a packet conflict (the Phase 40B contract
        requires at least two known evidence ids), so it becomes an explicit
        warning — and, when critical, a readiness blocker. That is the difference
        between "we could not represent this" and silently losing it.
        """

        conflicts: list[SynthesisEvidenceConflict] = []
        warnings: list[SynthesisWarning] = []
        blockers: list[str] = []
        for contradiction in evidence.contradictions:
            if contradiction.resolution_state is not ContradictionResolutionState.OPEN:
                continue
            participants = sorted(
                {
                    by_source[_normalize_identity(record_id)]
                    for record_id in contradiction.involved_record_ids
                    if _normalize_identity(record_id) in by_source
                }
            )
            critical = contradiction.severity is ContradictionSeverity.CRITICAL
            if len(participants) < 2:
                warnings.append(
                    SynthesisWarning(
                        code=SynthesisWarningCode.CONFLICTING_EVIDENCE,
                        message=(
                            "open contradiction could not be represented: fewer than "
                            "two of its records are present in the packet"
                        ),
                        subject_id=contradiction.contradiction_id,
                    )
                )
                if critical:
                    blockers.append("unrepresentable_critical_conflict")
                continue
            if critical:
                blockers.append("critical_conflict")
            conflict_id = derive_grounded_synthesis_id(
                "gs-conflict",
                json.dumps(
                    [_normalize_identity(contradiction.contradiction_id), participants],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
            )
            summary, _ = _bounded_text(contradiction.summary, self._limits.max_summary_length)
            conflicts.append(
                SynthesisEvidenceConflict(
                    conflict_id=conflict_id,
                    summary=summary or "open contradiction over packet evidence",
                    evidence_ids=participants,
                    severity=contradiction.severity,
                    contradiction_record_id=contradiction.contradiction_id,
                )
            )
        conflicts.sort(key=lambda item: item.conflict_id)
        if len(conflicts) > self._limits.max_conflicts:
            # Conflicts are never silently clipped; exceeding the bound is a
            # packet the service refuses to misrepresent.
            raise GroundingCandidateOverflowError(
                f"{len(conflicts)} representable conflicts exceed the max_conflicts "
                f"bound of {self._limits.max_conflicts}"
            )
        return conflicts, warnings, blockers

    def _build_missing_context(
        self,
        request: GroundedSynthesisRequest,
        selected: Sequence[_Candidate],
        dropped: Sequence[_Candidate],
        limits: GroundingAssemblyLimits,
    ) -> list[SynthesisMissingContext]:
        """Name the grounding the request asked for and the packet does not have.

        A gap is *data*, not an absence (Phase 40A §9). It is emitted only for
        evidence the request named explicitly, because that is the only case in
        which the service knows something specific is missing rather than merely
        unrequested.
        """

        requested_keys = {
            (item.grounding_kind.value, _normalize_identity(item.source_record_id or item.evidence_id))
            for item in request.evidence_references
        }
        if not requested_keys:
            return []
        present = {candidate.identity_key() for candidate in selected}
        missing = sorted(requested_keys - present)
        if not missing:
            return []
        kinds = sorted({key[0] for key in missing})
        gap_id = derive_grounded_synthesis_id(
            "gs-gap",
            json.dumps(
                ["requested-evidence-unavailable", [list(key) for key in missing]],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )
        description, _ = _bounded_text(
            f"{len(missing)} explicitly requested evidence item(s) are not present in "
            f"the assembled packet (families: {', '.join(kinds)})",
            limits.max_summary_length,
        )
        return [
            SynthesisMissingContext(
                gap_id=gap_id,
                description=description or "requested evidence unavailable",
                required_evidence_kinds=[
                    GroundingEvidenceKind(kind)
                    for kind in kinds
                    if kind in {member.value for member in GroundingEvidenceKind}
                ],
            )
        ]

    @staticmethod
    def _build_coverage(
        candidates: Sequence[_Candidate],
        included: Sequence[GroundingEvidenceReference],
    ) -> list[SynthesisSourceCoverage]:
        """One entry per family that supplied a candidate.

        Zero-count entries are kept deliberately: a family that offered evidence
        and contributed none is materially different from a family that was never
        consulted, and only the explicit zero makes that visible.
        """

        offered: dict[GroundingEvidenceKind, int] = {}
        for candidate in candidates:
            offered[candidate.kind] = offered.get(candidate.kind, 0) + 1
        used: dict[GroundingEvidenceKind, int] = {}
        for reference in included:
            used[reference.grounding_kind] = used.get(reference.grounding_kind, 0) + 1
        return [
            SynthesisSourceCoverage(
                grounding_kind=kind,
                referenced_count=used.get(kind, 0),
                note=(
                    None
                    if used.get(kind, 0)
                    else "offered candidates but contributed no packet evidence"
                ),
            )
            for kind in sorted(offered, key=lambda item: item.value)
        ]

    @staticmethod
    def _bound_warnings(
        warnings: Sequence[SynthesisWarning], limits: GroundingAssemblyLimits
    ) -> list[SynthesisWarning]:
        ordered = sorted(
            warnings,
            key=lambda item: (item.code.value, item.message, item.subject_id or ""),
        )
        if len(ordered) <= limits.max_warnings:
            return ordered
        # Keeping the first N in canonical order and replacing the tail with a
        # single explicit notice keeps the bound without pretending the omitted
        # warnings never existed.
        kept = ordered[: limits.max_warnings - 1]
        kept.append(
            SynthesisWarning(
                code=SynthesisWarningCode.BOUNDS_EXCEEDED,
                message=(
                    f"{len(ordered) - len(kept)} additional warning(s) omitted to "
                    f"satisfy the {limits.max_warnings} warning bound"
                ),
            )
        )
        return kept

    # ----------------------------------------------------------------- #
    # 8. Readiness
    # ----------------------------------------------------------------- #
    @staticmethod
    def _evaluate_readiness(
        *,
        included: Sequence[GroundingEvidenceReference],
        conflicts: Sequence[SynthesisEvidenceConflict],
        missing_context: Sequence[SynthesisMissingContext],
        blocking_reasons: Sequence[str],
        warnings: Sequence[SynthesisWarning],
    ) -> tuple[SynthesisReadinessStatus, str]:
        """Decide readiness by first-match rules, strongest failure first.

        The ordering is the point: a blocker outranks emptiness, emptiness
        outranks a gap, and only a packet with evidence, no gaps, and no critical
        conflict may call itself ``ready``. Warnings never downgrade ``ready`` —
        "ready with warnings" is exactly a ready packet carrying warnings — but
        they are always carried so a future synthesis stage cannot mistake a
        degraded packet for a clean one.
        """

        if blocking_reasons:
            return SynthesisReadinessStatus.BLOCKED, sorted(set(blocking_reasons))[0]
        if any(
            conflict.severity is ContradictionSeverity.CRITICAL for conflict in conflicts
        ):
            return SynthesisReadinessStatus.BLOCKED, "critical_conflict"
        if not included:
            return (
                SynthesisReadinessStatus.INSUFFICIENT_EVIDENCE,
                "no_eligible_evidence",
            )
        if missing_context:
            return SynthesisReadinessStatus.CONTEXT_REQUIRED, "missing_requested_context"
        if warnings:
            return SynthesisReadinessStatus.READY, "ready_with_warnings"
        return SynthesisReadinessStatus.READY, "ready"

    # ----------------------------------------------------------------- #
    # 9. Diagnostics + identity
    # ----------------------------------------------------------------- #
    @staticmethod
    def _build_metadata(
        *,
        request: GroundedSynthesisRequest,
        diagnostics: _Diagnostics,
        conflicts: Sequence[SynthesisEvidenceConflict],
        readiness_reason: str,
    ) -> dict[str, Any]:
        """Bounded, secret-free diagnostics.

        Every value is a count, a closed-enum literal, or a fixed slug. No path,
        remote, credential, environment value, excerpt, or provider payload can
        reach this bag, and the shallow shape stays well inside the Phase 40B
        metadata entry, container, depth and node bounds.
        """

        metadata: dict[str, Any] = {
            "assembly_version": GROUNDING_CONTEXT_ASSEMBLY_VERSION,
            "request_mode": request.mode.value,
            "candidates_inspected": diagnostics.inspected,
            "candidates_accepted": diagnostics.accepted,
            "candidates_excluded": diagnostics.excluded,
            "duplicates_removed": diagnostics.duplicates_removed,
            "items_truncated": diagnostics.truncated_items,
            "text_truncations": diagnostics.text_truncations,
            "critical_conflict_count": sum(
                1
                for conflict in conflicts
                if conflict.severity is ContradictionSeverity.CRITICAL
            ),
            "readiness_reason": readiness_reason,
        }
        if diagnostics.exclusions:
            metadata["exclusion_reasons"] = {
                reason.value: diagnostics.exclusions[reason]
                for reason in sorted(diagnostics.exclusions, key=lambda item: item.value)
            }
        if diagnostics.unsupported_kinds:
            metadata["unsupported_evidence_kinds"] = sorted(
                diagnostics.unsupported_kinds
            )
        return metadata

    @staticmethod
    def _derive_packet_id(
        *,
        request: GroundedSynthesisRequest,
        readiness: SynthesisReadinessStatus,
        included: Sequence[GroundingEvidenceReference],
        conflicts: Sequence[SynthesisEvidenceConflict],
        missing_context: Sequence[SynthesisMissingContext],
        coverage: Sequence[SynthesisSourceCoverage],
        warnings: Sequence[SynthesisWarning],
        assembled_at: datetime | None,
    ) -> str:
        return derive_context_packet_identity(
            schema_version=request.schema_version,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            mode=request.mode,
            readiness=readiness,
            assembled_at=assembled_at,
            evidence_references=included,
            conflicts=conflicts,
            missing_context=missing_context,
            source_coverage=coverage,
            warnings=warnings,
        )


def derive_context_packet_identity(
    *,
    schema_version: str,
    request_id: str,
    correlation_id: str | None,
    mode: GroundedSynthesisMode,
    readiness: SynthesisReadinessStatus,
    assembled_at: datetime | None,
    evidence_references: Sequence[GroundingEvidenceReference],
    conflicts: Sequence[SynthesisEvidenceConflict],
    missing_context: Sequence[SynthesisMissingContext],
    source_coverage: Sequence[SynthesisSourceCoverage],
    warnings: Sequence[SynthesisWarning],
) -> str:
    """Derive a packet identifier from everything that materially defines it.

    Folding the *ordered* evidence ids (not a set) in means a reordered packet is
    a different packet; folding the assembly version in means a packet built
    under different assembly rules can never collide with one built under these.
    Nothing random, clock-read, or environment-derived participates, so identical
    material always yields the same id.

    Public and parameterized by the packet's own fields — rather than private to
    the assembler — because Phase 40D re-derives this identity to detect a
    tampered packet. Both callers must fold *exactly* the same material or the
    check would be meaningless, so the material shape lives here once
    (Phase 40D §"packet consistency validation").
    """

    material = json.dumps(
        {
            "assembly_version": GROUNDING_CONTEXT_ASSEMBLY_VERSION,
            "schema_version": schema_version,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "mode": mode.value,
            "readiness": readiness.value,
            "assembled_at": _canonical_datetime(assembled_at),
            "evidence_ids": [item.evidence_id for item in evidence_references],
            "conflicts": [
                [
                    item.conflict_id,
                    None if item.severity is None else item.severity.value,
                    list(item.evidence_ids),
                ]
                for item in conflicts
            ],
            "missing_context": [item.gap_id for item in missing_context],
            "coverage": [
                [item.grounding_kind.value, item.referenced_count]
                for item in source_coverage
            ],
            "warnings": [
                [item.code.value, item.message, item.subject_id] for item in warnings
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return derive_grounded_synthesis_id("gs-packet", material)


def _replace_requested(candidate: _Candidate) -> _Candidate:
    """Return ``candidate`` flagged as directly requested (frozen dataclass copy)."""

    return _Candidate(
        kind=candidate.kind,
        source_record_id=candidate.source_record_id,
        reference=candidate.reference,
        evidence_type=candidate.evidence_type,
        source=candidate.source,
        scope=candidate.scope,
        observed_at=candidate.observed_at,
        confidence=candidate.confidence,
        label=candidate.label,
        summary=candidate.summary,
        content_digest=candidate.content_digest,
        metadata=candidate.metadata,
        authority_rank=candidate.authority_rank,
        requested=True,
        origin_record_id=candidate.origin_record_id,
        text_truncated=candidate.text_truncated,
    )


def assemble_grounding_context(
    request: GroundedSynthesisRequest,
    *,
    evidence: GroundingEvidenceSources,
    assembled_at: datetime | None = None,
    limits: GroundingAssemblyLimits | None = None,
) -> SynthesisContextPacket:
    """Module-level convenience wrapper.

    Mirrors the existing ``project_repository_evidence`` /
    ``build_context_packet`` entry-point convention so callers that need one call
    do not have to manage a service instance.
    """

    return GroundingContextAssemblyService(limits=limits).assemble(
        request, evidence=evidence, assembled_at=assembled_at
    )
