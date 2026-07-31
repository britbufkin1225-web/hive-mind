"""Phase 40G — Migration Candidate Assessment (Dry-Run) result contracts.

The typed **result** shapes for the first migration phase that reasons about a
*complete projected candidate set* rather than one artifact at a time. Where Phase
40F (:mod:`app.models.memory_migration_projection`) describes what a parser
interpreted from bytes and the bounded candidates it projected — each carrying its
own per-item diagnostics — this module describes what a deterministic **dry-run
assessor** concluded about the whole set: which candidates duplicate one another,
which source identities conflict, which source orderings are ambiguous, which
candidates are degenerate, and which Phase 40F findings remain unresolved.

Deliberately a *separate module* rather than an extension of the projection
contracts, following the Phase 40B/40D/40E/40F split exactly:

* the projection contracts describe what a parser *produced*; this module
  describes what Hive|Mind *concluded* about a set of those products. Merging them
  would let a candidate carry its own set-level verdict, which is the one thing a
  review gate must make impossible;
* the Phase 40F candidate, provenance, and projection-diagnostic shapes are reused
  **unchanged**. Nothing here redefines, mirrors, or narrows a candidate; a report
  names the candidates it describes by their content-derived ``candidate_id`` and
  never embeds candidate *content*.

What this module deliberately does **not** add — Phase 40G is read-only and
non-mutating, and the durable persistence medium remains undecided and outside
this phase (that is Phase 40H):

* No persistence, database write, Active Memory insertion, durable-medium
  selection, approval/verification/activation state, or import. A report is a
  passive record; producing one changes nothing.
* No candidate deletion, deduplication that removes records, re-ranking, or
  repair. Duplicates are *grouped and counted*, never collapsed.
* No I/O, clock read, or randomness. Every derived value is a pure function of the
  model's own fields, so identical input always yields a byte-equivalent report.

The load-bearing structural decisions, mirroring the Phase 40E/40F rationale:

* **Severity is a property of the code, not of the caller.**
  :data:`MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY` maps every
  :class:`MigrationCandidateAssessmentDiagnosticCode` to a fixed
  :class:`MigrationCandidateAssessmentSeverity`, and
  :class:`MigrationCandidateAssessmentDiagnostic` fills it in — rejecting a
  supplied severity that disagrees. A conflicting-identity finding therefore
  cannot be filed as advisory by a producer that would rather not block.

* **Readiness is derived and cannot outrun the diagnostics.** Any blocking
  finding forces ``review_readiness`` to ``blocked``; any advisory finding, absent
  a blocking one, forces ``review_with_warnings``; ``ready_for_review`` is
  reachable only with neither. The report recomputes the verdict from its own
  diagnostics and rejects a value that disagrees, and an unknown/absent severity
  fails closed to ``blocked`` rather than producing a ready verdict.

* **Identity is content-derived and tamper-evident.** ``report_id``, every
  duplicate ``group_id``, and every ``conflict_id`` are pure functions of stable
  fields folded through the repository's canonical-JSON + SHA-256 convention
  (:func:`~app.models.memory_migration.derive_migration_id`). The report
  recomputes ``report_id`` from its own contents and rejects a forged or stale id,
  exactly as the Phase 40F candidate verifies its own ``candidate_id``.

* **Diagnostics and aggregates carry no raw candidate content.** Messages carry
  counts, closed-enum literals, and stable candidate-local identifiers only.
  Coverage is grouped by the *closed* role and source-type vocabularies, never by
  arbitrary caller strings, and no candidate body, export byte, or conversation
  text appears anywhere in a report.

Phase 40G assesses candidates for later human review. It does not persist,
verify, approve, activate, rank, delete, or mutate them, and the durable
persistence medium remains deliberately undecided.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.active_memory import MemorySourceType
from app.models.memory_migration import (
    MAX_MIGRATION_ID_LENGTH,
    MAX_MIGRATION_SUMMARY_LENGTH,
    MEMORY_MIGRATION_CONTRACT_VERSION,
    _canonical_material,
    derive_migration_id,
)
from app.models.memory_migration_projection import (
    MAX_MIGRATION_CANDIDATES,
    MigrationCandidateRole,
    MigrationProjectionDiagnostic,
    MigrationProjectionSeverity,
)

# --------------------------------------------------------------------------- #
# Assessment policy version.
#
# A stable identifier for the *ruleset*, deliberately separate from
# ``MEMORY_MIGRATION_CONTRACT_VERSION`` (the wire shape) and from the Phase 40E
# intake-assessment and Phase 40F parser/projection versions — the same
# separation Phase 40C/40D/40E/40F established between contract and policy
# versions. The wire contract can stay ``memory-migration.v1`` while the dry-run
# rules tighten, and a consumer can tell which ruleset produced a verdict without
# inferring it from the codes.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION = (
    "memory-migration-candidate-assessment.v1"
)

# --------------------------------------------------------------------------- #
# Bounds.
#
# A dry-run report may legitimately carry one finding per duplicate group, per
# conflict, per degenerate candidate, per ambiguous-order group, plus one per
# carried Phase 40F finding and a summary. It reuses the Phase 40F candidate
# ceiling for the collections whose size is bounded by the candidate count
# (groups, conflicts, group members), and bounds the diagnostic list on its own
# axis; overflow of the diagnostic list is *represented* by an explicit blocking
# truncation finding rather than silently dropped.
#
# ``MAX_ASSESSED_CANDIDATES`` bounds one assessment run. It equals the Phase 40F
# per-result candidate ceiling, so a candidate set assembled from well-formed
# projection results is always within it; a set beyond it is refused loudly rather
# than assessed partially, because dropping candidates to fit would defeat the
# no-deletion guarantee.
# --------------------------------------------------------------------------- #
MAX_ASSESSED_CANDIDATES = MAX_MIGRATION_CANDIDATES
MAX_CANDIDATE_ASSESSMENT_GROUPS = MAX_MIGRATION_CANDIDATES
MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS = 512


# =========================================================================== #
# Enumerations (closed vocabularies)
# =========================================================================== #
class MigrationCandidateAssessmentSeverity(StrEnum):
    """Whether a set-level finding blocks review or is merely advisory.

    Two-valued on purpose. The dry-run outcome vocabulary is three-valued
    (:class:`MigrationReviewReadiness`), but it is *derived* from these two
    severities exactly as Phase 40E's three-valued status is derived from its
    findings: any blocking finding blocks, any advisory finding (absent a blocking
    one) warns, and neither is ready.

    * ``advisory`` — visible, but the candidate set remains reviewable. Reserved
      for findings a human reviewer can weigh (an identical duplicate, an
      ambiguous ordering, a degenerate candidate, a carried non-error projection
      note).
    * ``blocking`` — the set cannot be treated as review-ready: a source identity
      resolves to conflicting content, an unresolved Phase 40F error is carried,
      or the report itself could not be fully described.

    Severity is a property of the *code* (see
    :data:`MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY`), never of the caller.
    """

    ADVISORY = "advisory"
    BLOCKING = "blocking"


class MigrationCandidateAssessmentDiagnosticCode(StrEnum):
    """Closed taxonomy of Phase 40G dry-run findings.

    Every member names a specific condition the assessor detected in the projected
    candidate set or carried forward from Phase 40F. None of them carries a
    candidate's content: a duplicate is reported as a group of ids and a shared
    content digest, never by quoting the shared text.
    """

    # Set-level candidate findings.
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    CONFLICTING_SOURCE_IDENTITY = "conflicting_source_identity"
    AMBIGUOUS_SOURCE_ORDER = "ambiguous_source_order"
    EMPTY_OR_DEGENERATE_CANDIDATE = "empty_or_degenerate_candidate"

    # Carried Phase 40F projection findings.
    UNRESOLVED_PROJECTION_ERROR = "unresolved_projection_error"
    PROJECTION_TRUNCATION_WARNING = "projection_truncation_warning"

    # Report bounding.
    DIAGNOSTICS_TRUNCATED = "diagnostics_truncated"


# --------------------------------------------------------------------------- #
# Fixed severity per code.
#
# Fail-closed: a finding is advisory only when a human reviewer can still weigh it
# with the candidate set intact. A conflicting source identity, an unresolved
# Phase 40F error, and a report that could not be fully described all block.
# --------------------------------------------------------------------------- #
MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY: dict[
    MigrationCandidateAssessmentDiagnosticCode, MigrationCandidateAssessmentSeverity
] = {
    MigrationCandidateAssessmentDiagnosticCode.DUPLICATE_CANDIDATE: (
        MigrationCandidateAssessmentSeverity.ADVISORY
    ),
    MigrationCandidateAssessmentDiagnosticCode.CONFLICTING_SOURCE_IDENTITY: (
        MigrationCandidateAssessmentSeverity.BLOCKING
    ),
    MigrationCandidateAssessmentDiagnosticCode.AMBIGUOUS_SOURCE_ORDER: (
        MigrationCandidateAssessmentSeverity.ADVISORY
    ),
    MigrationCandidateAssessmentDiagnosticCode.EMPTY_OR_DEGENERATE_CANDIDATE: (
        MigrationCandidateAssessmentSeverity.ADVISORY
    ),
    MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR: (
        MigrationCandidateAssessmentSeverity.BLOCKING
    ),
    MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING: (
        MigrationCandidateAssessmentSeverity.ADVISORY
    ),
    MigrationCandidateAssessmentDiagnosticCode.DIAGNOSTICS_TRUNCATED: (
        MigrationCandidateAssessmentSeverity.BLOCKING
    ),
}


class MigrationReviewReadiness(StrEnum):
    """The dry-run verdict on whether a candidate set is ready for human review.

    * ``ready_for_review`` — no finding requires attention; a reviewer can proceed.
    * ``review_with_warnings`` — only advisory findings; a reviewer should proceed
      with the noted duplicates, ambiguities, or degenerate candidates in mind.
    * ``blocked`` — at least one blocking finding (a source-identity conflict, an
      unresolved Phase 40F error, or a truncated report); the set is not ready.

    Derived by the report from its diagnostics and never accepted as caller input.
    """

    READY_FOR_REVIEW = "ready_for_review"
    REVIEW_WITH_WARNINGS = "review_with_warnings"
    BLOCKED = "blocked"


# --------------------------------------------------------------------------- #
# Readiness derivation.
#
# Explicit ranks rather than enum declaration order, because the mapping from
# "most severe finding" to "derived readiness" is a rule the report enforces and
# must be stated where it can be read and tested — the Phase 40E lesson that a
# result contract and its producer must not hold two divergent copies of one rule.
# --------------------------------------------------------------------------- #
_SEVERITY_RANK: dict[MigrationCandidateAssessmentSeverity, int] = {
    MigrationCandidateAssessmentSeverity.ADVISORY: 0,
    MigrationCandidateAssessmentSeverity.BLOCKING: 1,
}

_RANK_READINESS: dict[int, MigrationReviewReadiness] = {
    0: MigrationReviewReadiness.REVIEW_WITH_WARNINGS,
    1: MigrationReviewReadiness.BLOCKED,
}


def resolve_review_readiness(
    severities: list[MigrationCandidateAssessmentSeverity | None],
) -> MigrationReviewReadiness:
    """Derive the review-readiness implied by a set of finding severities.

    Pure and total, and **fail-closed**: an empty set yields ``ready_for_review``;
    otherwise the single most severe finding decides. Any severity that is
    ``None`` or not a recognized member — an internally inconsistent finding that
    should be impossible through the supported contracts — collapses the verdict
    to ``blocked`` rather than being ignored, so a broken finding can never
    produce a ready verdict.

    Shared by the report model and the assessment service so the two can never
    disagree about what a set of findings means.
    """

    if not severities:
        return MigrationReviewReadiness.READY_FOR_REVIEW
    worst = -1
    for severity in severities:
        rank = _SEVERITY_RANK.get(severity)  # type: ignore[arg-type]
        if rank is None:
            # Unknown or missing severity: fail closed rather than guess.
            return MigrationReviewReadiness.BLOCKED
        worst = max(worst, rank)
    return _RANK_READINESS[worst]


# =========================================================================== #
# Identity derivation
# =========================================================================== #
def derive_candidate_source_identity(
    *,
    bundle_fingerprint: str,
    source_artifact_fingerprint: str,
    source_local_id: str,
    source_role: str,
    source_sequence_index: int,
    chunk_index: int,
) -> str:
    """The deterministic *source identity* of one candidate slot.

    Everything that locates a candidate back to its origin **except its content**:
    which bundle, which artifact, which source-local entry, which role, which
    source position, and which chunk of a split item. Two candidates sharing this
    identity occupy the same source slot — if they also share a content digest
    they are an identical duplicate, and if they do not they are a conflict.

    Reuses :func:`~app.models.memory_migration.derive_migration_id`, which
    NFC-normalizes and strips each part before folding it through canonical JSON +
    SHA-256, so the identity is stable across input ordering and explicit about
    Unicode normalization while depending only on canonical typed fields.
    """

    return derive_migration_id(
        "mm-source",
        bundle_fingerprint,
        source_artifact_fingerprint,
        source_local_id,
        source_role,
        str(source_sequence_index),
        str(chunk_index),
    )


def derive_duplicate_group_id(*, source_identity: str, content_digest: str) -> str:
    """The deterministic identity of one duplicate group.

    A pure function of the shared source identity and content digest, so the same
    group of duplicates always carries the same id regardless of input ordering.
    """

    return derive_migration_id("mm-duplicate-group", source_identity, content_digest)


def derive_source_conflict_id(*, source_identity: str) -> str:
    """The deterministic identity of one source-identity conflict."""

    return derive_migration_id("mm-source-conflict", source_identity)


def derive_ambiguous_order_group_id(
    *,
    bundle_fingerprint: str,
    source_artifact_fingerprint: str,
    source_sequence_index: int,
) -> str:
    """The deterministic identity of one ambiguous source-order group.

    Scoped to a single bundle+artifact and a single declared sequence position:
    the collision is that more than one distinct source-local entry claims that
    position within that scope.
    """

    return derive_migration_id(
        "mm-ambiguous-order",
        bundle_fingerprint,
        source_artifact_fingerprint,
        str(source_sequence_index),
    )


# =========================================================================== #
# Shared config / helpers
# =========================================================================== #
def _require_int(value: Any) -> Any:
    """Require an actual ``int`` where a count is expected (no bool, no coercion)."""

    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValueError("integer field must be an integer")
    return value


def _require_bool(value: Any) -> Any:
    """Reject a non-``bool`` supplied where a flag is expected."""

    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


def _clean_required_text(value: str, label: str) -> str:
    """Strip and reject blank/whitespace-only required text."""

    text = value.strip()
    if not text:
        raise ValueError(f"{label} must not be empty or whitespace-only")
    return text


def _validate_lowercase_hex(value: str, label: str) -> str:
    """Require a lowercase-hex digest value, the same rule Phase 40F digests use."""

    text = _clean_required_text(value, label)
    if any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{label} must be lowercase hexadecimal")
    return text


class _AssessmentModel(BaseModel):
    """Shared config: unknown fields are rejected, never absorbed.

    ``extra="forbid"`` is the load-bearing setting on every model here, for the
    same reason it is on the Phase 40E/40F families: it stops a content-bearing,
    persistence-shaped, or authority-shaped field from riding into a report on an
    unknown key.
    """

    model_config = ConfigDict(extra="forbid")


# =========================================================================== #
# Duplicate group
# =========================================================================== #
class MigrationCandidateDuplicateGroup(_AssessmentModel):
    """One candidate that appears more than once in the assessed set.

    Because a Phase 40F ``candidate_id`` is a pure function of exactly the
    source-identity components *and* the content digest, two byte-identical
    candidates from the same source slot necessarily share a ``candidate_id``. An
    identical duplicate is therefore "one candidate id occurring N≥2 times", not a
    set of distinct ids — and it is *counted*, never removed. ``content_digest`` is
    a SHA-256 over content (a non-reversible identity fragment the Phase 40F
    candidate already exposes), never the content itself.
    """

    group_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_identity: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    content_digest: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    candidate_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    occurrence_count: int = Field(ge=2)

    @field_validator("group_id", "source_identity", "candidate_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "duplicate group identifier")

    @field_validator("content_digest")
    @classmethod
    def _digest_is_hex(cls, value: str) -> str:
        return _validate_lowercase_hex(value, "content_digest")

    @field_validator("occurrence_count", mode="before")
    @classmethod
    def _count_is_integer(cls, value: Any) -> Any:
        return _require_int(value)

    @model_validator(mode="after")
    def _validate_group(self) -> "MigrationCandidateDuplicateGroup":
        expected = derive_duplicate_group_id(
            source_identity=self.source_identity, content_digest=self.content_digest
        )
        if self.group_id != expected:
            raise ValueError(
                "group_id is not the deterministic id for this source identity and "
                "content digest"
            )
        return self

    def sort_key(self) -> tuple[str, str, str]:
        """Canonical ordering key: source identity, content digest, then group id."""

        return (self.source_identity, self.content_digest, self.group_id)


# =========================================================================== #
# Source-identity conflict
# =========================================================================== #
class MigrationSourceIdentityConflict(_AssessmentModel):
    """One source identity resolving to materially different candidate content.

    Blocking: the same source slot produced two or more distinct contents, so a
    reviewer cannot tell which is the real material without going back to the
    source. All involved candidates stay visible through their safe ids;
    ``distinct_content_digest_count`` records how many distinct contents collided
    without reproducing any of them.
    """

    conflict_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_identity: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    distinct_content_digest_count: int = Field(ge=2)
    member_candidate_ids: list[str] = Field(
        min_length=2, max_length=MAX_ASSESSED_CANDIDATES
    )
    member_count: int = Field(ge=2)

    @field_validator("conflict_id", "source_identity")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "conflict identifier")

    @field_validator("distinct_content_digest_count", "member_count", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("member_candidate_ids")
    @classmethod
    def _members_clean(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_required_text(item, "member candidate id") for item in value]
        if any(len(item) > MAX_MIGRATION_ID_LENGTH for item in cleaned):
            raise ValueError("member candidate id exceeds the id length bound")
        return cleaned

    @model_validator(mode="after")
    def _validate_conflict(self) -> "MigrationSourceIdentityConflict":
        if self.member_count != len(self.member_candidate_ids):
            raise ValueError("member_count must equal the number of member ids")
        if sorted(self.member_candidate_ids) != self.member_candidate_ids:
            raise ValueError("member_candidate_ids must be in canonical (sorted) order")
        if len(set(self.member_candidate_ids)) != len(self.member_candidate_ids):
            raise ValueError("member_candidate_ids must be unique")
        if self.distinct_content_digest_count > self.member_count:
            raise ValueError(
                "distinct_content_digest_count cannot exceed the member count"
            )
        expected = derive_source_conflict_id(source_identity=self.source_identity)
        if self.conflict_id != expected:
            raise ValueError(
                "conflict_id is not the deterministic id for this source identity"
            )
        return self

    def sort_key(self) -> tuple[str, str]:
        """Canonical ordering key: source identity, then conflict id."""

        return (self.source_identity, self.conflict_id)


# =========================================================================== #
# Diagnostic
# =========================================================================== #
class MigrationCandidateAssessmentDiagnostic(_AssessmentModel):
    """One bounded, content-free dry-run finding.

    ``severity`` is derived from ``code`` through
    :data:`MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY` and rejects a supplied value
    that disagrees — the classification belongs to the taxonomy, so a blocking
    condition cannot be downgraded at the call site. ``message`` carries counts,
    closed-enum literals, and candidate-local identifiers only, never raw candidate
    content.

    A carried Phase 40F finding is preserved verbatim in ``carried`` — the Phase
    40F diagnostic contract already guarantees content-free messages — and the
    assessment ``code`` classifies it: an ``error``-severity projection finding
    becomes :attr:`~MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR`
    (blocking) and an ``info``-severity one becomes
    :attr:`~MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING`
    (advisory). The original severity cannot be downgraded, because the mapping is
    fixed and cross-checked here.
    """

    code: MigrationCandidateAssessmentDiagnosticCode
    severity: MigrationCandidateAssessmentSeverity | None = None
    message: str = Field(min_length=1, max_length=MAX_MIGRATION_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)
    group_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)
    count: int | None = Field(default=None, ge=0)
    carried: MigrationProjectionDiagnostic | None = None

    @model_validator(mode="before")
    @classmethod
    def _severity_follows_code(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "code" not in data:
            return data
        try:
            code = MigrationCandidateAssessmentDiagnosticCode(data["code"])
        except ValueError:
            return data
        expected = MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY[code]
        supplied = data.get("severity")
        if supplied is None:
            return {**data, "severity": expected}
        if MigrationCandidateAssessmentSeverity(supplied) is not expected:
            raise ValueError(
                f"diagnostic {code.value!r} is {expected.value!r}; severity is fixed "
                "by the code and cannot be reclassified"
            )
        return data

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "diagnostic message")

    @field_validator("subject_id", "group_id")
    @classmethod
    def _identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "diagnostic identifier")

    @field_validator("count", mode="before")
    @classmethod
    def _count_is_integer(cls, value: Any) -> Any:
        return _require_int(value)

    @model_validator(mode="after")
    def _validate_carried(self) -> "MigrationCandidateAssessmentDiagnostic":
        carried_codes = {
            MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR,
            MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING,
        }
        if self.code in carried_codes:
            if self.carried is None:
                raise ValueError(
                    f"diagnostic {self.code.value!r} carries a Phase 40F finding and "
                    "requires the original diagnostic in 'carried'"
                )
            is_error = self.carried.severity is MigrationProjectionSeverity.ERROR
            expects_error = (
                self.code
                is MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR
            )
            if is_error is not expects_error:
                raise ValueError(
                    "carried projection severity disagrees with the assessment code; "
                    "an error must map to unresolved_projection_error and an info to "
                    "projection_truncation_warning"
                )
        elif self.carried is not None:
            raise ValueError(
                f"diagnostic {self.code.value!r} does not carry a Phase 40F finding; "
                "'carried' must be omitted"
            )
        return self

    @property
    def is_blocking(self) -> bool:
        """Whether this finding prevents the set reaching ``ready_for_review``."""

        return self.severity is MigrationCandidateAssessmentSeverity.BLOCKING

    def sort_key(self) -> tuple[str, str, str, int, str, tuple[str, str, str, str]]:
        """Canonical ordering key.

        Code first so related findings group, then the subject and group id, then
        the count and message, and finally the carried finding's own key so several
        carried findings sharing the same summary remain distinct and ordered.
        """

        carried_key = (
            self.carried.sort_key() if self.carried is not None else ("", "", "", "")
        )
        return (
            self.code.value,
            self.subject_id or "",
            self.group_id or "",
            self.count if self.count is not None else -1,
            self.message,
            carried_key,
        )


# =========================================================================== #
# Coverage
# =========================================================================== #
class MigrationCandidateCoverage(_AssessmentModel):
    """Deterministic, bounded aggregate visibility over the assessed candidate set.

    Only defensible aggregates, grouped by the *closed* role and source-type
    vocabularies so every key is a known enum literal and the maps are bounded and
    leak nothing. No scoring, confidence, ranking, or persisted status appears
    here — a dry run counts, it does not judge quality.
    """

    total_candidates: int = Field(ge=0)
    counts_by_role: dict[str, int] = Field(default_factory=dict)
    counts_by_source_type: dict[str, int] = Field(default_factory=dict)
    distinct_source_identity_count: int = Field(ge=0)
    duplicate_group_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)

    @field_validator(
        "total_candidates",
        "distinct_source_identity_count",
        "duplicate_group_count",
        "conflict_count",
        mode="before",
    )
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("counts_by_role")
    @classmethod
    def _roles_are_known(cls, value: dict[str, int]) -> dict[str, int]:
        return _validate_closed_count_map(
            value, {role.value for role in MigrationCandidateRole}, "role"
        )

    @field_validator("counts_by_source_type")
    @classmethod
    def _source_types_are_known(cls, value: dict[str, int]) -> dict[str, int]:
        return _validate_closed_count_map(
            value, {item.value for item in MemorySourceType}, "source type"
        )

    @model_validator(mode="after")
    def _validate_coverage(self) -> "MigrationCandidateCoverage":
        if sum(self.counts_by_role.values()) != self.total_candidates:
            raise ValueError("counts_by_role must sum to total_candidates")
        if sum(self.counts_by_source_type.values()) != self.total_candidates:
            raise ValueError("counts_by_source_type must sum to total_candidates")
        if self.distinct_source_identity_count > self.total_candidates:
            raise ValueError(
                "distinct_source_identity_count cannot exceed total_candidates"
            )
        return self


def _validate_closed_count_map(
    value: dict[str, int], allowed: set[str], label: str
) -> dict[str, int]:
    """Bound a count map to a closed key vocabulary with non-negative int counts."""

    for key, count in value.items():
        if key not in allowed:
            raise ValueError(f"unknown {label} key {key!r} in count map")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"{label} count must be a non-negative integer")
    return value


# =========================================================================== #
# The report
# =========================================================================== #
def derive_candidate_assessment_report_id(
    *,
    candidate_count: int,
    coverage: "MigrationCandidateCoverage",
    duplicate_groups: list["MigrationCandidateDuplicateGroup"],
    conflicts: list["MigrationSourceIdentityConflict"],
    diagnostics: list["MigrationCandidateAssessmentDiagnostic"],
    review_readiness: MigrationReviewReadiness,
) -> str:
    """Derive the report's deterministic, content-addressed identity.

    Folds the whole assessment content — the candidate count, coverage, the
    canonically-ordered duplicate groups, conflicts, and diagnostics, and the
    derived readiness — into one SHA-256 through the repository's canonical-JSON
    convention, then labels it with the standard readable prefix. Identical
    assessment content always yields the same id; any change to any finding
    changes it. Reused by the service to build a report and by the report model to
    verify the id it was handed.
    """

    material: list[Any] = [
        MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION,
        candidate_count,
        coverage.model_dump(mode="json"),
        [group.model_dump(mode="json") for group in duplicate_groups],
        [conflict.model_dump(mode="json") for conflict in conflicts],
        [diagnostic.model_dump(mode="json") for diagnostic in diagnostics],
        review_readiness.value,
    ]
    folded = hashlib.sha256(_canonical_material(material)).hexdigest()
    return derive_migration_id("mm-candidate-assessment", folded)


class MigrationCandidateAssessmentReport(_AssessmentModel):
    """The deterministic dry-run verdict over one projected candidate set.

    A **passive result record**. It holds no candidate content, persists nothing,
    and mutates nothing; it names the candidates it describes by their
    content-derived ids, carries bounded aggregates and findings, and stops.

    Cross-field rules make the verdict impossible to misread:

    * ``read_only`` is pinned ``True``; ``candidates_mutated`` and ``persisted``
      are pinned ``False`` and reject being turned on — Phase 40G writes nothing;
    * ``review_readiness`` equals the readiness implied by the diagnostics, and a
      blocking finding forces ``blocked``, an advisory-only set ``review_with_
      warnings``, and an empty set ``ready_for_review``;
    * coverage, ``duplicate_groups``, ``conflicts``, and the diagnostic counts are
      internally consistent with one another;
    * duplicate groups, conflicts, and diagnostics are unique and canonically
      ordered, because identical input must yield a byte-equivalent report;
    * ``report_id`` equals the id derived from the report's own contents, so a
      forged or stale id cannot be constructed.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    assessment_version: str = Field(
        default=MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION
    )
    report_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    candidate_count: int = Field(ge=0)
    coverage: MigrationCandidateCoverage
    duplicate_groups: list[MigrationCandidateDuplicateGroup] = Field(
        default_factory=list, max_length=MAX_CANDIDATE_ASSESSMENT_GROUPS
    )
    conflicts: list[MigrationSourceIdentityConflict] = Field(
        default_factory=list, max_length=MAX_CANDIDATE_ASSESSMENT_GROUPS
    )
    diagnostics: list[MigrationCandidateAssessmentDiagnostic] = Field(
        default_factory=list, max_length=MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS
    )
    diagnostic_counts_by_severity: dict[str, int] = Field(default_factory=dict)
    diagnostic_counts_by_code: dict[str, int] = Field(default_factory=dict)
    blocking_diagnostic_count: int = Field(ge=0)
    advisory_diagnostic_count: int = Field(ge=0)
    review_readiness: MigrationReviewReadiness
    read_only: bool = True
    candidates_mutated: bool = False
    persisted: bool = False

    @field_validator("schema_version")
    @classmethod
    def _contract_version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("assessment_version")
    @classmethod
    def _assessment_version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION:
            raise ValueError(
                f"unsupported assessment_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION!r}"
            )
        return value

    @field_validator("report_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "report_id")

    @field_validator(
        "candidate_count",
        "blocking_diagnostic_count",
        "advisory_diagnostic_count",
        mode="before",
    )
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("read_only", "candidates_mutated", "persisted", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("diagnostic_counts_by_severity")
    @classmethod
    def _severity_counts_known(cls, value: dict[str, int]) -> dict[str, int]:
        return _validate_closed_count_map(
            value,
            {item.value for item in MigrationCandidateAssessmentSeverity},
            "severity",
        )

    @field_validator("diagnostic_counts_by_code")
    @classmethod
    def _code_counts_known(cls, value: dict[str, int]) -> dict[str, int]:
        return _validate_closed_count_map(
            value,
            {item.value for item in MigrationCandidateAssessmentDiagnosticCode},
            "diagnostic code",
        )

    @staticmethod
    def _assert_canonical_unique(items: list[Any], label: str) -> None:
        seen: set[Any] = set()
        previous: Any = None
        for item in items:
            key = item.sort_key()
            if key in seen:
                raise ValueError(f"{label} contain a duplicate ordering key")
            if previous is not None and key < previous:
                raise ValueError(f"{label} must be in canonical order")
            seen.add(key)
            previous = key

    @model_validator(mode="after")
    def _validate_report(self) -> "MigrationCandidateAssessmentReport":
        if not self.read_only:
            raise ValueError("read_only must remain True; Phase 40G writes nothing")
        if self.candidates_mutated:
            raise ValueError(
                "candidates_mutated must remain False; Phase 40G never mutates a "
                "candidate"
            )
        if self.persisted:
            raise ValueError(
                "persisted must remain False; Phase 40G persists nothing and the "
                "durable medium remains undecided (Phase 40H)"
            )

        self._assert_canonical_unique(self.duplicate_groups, "duplicate_groups")
        self._assert_canonical_unique(self.conflicts, "conflicts")
        self._assert_canonical_unique(self.diagnostics, "diagnostics")

        # Coverage must agree with the actual groups and conflicts carried.
        if self.coverage.total_candidates != self.candidate_count:
            raise ValueError("coverage.total_candidates must equal candidate_count")
        if self.coverage.duplicate_group_count != len(self.duplicate_groups):
            raise ValueError(
                "coverage.duplicate_group_count must equal the number of duplicate "
                "groups"
            )
        if self.coverage.conflict_count != len(self.conflicts):
            raise ValueError(
                "coverage.conflict_count must equal the number of conflicts"
            )

        # Diagnostic counts must be recomputable from the diagnostics themselves.
        by_severity: dict[str, int] = {}
        by_code: dict[str, int] = {}
        blocking = 0
        advisory = 0
        for diagnostic in self.diagnostics:
            severity = diagnostic.severity
            if severity is None:
                raise ValueError("a diagnostic reached the report without a severity")
            by_severity[severity.value] = by_severity.get(severity.value, 0) + 1
            by_code[diagnostic.code.value] = by_code.get(diagnostic.code.value, 0) + 1
            if severity is MigrationCandidateAssessmentSeverity.BLOCKING:
                blocking += 1
            else:
                advisory += 1
        if self.diagnostic_counts_by_severity != by_severity:
            raise ValueError(
                "diagnostic_counts_by_severity must be recomputable from the "
                "diagnostics"
            )
        if self.diagnostic_counts_by_code != by_code:
            raise ValueError(
                "diagnostic_counts_by_code must be recomputable from the diagnostics"
            )
        if self.blocking_diagnostic_count != blocking:
            raise ValueError(
                "blocking_diagnostic_count must equal the number of blocking findings"
            )
        if self.advisory_diagnostic_count != advisory:
            raise ValueError(
                "advisory_diagnostic_count must equal the number of advisory findings"
            )

        # Readiness is derived from the diagnostics and cannot be asserted.
        implied = resolve_review_readiness(
            [diagnostic.severity for diagnostic in self.diagnostics]
        )
        if self.review_readiness is not implied:
            raise ValueError(
                f"review_readiness {self.review_readiness.value!r} disagrees with the "
                f"readiness implied by the diagnostics ({implied.value!r})"
            )

        # Identity is content-addressed and verified in construction.
        expected_id = derive_candidate_assessment_report_id(
            candidate_count=self.candidate_count,
            coverage=self.coverage,
            duplicate_groups=self.duplicate_groups,
            conflicts=self.conflicts,
            diagnostics=self.diagnostics,
            review_readiness=self.review_readiness,
        )
        if self.report_id != expected_id:
            raise ValueError(
                "report_id is not the deterministic id for this report's contents"
            )
        return self

    @property
    def is_ready_for_review(self) -> bool:
        """Whether the set reached ``ready_for_review``."""

        return self.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW

    @property
    def blocking_diagnostics(self) -> list[MigrationCandidateAssessmentDiagnostic]:
        """Blocking findings, in canonical order."""

        return [item for item in self.diagnostics if item.is_blocking]
