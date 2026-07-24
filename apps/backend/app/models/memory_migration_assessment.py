"""Phase 40E — Memory Migration intake assessment result contracts.

The typed **result** shapes for the Phase 40E intake-safety boundary: a closed
diagnostic taxonomy, a three-valued severity axis fixed by the code, one bounded
diagnostic record, and the assessment report that carries an explicit derived
intake status.

Deliberately a *separate module* rather than an extension of
``app.models.memory_migration``, following the Phase 40B/40D split exactly:

* the declaration contracts describe what the **user** hands over; this module
  describes what **Hive|Mind concluded** about it. Merging them would let a
  declaration carry its own verdict, which is the one thing the intake boundary
  must make impossible;
* the Phase 40E declaration shapes are reused **unchanged**. Nothing here
  redefines, mirrors, or narrows a bundle, artifact descriptor, digest, or
  provenance record; a report names the bundle it describes by identifier and
  fingerprint and never embeds one.

What this module deliberately does **not** add:

* No parsed content, extracted entry list, candidate record, or repaired
  declaration. A report describes; it never produces or corrects.
* No lifecycle state beyond the four Phase 40E members. There is no ``parsed``,
  ``projected``, ``reviewed``, ``approved``, ``persisted``, or ``verified``
  outcome to report, because no code in this phase can reach one.
* No I/O, clock read, or randomness. Every field is caller-supplied and every
  derived value is a pure function of the model's own fields.

The load-bearing structural decisions:

* **Severity is a property of the code, not of the caller.**
  :data:`MIGRATION_DIAGNOSTIC_SEVERITY` maps every
  :class:`MigrationDiagnosticCode` to a fixed
  :class:`MigrationDiagnosticSeverity`, and :class:`MigrationIntakeDiagnostic`
  fills it in — rejecting a supplied severity that disagrees. A structurally
  unsafe condition therefore cannot be filed as advisory by a producer that would
  rather not quarantine.
* **Three severities, not two.** Phase 40D's guardrail severity is binary
  because its outcome is binary (ready or blocked). Phase 40E's outcome
  vocabulary is genuinely three-valued — ``ready_for_parsing``, ``blocked``,
  ``quarantined`` — and the distinction is operationally load-bearing: a blocked
  bundle can be fixed by re-declaring it, while a quarantined one describes
  material that is itself unsafe. A two-valued severity could not express which
  of the two a finding implies, and collapsing them would either quarantine
  recoverable declarations or let unsafe material be re-declared past the
  boundary.
* **Status is derived and cannot outrun the diagnostics.** Any quarantine
  finding forces ``assessed_status`` to ``quarantined``; any blocking finding
  (absent a quarantine) forces ``blocked``; ``ready_for_parsing`` is reachable
  only with neither. ``ready_for_parsing`` the boolean is true if and only if the
  status is, so a consumer can branch on one field without re-deriving the rule.
* **A report can never assess ``declared``.** ``declared`` is the caller's
  starting state, not a verdict. A report claiming it would mean the assessment
  reached no conclusion while still producing a record, so the model rejects it.

Phase 40E assesses declared metadata; it still parses nothing, reads no artifact
byte, and imports nothing.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.memory_migration import (
    MEMORY_MIGRATION_CONTRACT_VERSION,
    MAX_MIGRATION_COLLECTION_ITEMS,
    MAX_MIGRATION_ID_LENGTH,
    MAX_MIGRATION_SUMMARY_LENGTH,
    MigrationIntakeStatus,
)

# --------------------------------------------------------------------------- #
# Assessment policy version.
#
# A stable identifier for the *ruleset*, deliberately separate from
# ``MEMORY_MIGRATION_CONTRACT_VERSION`` (the wire shape) — the same separation
# Phase 40C/40D established between contract, assembly policy and validation
# policy. The wire contract can stay ``memory-migration.v1`` while the intake
# rules tighten, and a consumer can tell which ruleset produced a verdict without
# inferring it from the codes.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_ASSESSMENT_VERSION = "memory-migration-assessment.v1"

# A report may legitimately carry one finding per artifact plus bundle-scoped
# findings. It reuses the existing collection ceiling rather than declaring a new
# bound; overflow is *represented* by an explicit truncation diagnostic rather
# than silently dropped (see the Phase 40E assessment service).
MAX_MIGRATION_DIAGNOSTICS = MAX_MIGRATION_COLLECTION_ITEMS


class MigrationDiagnosticSeverity(StrEnum):
    """Advisory, blocking, or quarantine — fixed per diagnostic code.

    * ``advisory`` — visible, but the declaration remains usable. Reserved for
      findings that state a *limit of this phase* rather than a defect (most
      importantly: that a declared digest has not been verified).
    * ``blocking`` — the declaration cannot proceed to parsing, but the material
      may be fine. The user can re-declare it correctly.
    * ``quarantine`` — the described material is structurally unsafe. No
      re-declaration fixes it, and Phase 40F must never be handed it.

    The ordering advisory → blocking → quarantine is a strict escalation, and
    :meth:`MemoryMigrationIntakeAssessment` resolves the report's status by the
    single most severe finding present.
    """

    ADVISORY = "advisory"
    BLOCKING = "blocking"
    QUARANTINE = "quarantine"


class MigrationDiagnosticCode(StrEnum):
    """Closed taxonomy of Phase 40E intake findings.

    Every member names a specific condition the boundary detected in **declared
    metadata**. None of them describes a property of the artifact's actual bytes,
    because none of them was read.
    """

    # Contract and policy version.
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    UNSUPPORTED_INTAKE_STATUS = "unsupported_intake_status"

    # Provenance and custody.
    REFUSED_CUSTODY = "refused_custody"
    UNSUPPORTED_SOURCE_TYPE = "unsupported_source_type"
    MISSING_DECLARED_EXPORT_TIME = "missing_declared_export_time"
    INCONSISTENT_CUSTODY_TIMELINE = "inconsistent_custody_timeline"

    # Format and container support.
    UNRECOGNIZED_ARTIFACT_FORMAT = "unrecognized_artifact_format"
    UNSUPPORTED_ARTIFACT_FORMAT = "unsupported_artifact_format"
    UNSUPPORTED_CONTAINER_KIND = "unsupported_container_kind"
    FORMAT_CONTAINER_MISMATCH = "format_container_mismatch"

    # Declared path safety.
    ABSOLUTE_ARTIFACT_PATH = "absolute_artifact_path"
    TRAVERSING_ARTIFACT_PATH = "traversing_artifact_path"
    CONTROL_CHARACTER_IN_PATH = "control_character_in_path"
    RESERVED_DEVICE_PATH_SEGMENT = "reserved_device_path_segment"
    NON_CANONICAL_ARTIFACT_PATH = "non_canonical_artifact_path"

    # Declared entry-type safety.
    UNSAFE_ENTRY_KIND = "unsafe_entry_kind"
    UNSUPPORTED_ENTRY_KIND = "unsupported_entry_kind"

    # Declared digests.
    MISSING_DECLARED_DIGEST = "missing_declared_digest"
    WEAK_DIGEST_ALGORITHM = "weak_digest_algorithm"
    DECLARED_DIGEST_UNVERIFIED = "declared_digest_unverified"

    # Declared bounds and totals.
    MISSING_DECLARED_SIZE = "missing_declared_size"
    ARTIFACT_SIZE_LIMIT_EXCEEDED = "artifact_size_limit_exceeded"
    BUNDLE_SIZE_LIMIT_EXCEEDED = "bundle_size_limit_exceeded"
    ARTIFACT_COUNT_LIMIT_EXCEEDED = "artifact_count_limit_exceeded"
    DECLARED_COUNT_MISMATCH = "declared_count_mismatch"
    DECLARED_SIZE_MISMATCH = "declared_size_mismatch"

    # Declared identity.
    DUPLICATE_ARTIFACT_PATH = "duplicate_artifact_path"
    REDUNDANT_ARTIFACT_DECLARATION = "redundant_artifact_declaration"

    # Bundle composition.
    EMPTY_BUNDLE = "empty_bundle"
    DIAGNOSTICS_TRUNCATED = "diagnostics_truncated"


# --------------------------------------------------------------------------- #
# Fixed severity per code.
#
# Fail-closed is the default posture: a finding is advisory only when it states a
# limitation of this phase rather than a defect in the declaration.
#
# The one advisory member, with its reason:
#
# * ``declared_digest_unverified`` — emitted for *every* artifact carrying a
#   well-formed digest under an accepted algorithm. It is not a defect; it is the
#   phase telling the truth about itself. Phase 40E reads no bytes, so every
#   digest it sees is a claim, and a report that stayed silent about that would
#   let a reader mistake "a digest is present" for "the digest checked out". It
#   must not block, because blocking every correct declaration would make the
#   ready path unreachable.
#
# Quarantine members are exactly the conditions no re-declaration can fix: a path
# that escapes the intake tree, an entry that is not readable content, and an
# origin Hive|Mind refuses on principle. Everything else blocks.
# --------------------------------------------------------------------------- #
MIGRATION_DIAGNOSTIC_SEVERITY: dict[
    MigrationDiagnosticCode, MigrationDiagnosticSeverity
] = {
    MigrationDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.UNSUPPORTED_INTAKE_STATUS: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.REFUSED_CUSTODY: MigrationDiagnosticSeverity.QUARANTINE,
    MigrationDiagnosticCode.UNSUPPORTED_SOURCE_TYPE: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.MISSING_DECLARED_EXPORT_TIME: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.INCONSISTENT_CUSTODY_TIMELINE: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.UNRECOGNIZED_ARTIFACT_FORMAT: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.UNSUPPORTED_ARTIFACT_FORMAT: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.UNSUPPORTED_CONTAINER_KIND: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.FORMAT_CONTAINER_MISMATCH: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.ABSOLUTE_ARTIFACT_PATH: (
        MigrationDiagnosticSeverity.QUARANTINE
    ),
    MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH: (
        MigrationDiagnosticSeverity.QUARANTINE
    ),
    MigrationDiagnosticCode.CONTROL_CHARACTER_IN_PATH: (
        MigrationDiagnosticSeverity.QUARANTINE
    ),
    MigrationDiagnosticCode.RESERVED_DEVICE_PATH_SEGMENT: (
        MigrationDiagnosticSeverity.QUARANTINE
    ),
    MigrationDiagnosticCode.NON_CANONICAL_ARTIFACT_PATH: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.UNSAFE_ENTRY_KIND: MigrationDiagnosticSeverity.QUARANTINE,
    MigrationDiagnosticCode.UNSUPPORTED_ENTRY_KIND: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.MISSING_DECLARED_DIGEST: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.WEAK_DIGEST_ALGORITHM: MigrationDiagnosticSeverity.BLOCKING,
    MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED: (
        MigrationDiagnosticSeverity.ADVISORY
    ),
    MigrationDiagnosticCode.MISSING_DECLARED_SIZE: MigrationDiagnosticSeverity.BLOCKING,
    MigrationDiagnosticCode.ARTIFACT_SIZE_LIMIT_EXCEEDED: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.BUNDLE_SIZE_LIMIT_EXCEEDED: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.ARTIFACT_COUNT_LIMIT_EXCEEDED: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.DECLARED_COUNT_MISMATCH: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.DECLARED_SIZE_MISMATCH: MigrationDiagnosticSeverity.BLOCKING,
    MigrationDiagnosticCode.DUPLICATE_ARTIFACT_PATH: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.REDUNDANT_ARTIFACT_DECLARATION: (
        MigrationDiagnosticSeverity.BLOCKING
    ),
    MigrationDiagnosticCode.EMPTY_BUNDLE: MigrationDiagnosticSeverity.BLOCKING,
    MigrationDiagnosticCode.DIAGNOSTICS_TRUNCATED: MigrationDiagnosticSeverity.BLOCKING,
}

# The escalation order used to resolve a report's status from its findings.
# Explicit rather than relying on enum declaration order, because the mapping
# from "most severe finding" to "derived status" is a rule the report enforces
# and must therefore be stated where it can be read and tested.
_SEVERITY_RANK: dict[MigrationDiagnosticSeverity, int] = {
    MigrationDiagnosticSeverity.ADVISORY: 0,
    MigrationDiagnosticSeverity.BLOCKING: 1,
    MigrationDiagnosticSeverity.QUARANTINE: 2,
}

SEVERITY_INTAKE_STATUS: dict[MigrationDiagnosticSeverity, MigrationIntakeStatus] = {
    MigrationDiagnosticSeverity.ADVISORY: MigrationIntakeStatus.READY_FOR_PARSING,
    MigrationDiagnosticSeverity.BLOCKING: MigrationIntakeStatus.BLOCKED,
    MigrationDiagnosticSeverity.QUARANTINE: MigrationIntakeStatus.QUARANTINED,
}


def resolve_intake_status(
    severities: list[MigrationDiagnosticSeverity],
) -> MigrationIntakeStatus:
    """Derive the intake status implied by a set of finding severities.

    Pure and total: an empty set (or one containing only advisories) yields
    ``ready_for_parsing``, and otherwise the single most severe finding decides.
    Shared by the report model and the assessment service so the two can never
    disagree about what a set of findings means — the Phase 40D lesson that a
    guardrail and its result contract must not hold two copies of one rule.
    """

    if not severities:
        return MigrationIntakeStatus.READY_FOR_PARSING
    worst = max(severities, key=lambda item: _SEVERITY_RANK[item])
    return SEVERITY_INTAKE_STATUS[worst]


def _require_int(value: Any) -> Any:
    """Require an actual ``int`` where a count is expected.

    Pydantic's default coercion would also accept numeric strings and integral
    floats. Assessment counts are safety-relevant claims, so this module owns an
    exact type guard rather than depending on a sibling's private helper.
    """

    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        raise ValueError("integer field must be an integer")
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


class _AssessmentModel(BaseModel):
    """Shared config: unknown fields are rejected, never absorbed."""

    model_config = ConfigDict(extra="forbid")


class MigrationIntakeDiagnostic(_AssessmentModel):
    """One bounded, secret-free intake finding.

    ``severity`` is derived from ``code`` through
    :data:`MIGRATION_DIAGNOSTIC_SEVERITY`. It may be omitted entirely, and
    supplying one that disagrees with the code is rejected rather than honored —
    the classification belongs to the taxonomy, so a quarantine condition cannot
    be downgraded at the call site.

    ``artifact_id`` names the declared artifact the finding concerns; a
    bundle-scoped finding leaves it unset. ``subject_id`` carries the bundle or
    artifact identifier the message is *about*, so a consumer never has to parse
    the message to route the finding.

    ``message`` is bounded, human-readable, and carries only counts, closed-enum
    literals, and declaration-local identifiers — **never** a declared path, a
    media type, a digest value, an origin label, or any other caller-supplied
    string. That rule is stricter here than anywhere else in the codebase for a
    specific reason: the values Phase 40E inspects are precisely the ones most
    likely to be hostile or sensitive (a traversing path, a filename carrying
    personal information, an export label naming an account), and echoing the
    offending value into the report would move the problem from the declaration
    into the record of the declaration. The *shape* of a violation is always
    reportable; the value never is.
    """

    code: MigrationDiagnosticCode
    severity: MigrationDiagnosticSeverity | None = None
    message: str = Field(min_length=1, max_length=MAX_MIGRATION_SUMMARY_LENGTH)
    subject_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)
    artifact_id: str | None = Field(default=None, max_length=MAX_MIGRATION_ID_LENGTH)

    @model_validator(mode="before")
    @classmethod
    def _severity_follows_code(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "code" not in data:
            return data
        try:
            code = MigrationDiagnosticCode(data["code"])
        except ValueError:
            # Let the field validator report the unknown code with its own
            # message rather than masking it with a lookup failure.
            return data
        expected = MIGRATION_DIAGNOSTIC_SEVERITY[code]
        supplied = data.get("severity")
        if supplied is None:
            return {**data, "severity": expected}
        if MigrationDiagnosticSeverity(supplied) is not expected:
            raise ValueError(
                f"diagnostic {code.value!r} is {expected.value!r}; "
                "severity is fixed by the code and cannot be reclassified"
            )
        return data

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        return _clean_text(value, "diagnostic message")

    @field_validator("subject_id", "artifact_id")
    @classmethod
    def _identifier_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_text(value, "diagnostic identifier")

    @property
    def blocks_parsing(self) -> bool:
        """Whether this finding prevents the bundle reaching ``ready_for_parsing``."""

        return self.severity is not MigrationDiagnosticSeverity.ADVISORY

    @property
    def quarantines(self) -> bool:
        """Whether this finding describes structurally unsafe material."""

        return self.severity is MigrationDiagnosticSeverity.QUARANTINE

    def sort_key(self) -> tuple[str, str, str, str]:
        """The canonical ordering key for a diagnostic list.

        Code first so related findings group together, then the artifact and
        subject so a per-artifact view is contiguous, then the message as the
        final deterministic tie-break. Severity is deliberately *not* in the key:
        it is a pure function of the code, so including it would add nothing and
        would make the order look as though it could vary independently.
        """

        return (
            self.code.value,
            self.artifact_id or "",
            self.subject_id or "",
            self.message,
        )


class MemoryMigrationIntakeAssessment(_AssessmentModel):
    """The deterministic verdict over one :class:`MemoryMigrationBundle`.

    A **passive result record**. It holds no bundle, repairs nothing, parses
    nothing, and carries no artifact content; it names the bundle it describes by
    identifier plus content-derived fingerprint and records what the intake
    boundary found.

    ``bundle_fingerprint`` is carried rather than only ``bundle_id`` so a verdict
    is pinned to the *declaration it was made about*. A caller that alters a
    declaration and re-presents it under the same ``bundle_id`` produces a
    different fingerprint, so a stale assessment can be detected instead of being
    silently reused — the check Phase 40F must perform before parsing anything.

    Cross-field rules make the verdict impossible to misread:

    * any quarantine finding forces ``assessed_status`` to ``quarantined``;
    * any blocking finding, absent a quarantine, forces ``blocked``;
    * ``ready_for_parsing`` is true if and only if ``assessed_status`` is
      ``ready_for_parsing``, so the boolean can never disagree with the status;
    * an empty bundle can never be assessed ready — there is nothing to parse;
    * ``assessed_status`` is never ``declared``: that is the caller's starting
      state, not a conclusion;
    * diagnostics are unique and canonically ordered, because Phase 40E promises
      identical output for identical declared input.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    assessment_version: str = Field(default=MEMORY_MIGRATION_ASSESSMENT_VERSION)
    bundle_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    bundle_fingerprint: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    declared_status: MigrationIntakeStatus
    assessed_status: MigrationIntakeStatus
    ready_for_parsing: bool
    artifact_count: int = Field(ge=0)
    declared_total_byte_size: int | None = Field(default=None, ge=0)
    diagnostics: list[MigrationIntakeDiagnostic] = Field(
        default_factory=list, max_length=MAX_MIGRATION_DIAGNOSTICS
    )
    read_only: bool = True
    artifacts_read: bool = False

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
        if value != MEMORY_MIGRATION_ASSESSMENT_VERSION:
            raise ValueError(
                f"unsupported assessment_version {value!r}; "
                f"expected {MEMORY_MIGRATION_ASSESSMENT_VERSION!r}"
            )
        return value

    @field_validator("bundle_id", "bundle_fingerprint")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_text(value, "assessment identifier")

    @field_validator("artifact_count", "declared_total_byte_size", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("ready_for_parsing", "read_only", "artifacts_read", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_flag(value)

    @model_validator(mode="after")
    def _validate_assessment(self) -> "MemoryMigrationIntakeAssessment":
        if not self.read_only:
            # An assessment describes a declaration; there is no mode in which
            # producing one grants write authority.
            raise ValueError("read_only must remain True")
        if self.artifacts_read:
            # The single most important claim this record makes about itself.
            # Phase 40E judges declared metadata and nothing else; a report
            # asserting otherwise would misrepresent the strength of its own
            # verdict to every consumer downstream.
            raise ValueError(
                "artifacts_read must remain False; Phase 40E assesses declared "
                "metadata only and opens no artifact"
            )

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
                    "(code, artifact_id, subject_id, message)"
                )
            seen.add(key)
            previous = key

        if self.assessed_status is MigrationIntakeStatus.DECLARED:
            raise ValueError(
                "assessed_status must not be 'declared'; that is the caller's "
                "starting state, not an assessment outcome"
            )

        severities = [
            diagnostic.severity
            for diagnostic in self.diagnostics
            if diagnostic.severity is not None
        ]
        implied = resolve_intake_status(severities)
        if self.assessed_status is not implied:
            raise ValueError(
                f"assessed_status {self.assessed_status.value!r} disagrees with the "
                f"status implied by the diagnostics ({implied.value!r})"
            )

        if self.ready_for_parsing is not (
            self.assessed_status is MigrationIntakeStatus.READY_FOR_PARSING
        ):
            raise ValueError(
                "ready_for_parsing must be True if and only if assessed_status is "
                "'ready_for_parsing'"
            )
        if self.ready_for_parsing and self.artifact_count == 0:
            raise ValueError(
                "a bundle declaring no artifacts cannot be ready for parsing"
            )
        return self

    @property
    def quarantine_diagnostics(self) -> list[MigrationIntakeDiagnostic]:
        """Findings describing structurally unsafe material, in canonical order."""

        return [item for item in self.diagnostics if item.quarantines]

    @property
    def blocking_diagnostics(self) -> list[MigrationIntakeDiagnostic]:
        """Findings that prevent parsing but do not quarantine, canonically ordered."""

        return [
            item
            for item in self.diagnostics
            if item.severity is MigrationDiagnosticSeverity.BLOCKING
        ]

    @property
    def advisory_diagnostics(self) -> list[MigrationIntakeDiagnostic]:
        """Findings that are visible but do not prevent parsing."""

        return [
            item
            for item in self.diagnostics
            if item.severity is MigrationDiagnosticSeverity.ADVISORY
        ]

    def permits_parsing(self, *, bundle_fingerprint: str) -> bool:
        """Whether Phase 40F may parse the declaration with this fingerprint.

        The single call a future parser should make. It answers ``True`` only when
        this assessment reached ``ready_for_parsing`` **and** it was made about
        exactly the declaration being presented — an assessment of a different or
        since-edited bundle permits nothing, however favourable its verdict.

        Provided here, on the report, rather than left to each caller: a parser
        re-implementing "is it ready?" is a parser that can get it wrong, and
        Phase 40F is required to hold a matching ``ready_for_parsing`` assessment
        before it reads a single byte.
        """

        return self.ready_for_parsing and bundle_fingerprint == self.bundle_fingerprint
