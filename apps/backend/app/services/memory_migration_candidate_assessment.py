"""Phase 40G — deterministic, pure, read-only Migration Candidate Assessment.

The dry-run gate between Phase 40F candidate projection and any later
human-reviewed persistence (Phase 40H, whose durable medium remains deliberately
undecided). It answers exactly one question:

    Given a complete set of projected :class:`~app.models.memory_migration_projection.MemoryMigrationCandidate`
    records and the Phase 40F diagnostics that came with them, is the set ready for
    a human to review — and if not, precisely which set-level problems stand in the
    way?

It answers it and stops. Phase 40G persists nothing, imports nothing, mutates no
candidate, deletes nothing, ranks nothing, verifies nothing, and selects no
durable medium. It produces a typed
:class:`~app.models.memory_migration_candidate_assessment.MigrationCandidateAssessmentReport`
and nothing else.

**Pure and read-only.** :meth:`MemoryMigrationCandidateAssessor.assess` takes a
candidate sequence and a diagnostic sequence and returns a report. It never
mutates its inputs, never removes a duplicate, never rewrites an identifier, and
never reorders the candidates it was given. It reads no clock, opens no file,
touches no environment, and generates no random value, so the same input always
yields a byte-equivalent report in the same canonical order. That purity is
enforced structurally by an AST check in
``tests/test_memory_migration_candidate_assessment.py``, mirroring the Phase 40F
projector's purity test.

**Set-level, order-independent detection.** Every finding is computed from
dictionaries keyed on stable, content-derived identities and reported in canonical
order, so no finding depends on the order candidates or diagnostics happened to
arrive in. Reordering the input yields the identical report.

**Duplicates are grouped, conflicts block.** Two candidates occupy the *same
source slot* when they share a source identity (everything that locates them back
to origin except their content). If they also share a content digest they are an
identical duplicate — the same ``candidate_id`` occurring more than once, grouped
and counted, never removed, and treated as advisory. If they do not, the slot
resolved to conflicting content — a blocking finding that keeps every involved
candidate visible through its safe id without reproducing any content.

**Fail-closed.** Any blocking finding — a source-identity conflict, an unresolved
Phase 40F error, or a diagnostic list that had to be truncated — forces the
verdict to ``blocked``. An advisory-only set is ``review_with_warnings``; only a
set with nothing requiring attention is ``ready_for_review``. The readiness is
derived by the report from its own findings and can never be asserted.

**No raw content.** A report carries closed-enum literals, counts, stable
candidate-local identifiers, and content *digests* (non-reversible hashes) only.
No candidate body, export byte, or conversation text appears anywhere, and carried
Phase 40F diagnostics are content-free by their own contract.
"""

from __future__ import annotations

import unicodedata
from typing import Sequence

from app.models.memory_migration_projection import (
    MemoryMigrationCandidate,
    MigrationProjectionDiagnostic,
    MigrationProjectionSeverity,
)
from app.models.memory_migration_candidate_assessment import (
    MAX_ASSESSED_CANDIDATES,
    MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS,
    MigrationCandidateAssessmentDiagnostic,
    MigrationCandidateAssessmentDiagnosticCode,
    MigrationCandidateAssessmentReport,
    MigrationCandidateAssessmentSeverity,
    MigrationCandidateCoverage,
    MigrationCandidateDuplicateGroup,
    MigrationReviewReadiness,
    MigrationSourceIdentityConflict,
    derive_ambiguous_order_group_id,
    derive_candidate_assessment_report_id,
    derive_candidate_source_identity,
    derive_duplicate_group_id,
    derive_source_conflict_id,
    resolve_review_readiness,
)

# --------------------------------------------------------------------------- #
# Assessment policy version.
#
# A stable identifier for the *ruleset this service applies*, separate from the
# contract and result-shape versions — the three-way separation Phase
# 40C/40D/40E/40F established. Tightening a detection rule changes this, not the
# contracts.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_POLICY_VERSION = (
    "memory-migration-candidate-assessment-policy.v1"
)


def _degenerate_content(content: str) -> bool:
    """Whether a candidate carries no meaningful reviewable content.

    A candidate can be contract-valid (``content`` has length ≥ 1) yet hold only
    whitespace, which is nothing for a human to review. The check NFC-normalizes
    then strips: it does **not** weaken the candidate model or invent a length
    threshold, it only asks whether anything survives normalization and stripping.
    """

    return unicodedata.normalize("NFC", content).strip() == ""


class MemoryMigrationCandidateAssessor:
    """Assess one projected candidate set against the Phase 40G dry-run policy.

    Stateless between calls: nothing is retained or cached, and every returned
    report is freshly constructed from the inputs alone. The assessor is therefore
    safe to share, adds no persistence surface, and cannot let one assessment
    influence the next.
    """

    @property
    def policy_version(self) -> str:
        return MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_POLICY_VERSION

    # ----------------------------------------------------------------- #
    # Public entry point
    # ----------------------------------------------------------------- #
    def assess(
        self,
        *,
        candidates: Sequence[MemoryMigrationCandidate],
        projection_diagnostics: Sequence[MigrationProjectionDiagnostic] = (),
    ) -> MigrationCandidateAssessmentReport:
        """Return the deterministic dry-run report for a candidate set.

        The inputs are read and never written. Detection runs in a fixed order,
        but the order is an implementation detail: every finding is collected into
        canonically-ordered, content-addressed structures, so no check can hide
        another and no reordering of the inputs could change the report.

        A candidate set larger than :data:`MAX_ASSESSED_CANDIDATES` is refused with
        a ``ValueError`` rather than assessed partially — dropping candidates to
        fit would defeat the no-deletion guarantee, and a well-formed pipeline
        never exceeds the Phase 40F per-result ceiling.
        """

        candidate_list = list(candidates)
        if len(candidate_list) > MAX_ASSESSED_CANDIDATES:
            raise ValueError(
                f"candidate set of {len(candidate_list)} exceeds the assessment bound "
                f"of {MAX_ASSESSED_CANDIDATES}; assess within the Phase 40F ceiling"
            )

        # Precompute each candidate's source identity once.
        source_ids = [self._source_identity(candidate) for candidate in candidate_list]

        findings: list[MigrationCandidateAssessmentDiagnostic] = []
        duplicate_groups = self._detect_duplicates(
            candidate_list, source_ids, findings
        )
        conflicts = self._detect_conflicts(candidate_list, source_ids, findings)
        self._detect_ambiguous_order(candidate_list, findings)
        self._detect_degenerate(candidate_list, source_ids, findings)
        self._carry_projection_diagnostics(projection_diagnostics, findings)

        diagnostics = self._finalize_diagnostics(findings)
        coverage = self._build_coverage(
            candidate_list, source_ids, duplicate_groups, conflicts
        )

        by_severity, by_code, blocking, advisory = self._count_diagnostics(diagnostics)
        readiness = resolve_review_readiness(
            [diagnostic.severity for diagnostic in diagnostics]
        )
        report_id = derive_candidate_assessment_report_id(
            candidate_count=len(candidate_list),
            coverage=coverage,
            duplicate_groups=duplicate_groups,
            conflicts=conflicts,
            diagnostics=diagnostics,
            review_readiness=readiness,
        )
        return MigrationCandidateAssessmentReport(
            report_id=report_id,
            candidate_count=len(candidate_list),
            coverage=coverage,
            duplicate_groups=duplicate_groups,
            conflicts=conflicts,
            diagnostics=diagnostics,
            diagnostic_counts_by_severity=by_severity,
            diagnostic_counts_by_code=by_code,
            blocking_diagnostic_count=blocking,
            advisory_diagnostic_count=advisory,
            review_readiness=readiness,
        )

    # ----------------------------------------------------------------- #
    # Identity
    # ----------------------------------------------------------------- #
    @staticmethod
    def _source_identity(candidate: MemoryMigrationCandidate) -> str:
        provenance = candidate.provenance
        return derive_candidate_source_identity(
            bundle_fingerprint=provenance.bundle_fingerprint,
            source_artifact_fingerprint=provenance.source_artifact_fingerprint,
            source_local_id=provenance.source_local_id,
            source_role=provenance.source_role.value,
            source_sequence_index=candidate.source_sequence_index,
            chunk_index=candidate.chunk_index,
        )

    # ----------------------------------------------------------------- #
    # Duplicate detection (advisory)
    # ----------------------------------------------------------------- #
    def _detect_duplicates(
        self,
        candidates: list[MemoryMigrationCandidate],
        source_ids: list[str],
        findings: list[MigrationCandidateAssessmentDiagnostic],
    ) -> list[MigrationCandidateDuplicateGroup]:
        """Group candidates sharing a source identity *and* a content digest.

        Grouped by ``(source_identity, content_digest)``. Every candidate sharing
        such a key also shares its ``candidate_id``, so a group is one id occurring
        more than once. Groups are emitted in canonical order and nothing is
        removed.
        """

        occurrences: dict[tuple[str, str], list[MemoryMigrationCandidate]] = {}
        for candidate, source_id in zip(candidates, source_ids):
            occurrences.setdefault((source_id, candidate.content_digest), []).append(
                candidate
            )

        groups: list[MigrationCandidateDuplicateGroup] = []
        for (source_id, content_digest), members in occurrences.items():
            if len(members) < 2:
                continue
            candidate_id = members[0].candidate_id
            group_id = derive_duplicate_group_id(
                source_identity=source_id, content_digest=content_digest
            )
            groups.append(
                MigrationCandidateDuplicateGroup(
                    group_id=group_id,
                    source_identity=source_id,
                    content_digest=content_digest,
                    candidate_id=candidate_id,
                    occurrence_count=len(members),
                )
            )
            findings.append(
                MigrationCandidateAssessmentDiagnostic(
                    code=MigrationCandidateAssessmentDiagnosticCode.DUPLICATE_CANDIDATE,
                    message=(
                        f"{len(members)} identical candidates share one source "
                        "identity and content digest; they are grouped and counted, "
                        "never removed"
                    ),
                    subject_id=candidate_id,
                    group_id=group_id,
                    count=len(members),
                )
            )
        groups.sort(key=lambda group: group.sort_key())
        return groups

    # ----------------------------------------------------------------- #
    # Conflict detection (blocking)
    # ----------------------------------------------------------------- #
    def _detect_conflicts(
        self,
        candidates: list[MemoryMigrationCandidate],
        source_ids: list[str],
        findings: list[MigrationCandidateAssessmentDiagnostic],
    ) -> list[MigrationSourceIdentityConflict]:
        """Detect a source identity resolving to materially different content.

        Grouped by source identity; a source identity carrying more than one
        distinct content digest is a conflict. All involved candidates stay visible
        through their distinct ``candidate_id`` values, in canonical order.
        """

        by_source: dict[str, dict[str, str]] = {}
        for candidate, source_id in zip(candidates, source_ids):
            # Map content_digest -> candidate_id; identical digests share an id.
            by_source.setdefault(source_id, {})[candidate.content_digest] = (
                candidate.candidate_id
            )

        conflicts: list[MigrationSourceIdentityConflict] = []
        for source_id, digest_to_id in by_source.items():
            if len(digest_to_id) < 2:
                continue
            member_ids = sorted(set(digest_to_id.values()))
            conflict_id = derive_source_conflict_id(source_identity=source_id)
            conflicts.append(
                MigrationSourceIdentityConflict(
                    conflict_id=conflict_id,
                    source_identity=source_id,
                    distinct_content_digest_count=len(digest_to_id),
                    member_candidate_ids=member_ids,
                    member_count=len(member_ids),
                )
            )
            findings.append(
                MigrationCandidateAssessmentDiagnostic(
                    code=(
                        MigrationCandidateAssessmentDiagnosticCode.CONFLICTING_SOURCE_IDENTITY
                    ),
                    message=(
                        f"one source identity resolves to {len(digest_to_id)} distinct "
                        "candidate contents; a reviewer cannot tell which is the real "
                        "material"
                    ),
                    group_id=conflict_id,
                    count=len(member_ids),
                )
            )
        conflicts.sort(key=lambda conflict: conflict.sort_key())
        return conflicts

    # ----------------------------------------------------------------- #
    # Ambiguous source order (advisory)
    # ----------------------------------------------------------------- #
    def _detect_ambiguous_order(
        self,
        candidates: list[MemoryMigrationCandidate],
        findings: list[MigrationCandidateAssessmentDiagnostic],
    ) -> None:
        """Detect distinct source entries claiming one source-sequence position.

        Scoped to ``(bundle_fingerprint, source_artifact_fingerprint)`` and a
        single ``source_sequence_index``: a collision is more than one distinct
        ``source_local_id`` at that position within that scope. Chunks of one item
        share a ``source_local_id`` and never collide, and distinct artifacts or
        bundles never collide because the scope includes their fingerprints.
        """

        scope: dict[tuple[str, str, int], set[str]] = {}
        for candidate in candidates:
            provenance = candidate.provenance
            key = (
                provenance.bundle_fingerprint,
                provenance.source_artifact_fingerprint,
                candidate.source_sequence_index,
            )
            scope.setdefault(key, set()).add(provenance.source_local_id)

        for (bundle_fp, artifact_fp, sequence_index), local_ids in scope.items():
            if len(local_ids) < 2:
                continue
            group_id = derive_ambiguous_order_group_id(
                bundle_fingerprint=bundle_fp,
                source_artifact_fingerprint=artifact_fp,
                source_sequence_index=sequence_index,
            )
            findings.append(
                MigrationCandidateAssessmentDiagnostic(
                    code=(
                        MigrationCandidateAssessmentDiagnosticCode.AMBIGUOUS_SOURCE_ORDER
                    ),
                    message=(
                        f"{len(local_ids)} distinct source entries claim one source "
                        "sequence position within one artifact; their order is "
                        "ambiguous"
                    ),
                    group_id=group_id,
                    count=len(local_ids),
                )
            )

    # ----------------------------------------------------------------- #
    # Degenerate candidates (advisory)
    # ----------------------------------------------------------------- #
    def _detect_degenerate(
        self,
        candidates: list[MemoryMigrationCandidate],
        source_ids: list[str],
        findings: list[MigrationCandidateAssessmentDiagnostic],
    ) -> None:
        """Flag contract-valid candidates that carry no reviewable content.

        Reported once per distinct ``candidate_id`` so a duplicated degenerate
        candidate does not crowd the diagnostic list; the count says how many
        occurrences shared the id.
        """

        degenerate: dict[str, int] = {}
        for candidate in candidates:
            if _degenerate_content(candidate.content):
                degenerate[candidate.candidate_id] = (
                    degenerate.get(candidate.candidate_id, 0) + 1
                )
        for candidate_id in sorted(degenerate):
            findings.append(
                MigrationCandidateAssessmentDiagnostic(
                    code=(
                        MigrationCandidateAssessmentDiagnosticCode.EMPTY_OR_DEGENERATE_CANDIDATE
                    ),
                    message=(
                        "candidate content is whitespace-only after normalization and "
                        "carries nothing for a human to review"
                    ),
                    subject_id=candidate_id,
                    count=degenerate[candidate_id],
                )
            )

    # ----------------------------------------------------------------- #
    # Carried Phase 40F diagnostics
    # ----------------------------------------------------------------- #
    def _carry_projection_diagnostics(
        self,
        projection_diagnostics: Sequence[MigrationProjectionDiagnostic],
        findings: list[MigrationCandidateAssessmentDiagnostic],
    ) -> None:
        """Carry each Phase 40F finding forward, preserving its original severity.

        A Phase 40F ``error`` becomes a blocking unresolved-projection-error and an
        ``info`` becomes an advisory projection-truncation warning. The original
        typed diagnostic is preserved verbatim in ``carried`` (it is content-free
        by its own contract), so no information and no severity is lost or
        downgraded.
        """

        for diagnostic in projection_diagnostics:
            if diagnostic.severity is MigrationProjectionSeverity.ERROR:
                code = (
                    MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR
                )
                message = (
                    "an unresolved Phase 40F projection error is carried forward; the "
                    "candidate set cannot be treated as review-ready"
                )
            else:
                code = (
                    MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING
                )
                message = (
                    "a Phase 40F bounded-skip/overflow finding is carried forward for "
                    "reviewer awareness"
                )
            findings.append(
                MigrationCandidateAssessmentDiagnostic(
                    code=code,
                    message=message,
                    subject_id=diagnostic.subject_id,
                    count=diagnostic.count,
                    carried=diagnostic,
                )
            )

    # ----------------------------------------------------------------- #
    # Coverage
    # ----------------------------------------------------------------- #
    @staticmethod
    def _build_coverage(
        candidates: list[MemoryMigrationCandidate],
        source_ids: list[str],
        duplicate_groups: list[MigrationCandidateDuplicateGroup],
        conflicts: list[MigrationSourceIdentityConflict],
    ) -> MigrationCandidateCoverage:
        counts_by_role: dict[str, int] = {}
        counts_by_source_type: dict[str, int] = {}
        for candidate in candidates:
            role = candidate.provenance.source_role.value
            counts_by_role[role] = counts_by_role.get(role, 0) + 1
            source_type = candidate.provenance.source.source_type.value
            counts_by_source_type[source_type] = (
                counts_by_source_type.get(source_type, 0) + 1
            )
        return MigrationCandidateCoverage(
            total_candidates=len(candidates),
            counts_by_role=counts_by_role,
            counts_by_source_type=counts_by_source_type,
            distinct_source_identity_count=len(set(source_ids)),
            duplicate_group_count=len(duplicate_groups),
            conflict_count=len(conflicts),
        )

    # ----------------------------------------------------------------- #
    # Diagnostic bounding
    # ----------------------------------------------------------------- #
    def _finalize_diagnostics(
        self,
        findings: Sequence[MigrationCandidateAssessmentDiagnostic],
    ) -> list[MigrationCandidateAssessmentDiagnostic]:
        """Sort, deduplicate, and bound the finding list without softening severity.

        Deduplication collapses byte-identical findings; truncation retains findings
        **most-severe-first** and only then re-sorts canonically, so the retained
        set still contains the most severe severity present and the derived verdict
        cannot be softened by truncating. The truncation notice is itself blocking:
        a set that produced more findings than a report can carry has not been fully
        described and cannot be treated as ready.
        """

        ordered = sorted(findings, key=lambda item: item.sort_key())
        deduplicated: list[MigrationCandidateAssessmentDiagnostic] = []
        seen: set[tuple] = set()
        for finding in ordered:
            key = finding.sort_key()
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(finding)

        if len(deduplicated) <= MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS:
            return deduplicated

        by_severity = sorted(
            deduplicated,
            key=lambda item: (-_severity_rank(item), item.sort_key()),
        )
        kept = by_severity[: MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS - 1]
        kept.append(
            MigrationCandidateAssessmentDiagnostic(
                code=MigrationCandidateAssessmentDiagnosticCode.DIAGNOSTICS_TRUNCATED,
                message=(
                    f"{len(deduplicated) - len(kept)} further finding(s) were omitted "
                    f"to satisfy the {MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS} diagnostic "
                    "bound; the candidate set is not fully described and cannot be "
                    "treated as ready"
                ),
            )
        )
        return sorted(kept, key=lambda item: item.sort_key())

    # ----------------------------------------------------------------- #
    # Diagnostic counts
    # ----------------------------------------------------------------- #
    @staticmethod
    def _count_diagnostics(
        diagnostics: Sequence[MigrationCandidateAssessmentDiagnostic],
    ) -> tuple[dict[str, int], dict[str, int], int, int]:
        by_severity: dict[str, int] = {}
        by_code: dict[str, int] = {}
        blocking = 0
        advisory = 0
        for diagnostic in diagnostics:
            severity = diagnostic.severity
            assert severity is not None  # severity is code-derived at construction
            by_severity[severity.value] = by_severity.get(severity.value, 0) + 1
            by_code[diagnostic.code.value] = by_code.get(diagnostic.code.value, 0) + 1
            if severity is MigrationCandidateAssessmentSeverity.BLOCKING:
                blocking += 1
            else:
                advisory += 1
        return by_severity, by_code, blocking, advisory


def _severity_rank(diagnostic: MigrationCandidateAssessmentDiagnostic) -> int:
    """Order a finding by severity for truncation retention (blocking outranks)."""

    return {
        MigrationCandidateAssessmentSeverity.ADVISORY: 0,
        MigrationCandidateAssessmentSeverity.BLOCKING: 1,
    }[diagnostic.severity or MigrationCandidateAssessmentSeverity.BLOCKING]


def assess_memory_migration_candidates(
    candidates: Sequence[MemoryMigrationCandidate],
    *,
    projection_diagnostics: Sequence[MigrationProjectionDiagnostic] = (),
) -> MigrationCandidateAssessmentReport:
    """Module-level convenience wrapper.

    Mirrors the ``assess_memory_migration_intake`` /
    ``validate_synthesis_context_packet`` entry-point convention so a caller that
    needs one call does not have to manage an assessor instance.
    """

    return MemoryMigrationCandidateAssessor().assess(
        candidates=candidates, projection_diagnostics=projection_diagnostics
    )
