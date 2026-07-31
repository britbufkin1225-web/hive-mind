"""Phase 40G — Migration Candidate Assessment (Dry-Run) tests.

Covers the set-level dry-run gate over projected Phase 40F candidates: empty and
clean sets, advisory-only and blocking verdicts, byte-stable and order-independent
reports, duplicate grouping (never dropping), source-identity conflict detection,
ambiguous source order (with no false cross-scope collisions), degenerate-candidate
detection, carried Phase 40F findings preserving severity, fail-closed readiness,
no-raw-content safety, aggregate coverage, stable content-addressed identity,
input immutability, bounded-collection behavior, Unicode normalization, canonical
serialization/round-trip, and the structural purity of the assessor.

Every test drives the pure assessor from explicit, fully-validated fixtures — no
bytes, no clock, no randomness — so a passing run proves determinism rather than
assuming it.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.models.active_memory import (
    LifecycleState,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models.memory_migration import (
    CANDIDATE_MEMORY_POLICY,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
)
from app.models.memory_migration_projection import (
    MemoryMigrationCandidate,
    MigrationCandidateProvenance,
    MigrationCandidateRole,
    MigrationProjectionDiagnostic,
    MigrationProjectionDiagnosticCode,
    MigrationProjectionSeverity,
    derive_candidate_content_digest,
    derive_candidate_id,
)
from app.models.memory_migration_candidate_assessment import (
    MAX_ASSESSED_CANDIDATES,
    MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS,
    MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION,
    MigrationCandidateAssessmentDiagnostic,
    MigrationCandidateAssessmentDiagnosticCode,
    MigrationCandidateAssessmentReport,
    MigrationCandidateAssessmentSeverity,
    MigrationReviewReadiness,
    resolve_review_readiness,
)
from app.services import (
    memory_migration_candidate_assessment as assessment_module,
)
from app.services.memory_migration_candidate_assessment import (
    MemoryMigrationCandidateAssessor,
    assess_memory_migration_candidates,
)

BUNDLE_FP = "mm-bundle-000000000000000000000000"
ARTIFACT_FP = "mm-artifact-000000000000000000000000"
OBSERVED_SHA256 = "c" * 64


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _provenance(**overrides: Any) -> MigrationCandidateProvenance:
    fields: dict[str, Any] = {
        "bundle_id": "bundle-1",
        "bundle_fingerprint": BUNDLE_FP,
        "source_artifact_id": "artifact-1",
        "source_artifact_fingerprint": ARTIFACT_FP,
        "source_artifact_format": MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        "source_container": MigrationContainerKind.SINGLE_FILE,
        "observed_digest_algorithm": MigrationDigestAlgorithm.SHA256,
        "observed_digest_value": OBSERVED_SHA256,
        "custody": MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
        "source": MemorySource(source_type=MemorySourceType.CHATGPT, source_id="x"),
        "source_local_id": "conv-1:msg-1",
        "source_role": MigrationCandidateRole.USER,
    }
    fields.update(overrides)
    return MigrationCandidateProvenance(**fields)


def _candidate(
    content: str = "hello world",
    *,
    source_sequence_index: int = 0,
    chunk_index: int = 0,
    chunk_count: int = 1,
    provenance: MigrationCandidateProvenance | None = None,
    target_scope: MemoryScope | None = None,
    **provenance_overrides: Any,
) -> MemoryMigrationCandidate:
    prov = provenance or _provenance(**provenance_overrides)
    digest = derive_candidate_content_digest(content)
    candidate_id = derive_candidate_id(
        bundle_fingerprint=prov.bundle_fingerprint,
        artifact_fingerprint=prov.source_artifact_fingerprint,
        source_local_id=prov.source_local_id,
        role=prov.source_role.value,
        source_sequence_index=source_sequence_index,
        chunk_index=chunk_index,
        content_digest=digest,
    )
    return MemoryMigrationCandidate(
        candidate_id=candidate_id,
        content=content,
        content_digest=digest,
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        source_sequence_index=source_sequence_index,
        provenance=prov,
        target_scope=target_scope,
    )


def _clean_pair() -> list[MemoryMigrationCandidate]:
    return [
        _candidate("first message", source_local_id="c:m0", source_sequence_index=0),
        _candidate("second message", source_local_id="c:m1", source_sequence_index=1),
    ]


# --------------------------------------------------------------------------- #
# 1-2. Empty / clean input
# --------------------------------------------------------------------------- #
def test_empty_input_is_ready_for_review() -> None:
    report = assess_memory_migration_candidates([])
    assert report.candidate_count == 0
    assert report.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW
    assert report.diagnostics == []
    assert report.duplicate_groups == []
    assert report.conflicts == []
    assert report.coverage.total_candidates == 0


def test_clean_candidate_set_is_ready_for_review() -> None:
    report = assess_memory_migration_candidates(_clean_pair())
    assert report.candidate_count == 2
    assert report.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW
    assert report.diagnostics == []
    assert report.blocking_diagnostic_count == 0
    assert report.advisory_diagnostic_count == 0


# --------------------------------------------------------------------------- #
# 3-4. Advisory-only / blocking verdicts
# --------------------------------------------------------------------------- #
def test_advisory_only_findings_produce_review_with_warnings() -> None:
    dup = _candidate("dupe", source_local_id="c:m0")
    report = assess_memory_migration_candidates([dup, dup])
    assert report.review_readiness is MigrationReviewReadiness.REVIEW_WITH_WARNINGS
    assert report.blocking_diagnostic_count == 0
    assert report.advisory_diagnostic_count >= 1


def test_blocking_findings_produce_blocked() -> None:
    prov = _provenance(source_local_id="c:m0")
    a = _candidate("first", provenance=prov)
    b = _candidate("second", provenance=prov)  # same slot, different content
    report = assess_memory_migration_candidates([a, b])
    assert report.review_readiness is MigrationReviewReadiness.BLOCKED
    assert report.blocking_diagnostic_count == 1


# --------------------------------------------------------------------------- #
# 5-6. Determinism: byte-stable and order-independent
# --------------------------------------------------------------------------- #
def test_identical_input_produces_byte_equivalent_reports() -> None:
    candidates = _clean_pair()
    first = assess_memory_migration_candidates(candidates)
    second = assess_memory_migration_candidates(candidates)
    assert first.model_dump_json() == second.model_dump_json()
    assert first.report_id == second.report_id


def test_reordered_input_produces_the_same_canonical_report() -> None:
    dup = _candidate("dupe", source_local_id="c:m0")
    conflict_prov = _provenance(source_local_id="c:m9")
    ca = _candidate("alpha", provenance=conflict_prov)
    cb = _candidate("beta", provenance=conflict_prov)
    extra = _candidate("plain", source_local_id="c:m3", source_sequence_index=3)

    forward = assess_memory_migration_candidates([dup, dup, ca, cb, extra])
    reversed_report = assess_memory_migration_candidates([extra, cb, ca, dup, dup])
    assert forward.model_dump_json() == reversed_report.model_dump_json()


# --------------------------------------------------------------------------- #
# 7-8. Duplicate grouping and deterministic identity
# --------------------------------------------------------------------------- #
def test_duplicates_are_grouped_and_never_dropped() -> None:
    dup = _candidate("dupe", source_local_id="c:m0")
    report = assess_memory_migration_candidates([dup, dup, dup])
    assert len(report.duplicate_groups) == 1
    group = report.duplicate_groups[0]
    assert group.occurrence_count == 3
    assert group.candidate_id == dup.candidate_id
    # Nothing is removed: the count reflects every occurrence.
    assert report.candidate_count == 3


def test_duplicate_group_ordering_and_identity_are_deterministic() -> None:
    d1 = _candidate("one", source_local_id="c:m1")
    d2 = _candidate("two", source_local_id="c:m2")
    first = assess_memory_migration_candidates([d1, d1, d2, d2])
    second = assess_memory_migration_candidates([d2, d2, d1, d1])
    assert [g.group_id for g in first.duplicate_groups] == [
        g.group_id for g in second.duplicate_groups
    ]
    keys = [g.sort_key() for g in first.duplicate_groups]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------- #
# 9. Conflicting source identity
# --------------------------------------------------------------------------- #
def test_conflicting_source_identity_is_detected_and_blocks() -> None:
    prov = _provenance(source_local_id="c:m0")
    a = _candidate("real version", provenance=prov)
    b = _candidate("other version", provenance=prov)
    report = assess_memory_migration_candidates([a, b])
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert conflict.distinct_content_digest_count == 2
    assert sorted(conflict.member_candidate_ids) == sorted(
        {a.candidate_id, b.candidate_id}
    )
    assert report.review_readiness is MigrationReviewReadiness.BLOCKED


def test_identical_duplicate_is_not_misreported_as_a_conflict() -> None:
    dup = _candidate("same", source_local_id="c:m0")
    report = assess_memory_migration_candidates([dup, dup])
    assert report.conflicts == []
    assert len(report.duplicate_groups) == 1


# --------------------------------------------------------------------------- #
# 10-11. Ambiguous source order and scope isolation
# --------------------------------------------------------------------------- #
def test_same_sequence_index_within_scope_is_ambiguous() -> None:
    a = _candidate("a", source_local_id="c:m0", source_sequence_index=5)
    b = _candidate("b", source_local_id="c:m1", source_sequence_index=5)
    report = assess_memory_migration_candidates([a, b])
    codes = report.diagnostic_counts_by_code
    assert codes.get("ambiguous_source_order") == 1
    assert report.review_readiness is MigrationReviewReadiness.REVIEW_WITH_WARNINGS


def test_same_sequence_index_across_unrelated_scopes_is_not_a_collision() -> None:
    a = _candidate(
        "a",
        source_local_id="c:m0",
        source_sequence_index=5,
        source_artifact_fingerprint="mm-artifact-aaaaaaaaaaaaaaaaaaaaaaaa",
    )
    b = _candidate(
        "b",
        source_local_id="c:m1",
        source_sequence_index=5,
        source_artifact_fingerprint="mm-artifact-bbbbbbbbbbbbbbbbbbbbbbbb",
    )
    report = assess_memory_migration_candidates([a, b])
    assert "ambiguous_source_order" not in report.diagnostic_counts_by_code
    assert report.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW


def test_chunks_of_one_item_do_not_collide_on_sequence() -> None:
    prov = _provenance(source_local_id="c:m0")
    c0 = _candidate("chunk a", provenance=prov, chunk_index=0, chunk_count=2)
    c1 = _candidate("chunk b", provenance=prov, chunk_index=1, chunk_count=2)
    report = assess_memory_migration_candidates([c0, c1])
    assert "ambiguous_source_order" not in report.diagnostic_counts_by_code
    assert report.conflicts == []
    assert report.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW


# --------------------------------------------------------------------------- #
# 12. Empty / degenerate candidate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("content", [" ", "   ", "\t", "\n", " "])
def test_degenerate_candidate_is_detected(content: str) -> None:
    candidate = _candidate(content, source_local_id="c:m0")
    report = assess_memory_migration_candidates([candidate])
    assert report.diagnostic_counts_by_code.get("empty_or_degenerate_candidate") == 1
    assert report.review_readiness is MigrationReviewReadiness.REVIEW_WITH_WARNINGS


def test_meaningful_candidate_is_not_flagged_degenerate() -> None:
    report = assess_memory_migration_candidates([_candidate("real content")])
    assert "empty_or_degenerate_candidate" not in report.diagnostic_counts_by_code


# --------------------------------------------------------------------------- #
# 13-14. Carried Phase 40F findings
# --------------------------------------------------------------------------- #
def test_carried_projection_error_blocks() -> None:
    error = MigrationProjectionDiagnostic(
        code=MigrationProjectionDiagnosticCode.DIGEST_MISMATCH,
        message="artifact bytes did not match the declared digest",
        subject_id="bundle-1",
        artifact_id="artifact-1",
    )
    report = assess_memory_migration_candidates(
        _clean_pair(), projection_diagnostics=[error]
    )
    assert report.review_readiness is MigrationReviewReadiness.BLOCKED
    carried = [
        d
        for d in report.diagnostics
        if d.code
        is MigrationCandidateAssessmentDiagnosticCode.UNRESOLVED_PROJECTION_ERROR
    ]
    assert len(carried) == 1
    assert carried[0].carried == error
    assert carried[0].severity is MigrationCandidateAssessmentSeverity.BLOCKING


def test_carried_projection_info_preserves_advisory_severity() -> None:
    overflow = MigrationProjectionDiagnostic(
        code=MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW,
        message="source item content exceeded the parser bound and was chunked",
        subject_id="bundle-1",
        artifact_id="artifact-1",
        count=500,
    )
    report = assess_memory_migration_candidates(
        _clean_pair(), projection_diagnostics=[overflow]
    )
    assert report.review_readiness is MigrationReviewReadiness.REVIEW_WITH_WARNINGS
    carried = [
        d
        for d in report.diagnostics
        if d.code
        is MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING
    ]
    assert len(carried) == 1
    assert carried[0].carried == overflow
    # Original Phase 40F severity is preserved, not downgraded.
    assert carried[0].carried.severity is MigrationProjectionSeverity.INFO
    assert carried[0].severity is MigrationCandidateAssessmentSeverity.ADVISORY


def test_carried_error_cannot_be_downgraded_to_advisory() -> None:
    error = MigrationProjectionDiagnostic(
        code=MigrationProjectionDiagnosticCode.DIGEST_MISMATCH, message="x"
    )
    with pytest.raises(ValidationError):
        MigrationCandidateAssessmentDiagnostic(
            code=(
                MigrationCandidateAssessmentDiagnosticCode.PROJECTION_TRUNCATION_WARNING
            ),
            message="attempting to file an error as advisory",
            carried=error,
        )


# --------------------------------------------------------------------------- #
# 15. Fail-closed readiness
# --------------------------------------------------------------------------- #
def test_readiness_resolver_is_fail_closed() -> None:
    assert (
        resolve_review_readiness([]) is MigrationReviewReadiness.READY_FOR_REVIEW
    )
    assert (
        resolve_review_readiness([MigrationCandidateAssessmentSeverity.ADVISORY])
        is MigrationReviewReadiness.REVIEW_WITH_WARNINGS
    )
    assert (
        resolve_review_readiness([MigrationCandidateAssessmentSeverity.BLOCKING])
        is MigrationReviewReadiness.BLOCKED
    )
    # A None or unknown severity fails closed rather than producing a ready verdict.
    assert resolve_review_readiness([None]) is MigrationReviewReadiness.BLOCKED
    assert (
        resolve_review_readiness(
            [MigrationCandidateAssessmentSeverity.ADVISORY, None]
        )
        is MigrationReviewReadiness.BLOCKED
    )


def test_report_rejects_readiness_that_disagrees_with_diagnostics() -> None:
    report = assess_memory_migration_candidates(
        [_candidate("dupe", source_local_id="c:m0")] * 2
    )
    payload = report.model_dump()
    payload["review_readiness"] = MigrationReviewReadiness.READY_FOR_REVIEW.value
    with pytest.raises(ValidationError):
        MigrationCandidateAssessmentReport(**payload)


# --------------------------------------------------------------------------- #
# 16. No raw candidate content in diagnostics
# --------------------------------------------------------------------------- #
def test_report_contains_no_raw_candidate_content() -> None:
    secret = "TOPSECRETcontent-9f83aa-do-not-leak"
    prov = _provenance(source_local_id="c:m0")
    a = _candidate(secret, provenance=prov)
    b = _candidate(secret + " variant", provenance=prov)
    degenerate = _candidate("   ", source_local_id="c:m1")
    report = assess_memory_migration_candidates(
        [a, a, b, degenerate],
    )
    serialized = report.model_dump_json()
    assert secret not in serialized
    # The content digest (a non-reversible hash) may appear; the content may not.
    assert derive_candidate_content_digest(secret) in serialized


# --------------------------------------------------------------------------- #
# 17. Aggregate coverage
# --------------------------------------------------------------------------- #
def test_coverage_counts_by_role_and_source_type() -> None:
    user_c = _candidate("u", source_local_id="c:m0", source_role=MigrationCandidateRole.USER)
    asst_c = _candidate(
        "a",
        source_local_id="c:m1",
        source_role=MigrationCandidateRole.ASSISTANT,
    )
    doc_c = _candidate(
        "d",
        source_local_id="c:m2",
        source_role=MigrationCandidateRole.DOCUMENT,
        source=MemorySource(
            source_type=MemorySourceType.IMPORTED_DOCUMENT, source_id="doc"
        ),
    )
    report = assess_memory_migration_candidates([user_c, asst_c, doc_c])
    assert report.coverage.counts_by_role == {"user": 1, "assistant": 1, "document": 1}
    assert report.coverage.counts_by_source_type == {"chatgpt": 2, "imported_document": 1}
    assert report.coverage.distinct_source_identity_count == 3
    assert sum(report.coverage.counts_by_role.values()) == report.candidate_count


# --------------------------------------------------------------------------- #
# 18. Stable report identity
# --------------------------------------------------------------------------- #
def test_report_identity_is_stable_and_content_addressed() -> None:
    candidates = _clean_pair()
    first = assess_memory_migration_candidates(candidates)
    second = assess_memory_migration_candidates(candidates)
    assert first.report_id == second.report_id
    # A different set yields a different id.
    changed = assess_memory_migration_candidates(
        candidates + [_candidate("dupe", source_local_id="c:m0")] * 2
    )
    assert changed.report_id != first.report_id


def test_report_rejects_forged_identity() -> None:
    report = assess_memory_migration_candidates(_clean_pair())
    payload = report.model_dump()
    payload["candidate_count"] = report.candidate_count + 1
    with pytest.raises(ValidationError):
        MigrationCandidateAssessmentReport(**payload)


# --------------------------------------------------------------------------- #
# 19. CANDIDATE_MEMORY_POLICY remains pinned
# --------------------------------------------------------------------------- #
def test_candidate_memory_policy_remains_pinned() -> None:
    assert CANDIDATE_MEMORY_POLICY.lifecycle_state is LifecycleState.INACTIVE
    assert CANDIDATE_MEMORY_POLICY.verification_state is VerificationState.UNVERIFIED
    assert CANDIDATE_MEMORY_POLICY.represents_active_memory is False
    assert CANDIDATE_MEMORY_POLICY.human_review_required is True
    assert CANDIDATE_MEMORY_POLICY.persistable is False


def test_report_is_read_only_and_non_persisting() -> None:
    report = assess_memory_migration_candidates(_clean_pair())
    assert report.read_only is True
    assert report.candidates_mutated is False
    assert report.persisted is False
    for flag in ("read_only", "candidates_mutated", "persisted"):
        payload = report.model_dump()
        payload[flag] = not payload[flag]
        with pytest.raises(ValidationError):
            MigrationCandidateAssessmentReport(**payload)


# --------------------------------------------------------------------------- #
# 20. No mutation of inputs
# --------------------------------------------------------------------------- #
def test_assessment_does_not_mutate_inputs() -> None:
    candidates = _clean_pair() + [_candidate("dupe", source_local_id="c:m0")] * 2
    diag = MigrationProjectionDiagnostic(
        code=MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW,
        message="carried",
        count=1,
    )
    before_candidates = [c.model_dump() for c in candidates]
    before_diag = diag.model_dump()
    order_before = list(candidates)
    assess_memory_migration_candidates(candidates, projection_diagnostics=[diag])
    assert [c.model_dump() for c in candidates] == before_candidates
    assert diag.model_dump() == before_diag
    assert list(candidates) == order_before  # input sequence order untouched


# --------------------------------------------------------------------------- #
# 21. AST purity enforcement
# --------------------------------------------------------------------------- #
_FORBIDDEN_IMPORTS = {
    "os",
    "io",
    "pathlib",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "zipfile",
    "random",
    "uuid",
    "secrets",
    "http",
    "ftplib",
    "shutil",
    "tempfile",
    "datetime",
    "time",
    "sqlite3",
}

_FORBIDDEN_CALLS = {
    "open",
    "now",
    "today",
    "utcnow",
    "time",
    "monotonic",
    "system",
    "popen",
    "run",
    "urlopen",
}


def test_assessment_module_performs_no_io_clock_or_randomness() -> None:
    tree = ast.parse(
        Path(inspect.getfile(assessment_module)).read_text(encoding="utf-8")
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in _FORBIDDEN_IMPORTS, alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in _FORBIDDEN_IMPORTS, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            )
            assert name not in _FORBIDDEN_CALLS, name


# --------------------------------------------------------------------------- #
# 22. Bounded-collection behavior
# --------------------------------------------------------------------------- #
def test_candidate_set_at_the_bound_is_assessed() -> None:
    dup = _candidate("dupe", source_local_id="c:m0")
    report = assess_memory_migration_candidates([dup] * MAX_ASSESSED_CANDIDATES)
    assert report.candidate_count == MAX_ASSESSED_CANDIDATES
    assert report.duplicate_groups[0].occurrence_count == MAX_ASSESSED_CANDIDATES


def test_candidate_set_beyond_the_bound_is_refused() -> None:
    dup = _candidate("dupe", source_local_id="c:m0")
    with pytest.raises(ValueError):
        assess_memory_migration_candidates([dup] * (MAX_ASSESSED_CANDIDATES + 1))


def test_diagnostics_are_bounded_with_a_blocking_truncation_notice() -> None:
    overflow = MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS + 5
    candidates = [
        _candidate(" ", source_local_id=f"c:m{i}", source_sequence_index=i)
        for i in range(overflow)
    ]
    report = assess_memory_migration_candidates(candidates)
    assert len(report.diagnostics) == MAX_CANDIDATE_ASSESSMENT_DIAGNOSTICS
    assert (
        report.diagnostic_counts_by_code.get("diagnostics_truncated") == 1
    )
    assert report.review_readiness is MigrationReviewReadiness.BLOCKED


# --------------------------------------------------------------------------- #
# 23. Unicode normalization
# --------------------------------------------------------------------------- #
def test_source_identity_is_nfc_normalized() -> None:
    composed = "café"  # café with composed é
    decomposed = "café"  # café with combining acute accent
    assert composed != decomposed
    a = _candidate("same content", source_local_id=composed)
    b = _candidate("same content", source_local_id=decomposed)
    # NFC-equal local ids + identical content => the same candidate and one group.
    assert a.candidate_id == b.candidate_id
    report = assess_memory_migration_candidates([a, b])
    assert len(report.duplicate_groups) == 1
    assert report.duplicate_groups[0].occurrence_count == 2


def test_degenerate_detection_normalizes_before_stripping() -> None:
    # A combining grapheme joiner alone is whitespace-free but normalization +
    # strip still leaves nothing meaningful for content that is only separators.
    report = assess_memory_migration_candidates(
        [_candidate("  ", source_local_id="c:m0")]
    )
    assert report.diagnostic_counts_by_code.get("empty_or_degenerate_candidate") == 1


# --------------------------------------------------------------------------- #
# 24. Canonical serialization / round-trip
# --------------------------------------------------------------------------- #
def test_report_round_trips_through_json_and_python() -> None:
    prov = _provenance(source_local_id="c:m0")
    report = assess_memory_migration_candidates(
        _clean_pair()
        + [_candidate("dupe", source_local_id="c:m4")] * 2
        + [_candidate("v1", provenance=prov), _candidate("v2", provenance=prov)],
        projection_diagnostics=[
            MigrationProjectionDiagnostic(
                code=MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW,
                message="carried",
                count=3,
            )
        ],
    )
    from_json = MigrationCandidateAssessmentReport.model_validate_json(
        report.model_dump_json()
    )
    assert from_json == report
    from_python = MigrationCandidateAssessmentReport.model_validate(report.model_dump())
    assert from_python == report
    assert report.assessment_version == MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION


# --------------------------------------------------------------------------- #
# Diagnostic severity is code-derived, not caller-controlled
# --------------------------------------------------------------------------- #
def test_assessment_diagnostic_severity_follows_the_code() -> None:
    diag = MigrationCandidateAssessmentDiagnostic(
        code=MigrationCandidateAssessmentDiagnosticCode.CONFLICTING_SOURCE_IDENTITY,
        message="x",
        group_id="mm-source-conflict-000000000000000000000000",
        count=2,
    )
    assert diag.severity is MigrationCandidateAssessmentSeverity.BLOCKING
    with pytest.raises(ValidationError):
        MigrationCandidateAssessmentDiagnostic(
            code=(
                MigrationCandidateAssessmentDiagnosticCode.CONFLICTING_SOURCE_IDENTITY
            ),
            severity=MigrationCandidateAssessmentSeverity.ADVISORY,
            message="x",
        )


def test_module_wrapper_matches_class_assessor() -> None:
    candidates = _clean_pair()
    via_wrapper = assess_memory_migration_candidates(candidates)
    via_class = MemoryMigrationCandidateAssessor().assess(candidates=candidates)
    assert via_wrapper.model_dump_json() == via_class.model_dump_json()


def test_target_scope_candidates_are_assessed_without_error() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="proj")
    report = assess_memory_migration_candidates(
        [_candidate("scoped", source_local_id="c:m0", target_scope=scope)]
    )
    assert report.review_readiness is MigrationReviewReadiness.READY_FOR_REVIEW
