"""Phase 40E — deterministic memory-migration intake-safety assessment.

The trust boundary between a user handing Hive|Mind their own history and any
future attempt to parse it. It answers exactly one question:

    Given only what has been **declared** about this migration bundle, may
    Phase 40F attempt to parse it — and if not, precisely why?

It answers it and stops. Phase 40E parses nothing, extracts nothing, projects no
candidate, persists nothing, and imports nothing. It produces a typed
:class:`~app.models.memory_migration_assessment.MemoryMigrationIntakeAssessment`
and nothing else.

**Declared metadata only.** The assessment opens no file, extracts no archive,
enumerates no directory, reads no byte, resolves no path against a real
filesystem, recomputes no digest, runs no Git command, and makes no network call.
Every input is a caller-supplied declaration. That is not a limitation to be
worked around later — it is the design: the boundary that decides whether
untrusted material may be touched must itself not touch it.

**Pure and read-only.** :meth:`MemoryMigrationIntakeAssessor.assess` takes a
bundle and returns a report. It never mutates the bundle, repairs a path,
normalizes an identifier, clips an oversized declaration, drops an unsafe
artifact, or rewrites a digest. It reads no clock and generates no random
identifier, so the same declaration always yields the same report, in the same
order, with the same codes.

**Nothing is repaired, and identity-bearing material is never rewritten.** A
traversing path is reported as traversing, not sanitized into a safe one. A
bundle over its bound is reported as over its bound, not trimmed to fit. Making
an unsafe declaration *look* acceptable by editing it is the failure mode this
whole layer exists to prevent, and a rewritten path would additionally destroy
the provenance link a migrated candidate must carry back to its origin.

**Readiness is derived, never trusted.** ``MemoryMigrationBundle.intake_status``
is pinned to ``declared`` by the contract, and this service ignores it as an
input to the decision — it recomputes the status from the bundle's actual
contents and reports any disagreement as a finding. A caller cannot assert that
its own material is safe.

**Fail-closed by construction.** Every policy set below is an *allowlist*.
Anything outside it — including a value added to a contract enum by a later
revision that this service has never seen — falls through to a typed blocking or
quarantining diagnostic rather than to acceptance. Adding a vocabulary member can
therefore never silently widen what the boundary lets through.

**Diagnostics carry no declared values.** Messages contain counts, closed-enum
literals, and declaration-local identifiers only. A declared path, media type,
digest value, origin label, or filename is **never** echoed into a message, even
when the value is precisely what the boundary rejected. The values this phase
inspects are the ones most likely to be hostile (a traversal payload) or
sensitive (a filename or export label carrying personal information), and copying
one into the report would move the problem from the declaration into the record
of the declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from app.models.active_memory import MemorySourceType
from app.models.memory_migration import (
    MAX_MIGRATION_BUNDLE_ARTIFACTS,
    MAX_MIGRATION_ID_LENGTH,
    MAX_MIGRATION_SUMMARY_LENGTH,
    MEMORY_MIGRATION_CONTRACT_VERSION,
    MemoryMigrationBundle,
    MigrationArtifactDescriptor,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
    MigrationEntryKind,
    MigrationIntakeStatus,
    derive_artifact_fingerprint,
    derive_bundle_fingerprint,
)
from app.models.memory_migration_assessment import (
    MAX_MIGRATION_DIAGNOSTICS,
    MIGRATION_DIAGNOSTIC_SEVERITY,
    MemoryMigrationIntakeAssessment,
    MigrationDiagnosticCode,
    MigrationDiagnosticSeverity,
    MigrationIntakeDiagnostic,
    resolve_intake_status,
)

# --------------------------------------------------------------------------- #
# Intake policy version.
#
# A stable identifier for the *ruleset this service applies*, deliberately
# separate from ``MEMORY_MIGRATION_CONTRACT_VERSION`` (the wire shape) and from
# ``MEMORY_MIGRATION_ASSESSMENT_VERSION`` (the report shape) — the same
# three-way separation Phase 40C/40D established. Tightening a bound or removing
# a format from the parseable set changes this, not the contracts.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_INTAKE_POLICY_VERSION = "memory-migration-intake.v1"


# --------------------------------------------------------------------------- #
# Initial Phase 40E assessment-policy bounds.
#
# These are *named initial values*, chosen to be permissive enough that no
# realistic user-controlled export is refused for size alone, while still being a
# hard, stated ceiling rather than an open door:
#
# * ``MAX_DECLARED_ARTIFACT_BYTES`` (1 GiB) comfortably exceeds a large ChatGPT
#   ``conversations.json`` or a full export archive, so a legitimate single
#   artifact never approaches it. A declaration above it is far more likely to be
#   a mis-declared size or a decompression-bomb-shaped claim than a real export.
# * ``MAX_DECLARED_BUNDLE_BYTES`` (2 GiB) is deliberately only *twice* the
#   per-artifact bound rather than a multiple of the artifact count: a migration
#   bundle is one person's own history, not a bulk corpus, and a total far above
#   a couple of large artifacts indicates the bundle is being used as a data dump.
# * ``MAX_DECLARED_ARTIFACTS`` (512) bounds the per-artifact assessment work and
#   keeps a bundle reviewable by a human in Phase 40G. It sits well below the
#   ``memory-migration.v1`` contract ceiling of
#   ``MAX_MIGRATION_BUNDLE_ARTIFACTS`` (2048) so policy can tighten or relax
#   without a contract change.
#
# These are declared-size bounds. Nothing here has been measured, so exceeding
# one is a statement about the *declaration*, never about the artifact's real
# size — which remains unknown until a later phase reads bytes.
# --------------------------------------------------------------------------- #
MAX_DECLARED_ARTIFACT_BYTES = 1 * 1024 * 1024 * 1024
MAX_DECLARED_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
MAX_DECLARED_ARTIFACTS = 512


# --------------------------------------------------------------------------- #
# Allowlists.
#
# Every set below is an allowlist and every check falls through to a typed
# failure. That is what makes a future contract enum addition fail closed instead
# of arriving as an accepted value nobody reviewed.
# --------------------------------------------------------------------------- #

# Formats the migration track intends to parse in Phase 40F.
#
# ``obsidian_vault_export`` is recognized but deliberately **excluded**: Hive|Mind
# already has a dedicated Obsidian import path
# (``app.services.obsidian_import``), and routing vault material through the
# migration track as well would create two competing import paths with different
# safety rules over the same source. It fails closed as an unsupported format
# rather than being silently treated as a generic Markdown bundle.
PARSEABLE_ARTIFACT_FORMATS: frozenset[MigrationArtifactFormat] = frozenset(
    {
        MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE,
        MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        MigrationArtifactFormat.CURATED_MARKDOWN_BUNDLE,
        MigrationArtifactFormat.CURATED_JSON_BUNDLE,
        MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT,
    }
)

# Container kinds whose declared contents can be bounded from metadata alone.
#
# ``directory_tree`` is excluded on purpose. A single descriptor for a whole tree
# declares a size and a digest for material whose individual entries — their
# paths, their entry kinds, their count — are simply not stated, so none of the
# per-entry safety rules in this module can be applied to any of them. Accepting
# it would mean passing an unbounded, unenumerated set of unknown entries as
# "assessed". A user with a directory of files should declare the files.
SUPPORTED_CONTAINER_KINDS: frozenset[MigrationContainerKind] = frozenset(
    {MigrationContainerKind.SINGLE_FILE, MigrationContainerKind.ZIP_ARCHIVE}
)

# Formats whose very name asserts a container, so declaring the other one makes
# the declaration internally inconsistent — and an inconsistent declaration
# cannot be assessed, because it is unclear which half is wrong.
_ARCHIVE_ONLY_FORMATS: frozenset[MigrationArtifactFormat] = frozenset(
    {MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE}
)
_SINGLE_FILE_ONLY_FORMATS: frozenset[MigrationArtifactFormat] = frozenset(
    {
        MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT,
    }
)

# The only entry kind that is readable content at a bounded, known location.
SAFE_ENTRY_KINDS: frozenset[MigrationEntryKind] = frozenset({MigrationEntryKind.FILE})

# Entry kinds that are structurally unsafe rather than merely undeclarable.
# A symlink or hardlink can resolve outside the intake tree, and a device, socket
# or FIFO is not content at all — reading one is an interaction with the host,
# not an import. No re-declaration makes any of them safe, so they quarantine.
#
# ``directory`` and ``unknown`` are deliberately *not* here: a directory carries
# no bytes to parse and no digest to anchor, and an entry the declarer could not
# type is a deficient declaration — both are recoverable by declaring the actual
# files, so they block instead of quarantining.
UNSAFE_ENTRY_KINDS: frozenset[MigrationEntryKind] = frozenset(
    {
        MigrationEntryKind.SYMLINK,
        MigrationEntryKind.HARDLINK,
        MigrationEntryKind.DEVICE,
        MigrationEntryKind.SOCKET,
        MigrationEntryKind.FIFO,
    }
)

# Digest algorithms strong enough to anchor a future integrity check. ``sha1``
# and ``md5`` are excluded because a later phase recomputing them could be
# satisfied by substituted bytes, which would make the verification step
# ceremonial rather than real.
ACCEPTED_DIGEST_ALGORITHMS: frozenset[MigrationDigestAlgorithm] = frozenset(
    {MigrationDigestAlgorithm.SHA256, MigrationDigestAlgorithm.SHA512}
)

# Custody kinds the boundary accepts. Everything else — including
# ``third_party_transfer`` and ``automated_account_link``, and including any
# member a later contract revision adds — quarantines.
#
# Refusing those two is the operative form of the project's honesty principle:
# Hive|Mind claims no direct, account-to-account access to a provider's private
# system memory, so material described as arriving that way is refused at the
# boundary rather than accepted with a caveat.
ACCEPTED_CUSTODY_KINDS: frozenset[MigrationCustodyKind] = frozenset(
    {
        MigrationCustodyKind.USER_REQUESTED_EXPORT,
        MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
        MigrationCustodyKind.USER_PROVIDED_DOCUMENT,
    }
)

# Custody kinds that must declare when the export was produced. Without it the
# migrated material cannot be ordered against memory Hive|Mind already holds, so
# a later contradiction between an imported claim and a current one could not be
# resolved by recency — the export would be undatable rather than merely undated.
_EXPORT_TIME_REQUIRED_CUSTODY: frozenset[MigrationCustodyKind] = frozenset(
    {MigrationCustodyKind.USER_REQUESTED_EXPORT}
)

# Source identities acceptable for user-supplied migration material.
#
# The excluded members are excluded for one specific reason: ``repository_observer``,
# ``ci_system`` and ``cli_report`` are Hive|Mind's *own* internal producers, whose
# output is deterministic and already grounded. A user-supplied bundle declaring
# one of them as its origin would launder that internal authority onto unread
# bytes. ``unknown`` is excluded because unattributable material cannot preserve
# provenance, which is the entire purpose of this track.
ACCEPTED_SOURCE_TYPES: frozenset[MemorySourceType] = frozenset(
    {
        MemorySourceType.HUMAN,
        MemorySourceType.CHATGPT,
        MemorySourceType.CODEX,
        MemorySourceType.CLAUDE_CODE,
        MemorySourceType.IMPORTED_DOCUMENT,
    }
)

# Windows reserved device names. Checked on every platform on purpose: a declared
# path is portable data, and a bundle assessed on Linux may well be parsed on the
# Windows host this project targets, where opening such a name addresses a device
# rather than a file.
_RESERVED_DEVICE_NAMES: frozenset[str] = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)

_TRAVERSAL_SEGMENT = ".."
_CURRENT_SEGMENT = "."


# --------------------------------------------------------------------------- #
# Bounds
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MemoryMigrationIntakeLimits:
    """Assessment-policy bounds layered *under* the ``memory-migration.v1``
    contract ceilings.

    A frozen dataclass rather than a Pydantic model, matching
    ``GroundingAssemblyLimits``: this is in-process service configuration, not a
    wire shape, and adding a contract-adjacent model would start a vocabulary
    that could drift from the declaration contracts.

    ``max_artifacts`` is validated against the contract ceiling so a policy can
    only ever be *at or below* what a bundle can represent — a policy above it
    would be unreachable and would misdescribe the boundary.
    """

    max_artifact_bytes: int = MAX_DECLARED_ARTIFACT_BYTES
    max_bundle_bytes: int = MAX_DECLARED_BUNDLE_BYTES
    max_artifacts: int = MAX_DECLARED_ARTIFACTS

    def __post_init__(self) -> None:
        for name in ("max_artifact_bytes", "max_bundle_bytes", "max_artifacts"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_artifacts > MAX_MIGRATION_BUNDLE_ARTIFACTS:
            raise ValueError(
                f"max_artifacts={self.max_artifacts} exceeds the "
                f"memory-migration.v1 contract ceiling {MAX_MIGRATION_BUNDLE_ARTIFACTS}"
            )
        if self.max_artifact_bytes > self.max_bundle_bytes:
            raise ValueError(
                "max_artifact_bytes must not exceed max_bundle_bytes; a single "
                "artifact cannot be permitted to be larger than the whole bundle"
            )


# --------------------------------------------------------------------------- #
# Pure declared-path predicates.
#
# Every one of these operates on the declared string alone. None of them resolves
# a path, consults a filesystem, or asks the host what a separator means — a
# declaration assessed on one platform must reach the same verdict on another.
# --------------------------------------------------------------------------- #
def _to_forward_slashes(value: str) -> str:
    """View a declared path with both separators unified, without altering it.

    A *view*, never a rewrite: the descriptor's own value is left untouched. Both
    separators are treated as separators because a declared path is portable data
    and a backslash-separated declaration must not be able to hide a ``..``
    segment from a forward-slash-only check.
    """

    return value.replace("\\", "/")


def _segments(value: str) -> list[str]:
    return _to_forward_slashes(value).split("/")


def _is_absolute_declared_path(value: str) -> bool:
    text = _to_forward_slashes(value)
    if text.startswith("/"):
        return True
    return len(text) >= 3 and text[1] == ":" and text[2] == "/" and text[0].isalpha()


def _has_traversal(value: str) -> bool:
    return _TRAVERSAL_SEGMENT in _segments(value)


def _has_control_characters(value: str) -> bool:
    return any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)


def _has_reserved_device_segment(value: str) -> bool:
    for segment in _segments(value):
        stem = segment.split(".", 1)[0].strip().upper()
        if stem in _RESERVED_DEVICE_NAMES:
            return True
    return False


def _is_non_canonical(value: str) -> bool:
    """Whether the declared path carries shape that will not resolve as written.

    Surrounding or embedded whitespace, an empty segment (``a//b`` or a trailing
    separator), a ``.`` segment, or a backslash separator all mean the path as
    declared is not the path a parser would open. This is reported rather than
    corrected: the path is identity-bearing, so the user must restate it.
    """

    if value != value.strip():
        return True
    if "\\" in value:
        return True
    segments = _segments(value)
    return any(
        segment == "" or segment == _CURRENT_SEGMENT or segment != segment.strip()
        for segment in segments
    )


def _comparable_instants(first: datetime, second: datetime) -> bool:
    """Whether two timestamps can be compared without raising.

    A naive and an aware datetime are not orderable in Python, and this service
    must not invent a timezone to make them so — assuming UTC for a naive
    declaration would be exactly the silent normalization the phase forbids. When
    they are not comparable the timeline check is simply skipped; the values
    remain in the declaration, unaltered.
    """

    return (first.tzinfo is None) == (second.tzinfo is None)


class MemoryMigrationIntakeAssessor:
    """Assess one declared migration bundle against the Phase 40E intake policy.

    Stateless between calls: the limits are the only configuration, nothing is
    retained or cached, and every returned report is freshly constructed. The
    assessor is therefore safe to share, adds no persistence surface, and cannot
    let one bundle's assessment influence the next.
    """

    def __init__(self, *, limits: MemoryMigrationIntakeLimits | None = None) -> None:
        self._limits = limits or MemoryMigrationIntakeLimits()

    @property
    def limits(self) -> MemoryMigrationIntakeLimits:
        return self._limits

    @property
    def policy_version(self) -> str:
        return MEMORY_MIGRATION_INTAKE_POLICY_VERSION

    # ----------------------------------------------------------------- #
    # Public entry point
    # ----------------------------------------------------------------- #
    def assess(
        self, bundle: MemoryMigrationBundle
    ) -> MemoryMigrationIntakeAssessment:
        """Return the deterministic intake verdict for ``bundle``.

        The bundle is read and never written. Checks run in a fixed order, but
        the order is an implementation detail: every finding is collected and the
        result is sorted canonically, so no check can hide another and no
        reordering of the checks could change the report.
        """

        findings: list[MigrationIntakeDiagnostic] = []

        self._check_bundle_declaration(bundle, findings)
        self._check_provenance(bundle, findings)
        for artifact in bundle.artifacts:
            self._check_artifact(bundle, artifact, findings)
        self._check_declared_identity(bundle, findings)
        self._check_declared_totals(bundle, findings)
        self._note_unverified_digests(bundle, findings)

        diagnostics = self._finalize(bundle, findings)
        severities = [
            diagnostic.severity
            for diagnostic in diagnostics
            if diagnostic.severity is not None
        ]
        assessed = resolve_intake_status(severities)
        return MemoryMigrationIntakeAssessment(
            bundle_id=bundle.bundle_id,
            bundle_fingerprint=derive_bundle_fingerprint(bundle),
            declared_status=bundle.intake_status,
            assessed_status=assessed,
            ready_for_parsing=assessed is MigrationIntakeStatus.READY_FOR_PARSING,
            artifact_count=len(bundle.artifacts),
            declared_total_byte_size=bundle.declared_total_byte_size,
            diagnostics=diagnostics,
        )

    # ----------------------------------------------------------------- #
    # Diagnostic construction
    # ----------------------------------------------------------------- #
    @staticmethod
    def _finding(
        code: MigrationDiagnosticCode,
        message: str,
        *,
        subject_id: str | None = None,
        artifact_id: str | None = None,
    ) -> MigrationIntakeDiagnostic:
        """Build one finding, bounding its identifiers rather than failing.

        A subject or artifact identifier arrives from the declaration under
        inspection, so on a tampered record it may itself be out of bounds.
        Bounding it here keeps the report constructible: a boundary that crashes
        on malformed input reports nothing at all, which is strictly worse than
        reporting a bounded identifier.
        """

        return MigrationIntakeDiagnostic(
            code=code,
            message=message[:MAX_MIGRATION_SUMMARY_LENGTH],
            subject_id=(
                None if subject_id is None else subject_id[:MAX_MIGRATION_ID_LENGTH]
            )
            or None,
            artifact_id=(
                None if artifact_id is None else artifact_id[:MAX_MIGRATION_ID_LENGTH]
            )
            or None,
        )

    # ----------------------------------------------------------------- #
    # 1. Bundle declaration
    # ----------------------------------------------------------------- #
    def _check_bundle_declaration(
        self,
        bundle: MemoryMigrationBundle,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        """Check the bundle's own version, declared status, and composition.

        The version and status restatements duplicate rules the contract already
        enforces. They are kept because Phase 40E is the trust boundary: a bundle
        that reached this service by any path other than full model construction
        (``model_construct``, a partially-migrated producer, a future transport
        that rebuilds a record field by field) must still be caught, and a
        boundary that assumes its input was validated elsewhere guards nothing.
        """

        if bundle.schema_version != MEMORY_MIGRATION_CONTRACT_VERSION:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION,
                    "bundle declares a schema version this intake boundary does not "
                    f"implement; expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}",
                    subject_id=bundle.bundle_id,
                )
            )

        if bundle.intake_status is not MigrationIntakeStatus.DECLARED:
            # Readiness is derived here, never read off the bundle. A bundle
            # arriving with any other status has asserted an outcome only this
            # service may reach.
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_INTAKE_STATUS,
                    f"bundle declares intake status "
                    f"{bundle.intake_status.value!r}; only "
                    f"{MigrationIntakeStatus.DECLARED.value!r} may be declared, and "
                    "readiness is derived by this assessment",
                    subject_id=bundle.bundle_id,
                )
            )

        if not bundle.artifacts:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.EMPTY_BUNDLE,
                    "bundle declares no artifacts; there is nothing to parse",
                    subject_id=bundle.bundle_id,
                )
            )

        if len(bundle.artifacts) > self._limits.max_artifacts:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.ARTIFACT_COUNT_LIMIT_EXCEEDED,
                    f"bundle declares {len(bundle.artifacts)} artifacts, exceeding "
                    f"the intake bound of {self._limits.max_artifacts}",
                    subject_id=bundle.bundle_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 2. Custody and provenance
    # ----------------------------------------------------------------- #
    def _check_provenance(
        self,
        bundle: MemoryMigrationBundle,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        provenance = bundle.provenance

        if provenance.custody not in ACCEPTED_CUSTODY_KINDS:
            # Fail-closed allowlist: a refused custody kind and an unrecognized
            # future one land in the same branch, so a later vocabulary addition
            # cannot arrive as an accepted value.
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.REFUSED_CUSTODY,
                    f"custody {provenance.custody.value!r} is not an accepted intake "
                    "custody; Hive|Mind accepts only material the user themselves "
                    "exported, assembled, or provided",
                    subject_id=bundle.bundle_id,
                )
            )

        source_type = provenance.source.source_type
        if source_type not in ACCEPTED_SOURCE_TYPES:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_SOURCE_TYPE,
                    f"declared source type {source_type.value!r} is not accepted for "
                    "user-supplied migration material",
                    subject_id=bundle.bundle_id,
                )
            )

        if (
            provenance.custody in _EXPORT_TIME_REQUIRED_CUSTODY
            and provenance.declared_exported_at is None
        ):
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.MISSING_DECLARED_EXPORT_TIME,
                    f"custody {provenance.custody.value!r} declares no export time; "
                    "migrated material could not be ordered against existing memory",
                    subject_id=bundle.bundle_id,
                )
            )

        exported_at = provenance.declared_exported_at
        acquired_at = provenance.declared_acquired_at
        if (
            exported_at is not None
            and acquired_at is not None
            and _comparable_instants(exported_at, acquired_at)
            and acquired_at < exported_at
        ):
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.INCONSISTENT_CUSTODY_TIMELINE,
                    "declared acquisition precedes declared export; the custody "
                    "chain as declared could not have happened",
                    subject_id=bundle.bundle_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 3. Per-artifact declaration
    # ----------------------------------------------------------------- #
    def _check_artifact(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        artifact_id = artifact.artifact_id

        if artifact.schema_version != MEMORY_MIGRATION_CONTRACT_VERSION:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION,
                    "artifact declares a schema version this intake boundary does "
                    f"not implement; expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact_id,
                )
            )

        self._check_artifact_path(bundle, artifact, findings)
        self._check_artifact_entry_kind(bundle, artifact, findings)
        self._check_artifact_format(bundle, artifact, findings)
        self._check_artifact_size(bundle, artifact, findings)
        self._check_artifact_digest(bundle, artifact, findings)

    def _check_artifact_path(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        """Judge the declared path's shape. The value is never echoed or rewritten."""

        path = artifact.declared_relative_path
        artifact_id = artifact.artifact_id

        for predicate, code, message in (
            (
                _is_absolute_declared_path,
                MigrationDiagnosticCode.ABSOLUTE_ARTIFACT_PATH,
                "declared path is absolute; an intake path must be relative to the "
                "bundle root",
            ),
            (
                _has_traversal,
                MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH,
                "declared path contains a parent-directory segment and can escape "
                "the bundle root",
            ),
            (
                _has_control_characters,
                MigrationDiagnosticCode.CONTROL_CHARACTER_IN_PATH,
                "declared path contains control characters and cannot be treated as "
                "a safe location",
            ),
            (
                _has_reserved_device_segment,
                MigrationDiagnosticCode.RESERVED_DEVICE_PATH_SEGMENT,
                "declared path contains a reserved device-name segment, which "
                "addresses a device rather than a file on Windows hosts",
            ),
            (
                _is_non_canonical,
                MigrationDiagnosticCode.NON_CANONICAL_ARTIFACT_PATH,
                "declared path is not canonical (surrounding or embedded "
                "whitespace, an empty or '.' segment, or a backslash separator); "
                "it is reported rather than rewritten because the path is "
                "identity-bearing",
            ),
        ):
            if predicate(path):
                findings.append(
                    self._finding(
                        code,
                        message,
                        subject_id=bundle.bundle_id,
                        artifact_id=artifact_id,
                    )
                )

    def _check_artifact_entry_kind(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        kind = artifact.entry_kind
        if kind in SAFE_ENTRY_KINDS:
            return
        if kind in UNSAFE_ENTRY_KINDS:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSAFE_ENTRY_KIND,
                    f"declared entry kind {kind.value!r} is structurally unsafe for "
                    "intake; it can resolve outside the bundle or is not readable "
                    "content",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact.artifact_id,
                )
            )
            return
        # Fail-closed allowlist: ``directory``, ``unknown``, and any future member
        # that is neither explicitly safe nor explicitly unsafe block here.
        findings.append(
            self._finding(
                MigrationDiagnosticCode.UNSUPPORTED_ENTRY_KIND,
                f"declared entry kind {kind.value!r} is not parseable content; "
                "declare the individual files instead",
                subject_id=bundle.bundle_id,
                artifact_id=artifact.artifact_id,
            )
        )

    def _check_artifact_format(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        artifact_id = artifact.artifact_id
        artifact_format = artifact.artifact_format
        container = artifact.container

        if artifact_format is MigrationArtifactFormat.UNRECOGNIZED:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNRECOGNIZED_ARTIFACT_FORMAT,
                    "artifact format is declared unrecognized; material Hive|Mind "
                    "cannot name must not be handed to a parser",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact_id,
                )
            )
        elif artifact_format not in PARSEABLE_ARTIFACT_FORMATS:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_ARTIFACT_FORMAT,
                    f"artifact format {artifact_format.value!r} is recognized but has "
                    "no migration-track parser",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact_id,
                )
            )

        if container not in SUPPORTED_CONTAINER_KINDS:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.UNSUPPORTED_CONTAINER_KIND,
                    f"container kind {container.value!r} declares no per-entry "
                    "metadata, so its contents cannot be assessed",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact_id,
                )
            )
            return

        mismatched = (
            artifact_format in _ARCHIVE_ONLY_FORMATS
            and container is not MigrationContainerKind.ZIP_ARCHIVE
        ) or (
            artifact_format in _SINGLE_FILE_ONLY_FORMATS
            and container is not MigrationContainerKind.SINGLE_FILE
        )
        if mismatched:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.FORMAT_CONTAINER_MISMATCH,
                    f"format {artifact_format.value!r} and container "
                    f"{container.value!r} contradict each other; the declaration "
                    "cannot be assessed because it is unclear which is wrong",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact_id,
                )
            )

    def _check_artifact_size(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        size = artifact.declared_byte_size
        if size is None:
            # Fail closed: an undeclared size is unbounded, and this phase cannot
            # measure it. Accepting it would hand Phase 40F an artifact of
            # unknown extent under an assessment that claims bounds were checked.
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.MISSING_DECLARED_SIZE,
                    "artifact declares no byte size; an unbounded declaration "
                    "cannot be size-checked and Phase 40E measures nothing",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact.artifact_id,
                )
            )
            return
        if size > self._limits.max_artifact_bytes:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.ARTIFACT_SIZE_LIMIT_EXCEEDED,
                    f"artifact declares {size} bytes, exceeding the intake bound of "
                    f"{self._limits.max_artifact_bytes}",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact.artifact_id,
                )
            )

    def _check_artifact_digest(
        self,
        bundle: MemoryMigrationBundle,
        artifact: MigrationArtifactDescriptor,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        digest = artifact.declared_digest
        if digest is None:
            # Fail closed. Phase 40E cannot verify a digest, but without one
            # declared, *no* later phase could either: there would be nothing to
            # recompute against, so substituted bytes would remain undetectable
            # for the whole life of the migrated record.
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.MISSING_DECLARED_DIGEST,
                    "artifact declares no digest; without one no later phase can "
                    "ever confirm the bytes it reads are the bytes declared here",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact.artifact_id,
                )
            )
            return
        if digest.algorithm not in ACCEPTED_DIGEST_ALGORITHMS:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.WEAK_DIGEST_ALGORITHM,
                    f"declared digest algorithm {digest.algorithm.value!r} is too "
                    "weak to anchor a later integrity check",
                    subject_id=bundle.bundle_id,
                    artifact_id=artifact.artifact_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 4. Declared identity across the bundle
    # ----------------------------------------------------------------- #
    def _check_declared_identity(
        self,
        bundle: MemoryMigrationBundle,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        """Detect declarations that collide or repeat.

        Paths are grouped **exactly as declared**, with no case folding, Unicode
        folding, or separator rewriting. Two declarations that differ only in case
        are genuinely different on a case-sensitive filesystem, and treating them
        as one here would invent an equivalence this phase cannot verify.

        Everything is computed from dictionaries keyed on stable strings and
        reported in sorted order, so the findings do not depend on the order the
        artifacts appear in.
        """

        by_path: dict[str, list[str]] = {}
        by_fingerprint: dict[str, list[str]] = {}
        for artifact in bundle.artifacts:
            by_path.setdefault(artifact.declared_relative_path, []).append(
                artifact.artifact_id
            )
            by_fingerprint.setdefault(derive_artifact_fingerprint(artifact), []).append(
                artifact.artifact_id
            )

        for path in sorted(by_path):
            group = by_path[path]
            if len(group) > 1:
                findings.append(
                    self._finding(
                        MigrationDiagnosticCode.DUPLICATE_ARTIFACT_PATH,
                        f"{len(group)} artifacts declare the same relative path; a "
                        "parser could not tell which entry a candidate came from",
                        subject_id=bundle.bundle_id,
                        artifact_id=min(group),
                    )
                )

        for fingerprint in sorted(by_fingerprint):
            group = by_fingerprint[fingerprint]
            if len(group) > 1:
                findings.append(
                    self._finding(
                        MigrationDiagnosticCode.REDUNDANT_ARTIFACT_DECLARATION,
                        f"{len(group)} artifacts declare materially identical "
                        "material under different identifiers, which would import "
                        "the same history more than once",
                        subject_id=bundle.bundle_id,
                        artifact_id=min(group),
                    )
                )

    # ----------------------------------------------------------------- #
    # 5. Declared totals
    # ----------------------------------------------------------------- #
    def _check_declared_totals(
        self,
        bundle: MemoryMigrationBundle,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        """Reconcile the bundle's declared totals against what it actually carries.

        The Phase 40D discipline applied to intake: a declared total is not
        trusted, it is recomputed from the artifacts present and compared. A
        bundle whose summary fields merely *look* plausible therefore fails.
        """

        declared_count = bundle.declared_artifact_count
        actual_count = len(bundle.artifacts)
        if declared_count is not None and declared_count != actual_count:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.DECLARED_COUNT_MISMATCH,
                    f"bundle declares {declared_count} artifact(s) but carries "
                    f"{actual_count}",
                    subject_id=bundle.bundle_id,
                )
            )

        sizes = [artifact.declared_byte_size for artifact in bundle.artifacts]
        # A recomputed total is only meaningful when every artifact declared a
        # size. When one did not, the per-artifact ``missing_declared_size``
        # finding already blocks, and comparing a partial sum against a declared
        # total would produce a second, misleading mismatch finding.
        recomputed = (
            sum(size for size in sizes if size is not None)
            if sizes and all(size is not None for size in sizes)
            else None
        )

        declared_total = bundle.declared_total_byte_size
        if (
            recomputed is not None
            and declared_total is not None
            and declared_total != recomputed
        ):
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.DECLARED_SIZE_MISMATCH,
                    f"bundle declares {declared_total} total bytes but its artifacts "
                    f"declare {recomputed}",
                    subject_id=bundle.bundle_id,
                )
            )

        # Bound the larger of the two declared views, so neither an understated
        # bundle total nor an understated set of artifact sizes can slip a bundle
        # under the ceiling.
        candidates = [value for value in (recomputed, declared_total) if value is not None]
        if candidates and max(candidates) > self._limits.max_bundle_bytes:
            findings.append(
                self._finding(
                    MigrationDiagnosticCode.BUNDLE_SIZE_LIMIT_EXCEEDED,
                    f"bundle declares {max(candidates)} total bytes, exceeding the "
                    f"intake bound of {self._limits.max_bundle_bytes}",
                    subject_id=bundle.bundle_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 6. The standing unverified-digest statement
    # ----------------------------------------------------------------- #
    def _note_unverified_digests(
        self,
        bundle: MemoryMigrationBundle,
        findings: list[MigrationIntakeDiagnostic],
    ) -> None:
        """Record, always, that accepted digests remain unverified.

        Emitted once per bundle rather than once per artifact. The statement is
        identical for every artifact — Phase 40E read none of them — so per-
        artifact copies would add no information while crowding real findings out
        of the bounded diagnostic list.

        Artifacts whose algorithm was rejected are excluded from the count: their
        digest is already blocked as unusable, and describing it as "declared but
        unverified" would imply it could become verified later.
        """

        countable = sum(
            1
            for artifact in bundle.artifacts
            if artifact.declared_digest is not None
            and artifact.declared_digest.algorithm in ACCEPTED_DIGEST_ALGORITHMS
        )
        if not countable:
            return
        findings.append(
            self._finding(
                MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED,
                f"{countable} declared digest(s) remain unverified; Phase 40E reads "
                "no artifact bytes, so a later phase must recompute them before any "
                "integrity claim is made",
                subject_id=bundle.bundle_id,
            )
        )

    # ----------------------------------------------------------------- #
    # 7. Canonical ordering, deduplication and bounded truncation
    # ----------------------------------------------------------------- #
    def _finalize(
        self,
        bundle: MemoryMigrationBundle,
        findings: Sequence[MigrationIntakeDiagnostic],
    ) -> list[MigrationIntakeDiagnostic]:
        """Sort, deduplicate, and bound the finding list without losing severity.

        Deduplication collapses byte-identical findings: a malformed declaration
        can make the same per-artifact check fire twice with identical output, and
        a report is a *set* of findings, so reporting it once is correct and keeps
        the result constructible.

        Truncation retains findings **most-severe-first** and only then re-sorts
        canonically. That ordering is what guarantees the retained set still
        contains the most severe severity present in the full set, so the derived
        status cannot be softened by the act of truncating. The truncation notice
        itself is blocking: a declaration that produced more findings than a report
        can carry has not been fully described, and reporting it as ready would be
        a claim the assessment cannot support.
        """

        ordered = sorted(findings, key=lambda item: item.sort_key())
        deduplicated: list[MigrationIntakeDiagnostic] = []
        seen: set[tuple[str, str, str, str]] = set()
        for finding in ordered:
            key = finding.sort_key()
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(finding)

        if len(deduplicated) <= MAX_MIGRATION_DIAGNOSTICS:
            return deduplicated

        by_severity = sorted(
            deduplicated,
            key=lambda item: (
                -_severity_rank(item),
                item.sort_key(),
            ),
        )
        kept = by_severity[: MAX_MIGRATION_DIAGNOSTICS - 1]
        kept.append(
            self._finding(
                MigrationDiagnosticCode.DIAGNOSTICS_TRUNCATED,
                f"{len(deduplicated) - len(kept)} further finding(s) were omitted to "
                f"satisfy the {MAX_MIGRATION_DIAGNOSTICS} diagnostic bound; the "
                "declaration is not fully described and cannot be treated as ready",
                subject_id=bundle.bundle_id,
            )
        )
        return sorted(kept, key=lambda item: item.sort_key())


def _severity_rank(diagnostic: MigrationIntakeDiagnostic) -> int:
    """Order a finding by severity for truncation retention.

    Reads the severity from the taxonomy rather than from the instance, so a
    finding that somehow reached this point without a filled-in severity still
    ranks by what its code means.
    """

    severity = diagnostic.severity or MIGRATION_DIAGNOSTIC_SEVERITY[diagnostic.code]
    return {
        MigrationDiagnosticSeverity.ADVISORY: 0,
        MigrationDiagnosticSeverity.BLOCKING: 1,
        MigrationDiagnosticSeverity.QUARANTINE: 2,
    }[severity]


def assess_memory_migration_intake(
    bundle: MemoryMigrationBundle,
    *,
    limits: MemoryMigrationIntakeLimits | None = None,
) -> MemoryMigrationIntakeAssessment:
    """Module-level convenience wrapper.

    Mirrors the ``assemble_grounding_context`` /
    ``validate_synthesis_context_packet`` entry-point convention so a caller that
    needs one call does not have to manage an assessor instance.
    """

    return MemoryMigrationIntakeAssessor(limits=limits).assess(bundle)
