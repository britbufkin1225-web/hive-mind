"""Phase 40F — Memory Migration parsing/projection result contracts.

The typed **result** shapes for the first memory-migration phase permitted to
read user-controlled artifact bytes. Where Phase 40E described what the user
*declared* and what Hive|Mind *concluded* about that declaration, this module
describes what a parser *interpreted* from the actual bytes and the bounded,
provenance-linked **candidates** projected from it.

A deliberate *separate module* from ``app.models.memory_migration`` and
``app.models.memory_migration_assessment``, following the same Phase 40B/40D/40E
split: the declaration contracts and the assessment result stay untouched, and
this module names them by reference rather than redefining, mirroring, or
narrowing any of them. The Phase 40E contracts are consumed exactly as shipped.

Everything here is a **pure data shape**. No model in this module reads a byte,
opens a file, extracts an archive, reads a clock, or generates a random value —
that all lives in :mod:`app.services.memory_migration_parser`, the only Phase 40F
component permitted I/O. The projector
(:mod:`app.services.memory_migration_projection`) that turns parsed items into
these candidate records is likewise pure and deterministic.

The load-bearing structural decisions:

* **A candidate is not a ``MemoryRecord``.** Phase 40E deliberately refused to
  reuse the permissive Active Memory record models, because a ``MemoryRecord`` can
  be constructed ``active`` and ``human_confirmed`` — exactly the standing a
  migration candidate must be *structurally incapable* of holding.
  :class:`MemoryMigrationCandidate` therefore pins the five candidate-standing
  fields to the values in :data:`~app.models.memory_migration.CANDIDATE_MEMORY_POLICY`,
  rejects any other value, and additionally cross-checks itself against that
  policy so a candidate can never disagree with the ceiling the migration track
  set in Phase 40E. Parsing is interpretation, not activation.

* **Byte integrity is not factual truth.** :class:`VerifiedArtifactIntegrity`
  records that *these bytes match the bytes the user declared* — a recomputed
  digest over material actually read. It says nothing about whether the
  statements inside those bytes are true. The two are kept in separate fields on
  separate models so no consumer can read "integrity verified" as "claim
  verified": every candidate stays ``unverified`` no matter how cleanly its
  source artifact hashed.

* **Identity is content-derived and deterministic.** A candidate's id and content
  digest are pure functions of stable source material (bundle fingerprint,
  artifact fingerprint, source-local identifier, role, chunk index, and the
  content itself) folded through the repository's canonical-JSON + SHA-256
  convention. Nothing reads a clock, a random source, or object identity, so
  identical bytes and configuration always yield byte-equivalent candidates in
  the same canonical order.

* **Bounds are honest, never silent.** Candidate content is bounded; when a
  parsed item exceeds the bound it is split into deterministically-ordered chunks
  carrying explicit chunk metadata, and overflow beyond the chunk ceiling is
  represented by a typed diagnostic rather than a silent truncation. Candidate
  *count* overflow is likewise represented, never hidden by dropping records to
  fit.

* **Diagnostics carry no exported content.** The projection diagnostic vocabulary
  is closed and its severity is fixed per code, not caller-controlled. Messages
  carry counts, closed-enum literals, and declaration-local identifiers only —
  never raw exported conversation text, a declared path, a digest value, or any
  other caller-supplied string, for the same reason Phase 40E refused to echo
  declared values: the material this phase reads is the material most likely to be
  sensitive.

Phase 40F stops at candidates. It persists nothing, inserts nothing into Active
Memory, activates nothing, and confirms nothing. Reviewed persistence is the
exclusive Phase 40G boundary, and :class:`MemoryMigrationProjectionResult` pins
``persisted`` and ``imported`` to ``False`` and rejects being turned on.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.active_memory import (
    LifecycleState,
    MemoryScope,
    MemorySource,
    VerificationState,
)
from app.models.memory_migration import (
    CANDIDATE_MEMORY_POLICY,
    MAX_MIGRATION_ID_LENGTH,
    MAX_MIGRATION_LABEL_LENGTH,
    MAX_MIGRATION_SUMMARY_LENGTH,
    MEMORY_MIGRATION_CONTRACT_VERSION,
    CandidateMemoryPolicy,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
    _validate_bounded_metadata,
    derive_migration_id,
)

# --------------------------------------------------------------------------- #
# Policy versions.
#
# Three stable identifiers, deliberately separate from the wire contract version
# (``memory-migration.v1``) and from each other, mirroring the Phase 40C/40D/40E
# separation of contract / assessment / intake-policy versions:
#
# * the parser version identifies the ruleset that read and interpreted bytes;
# * the projection version identifies the ruleset that turned parsed items into
#   candidates;
# * the curated version versions the one structured input shape this phase adds.
#
# A consumer can tell which ruleset produced a candidate without inferring it, and
# either can tighten without a wire-contract change.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_PARSER_VERSION = "memory-migration-parser.v1"
MEMORY_MIGRATION_PROJECTION_VERSION = "memory-migration-projection.v1"
MEMORY_MIGRATION_CURATED_VERSION = "memory-migration-curated.v1"


# --------------------------------------------------------------------------- #
# Bounds.
#
# ``MAX_CANDIDATE_CONTENT_CHARS`` is the ceiling on one reviewable candidate's
# content. A single exported message longer than this is split into ordered
# chunks rather than truncated, so a Phase 40G reviewer sees the whole message
# across bounded pieces.
#
# ``MAX_CANDIDATE_CHUNKS_PER_ITEM`` caps how many chunks a single source item may
# produce, so one pathological message cannot expand into an unbounded candidate
# set. ``MAX_PARSED_ITEM_CHARS`` is the derived per-item text ceiling the parser
# applies before projection; content beyond it is reported as overflow, never
# silently dropped.
#
# ``MAX_MIGRATION_CANDIDATES`` bounds the whole projection run. Reaching it is
# represented by a typed count-overflow diagnostic; candidates are never dropped
# merely to fit.
# --------------------------------------------------------------------------- #
MAX_CANDIDATE_CONTENT_CHARS = 4096
MAX_CANDIDATE_CHUNKS_PER_ITEM = 64
MAX_PARSED_ITEM_CHARS = MAX_CANDIDATE_CONTENT_CHARS * MAX_CANDIDATE_CHUNKS_PER_ITEM
MAX_MIGRATION_CANDIDATES = 4096
MAX_MIGRATION_PROJECTION_DIAGNOSTICS = 512
MAX_CURATED_BUNDLE_ENTRIES = 4096


# =========================================================================== #
# Enumerations (closed wire vocabularies)
# =========================================================================== #
class MigrationCandidateRole(StrEnum):
    """The source role a candidate's content came from.

    Closed on purpose and deliberately narrow. Only conversational content the
    user can actually see — ``user`` and ``assistant`` turns — and
    user-authored documents become candidates. There is no ``system``, ``tool``,
    or ``developer`` member: internal, tool, and system-role material is skipped
    at the parser with a typed diagnostic and never reaches a candidate, so a
    vocabulary able to name it here would imply a standing it must never have.

    ``document`` covers a whole plain-text or Markdown artifact; ``curated_entry``
    covers one entry in a user-assembled curated bundle whose role was not
    otherwise specified.
    """

    USER = "user"
    ASSISTANT = "assistant"
    DOCUMENT = "document"
    CURATED_ENTRY = "curated_entry"


class MigrationProjectionSeverity(StrEnum):
    """Whether a finding stopped work or merely recorded a bounded skip.

    * ``info`` — an individual source item was skipped or a bound was reached, and
      the rest of the run proceeded. The candidate set is still usable; it is just
      honestly incomplete in the way the finding names.
    * ``error`` — an artifact produced no candidates, or the whole run could not
      proceed (the assessment gate rejected it, an archive was unsafe, a digest
      mismatched). The finding explains why nothing was produced from that scope.

    Severity is a property of the *code* (see :data:`MIGRATION_PROJECTION_SEVERITY`),
    never of the caller — the same fail-closed classification decision Phase 40E
    made for its intake diagnostics.
    """

    INFO = "info"
    ERROR = "error"


class MigrationProjectionDiagnosticCode(StrEnum):
    """Closed taxonomy of Phase 40F parsing/projection findings.

    Every member names a specific condition the parser or projector encountered.
    None of them carries the offending value: a malformed message is reported as
    malformed, never by quoting it.
    """

    # Authorization and staleness (no bytes are read on any of these).
    ASSESSMENT_GATE_REJECTED = "assessment_gate_rejected"
    STALE_ASSESSMENT = "stale_assessment"

    # Byte access and integrity.
    ARTIFACT_SOURCE_MISSING = "artifact_source_missing"
    ACTUAL_SIZE_MISMATCH = "actual_size_mismatch"
    DIGEST_MISMATCH = "digest_mismatch"

    # Format / container dispatch.
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_CONTAINER = "unsupported_container"

    # Archive safety and bounds.
    ARCHIVE_SAFETY_VIOLATION = "archive_safety_violation"
    ARCHIVE_BOUND_EXCEEDED = "archive_bound_exceeded"
    ARCHIVE_MEMBER_MISSING = "archive_member_missing"

    # Structural parsing.
    DECODE_ERROR = "decode_error"
    MALFORMED_JSON = "malformed_json"
    UNSUPPORTED_JSON_SHAPE = "unsupported_json_shape"
    MALFORMED_CONVERSATION = "malformed_conversation"
    MALFORMED_MESSAGE = "malformed_message"
    UNSUPPORTED_MESSAGE_ROLE = "unsupported_message_role"
    NON_TEXT_CONTENT_SKIPPED = "non_text_content_skipped"
    EMPTY_CONTENT_SKIPPED = "empty_content_skipped"

    # Bounds/overflow.
    CANDIDATE_CONTENT_OVERFLOW = "candidate_content_overflow"
    CANDIDATE_COUNT_OVERFLOW = "candidate_count_overflow"

    # Catch-all and result bounding.
    PROJECTION_FAILURE = "projection_failure"
    DIAGNOSTICS_TRUNCATED = "diagnostics_truncated"


# --------------------------------------------------------------------------- #
# Fixed severity per code.
#
# Fail-closed: a finding is ``info`` only when the run genuinely continued past it
# with a usable (if honestly incomplete) result. Everything that stopped an
# artifact or the whole run is ``error``.
# --------------------------------------------------------------------------- #
MIGRATION_PROJECTION_SEVERITY: dict[
    MigrationProjectionDiagnosticCode, MigrationProjectionSeverity
] = {
    MigrationProjectionDiagnosticCode.ASSESSMENT_GATE_REJECTED: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.STALE_ASSESSMENT: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.ARTIFACT_SOURCE_MISSING: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.ACTUAL_SIZE_MISMATCH: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.DIGEST_MISMATCH: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.UNSUPPORTED_FORMAT: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.UNSUPPORTED_CONTAINER: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.ARCHIVE_MEMBER_MISSING: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.DECODE_ERROR: MigrationProjectionSeverity.ERROR,
    MigrationProjectionDiagnosticCode.MALFORMED_JSON: MigrationProjectionSeverity.ERROR,
    MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.MALFORMED_CONVERSATION: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.MALFORMED_MESSAGE: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.UNSUPPORTED_MESSAGE_ROLE: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.NON_TEXT_CONTENT_SKIPPED: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.EMPTY_CONTENT_SKIPPED: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.CANDIDATE_COUNT_OVERFLOW: (
        MigrationProjectionSeverity.INFO
    ),
    MigrationProjectionDiagnosticCode.PROJECTION_FAILURE: (
        MigrationProjectionSeverity.ERROR
    ),
    MigrationProjectionDiagnosticCode.DIAGNOSTICS_TRUNCATED: (
        MigrationProjectionSeverity.ERROR
    ),
}


# =========================================================================== #
# Shared helpers and config
# =========================================================================== #
def _require_int(value: Any) -> Any:
    """Require an actual ``int`` where an integer is expected (no bool, no coercion)."""

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
    """Require a lowercase-hex digest value, the same rule the declared digest uses."""

    text = _clean_required_text(value, label)
    if any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{label} must be lowercase hexadecimal")
    return text


def derive_candidate_content_digest(content: str) -> str:
    """The deterministic content identity of one candidate's bounded content.

    A pure SHA-256 over the UTF-8 bytes of the content. It is *content* identity —
    two candidates carrying byte-identical content share a digest — while the
    candidate id additionally folds in provenance so distinct source entries never
    collapse merely because their text matches.
    """

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def derive_candidate_id(
    *,
    bundle_fingerprint: str,
    artifact_fingerprint: str,
    source_local_id: str,
    role: str,
    source_sequence_index: int,
    chunk_index: int,
    content_digest: str,
) -> str:
    """Derive a candidate's deterministic identity from stable source material.

    Reuses the repository's :func:`~app.models.memory_migration.derive_migration_id`
    convention (readable prefix + bounded canonical-JSON SHA-256) rather than
    inventing a scheme. The material deliberately includes both the bundle and
    artifact fingerprints (which bundle / which bytes), the source-local id and
    role (which entry), the chunk index (which piece of a split item), and the
    content digest (what it says). Identical inputs always yield the same id; any
    change to the source material changes it.
    """

    return derive_migration_id(
        "mm-candidate",
        bundle_fingerprint,
        artifact_fingerprint,
        source_local_id,
        role,
        str(source_sequence_index),
        str(chunk_index),
        content_digest,
    )


class _ProjectionModel(BaseModel):
    """Shared config: unknown fields are rejected, never absorbed.

    ``extra="forbid"`` is the load-bearing setting on every model here for the
    same reason it is on the Phase 40E family — it is what stops a byte-bearing
    field, a credential, or an activation/persistence directive from riding into a
    candidate or a curated input on an unknown key.
    """

    model_config = ConfigDict(extra="forbid")

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> "_ProjectionModel":
        """Copy through validation so updates cannot bypass pinned invariants."""

        copied = super().model_copy(update=update, deep=deep)
        return self.__class__.model_validate(copied.model_dump())


# =========================================================================== #
# Curated input contract
# =========================================================================== #
class CuratedMigrationEntry(_ProjectionModel):
    """One entry in a user-assembled ``curated_json_bundle``.

    A *bounded, versioned, structured* shape — but still unverified imported
    material. ``extra="forbid"`` is what makes it incapable of asserting
    verification, activation, approval, or persistence: a curated file cannot
    smuggle a ``verified``/``active``/``persist`` field, because any field this
    model does not name is rejected. A curated input is granted no stronger
    standing merely because the user assembled it by hand.

    ``role`` is optional and defaults to ``curated_entry``; a caller may mark an
    entry as ``user``/``assistant``/``document`` when it genuinely reproduces one,
    but the projector applies the same candidate ceiling regardless.
    """

    entry_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    text: str = Field(min_length=1, max_length=MAX_PARSED_ITEM_CHARS)
    role: MigrationCandidateRole = MigrationCandidateRole.CURATED_ENTRY
    timestamp: datetime | None = None
    label: str | None = Field(default=None, max_length=MAX_MIGRATION_LABEL_LENGTH)

    @field_validator("entry_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "entry_id")

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("curated entry text must not be blank")
        return value

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "curated entry label")


class CuratedMigrationBundleDocument(_ProjectionModel):
    """The top-level shape of a ``curated_json_bundle`` artifact.

    Versioned by :data:`MEMORY_MIGRATION_CURATED_VERSION` and pinned to it, so a
    later curated shape cannot be read by this parser without an explicit version
    bump. Entries are bounded and their identifiers must be unique — duplicate
    entry ids would make a candidate's provenance ambiguous about which entry it
    came from.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CURATED_VERSION)
    entries: list[CuratedMigrationEntry] = Field(
        default_factory=list, max_length=MAX_CURATED_BUNDLE_ENTRIES
    )

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CURATED_VERSION:
            raise ValueError(
                f"unsupported curated schema_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CURATED_VERSION!r}"
            )
        return value

    @model_validator(mode="after")
    def _entries_unique(self) -> "CuratedMigrationBundleDocument":
        ids = [entry.entry_id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError("curated bundle entries contain duplicate entry_id values")
        return self


# =========================================================================== #
# Parsed intermediate item (parser -> projector boundary)
# =========================================================================== #
class ParsedMigrationItem(_ProjectionModel):
    """One bounded unit of interpreted content, before projection into a candidate.

    The clean boundary between the *only* I/O-bearing Phase 40F component (the
    parser) and the pure projector: the parser produces these from bytes it has
    already read and integrity-verified, and the projector consumes them without
    ever reopening a file, reading a clock, or touching the environment.

    ``content`` is bounded at :data:`MAX_PARSED_ITEM_CHARS` by the parser;
    ``original_content_length`` records the length before that cap so the projector
    can represent overflow honestly instead of silently truncating.
    ``source_sequence_index`` is the deterministic position of this item within its
    artifact, assigned by the parser from a stable traversal so the projector never
    has to rely on JSON object insertion order.
    """

    artifact_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    artifact_fingerprint: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_local_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_container_id: str | None = Field(
        default=None, max_length=MAX_MIGRATION_ID_LENGTH
    )
    source_entry_id: str | None = Field(
        default=None, max_length=MAX_MIGRATION_ID_LENGTH
    )
    role: MigrationCandidateRole
    source_sequence_index: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=MAX_PARSED_ITEM_CHARS)
    original_content_length: int = Field(ge=0)
    declared_source_timestamp: datetime | None = None

    @field_validator("artifact_id", "artifact_fingerprint", "source_local_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "parsed item identifier")

    @field_validator("source_container_id", "source_entry_id")
    @classmethod
    def _optional_identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "parsed item identifier")

    @field_validator("source_sequence_index", "original_content_length", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @model_validator(mode="after")
    def _validate_item(self) -> "ParsedMigrationItem":
        if not self.content.strip():
            raise ValueError("parsed item content must not be blank")
        if self.original_content_length < len(self.content):
            raise ValueError(
                "original_content_length cannot be smaller than the bounded content"
            )
        return self


# =========================================================================== #
# Verified artifact integrity (Phase 40F measured-integrity result)
# =========================================================================== #
class VerifiedArtifactIntegrity(_ProjectionModel):
    """A measured, verified integrity result for one artifact's actual bytes.

    Distinct from the Phase 40E :class:`~app.models.memory_migration.DeclaredArtifactDigest`
    on purpose: that declaration pins ``verified`` to ``False`` and Phase 40F must
    not rewrite it. This is the Phase 40F *result* shape instead — it records that
    the bytes actually read hashed to the value the user declared, under an
    accepted algorithm, at the declared size.

    ``integrity_verified`` is pinned ``True`` and rejects ``False``: this record
    only ever describes an artifact that passed. A mismatch produces a typed
    diagnostic and no integrity record, never a record asserting failure. And
    integrity verified here means *these bytes match the declared bytes* — it makes
    no claim about the truth of anything the bytes say.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    artifact_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    artifact_fingerprint: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    algorithm: MigrationDigestAlgorithm
    declared_digest_value: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    observed_digest_value: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    declared_byte_size: int | None = Field(default=None, ge=0)
    observed_byte_size: int = Field(ge=0)
    integrity_verified: bool = True

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("artifact_id", "artifact_fingerprint")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "integrity identifier")

    @field_validator("declared_digest_value", "observed_digest_value")
    @classmethod
    def _digest_is_hex(cls, value: str) -> str:
        return _validate_lowercase_hex(value, "digest value")

    @field_validator("declared_byte_size", "observed_byte_size", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("integrity_verified", mode="before")
    @classmethod
    def _flag_is_boolean(cls, value: Any) -> Any:
        return _require_bool(value)

    @model_validator(mode="after")
    def _validate_integrity(self) -> "VerifiedArtifactIntegrity":
        if not self.integrity_verified:
            raise ValueError(
                "integrity_verified must remain True; a mismatch is reported as a "
                "diagnostic and produces no integrity record"
            )
        if self.observed_digest_value != self.declared_digest_value:
            raise ValueError(
                "a verified integrity result requires observed and declared digests "
                "to match"
            )
        if (
            self.declared_byte_size is not None
            and self.declared_byte_size != self.observed_byte_size
        ):
            raise ValueError(
                "a verified integrity result requires observed and declared sizes "
                "to match"
            )
        return self


# =========================================================================== #
# Candidate provenance
# =========================================================================== #
class MigrationCandidateProvenance(_ProjectionModel):
    """The complete traceability chain from a candidate back to verified bytes.

    Designed so a Phase 40G reviewer can answer, for any candidate: which
    user-provided bundle, which artifact, which verified byte stream, which
    conversation/document/entry, which source role, which source timestamp, and
    which parser/projection policy produced it — without reopening anything.

    ``integrity_verified`` is pinned ``True``: a candidate cannot exist unless the
    bytes it came from matched their declared digest, so its provenance always
    references a verified byte stream (named by ``observed_digest_*``).
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    bundle_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    bundle_fingerprint: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_artifact_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_artifact_fingerprint: str = Field(
        min_length=1, max_length=MAX_MIGRATION_ID_LENGTH
    )
    source_artifact_format: MigrationArtifactFormat
    source_container: MigrationContainerKind
    integrity_verified: bool = True
    observed_digest_algorithm: MigrationDigestAlgorithm
    observed_digest_value: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    custody: MigrationCustodyKind
    source: MemorySource
    source_local_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    source_container_id: str | None = Field(
        default=None, max_length=MAX_MIGRATION_ID_LENGTH
    )
    source_entry_id: str | None = Field(
        default=None, max_length=MAX_MIGRATION_ID_LENGTH
    )
    source_role: MigrationCandidateRole
    declared_source_timestamp: datetime | None = None
    parser_version: str = Field(default=MEMORY_MIGRATION_PARSER_VERSION)
    projection_version: str = Field(default=MEMORY_MIGRATION_PROJECTION_VERSION)
    candidate_policy_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)

    @field_validator(
        "bundle_id",
        "bundle_fingerprint",
        "source_artifact_id",
        "source_artifact_fingerprint",
        "source_local_id",
    )
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "provenance identifier")

    @field_validator("source_container_id", "source_entry_id")
    @classmethod
    def _optional_identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "provenance identifier")

    @field_validator("observed_digest_value")
    @classmethod
    def _digest_is_hex(cls, value: str) -> str:
        return _validate_lowercase_hex(value, "observed digest value")

    @field_validator("integrity_verified", mode="before")
    @classmethod
    def _flag_is_boolean(cls, value: Any) -> Any:
        return _require_bool(value)

    @model_validator(mode="after")
    def _validate_provenance(self) -> "MigrationCandidateProvenance":
        if not self.integrity_verified:
            raise ValueError(
                "integrity_verified must remain True; a candidate only exists for "
                "bytes whose declared digest was confirmed"
            )
        return self


# =========================================================================== #
# The candidate record
# =========================================================================== #
class MemoryMigrationCandidate(_ProjectionModel):
    """One bounded, provenance-linked candidate projected from verified bytes.

    Structurally incapable of exceeding
    :data:`~app.models.memory_migration.CANDIDATE_MEMORY_POLICY`. The five
    candidate-standing fields are pinned and reject any other value, and the model
    additionally cross-checks itself against ``CANDIDATE_MEMORY_POLICY`` so a
    candidate can never disagree with the ceiling the migration track fixed in
    Phase 40E:

    * ``lifecycle_state`` is ``inactive`` — never part of the active baseline;
    * ``verification_state`` is ``unverified`` — parsing is not verification;
    * ``represents_active_memory`` is ``False`` — a candidate never stands in for
      an approved record;
    * ``human_review_required`` is ``True``;
    * ``persistable`` is ``False`` — Phase 40G is the exclusive persistence
      boundary.

    No caller can override these. A candidate is emphatically **not** a
    :class:`~app.models.active_memory.MemoryRecord`: it carries no
    ``MemoryRecordKind``, no evidence, no confidence, and cannot be constructed
    active or human-confirmed.

    Identity is verified in construction: ``content_digest`` must equal the digest
    derived from ``content``, and ``candidate_id`` must equal the id derived from
    the provenance, role, chunk index, and content digest. A candidate carrying a
    forged or stale id therefore cannot be built at all.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    candidate_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    content: str = Field(min_length=1, max_length=MAX_CANDIDATE_CONTENT_CHARS)
    content_digest: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    chunk_index: int = Field(ge=0)
    chunk_count: int = Field(ge=1)
    source_sequence_index: int = Field(ge=0)
    content_truncated: bool = False
    provenance: MigrationCandidateProvenance
    target_scope: MemoryScope | None = None
    policy: CandidateMemoryPolicy = Field(default_factory=lambda: CANDIDATE_MEMORY_POLICY)
    lifecycle_state: LifecycleState = LifecycleState.INACTIVE
    verification_state: VerificationState = VerificationState.UNVERIFIED
    represents_active_memory: bool = False
    human_review_required: bool = True
    persistable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("candidate_id", "content_digest")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "candidate identifier")

    @field_validator("content_digest")
    @classmethod
    def _digest_is_hex(cls, value: str) -> str:
        return _validate_lowercase_hex(value, "content_digest")

    @field_validator("chunk_index", "chunk_count", "source_sequence_index", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator(
        "represents_active_memory",
        "human_review_required",
        "persistable",
        "content_truncated",
        mode="before",
    )
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    @model_validator(mode="after")
    def _validate_candidate(self) -> "MemoryMigrationCandidate":
        # The candidate-standing ceiling. Pinned here *and* cross-checked against
        # the canonical policy so the two can never drift: a widened policy or a
        # widened candidate would both be caught.
        if self.lifecycle_state is not LifecycleState.INACTIVE:
            raise ValueError("candidate lifecycle_state must remain 'inactive'")
        if self.verification_state is not VerificationState.UNVERIFIED:
            raise ValueError("candidate verification_state must remain 'unverified'")
        if self.represents_active_memory:
            raise ValueError("represents_active_memory must remain False")
        if not self.human_review_required:
            raise ValueError("human_review_required must remain True")
        if self.persistable:
            raise ValueError(
                "persistable must remain False; Phase 40G is the exclusive "
                "reviewed-persistence boundary"
            )
        if (
            self.policy.lifecycle_state is not CANDIDATE_MEMORY_POLICY.lifecycle_state
            or self.policy.verification_state
            is not CANDIDATE_MEMORY_POLICY.verification_state
            or self.policy.represents_active_memory
            != CANDIDATE_MEMORY_POLICY.represents_active_memory
            or self.policy.human_review_required
            != CANDIDATE_MEMORY_POLICY.human_review_required
            or self.policy.persistable != CANDIDATE_MEMORY_POLICY.persistable
        ):
            raise ValueError(
                "candidate policy disagrees with CANDIDATE_MEMORY_POLICY; candidate "
                "construction fails closed"
            )
        # The candidate's own standing must equal the policy it carries. This is
        # what makes the candidate structurally incapable of exceeding the policy.
        if (
            self.lifecycle_state is not self.policy.lifecycle_state
            or self.verification_state is not self.policy.verification_state
            or self.represents_active_memory != self.policy.represents_active_memory
            or self.human_review_required != self.policy.human_review_required
            or self.persistable != self.policy.persistable
        ):
            raise ValueError("candidate standing disagrees with its own policy")

        if self.chunk_index >= self.chunk_count:
            raise ValueError("chunk_index must be less than chunk_count")

        expected_digest = derive_candidate_content_digest(self.content)
        if self.content_digest != expected_digest:
            raise ValueError("content_digest does not match content")

        expected_id = derive_candidate_id(
            bundle_fingerprint=self.provenance.bundle_fingerprint,
            artifact_fingerprint=self.provenance.source_artifact_fingerprint,
            source_local_id=self.provenance.source_local_id,
            role=self.provenance.source_role.value,
            source_sequence_index=self.source_sequence_index,
            chunk_index=self.chunk_index,
            content_digest=self.content_digest,
        )
        if self.candidate_id != expected_id:
            raise ValueError(
                "candidate_id is not the deterministic id for this provenance, role, "
                "chunk, and content"
            )
        return self

    def sort_key(self) -> tuple[str, int, int, str]:
        """Canonical ordering key: artifact, source position, chunk, then id.

        Deterministic and independent of the order source entries happened to
        appear in the input, because ``source_sequence_index`` was assigned by a
        stable traversal in the parser.
        """

        return (
            self.provenance.source_artifact_id,
            self.source_sequence_index,
            self.chunk_index,
            self.candidate_id,
        )


# =========================================================================== #
# Projection diagnostic
# =========================================================================== #
class MigrationProjectionDiagnostic(_ProjectionModel):
    """One bounded, content-free parsing/projection finding.

    ``severity`` is derived from ``code`` through
    :data:`MIGRATION_PROJECTION_SEVERITY` and rejects a supplied value that
    disagrees — the classification belongs to the taxonomy, exactly as in Phase
    40E. ``message`` carries counts, closed-enum literals, and declaration-local
    identifiers only, never raw exported content or a caller-supplied path/digest.
    ``count`` optionally records how many items a finding summarizes (e.g. skipped
    messages) without naming any of them.
    """

    code: MigrationProjectionDiagnosticCode
    severity: MigrationProjectionSeverity | None = None
    message: str = Field(min_length=1, max_length=MAX_MIGRATION_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)
    artifact_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)
    count: int | None = Field(default=None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def _severity_follows_code(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "code" not in data:
            return data
        try:
            code = MigrationProjectionDiagnosticCode(data["code"])
        except ValueError:
            return data
        expected = MIGRATION_PROJECTION_SEVERITY[code]
        supplied = data.get("severity")
        if supplied is None:
            return {**data, "severity": expected}
        if MigrationProjectionSeverity(supplied) is not expected:
            raise ValueError(
                f"diagnostic {code.value!r} is {expected.value!r}; severity is fixed "
                "by the code and cannot be reclassified"
            )
        return data

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "diagnostic message")

    @field_validator("subject_id", "artifact_id")
    @classmethod
    def _identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "diagnostic identifier")

    @field_validator("count", mode="before")
    @classmethod
    def _count_is_integer(cls, value: Any) -> Any:
        return _require_int(value)

    @property
    def is_error(self) -> bool:
        """Whether this finding stopped an artifact or the whole run."""

        return self.severity is MigrationProjectionSeverity.ERROR

    def sort_key(self) -> tuple[str, str, str, str]:
        """Canonical ordering key: code, artifact, subject, then message."""

        return (
            self.code.value,
            self.artifact_id or "",
            self.subject_id or "",
            self.message,
        )


# =========================================================================== #
# The projection result
# =========================================================================== #
class MemoryMigrationProjectionResult(_ProjectionModel):
    """The deterministic outcome of parsing one bundle and projecting candidates.

    A **passive result record**. It carries candidates and bounded diagnostics and
    stops. ``persisted`` and ``imported`` are pinned ``False`` and reject being
    turned on: Phase 40F never persists a candidate or imports one into Active
    Memory, and a result asserting otherwise would misrepresent the boundary to
    every consumer downstream. ``gate_permitted`` records whether the Phase 40E
    authorization gate allowed byte access at all — when it is ``False``, no bytes
    were read, ``artifacts_read`` is zero, and there are no candidates.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    parser_version: str = Field(default=MEMORY_MIGRATION_PARSER_VERSION)
    projection_version: str = Field(default=MEMORY_MIGRATION_PROJECTION_VERSION)
    bundle_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    bundle_fingerprint: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    assessment_bundle_fingerprint: str = Field(
        min_length=1, max_length=MAX_MIGRATION_ID_LENGTH
    )
    gate_permitted: bool
    artifacts_read: int = Field(ge=0)
    integrity_results: list[VerifiedArtifactIntegrity] = Field(default_factory=list)
    candidates: list[MemoryMigrationCandidate] = Field(
        default_factory=list, max_length=MAX_MIGRATION_CANDIDATES
    )
    diagnostics: list[MigrationProjectionDiagnostic] = Field(
        default_factory=list, max_length=MAX_MIGRATION_PROJECTION_DIAGNOSTICS
    )
    persisted: bool = False
    imported: bool = False

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        if value != MEMORY_MIGRATION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("bundle_id", "bundle_fingerprint", "assessment_bundle_fingerprint")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "result identifier")

    @field_validator("artifacts_read", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("gate_permitted", "persisted", "imported", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @model_validator(mode="after")
    def _validate_result(self) -> "MemoryMigrationProjectionResult":
        if self.persisted:
            raise ValueError(
                "persisted must remain False; Phase 40F never persists a candidate"
            )
        if self.imported:
            raise ValueError(
                "imported must remain False; importing into Active Memory is the "
                "exclusive Phase 40G boundary"
            )
        if not self.gate_permitted and (
            self.candidates or self.integrity_results or self.artifacts_read
        ):
            raise ValueError(
                "a rejected authorization gate must read no bytes and produce no "
                "candidates or integrity results"
            )

        seen: set[tuple[str, int, int, str]] = set()
        previous: tuple[str, int, int, str] | None = None
        for candidate in self.candidates:
            key = candidate.sort_key()
            if key in seen:
                raise ValueError("candidates contain a duplicate ordering key")
            if previous is not None and key < previous:
                raise ValueError("candidates must be in canonical order")
            seen.add(key)
            previous = key

        diag_seen: set[tuple[str, str, str, str]] = set()
        diag_previous: tuple[str, str, str, str] | None = None
        for diagnostic in self.diagnostics:
            key = diagnostic.sort_key()
            if key in diag_seen:
                raise ValueError("diagnostics contain a duplicate ordering key")
            if diag_previous is not None and key < diag_previous:
                raise ValueError("diagnostics must be in canonical order")
            diag_seen.add(key)
            diag_previous = key
        return self
