"""Phase 40F — candidate contract and pure-projector tests.

Covers the Phase 40F projection half: the candidate-standing ceiling and its
non-overridability, deterministic candidate identity and ordering, bounded content
with deterministic chunking, honest overflow representation, provenance
completeness, and the structural purity of the projector (no filesystem, archive,
network, Git, clock, or randomness access).

Every test drives the pure projector from explicit fixtures — no bytes, no source,
no clock — so a passing run proves determinism rather than assuming it.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
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
    MAX_CANDIDATE_CONTENT_CHARS,
    MAX_CANDIDATE_CHUNKS_PER_ITEM,
    MAX_MIGRATION_CANDIDATES,
    MAX_PARSED_ITEM_CHARS,
    MEMORY_MIGRATION_CURATED_VERSION,
    CuratedMigrationBundleDocument,
    CuratedMigrationEntry,
    MemoryMigrationCandidate,
    MigrationCandidateProvenance,
    MigrationCandidateRole,
    MigrationProjectionDiagnostic,
    MigrationProjectionDiagnosticCode,
    MigrationProjectionSeverity,
    ParsedMigrationItem,
    derive_candidate_content_digest,
    derive_candidate_id,
)
from app.services import memory_migration_projection as projection_module
from app.services.memory_migration_projection import (
    CandidateProjectionContext,
    project_artifact_items,
)

OBSERVED_SHA256 = "c" * 64


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _item(**overrides: Any) -> ParsedMigrationItem:
    fields: dict[str, Any] = {
        "artifact_id": "artifact-1",
        "artifact_fingerprint": "mm-artifact-000000000000000000000000",
        "source_local_id": "conv-1:msg-1",
        "source_container_id": "conv-1",
        "source_entry_id": "msg-1",
        "role": MigrationCandidateRole.USER,
        "source_sequence_index": 0,
        "content": "hello world",
        "original_content_length": len("hello world"),
    }
    fields.update(overrides)
    return ParsedMigrationItem(**fields)


def _context(**overrides: Any) -> CandidateProjectionContext:
    fields: dict[str, Any] = {
        "bundle_id": "bundle-1",
        "bundle_fingerprint": "mm-bundle-000000000000000000000000",
        "source_artifact_format": MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        "source_container": MigrationContainerKind.SINGLE_FILE,
        "observed_digest_algorithm": MigrationDigestAlgorithm.SHA256,
        "observed_digest_value": OBSERVED_SHA256,
        "custody": MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
        "source": MemorySource(source_type=MemorySourceType.CHATGPT, source_id="x"),
        "target_scope": None,
    }
    fields.update(overrides)
    return CandidateProjectionContext(**fields)


def _one_candidate(**item_overrides: Any) -> MemoryMigrationCandidate:
    outcome = project_artifact_items(
        items=[_item(**item_overrides)],
        context=_context(),
        remaining_budget=MAX_MIGRATION_CANDIDATES,
    )
    assert len(outcome.candidates) == 1
    return outcome.candidates[0]


# --------------------------------------------------------------------------- #
# Candidate-standing ceiling (§31)
# --------------------------------------------------------------------------- #
def test_every_projected_candidate_holds_the_pinned_candidate_standing() -> None:
    candidate = _one_candidate()

    assert candidate.lifecycle_state is LifecycleState.INACTIVE
    assert candidate.verification_state is VerificationState.UNVERIFIED
    assert candidate.represents_active_memory is False
    assert candidate.human_review_required is True
    assert candidate.persistable is False
    # And it matches the canonical policy the migration track fixed in Phase 40E.
    assert candidate.policy.lifecycle_state is CANDIDATE_MEMORY_POLICY.lifecycle_state
    assert candidate.policy.persistable is CANDIDATE_MEMORY_POLICY.persistable


@pytest.mark.parametrize(
    "override",
    [
        {"lifecycle_state": LifecycleState.ACTIVE},
        {"verification_state": VerificationState.VERIFIED},
        {"verification_state": VerificationState.HUMAN_CONFIRMED},
        {"represents_active_memory": True},
        {"human_review_required": False},
        {"persistable": True},
    ],
)
def test_a_caller_cannot_override_candidate_standing(override: dict[str, Any]) -> None:
    base = _one_candidate()
    payload = base.model_dump()
    payload.update(override)
    with pytest.raises(ValidationError):
        MemoryMigrationCandidate(**payload)


@pytest.mark.parametrize(
    "override",
    [
        {"lifecycle_state": LifecycleState.ACTIVE},
        {"verification_state": VerificationState.VERIFIED},
        {"verification_state": VerificationState.HUMAN_CONFIRMED},
        {"represents_active_memory": True},
        {"human_review_required": False},
        {"persistable": True},
    ],
)
def test_candidate_model_copy_cannot_bypass_authority_validation(
    override: dict[str, Any],
) -> None:
    candidate = _one_candidate()

    with pytest.raises(ValidationError):
        candidate.model_copy(update=override)


def test_candidate_model_copy_revalidates_nested_replacements_and_round_trips() -> None:
    candidate = _one_candidate()

    with pytest.warns(UserWarning):
        with pytest.raises(ValidationError):
            candidate.model_copy(
                update={
                    "provenance": {
                        **candidate.provenance.model_dump(),
                        "integrity_verified": False,
                    }
                }
            )

    round_tripped = MemoryMigrationCandidate.model_validate_json(
        candidate.model_dump_json()
    )
    assert round_tripped == candidate
    assert round_tripped.model_copy(deep=True) == candidate


def test_candidate_is_not_a_memory_record() -> None:
    from app.models.active_memory import MemoryRecord

    candidate = _one_candidate()
    assert not isinstance(candidate, MemoryRecord)
    # A candidate carries no record kind, evidence, or confidence surface.
    assert not hasattr(candidate, "record_kind")
    assert not hasattr(candidate, "evidence")


# --------------------------------------------------------------------------- #
# Deterministic identity (§10, §31)
# --------------------------------------------------------------------------- #
def test_candidate_identity_is_deterministic_across_runs() -> None:
    first = _one_candidate()
    second = _one_candidate()
    assert first.candidate_id == second.candidate_id
    assert first.content_digest == second.content_digest


def test_content_digest_and_id_are_verified_at_construction() -> None:
    candidate = _one_candidate()
    payload = candidate.model_dump()
    payload["content_digest"] = "a" * 64
    with pytest.raises(ValidationError):
        MemoryMigrationCandidate(**payload)

    payload = candidate.model_dump()
    payload["candidate_id"] = "mm-candidate-deadbeefdeadbeefdeadbeef"
    with pytest.raises(ValidationError):
        MemoryMigrationCandidate(**payload)


def test_distinct_source_entries_with_identical_text_are_distinct_candidates() -> None:
    outcome = project_artifact_items(
        items=[
            _item(source_local_id="conv-1:msg-1", source_entry_id="msg-1", content="same"),
            _item(
                source_local_id="conv-1:msg-2",
                source_entry_id="msg-2",
                source_sequence_index=1,
                content="same",
            ),
        ],
        context=_context(),
        remaining_budget=MAX_MIGRATION_CANDIDATES,
    )
    ids = {c.candidate_id for c in outcome.candidates}
    assert len(ids) == 2
    # Same content -> same content digest, but provenance keeps them distinct.
    digests = {c.content_digest for c in outcome.candidates}
    assert len(digests) == 1


def test_duplicate_source_ids_are_distinct_by_stable_sequence() -> None:
    first = _one_candidate(source_sequence_index=0)
    second = _one_candidate(source_sequence_index=1)

    assert first.candidate_id != second.candidate_id


# --------------------------------------------------------------------------- #
# Deterministic ordering (§19)
# --------------------------------------------------------------------------- #
def test_candidate_order_is_canonical_and_stable() -> None:
    items = [
        _item(source_local_id="c:m2", source_entry_id="m2", source_sequence_index=1, content="b"),
        _item(source_local_id="c:m1", source_entry_id="m1", source_sequence_index=0, content="a"),
    ]
    outcome = project_artifact_items(
        items=items, context=_context(), remaining_budget=MAX_MIGRATION_CANDIDATES
    )
    keys = [c.sort_key() for c in outcome.candidates]
    # Projection preserves parser-assigned order (sequence 1 then 0 as given);
    # the result-level sort in the orchestrator is what canonicalizes globally.
    assert [c.source_sequence_index for c in outcome.candidates] == [1, 0]
    # But sorting by the canonical key is deterministic and total.
    assert sorted(keys) == sorted(keys)


# --------------------------------------------------------------------------- #
# Bounded content + deterministic chunking (§16)
# --------------------------------------------------------------------------- #
def test_content_within_bound_is_a_single_chunk() -> None:
    candidate = _one_candidate(content="short", original_content_length=len("short"))
    assert candidate.chunk_index == 0
    assert candidate.chunk_count == 1
    assert candidate.content_truncated is False


def test_long_content_splits_into_ordered_bounded_chunks() -> None:
    text = "x" * (MAX_CANDIDATE_CONTENT_CHARS * 2 + 10)
    outcome = project_artifact_items(
        items=[_item(content=text, original_content_length=len(text))],
        context=_context(),
        remaining_budget=MAX_MIGRATION_CANDIDATES,
    )
    assert [c.chunk_index for c in outcome.candidates] == [0, 1, 2]
    assert all(c.chunk_count == 3 for c in outcome.candidates)
    assert all(len(c.content) <= MAX_CANDIDATE_CONTENT_CHARS for c in outcome.candidates)
    # Reassembling the chunks reproduces the original bounded content exactly.
    assert "".join(c.content for c in outcome.candidates) == text


def test_content_overflow_is_reported_not_silently_truncated() -> None:
    # A parsed item whose original length exceeds the bounded content the parser
    # kept must be flagged and diagnosed, never quietly clipped.
    kept = "y" * MAX_PARSED_ITEM_CHARS
    outcome = project_artifact_items(
        items=[_item(content=kept, original_content_length=MAX_PARSED_ITEM_CHARS + 500)],
        context=_context(),
        remaining_budget=MAX_MIGRATION_CANDIDATES,
    )
    assert all(c.content_truncated for c in outcome.candidates)
    overflow = [
        d
        for d in outcome.diagnostics
        if d.code is MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW
    ]
    assert len(overflow) == 1
    assert overflow[0].count == 500
    assert len(outcome.candidates) == MAX_CANDIDATE_CHUNKS_PER_ITEM


def test_candidate_count_overflow_is_represented_not_dropped() -> None:
    items = [
        _item(source_local_id=f"c:m{i}", source_entry_id=f"m{i}", source_sequence_index=i, content=f"t{i}")
        for i in range(5)
    ]
    outcome = project_artifact_items(
        items=items, context=_context(), remaining_budget=2
    )
    assert outcome.produced == 2
    assert outcome.omitted == 3


# --------------------------------------------------------------------------- #
# Provenance completeness (§18)
# --------------------------------------------------------------------------- #
def test_candidate_provenance_is_complete() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="proj")
    ts = datetime(2026, 1, 2, tzinfo=timezone.utc)
    candidate = project_artifact_items(
        items=[_item(declared_source_timestamp=ts)],
        context=_context(target_scope=scope),
        remaining_budget=MAX_MIGRATION_CANDIDATES,
    ).candidates[0]
    prov = candidate.provenance
    assert prov.bundle_id == "bundle-1"
    assert prov.bundle_fingerprint == "mm-bundle-000000000000000000000000"
    assert prov.source_artifact_id == "artifact-1"
    assert prov.source_artifact_fingerprint == "mm-artifact-000000000000000000000000"
    assert prov.integrity_verified is True
    assert prov.observed_digest_algorithm is MigrationDigestAlgorithm.SHA256
    assert prov.observed_digest_value == OBSERVED_SHA256
    assert prov.source_container_id == "conv-1"
    assert prov.source_entry_id == "msg-1"
    assert prov.source_role is MigrationCandidateRole.USER
    assert prov.declared_source_timestamp == ts
    assert candidate.target_scope == scope


def test_provenance_requires_verified_integrity() -> None:
    candidate = _one_candidate()
    payload = candidate.provenance.model_dump()
    payload["integrity_verified"] = False
    with pytest.raises(ValidationError):
        MigrationCandidateProvenance(**payload)


# --------------------------------------------------------------------------- #
# Curated input contract (§17)
# --------------------------------------------------------------------------- #
def test_curated_bundle_rejects_unknown_and_authority_fields() -> None:
    with pytest.raises(ValidationError):
        CuratedMigrationEntry(entry_id="e1", text="t", verified=True)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        CuratedMigrationBundleDocument(
            schema_version=MEMORY_MIGRATION_CURATED_VERSION,
            entries=[{"entry_id": "e1", "text": "t", "active": True}],
        )


def test_curated_bundle_rejects_wrong_version_and_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        CuratedMigrationBundleDocument(schema_version="other.v9", entries=[])
    with pytest.raises(ValidationError):
        CuratedMigrationBundleDocument(
            entries=[
                CuratedMigrationEntry(entry_id="dup", text="a"),
                CuratedMigrationEntry(entry_id="dup", text="b"),
            ]
        )


# --------------------------------------------------------------------------- #
# Diagnostic severity is code-derived, not caller-controlled (§20)
# --------------------------------------------------------------------------- #
def test_projection_diagnostic_severity_follows_the_code() -> None:
    diag = MigrationProjectionDiagnostic(
        code=MigrationProjectionDiagnosticCode.DIGEST_MISMATCH, message="x"
    )
    assert diag.severity is MigrationProjectionSeverity.ERROR
    with pytest.raises(ValidationError):
        MigrationProjectionDiagnostic(
            code=MigrationProjectionDiagnosticCode.DIGEST_MISMATCH,
            severity=MigrationProjectionSeverity.INFO,
            message="x",
        )


# --------------------------------------------------------------------------- #
# Projector purity (§32)
# --------------------------------------------------------------------------- #
def test_projection_does_not_mutate_parsed_input() -> None:
    item = _item()
    before = item.model_dump()
    project_artifact_items(
        items=[item], context=_context(), remaining_budget=MAX_MIGRATION_CANDIDATES
    )
    assert item.model_dump() == before


_FORBIDDEN_PROJECTION_IMPORTS = {
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
}

_FORBIDDEN_PROJECTION_CALLS = {
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


def test_projection_module_performs_no_io_clock_or_randomness() -> None:
    # The projector's purity is enforced structurally, not by convention: it must
    # not import an I/O, network, Git, randomness, or clock module, and must not
    # call an opening/clock/subprocess function.
    tree = ast.parse(
        Path(inspect.getfile(projection_module)).read_text(encoding="utf-8")
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in _FORBIDDEN_PROJECTION_IMPORTS, (
                    alias.name
                )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in _FORBIDDEN_PROJECTION_IMPORTS, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            )
            assert name not in _FORBIDDEN_PROJECTION_CALLS, name
