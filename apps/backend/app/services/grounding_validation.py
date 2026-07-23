"""Phase 40D — deterministic Grounded Synthesis validation guardrails.

The trust boundary between grounding *assembly* (Phase 40C) and any future
synthesis *generation*. It answers exactly one question:

    Is this :class:`SynthesisContextPacket` sufficiently grounded, internally
    consistent, and provenance-complete to be handed to a synthesis capability?

It answers it and stops. Phase 40D generates no synthesis output, no musing, no
loom artifact, no prose, no prompt, and no recommendation. It produces a typed
:class:`SynthesisPacketValidationReport` and nothing else.

**Pure and read-only.** :meth:`SynthesisContextPacketValidator.validate` takes a
packet and returns a report. It never mutates the packet, rewrites an evidence
record, removes an invalid entry, repairs a provenance reference, re-ranks
evidence, re-assembles context, persists a verdict, or touches a repository,
graph, source, store, or Active Memory. It reads no clock, generates no random
identifier, and performs no filesystem, Git, or network access — so the same
packet always yields the same report, in the same order, with the same codes.

**A packet is never trusted on its own word.** The Phase 40C assembler computes
every count, coverage total, truncation figure, readiness reason and packet
identifier that a packet carries. Phase 40D recomputes them from the packet's
actual contents and compares. A hand-built or tampered packet whose summary
fields merely *look* plausible therefore fails, and — because the packet
identifier is a content-derived hash over the packet's own material — so does one
whose evidence, conflicts, gaps, coverage or warnings were edited after assembly.

**Two layers, not one.** The Phase 40B contract models already enforce field
shape: bounds, enum membership, metadata safety, identifier uniqueness, dangling
cross-references, and the readiness rules a constructed packet must satisfy.
Phase 40D deliberately does not re-implement field parsing. It restates the
*semantic* rules that a bypassed construction path (``model_construct``, a
partially-migrated producer, a future transport that reconstructs a packet
field-by-field) could evade, and it adds the cross-record, cross-summary and
cross-assembler checks Pydantic cannot express at all.

**Blocking is the default posture.** A finding is advisory only when the packet's
grounding remains fully trustworthy and traceable despite it; every other
condition prevents synthesis readiness. Readiness is *computed*, never read off
the packet: a packet declaring ``ready`` while carrying a blocking condition is
assessed ``blocked``, and the disagreement is itself reported.

**Diagnostics carry no secrets.** Messages contain counts, closed-enum literals,
and packet-local identifiers only. A reference *value* — a path, a remote, a
command, an excerpt — is never echoed into a message, even when the value is
precisely what the guardrail rejected. Phase 40C kept raw provider material out
of packets; Phase 40D must not reintroduce it through a diagnostic.

Policy is reused rather than re-declared: the supported evidence families, the
assembly bounds, the assembly version, and the packet-identity derivation all
come from :mod:`app.services.grounding_context`. A second copy of any of them
would let the validator and the assembler drift into disagreeing about what a
valid packet is, which is the one failure a guardrail layer cannot afford.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Sequence

from app.models.active_memory import ContradictionSeverity, EvidenceReferenceKind
from app.models.grounded_synthesis import (
    GROUNDED_SYNTHESIS_CONTRACT_VERSION,
    MAX_SYNTHESIS_CONTEXT_SUMMARIES,
    MAX_SYNTHESIS_ID_LENGTH,
    MAX_SYNTHESIS_LABEL_LENGTH,
    MAX_SYNTHESIS_METADATA_ENTRIES,
    MAX_SYNTHESIS_SUMMARY_LENGTH,
    GroundingEvidenceKind,
    GroundingEvidenceReference,
    SynthesisContextPacket,
    SynthesisReadinessStatus,
    SynthesisWarningCode,
)
from app.models.grounded_synthesis_validation import (
    GroundingDiagnosticCode,
    GroundingValidationDiagnostic,
    SynthesisPacketValidationReport,
)
from app.services.grounding_context import (
    GROUNDING_CONTEXT_ASSEMBLY_VERSION,
    SUPPORTED_GROUNDING_KINDS,
    GroundingAssemblyLimits,
    derive_context_packet_identity,
)

# --------------------------------------------------------------------------- #
# Provenance expectations per evidence family.
#
# Deliberately *per family*, because the canonical contract intentionally
# distinguishes them (Phase 40D §4): requiring one uniform provenance shape would
# reject legitimate evidence.
#
# ``active_memory_evidence_record`` is absent on purpose. Phase 40C reuses the
# ``EvidenceRecord``'s own ``EvidenceReference`` verbatim, and an evidence record
# may legitimately point at any of the ten Phase 37A pointer kinds — so there is
# no expected subset to check, and inventing one would reject valid grounding.
#
# A deviation here is *advisory*, not blocking: Phase 37A permits every pointer
# kind on every reference, so an unexpected kind means "this pointer may not
# resolve the way this family's pointers usually do", not "this evidence is
# untrustworthy".
# --------------------------------------------------------------------------- #
_EXPECTED_REFERENCE_KINDS: dict[
    GroundingEvidenceKind, frozenset[EvidenceReferenceKind]
] = {
    GroundingEvidenceKind.REPOSITORY_OBSERVATION: frozenset(
        {
            EvidenceReferenceKind.FILE_PATH,
            EvidenceReferenceKind.COMMIT_HASH,
            EvidenceReferenceKind.BRANCH_NAME,
            EvidenceReferenceKind.ARTIFACT_ID,
        }
    ),
    GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING: frozenset(
        {
            EvidenceReferenceKind.FILE_PATH,
            EvidenceReferenceKind.COMMIT_HASH,
            EvidenceReferenceKind.ARTIFACT_ID,
        }
    ),
    GroundingEvidenceKind.ACTIVE_MEMORY_RECORD: frozenset(
        {EvidenceReferenceKind.SOURCE_RECORD_ID}
    ),
    GroundingEvidenceKind.CONTRADICTION_RECORD: frozenset(
        {EvidenceReferenceKind.SOURCE_RECORD_ID}
    ),
}

# Families whose evidence is produced by an identified subsystem rather than
# asserted by the record itself. A repository observation with no declared
# producer cannot be traced back to the observer run that made it, so its
# provenance is unresolved rather than merely sparse.
_PROVENANCE_SOURCE_REQUIRED: frozenset[GroundingEvidenceKind] = frozenset(
    {
        GroundingEvidenceKind.REPOSITORY_OBSERVATION,
        GroundingEvidenceKind.REPOSITORY_DRIFT_FINDING,
    }
)

# --------------------------------------------------------------------------- #
# Assembler readiness-reason vocabulary.
#
# Phase 40C records *why* it reached a readiness state in packet metadata. These
# are the reasons that describe a blocked packet; a packet asserting one of them
# while claiming any other readiness is internally inconsistent, whichever of the
# two fields was edited.
# --------------------------------------------------------------------------- #
_BLOCKING_READINESS_REASONS: frozenset[str] = frozenset(
    {
        "unsafe_repository_identity",
        "critical_conflict",
        "unrepresentable_critical_conflict",
        "critical_evidence_truncated",
    }
)

# Reasons that assert critical grounding the packet could not represent. The
# packet is not merely blocked — it is knowingly incomplete about the evidence
# that mattered most, which is the "unknown critical evidence" condition.
_CRITICAL_LOSS_READINESS_REASONS: frozenset[str] = frozenset(
    {"unrepresentable_critical_conflict", "critical_evidence_truncated"}
)

_READY_READINESS_REASONS: frozenset[str] = frozenset({"ready", "ready_with_warnings"})

# Windows drive-letter prefixes and POSIX/UNC roots. A ``file_path`` reference is
# contractually a *repository-relative* pointer (Phase 37A §4.7); an absolute or
# traversing one names a location outside the repository the packet claims to be
# grounded in.
_PATH_TRAVERSAL_SEGMENTS: frozenset[str] = frozenset({".."})


def _normalize_identity(value: str) -> str:
    """NFC-normalize and strip an identifier used as a canonical identity key.

    Identical to the Phase 40C assembler rule, and deliberately so: if the
    validator normalized identity differently, two records the assembler
    considers the same would look distinct here (or the reverse), and the
    guardrail would disagree with the producer it exists to check.
    """

    return unicodedata.normalize("NFC", value).strip()


def _is_count(value: Any) -> bool:
    """Whether a metadata value is a usable non-negative count."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_absolute_path(value: str) -> bool:
    text = value.strip().replace("\\", "/")
    if text.startswith("/"):
        return True
    return len(text) >= 3 and text[1] == ":" and text[2] == "/" and text[0].isalpha()


def _has_traversal(value: str) -> bool:
    return any(
        segment in _PATH_TRAVERSAL_SEGMENTS
        for segment in value.strip().replace("\\", "/").split("/")
    )


def _carries_url_credentials(value: str) -> bool:
    """Whether a reference value embeds ``user:password@host`` in a URL.

    Checked because a remote URL with inline credentials is the one shape in
    which a bounded, innocuous-looking pointer can carry a secret. The value
    itself is never echoed into the resulting diagnostic.
    """

    scheme_split = value.split("://", 1)
    if len(scheme_split) != 2:
        return False
    authority = scheme_split[1].split("/", 1)[0]
    return "@" in authority and ":" in authority.split("@", 1)[0]


def _evidence_material(reference: GroundingEvidenceReference) -> str:
    """Canonical JSON of everything except the derived evidence identifier.

    Two references sharing a canonical identity are compared on this: if the
    material matches they are a redundant copy, and if it differs they are
    genuinely conflicting records wearing the same identity. Serialization goes
    through the contract model's own ``model_dump`` so the comparison always
    covers every contract field, including any a later contract revision adds.
    """

    try:
        payload = reference.model_dump(exclude={"evidence_id"})
    except Exception:  # pragma: no cover - only reachable for a tampered model
        return repr(reference)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _source_material(reference: GroundingEvidenceReference) -> str:
    """Canonical JSON of the declared producer identity alone."""

    source = reference.source
    if source is None:
        return "null"
    return json.dumps(
        [
            source.source_type.value,
            source.source_id,
            source.display_label,
            source.session_id,
        ],
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


class SynthesisContextPacketValidator:
    """Validate a Phase 40C packet against the Phase 40D guardrails.

    Stateless between calls: the assembly limits are the only configuration,
    nothing is retained or cached, and every returned report is freshly
    constructed. The validator is therefore safe to share, adds no persistence
    surface, and cannot let one packet's validation influence the next.

    ``limits`` defaults to the Phase 40C defaults so the validator checks the
    bounds the assembler actually applied. A caller that assembled under narrowed
    limits should validate under the same ones; validating a narrowly-assembled
    packet against the defaults simply checks less, never more.
    """

    def __init__(self, *, limits: GroundingAssemblyLimits | None = None) -> None:
        self._limits = limits or GroundingAssemblyLimits()

    @property
    def limits(self) -> GroundingAssemblyLimits:
        return self._limits

    # ----------------------------------------------------------------- #
    # Public entry point
    # ----------------------------------------------------------------- #
    def validate(
        self, packet: SynthesisContextPacket
    ) -> SynthesisPacketValidationReport:
        """Return the deterministic guardrail verdict for ``packet``.

        The packet is read and never written. Checks run in a fixed order, but
        the order is an implementation detail: every finding is collected and the
        result is sorted canonically, so no check can hide another and no
        reordering of the checks could change the report.
        """

        diagnostics: list[GroundingValidationDiagnostic] = []
        metadata = packet.metadata if isinstance(packet.metadata, dict) else {}
        declared_assembly = metadata.get("assembly_version")
        # "Assembler-declared" means the packet claims to be the output of the
        # Phase 40C assembly policy. Only such a packet can be held to that
        # policy's derived claims — identity, coverage completeness, canonical
        # ordering, and the empty-summaries rule. A hand-built packet is checked
        # against the contract alone, because holding it to an assembly it never
        # claimed would reject legitimate input.
        assembler_declared = declared_assembly is not None

        self._check_versions(packet, declared_assembly, diagnostics)
        self._check_evidence_identity(packet, diagnostics)
        self._check_provenance(packet, diagnostics)
        self._check_source_safety(packet, metadata, diagnostics)
        self._check_cross_references(packet, assembler_declared, diagnostics)
        self._check_bounds(packet, diagnostics)
        self._check_packet_consistency(packet, metadata, assembler_declared, diagnostics)
        self._check_ordering(packet, assembler_declared, diagnostics)
        self._check_packet_identity(packet, declared_assembly, diagnostics)

        if not packet.evidence_references:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.NO_GROUNDING_EVIDENCE,
                    "packet carries no grounding evidence references",
                    subject_id=packet.packet_id,
                )
            )

        # Sort, then collapse identical findings. A malformed packet can carry two
        # references under one identifier, which makes the same per-record check
        # fire twice with byte-identical output; a report is a *set* of findings,
        # so reporting it once is correct and keeps the result constructible.
        diagnostics.sort(key=lambda item: item.sort_key())
        deduplicated: list[GroundingValidationDiagnostic] = []
        seen: set[tuple[str, str, str, str]] = set()
        for diagnostic in diagnostics:
            key = diagnostic.sort_key()
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(diagnostic)
        diagnostics = deduplicated

        assessed = self._assess_readiness(packet, diagnostics)
        families = {
            reference.grounding_kind for reference in packet.evidence_references
        }
        return SynthesisPacketValidationReport(
            packet_id=packet.packet_id,
            request_id=packet.request_id,
            mode=packet.mode,
            declared_readiness=packet.readiness,
            assessed_readiness=assessed,
            synthesis_ready=assessed is SynthesisReadinessStatus.READY,
            evidence_count=len(packet.evidence_references),
            family_count=len(families),
            diagnostics=diagnostics,
        )

    # ----------------------------------------------------------------- #
    # Diagnostic construction
    # ----------------------------------------------------------------- #
    @staticmethod
    def _diagnostic(
        code: GroundingDiagnosticCode,
        message: str,
        *,
        subject_id: str | None = None,
        grounding_kind: GroundingEvidenceKind | None = None,
    ) -> GroundingValidationDiagnostic:
        """Build one finding, truncating an over-long subject rather than failing.

        A subject identifier arrives from the packet under inspection, so it may
        itself be out of bounds on a tampered packet. Bounding it here keeps the
        report constructible: a guardrail that crashes on malformed input reports
        nothing at all, which is strictly worse than reporting a bounded subject.
        """

        bounded_subject = (
            None if subject_id is None else subject_id[:MAX_SYNTHESIS_ID_LENGTH]
        )
        return GroundingValidationDiagnostic(
            code=code,
            message=message[:MAX_SYNTHESIS_SUMMARY_LENGTH],
            subject_id=bounded_subject or None,
            grounding_kind=grounding_kind,
        )

    # ----------------------------------------------------------------- #
    # 1. Contract and policy versions
    # ----------------------------------------------------------------- #
    def _check_versions(
        self,
        packet: SynthesisContextPacket,
        declared_assembly: Any,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        if packet.schema_version != GROUNDED_SYNTHESIS_CONTRACT_VERSION:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION,
                    "packet declares a schema version this validator does not "
                    f"implement; expected {GROUNDED_SYNTHESIS_CONTRACT_VERSION!r}",
                    subject_id=packet.packet_id,
                )
            )
        if (
            declared_assembly is not None
            and declared_assembly != GROUNDING_CONTEXT_ASSEMBLY_VERSION
        ):
            # An unrecognized assembly policy is fail-closed, not ignored: its
            # eligibility, ranking and bounds rules are unknown, so none of the
            # packet's derived claims can be checked against anything.
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNSUPPORTED_ASSEMBLY_VERSION,
                    "packet declares an assembly version this validator does not "
                    f"implement; expected {GROUNDING_CONTEXT_ASSEMBLY_VERSION!r}",
                    subject_id=packet.packet_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 2. Evidence identity
    # ----------------------------------------------------------------- #
    def _check_evidence_identity(
        self,
        packet: SynthesisContextPacket,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Verify canonical evidence identity across the packet.

        The canonical key is ``(grounding_kind, NFC-normalized source record
        id)`` — the assembler's own key. Including the family is what stops two
        genuinely different records collapsing merely because two subsystems
        happen to use the same provider id; excluding it would invent an
        equivalence the assembler explicitly refuses to make.

        Everything here is computed from grouped dictionaries keyed on stable
        strings and reported in sorted order, so the findings do not depend on
        the order the references appear in.
        """

        by_identifier: dict[str, int] = {}
        by_canonical: dict[
            tuple[str, str], list[GroundingEvidenceReference]
        ] = {}
        unsupported: dict[GroundingEvidenceKind, int] = {}

        for reference in packet.evidence_references:
            evidence_id = _normalize_identity(reference.evidence_id)
            by_identifier[evidence_id] = by_identifier.get(evidence_id, 0) + 1
            canonical = _normalize_identity(
                reference.source_record_id or reference.evidence_id
            )
            key = (reference.grounding_kind.value, canonical)
            by_canonical.setdefault(key, []).append(reference)
            if reference.grounding_kind not in SUPPORTED_GROUNDING_KINDS:
                unsupported[reference.grounding_kind] = (
                    unsupported.get(reference.grounding_kind, 0) + 1
                )

        for evidence_id in sorted(by_identifier):
            count = by_identifier[evidence_id]
            if count > 1:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.DUPLICATE_EVIDENCE_IDENTIFIER,
                        f"{count} evidence references share one evidence identifier",
                        subject_id=evidence_id,
                    )
                )

        for key in sorted(by_canonical):
            group = by_canonical[key]
            if len(group) < 2:
                continue
            kind = group[0].grounding_kind
            subject = min(_normalize_identity(item.evidence_id) for item in group)
            sources = {_source_material(item) for item in group}
            materials = {_evidence_material(item) for item in group}
            if len(sources) > 1:
                # Two producers claiming the same canonical record is a source
                # identity conflict, not a duplicate: neither copy can be
                # preferred without deciding which producer to disbelieve.
                code = GroundingDiagnosticCode.CONFLICTING_SOURCE_IDENTITY
                detail = "declare conflicting source identities"
            elif len(materials) > 1:
                code = GroundingDiagnosticCode.CONFLICTING_EVIDENCE_IDENTITY
                detail = "carry materially different content"
            else:
                code = GroundingDiagnosticCode.REDUNDANT_EVIDENCE_IDENTITY
                detail = "are identical copies"
            diagnostics.append(
                self._diagnostic(
                    code,
                    f"{len(group)} evidence references share one canonical identity "
                    f"within this family and {detail}",
                    subject_id=subject,
                    grounding_kind=kind,
                )
            )

        for kind in sorted(unsupported, key=lambda item: item.value):
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNSUPPORTED_GROUNDING_KIND,
                    f"{unsupported[kind]} evidence reference(s) belong to a grounding "
                    "family Hive|Mind has no verified normalization for",
                    grounding_kind=kind,
                )
            )

    # ----------------------------------------------------------------- #
    # 3. Provenance
    # ----------------------------------------------------------------- #
    def _check_provenance(
        self,
        packet: SynthesisContextPacket,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Verify each reference can be traced back to what produced it."""

        for reference in packet.evidence_references:
            subject = reference.evidence_id
            kind = reference.grounding_kind

            pointer = getattr(reference.reference, "value", None)
            if not isinstance(pointer, str) or not pointer.strip():
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.MALFORMED_PROVENANCE_IDENTIFIER,
                        "evidence reference carries no usable pointer value",
                        subject_id=subject,
                        grounding_kind=kind,
                    )
                )

            record_id = reference.source_record_id
            if record_id is None or not record_id.strip():
                # Without the producing record's own id the reference cannot be
                # resolved back to its origin, which is the whole purpose of the
                # provenance chain (Phase 40A §6).
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.MISSING_PROVENANCE_REFERENCE,
                        "evidence reference declares no source record identifier",
                        subject_id=subject,
                        grounding_kind=kind,
                    )
                )

            if kind in _PROVENANCE_SOURCE_REQUIRED and reference.source is None:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.MISSING_PROVENANCE_SOURCE,
                        "subsystem-produced evidence declares no producing source",
                        subject_id=subject,
                        grounding_kind=kind,
                    )
                )

            expected = _EXPECTED_REFERENCE_KINDS.get(kind)
            reference_kind = getattr(reference.reference, "reference_kind", None)
            if (
                expected is not None
                and reference_kind is not None
                and reference_kind not in expected
            ):
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.UNEXPECTED_PROVENANCE_REFERENCE_KIND,
                        f"pointer kind {reference_kind.value!r} is outside the set "
                        "Hive|Mind's producers emit for this grounding family",
                        subject_id=subject,
                        grounding_kind=kind,
                    )
                )

    # ----------------------------------------------------------------- #
    # 4. Repository and source safety
    # ----------------------------------------------------------------- #
    def _check_source_safety(
        self,
        packet: SynthesisContextPacket,
        metadata: dict[str, Any],
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Preserve the Phase 40C fail-closed source-identity posture.

        Two independent signals:

        * the packet's own assembly diagnostics record that unsafe repository
          identity was encountered — a packet-scoped finding, deliberately *not*
          attached to any evidence reference, because the safe evidence that
          survived alongside it must not be misrepresented as unsafe;
        * a reference whose pointer is not the bounded, repository-relative,
          credential-free shape the contract promises — a record-scoped finding,
          so exactly the offending record is named and no other is implicated.

        Neither is ever normalized away into a trusted identity, and the report
        remains useful: the rest of the packet is still fully validated.
        """

        exclusions = metadata.get("exclusion_reasons")
        if isinstance(exclusions, dict):
            unsafe = exclusions.get("unsafe_repository_identity")
            if _is_count(unsafe) and unsafe > 0:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.UNSAFE_REPOSITORY_IDENTITY,
                        f"{unsafe} candidate(s) were excluded for unsafe repository "
                        "identity; the packet cannot be treated as safely grounded",
                        subject_id=packet.packet_id,
                    )
                )

        for reference in packet.evidence_references:
            pointer = getattr(reference.reference, "value", None)
            detail = getattr(reference.reference, "detail", None)
            reference_kind = getattr(reference.reference, "reference_kind", None)
            if not isinstance(pointer, str):
                continue
            if reference_kind is EvidenceReferenceKind.FILE_PATH and (
                _is_absolute_path(pointer) or _has_traversal(pointer)
            ):
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE,
                        "file pointer is not a bounded repository-relative path",
                        subject_id=reference.evidence_id,
                        grounding_kind=reference.grounding_kind,
                    )
                )
            candidates = [pointer]
            if isinstance(detail, str):
                candidates.append(detail)
            if any(_carries_url_credentials(item) for item in candidates):
                # The offending value is never echoed — reporting it would put the
                # credential into the report the guardrail exists to keep clean.
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.UNSAFE_SOURCE_REFERENCE,
                        "evidence pointer embeds credentials in a URL authority",
                        subject_id=reference.evidence_id,
                        grounding_kind=reference.grounding_kind,
                    )
                )

    # ----------------------------------------------------------------- #
    # 5. Cross-record references and context summaries
    # ----------------------------------------------------------------- #
    def _check_cross_references(
        self,
        packet: SynthesisContextPacket,
        assembler_declared: bool,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        known = {reference.evidence_id for reference in packet.evidence_references}

        for conflict in packet.conflicts:
            unknown = sorted(
                item for item in conflict.evidence_ids if item not in known
            )
            if unknown:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE,
                        f"conflict cites {len(unknown)} evidence id(s) the packet "
                        "does not carry",
                        subject_id=conflict.conflict_id,
                    )
                )
            resolved = [item for item in conflict.evidence_ids if item in known]
            if len(resolved) < 2:
                # A conflict is a relation between participants; with fewer than
                # two resolvable ones it asserts a disagreement the packet cannot
                # show, which is worse than carrying no conflict at all.
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE,
                        "conflict resolves fewer than two packet evidence records",
                        subject_id=conflict.conflict_id,
                    )
                )

        for summary in packet.context_summaries:
            unknown = sorted(item for item in summary.evidence_ids if item not in known)
            if unknown:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.DANGLING_EVIDENCE_REFERENCE,
                        f"context summary cites {len(unknown)} evidence id(s) the "
                        "packet does not carry",
                        subject_id=summary.summary_id,
                    )
                )
            if not summary.evidence_ids:
                # An unattributed narrative inside the grounded input boundary is
                # exactly what Phase 40A §6 forbids: it would let a future
                # synthesis stage read prose no evidence supports.
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.UNGROUNDED_CONTEXT_SUMMARY,
                        "context summary attributes itself to no evidence",
                        subject_id=summary.summary_id,
                    )
                )

        if assembler_declared and packet.context_summaries:
            # Phase 40C never summarizes; summaries are the one packet collection
            # that the packet identifier does not cover, so an assembler-declared
            # packet carrying them was edited after assembly.
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNEXPECTED_CONTEXT_SUMMARY,
                    f"{len(packet.context_summaries)} context summary/summaries are "
                    "present in a packet the assembler declares it produced, and the "
                    "assembler produces none",
                    subject_id=packet.packet_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 6. Bounds and overflow
    # ----------------------------------------------------------------- #
    def _check_bounds(
        self,
        packet: SynthesisContextPacket,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Confirm the packet is inside the bounds it was assembled under.

        Nothing is clipped, dropped, or repaired to bring a packet back inside a
        bound: an over-full packet is reported as over-full. Making it *look*
        valid by removing records is the failure mode this whole layer exists to
        prevent.
        """

        limits = self._limits
        for label, actual, ceiling in (
            ("evidence reference", len(packet.evidence_references), limits.max_evidence_items),
            ("conflict", len(packet.conflicts), limits.max_conflicts),
            ("missing-context", len(packet.missing_context), limits.max_missing_context),
            ("warning", len(packet.warnings), limits.max_warnings),
            (
                "context summary",
                len(packet.context_summaries),
                MAX_SYNTHESIS_CONTEXT_SUMMARIES,
            ),
        ):
            if actual > ceiling:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.PACKET_BOUND_EXCEEDED,
                        f"packet carries {actual} {label} entries, exceeding the "
                        f"bound of {ceiling}",
                        subject_id=packet.packet_id,
                    )
                )

        per_family: dict[GroundingEvidenceKind, int] = {}
        for reference in packet.evidence_references:
            per_family[reference.grounding_kind] = (
                per_family.get(reference.grounding_kind, 0) + 1
            )
        # The per-family cap exists to stop one family crowding out the others, so
        # it has no meaning when only one family contributed — the same condition
        # under which the assembler lifts it.
        if len(per_family) > 1:
            for kind in sorted(per_family, key=lambda item: item.value):
                if per_family[kind] > limits.max_items_per_kind:
                    diagnostics.append(
                        self._diagnostic(
                            GroundingDiagnosticCode.FAMILY_BOUND_EXCEEDED,
                            f"family carries {per_family[kind]} evidence references, "
                            f"exceeding the per-family bound of "
                            f"{limits.max_items_per_kind}",
                            grounding_kind=kind,
                        )
                    )

        for reference in packet.evidence_references:
            for label, value, ceiling in (
                ("evidence_id", reference.evidence_id, MAX_SYNTHESIS_ID_LENGTH),
                ("label", reference.label, MAX_SYNTHESIS_LABEL_LENGTH),
                ("summary", reference.summary, MAX_SYNTHESIS_SUMMARY_LENGTH),
            ):
                if isinstance(value, str) and len(value) > ceiling:
                    diagnostics.append(
                        self._diagnostic(
                            GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD,
                            f"evidence {label} is {len(value)} characters, exceeding "
                            f"the bound of {ceiling}",
                            subject_id=reference.evidence_id,
                            grounding_kind=reference.grounding_kind,
                        )
                    )
            if (
                isinstance(reference.metadata, dict)
                and len(reference.metadata) > MAX_SYNTHESIS_METADATA_ENTRIES
            ):
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD,
                        f"evidence metadata carries {len(reference.metadata)} entries, "
                        f"exceeding the bound of {MAX_SYNTHESIS_METADATA_ENTRIES}",
                        subject_id=reference.evidence_id,
                        grounding_kind=reference.grounding_kind,
                    )
                )

        if (
            isinstance(packet.metadata, dict)
            and len(packet.metadata) > MAX_SYNTHESIS_METADATA_ENTRIES
        ):
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.OVERSIZED_PACKET_FIELD,
                    f"packet metadata carries {len(packet.metadata)} entries, "
                    f"exceeding the bound of {MAX_SYNTHESIS_METADATA_ENTRIES}",
                    subject_id=packet.packet_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 7. Packet self-consistency
    # ----------------------------------------------------------------- #
    def _check_packet_consistency(
        self,
        packet: SynthesisContextPacket,
        metadata: dict[str, Any],
        assembler_declared: bool,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Reconcile every declared total against the packet's actual contents."""

        actual_evidence = len(packet.evidence_references)
        accepted = metadata.get("candidates_accepted")
        inspected = metadata.get("candidates_inspected")
        if _is_count(accepted) and accepted != actual_evidence:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH,
                    f"packet declares {accepted} accepted evidence item(s) but carries "
                    f"{actual_evidence}",
                    subject_id=packet.packet_id,
                )
            )
        if _is_count(accepted) and _is_count(inspected) and accepted > inspected:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.EVIDENCE_COUNT_MISMATCH,
                    f"packet declares {accepted} accepted item(s) from only "
                    f"{inspected} inspected candidate(s)",
                    subject_id=packet.packet_id,
                )
            )

        actual_critical = sum(
            1
            for conflict in packet.conflicts
            if conflict.severity is ContradictionSeverity.CRITICAL
        )
        declared_critical = metadata.get("critical_conflict_count")
        if _is_count(declared_critical) and declared_critical != actual_critical:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.CONFLICT_COUNT_MISMATCH,
                    f"packet declares {declared_critical} critical conflict(s) but "
                    f"carries {actual_critical}",
                    subject_id=packet.packet_id,
                )
            )

        self._check_coverage(packet, assembler_declared, diagnostics)
        self._check_truncation(packet, metadata, diagnostics)
        self._check_readiness_claims(packet, metadata, diagnostics)

    def _check_coverage(
        self,
        packet: SynthesisContextPacket,
        assembler_declared: bool,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        actual: dict[GroundingEvidenceKind, int] = {}
        for reference in packet.evidence_references:
            actual[reference.grounding_kind] = (
                actual.get(reference.grounding_kind, 0) + 1
            )
        declared = {entry.grounding_kind: entry for entry in packet.source_coverage}

        # Coverage is optional in the Phase 40B contract, so an entirely absent
        # coverage list is not a defect. A *partial* one is: it reports on some
        # families while staying silent about others the packet actually carries.
        require_entries = assembler_declared or bool(packet.source_coverage)
        if require_entries:
            for kind in sorted(actual, key=lambda item: item.value):
                if kind not in declared:
                    diagnostics.append(
                        self._diagnostic(
                            GroundingDiagnosticCode.MISSING_COVERAGE_ENTRY,
                            f"packet carries {actual[kind]} evidence reference(s) from "
                            "this family but declares no coverage entry for it",
                            grounding_kind=kind,
                        )
                    )

        for kind in sorted(declared, key=lambda item: item.value):
            entry = declared[kind]
            observed = actual.get(kind, 0)
            if entry.referenced_count != observed:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.COVERAGE_COUNT_MISMATCH,
                        f"coverage declares {entry.referenced_count} reference(s) for "
                        f"this family but the packet carries {observed}",
                        grounding_kind=kind,
                    )
                )

    def _check_truncation(
        self,
        packet: SynthesisContextPacket,
        metadata: dict[str, Any],
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        exclusions = metadata.get("exclusion_reasons")
        bounds_excluded = (
            exclusions.get("bounds_exceeded") if isinstance(exclusions, dict) else None
        )
        items_truncated = metadata.get("items_truncated")
        text_truncations = metadata.get("text_truncations")

        if _is_count(items_truncated) and _is_count(bounds_excluded):
            if items_truncated != bounds_excluded:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.INVALID_TRUNCATION_CLAIM,
                        f"packet declares {items_truncated} truncated item(s) but "
                        f"{bounds_excluded} bounds-based exclusion(s)",
                        subject_id=packet.packet_id,
                    )
                )
        elif _is_count(items_truncated) and items_truncated > 0:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.INVALID_TRUNCATION_CLAIM,
                    f"packet declares {items_truncated} truncated item(s) but records "
                    "no bounds-based exclusion",
                    subject_id=packet.packet_id,
                )
            )

        truncated = (_is_count(items_truncated) and items_truncated > 0) or (
            _is_count(text_truncations) and text_truncations > 0
        )
        if truncated and not any(
            warning.code is SynthesisWarningCode.BOUNDS_EXCEEDED
            for warning in packet.warnings
        ):
            # Truncation without the warning that represents it is a packet
            # claiming completeness it does not have.
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNDECLARED_TRUNCATION,
                    "packet records truncation but carries no bounds-exceeded warning",
                    subject_id=packet.packet_id,
                )
            )

    def _check_readiness_claims(
        self,
        packet: SynthesisContextPacket,
        metadata: dict[str, Any],
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Reconcile the declared readiness with the evidence and the reason slug.

        The Phase 40B model already rejects the three impossible ``ready``
        packets, so these restatements only fire for a packet that reached the
        validator without full model construction. They are kept because Phase 40D
        is the trust boundary: a guardrail that assumes its input was validated
        elsewhere guards nothing.
        """

        if packet.readiness is SynthesisReadinessStatus.READY:
            if not packet.evidence_references:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                        "packet claims 'ready' while carrying no evidence",
                        subject_id=packet.packet_id,
                    )
                )
            if packet.missing_context:
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                        f"packet claims 'ready' while declaring "
                        f"{len(packet.missing_context)} unresolved context gap(s)",
                        subject_id=packet.packet_id,
                    )
                )
            if any(
                conflict.severity is ContradictionSeverity.CRITICAL
                for conflict in packet.conflicts
            ):
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                        "packet claims 'ready' while carrying a critical conflict",
                        subject_id=packet.packet_id,
                    )
                )

        reason = metadata.get("readiness_reason")
        if not isinstance(reason, str):
            return

        if (
            reason in _BLOCKING_READINESS_REASONS
            and packet.readiness is not SynthesisReadinessStatus.BLOCKED
        ):
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    f"packet records a blocking readiness reason but declares "
                    f"readiness {packet.readiness.value!r}",
                    subject_id=packet.packet_id,
                )
            )
        if (
            reason in _READY_READINESS_REASONS
            and packet.readiness is not SynthesisReadinessStatus.READY
        ):
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    f"packet records a ready readiness reason but declares readiness "
                    f"{packet.readiness.value!r}",
                    subject_id=packet.packet_id,
                )
            )
        if reason == "ready" and packet.warnings:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    f"packet records an unqualified 'ready' reason while carrying "
                    f"{len(packet.warnings)} warning(s)",
                    subject_id=packet.packet_id,
                )
            )
        if reason == "ready_with_warnings" and not packet.warnings:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    "packet records a 'ready with warnings' reason but carries no "
                    "warnings",
                    subject_id=packet.packet_id,
                )
            )
        if reason == "no_eligible_evidence" and packet.evidence_references:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    f"packet records that no evidence was eligible but carries "
                    f"{len(packet.evidence_references)} evidence reference(s)",
                    subject_id=packet.packet_id,
                )
            )
        if reason == "missing_requested_context" and not packet.missing_context:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.READINESS_CLAIM_UNSUPPORTED,
                    "packet records missing requested context but declares no gaps",
                    subject_id=packet.packet_id,
                )
            )
        if reason in _CRITICAL_LOSS_READINESS_REASONS:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.UNKNOWN_CRITICAL_EVIDENCE,
                    "packet records critical grounding it could not represent; the "
                    "evidence that mattered most is not in the packet",
                    subject_id=packet.packet_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 8. Canonical ordering
    # ----------------------------------------------------------------- #
    def _check_ordering(
        self,
        packet: SynthesisContextPacket,
        assembler_declared: bool,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Check the collections whose ordering the assembler actually claims.

        ``evidence_references`` is deliberately excluded: the assembler emits it
        in *rank* order, which is meaningful rather than lexical, and the Phase
        40B contract explicitly preserves caller ordering. Only the three
        collections the assembler sorts canonically are checked, and only for a
        packet that declares assembler provenance — a hand-built packet never made
        the claim.

        Advisory rather than blocking: reordering a packet changes no claim,
        drops no evidence, and breaks no provenance chain.
        """

        if not assembler_declared:
            return
        for label, keys in (
            ("conflicts", [conflict.conflict_id for conflict in packet.conflicts]),
            (
                "source coverage",
                [entry.grounding_kind.value for entry in packet.source_coverage],
            ),
            (
                "warnings",
                [
                    (warning.code.value, warning.message, warning.subject_id or "")
                    for warning in packet.warnings
                ],
            ),
        ):
            if list(keys) != sorted(keys):
                diagnostics.append(
                    self._diagnostic(
                        GroundingDiagnosticCode.NON_CANONICAL_ORDERING,
                        f"packet {label} are not in the canonical order the assembler "
                        "produces",
                        subject_id=packet.packet_id,
                    )
                )

    # ----------------------------------------------------------------- #
    # 9. Packet identity re-derivation
    # ----------------------------------------------------------------- #
    def _check_packet_identity(
        self,
        packet: SynthesisContextPacket,
        declared_assembly: Any,
        diagnostics: list[GroundingValidationDiagnostic],
    ) -> None:
        """Re-derive the packet identifier and compare it with the declared one.

        The strongest available tamper check, and the reason it is worth its
        coupling to the assembler: the Phase 40C identifier is a content-derived
        hash over the packet's mode, readiness, assembly time, ordered evidence
        ids, conflicts, gaps, coverage and warnings. Editing any of them after
        assembly changes the derived id, so a packet whose contents were altered
        can no longer present the id it was assembled under.

        Run only when the packet declares the assembly version that produced that
        derivation. A packet from any other producer never claimed a derived
        identifier, and holding it to one would reject valid input.
        """

        if declared_assembly != GROUNDING_CONTEXT_ASSEMBLY_VERSION:
            return
        try:
            expected = derive_context_packet_identity(
                schema_version=packet.schema_version,
                request_id=packet.request_id,
                correlation_id=packet.correlation_id,
                mode=packet.mode,
                readiness=packet.readiness,
                assembled_at=packet.assembled_at,
                evidence_references=packet.evidence_references,
                conflicts=packet.conflicts,
                missing_context=packet.missing_context,
                source_coverage=packet.source_coverage,
                warnings=packet.warnings,
            )
        except Exception:
            # A packet whose material cannot even be canonicalized cannot have
            # its identity confirmed, which is itself the finding.
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH,
                    "packet identity could not be re-derived from its contents",
                    subject_id=packet.packet_id,
                )
            )
            return
        if expected != packet.packet_id:
            diagnostics.append(
                self._diagnostic(
                    GroundingDiagnosticCode.PACKET_IDENTITY_MISMATCH,
                    "packet identifier does not match the identity derived from the "
                    "packet's own contents",
                    subject_id=packet.packet_id,
                )
            )

    # ----------------------------------------------------------------- #
    # 10. Readiness determination
    # ----------------------------------------------------------------- #
    @staticmethod
    def _assess_readiness(
        packet: SynthesisContextPacket,
        diagnostics: Sequence[GroundingValidationDiagnostic],
    ) -> SynthesisReadinessStatus:
        """Compute readiness rather than reading the packet's claim.

        Any blocking finding blocks, whatever the packet says. Otherwise the
        packet's own declaration stands: a validator that upgraded an honestly
        ``context_required`` packet to ``ready`` would be re-assembling it, and a
        validator that downgraded a clean ``ready`` packet over advisory findings
        would make "ready with warnings" unreachable — which Phase 40C
        deliberately made reachable.
        """

        if any(item.blocking for item in diagnostics):
            return SynthesisReadinessStatus.BLOCKED
        return packet.readiness


def validate_synthesis_context_packet(
    packet: SynthesisContextPacket,
    *,
    limits: GroundingAssemblyLimits | None = None,
) -> SynthesisPacketValidationReport:
    """Module-level convenience wrapper.

    Mirrors the ``assemble_grounding_context`` entry-point convention so a caller
    that needs one call does not have to manage a validator instance.
    """

    return SynthesisContextPacketValidator(limits=limits).validate(packet)
