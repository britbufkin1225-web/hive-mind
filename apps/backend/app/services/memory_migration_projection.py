"""Phase 40F — pure, deterministic projection of parsed items into candidates.

The second half of the Phase 40F pipeline:

    unsafe external bytes -> parser -> bounded parsed items
                                          -> **pure candidate projector** -> candidates

This module is the projector. It takes :class:`~app.models.memory_migration_projection.ParsedMigrationItem`
values the parser already extracted from verified bytes and turns them into
bounded, provenance-linked :class:`~app.models.memory_migration_projection.MemoryMigrationCandidate`
records. It does **nothing else** and reaches nothing else:

* it opens no file, reads no archive, and touches no byte source — the parser did
  all byte access before an item ever reached here;
* it reads no clock, generates no random value, makes no network or Git call, and
  inspects no environment;
* it persists nothing and imports nothing — Phase 40G owns reviewed persistence.

That purity is enforced structurally by
``tests/test_memory_migration_projection.py`` (an AST check over this module),
not merely promised in prose. Keeping projection pure is what makes a candidate's
identity and ordering reproducible: identical parsed items and context always
yield byte-equivalent candidates in the same canonical order.

The projector applies the migration track's candidate ceiling to everything it
produces. It cannot widen it: every candidate is constructed through
:class:`~app.models.memory_migration_projection.MemoryMigrationCandidate`, which
pins the five candidate-standing fields and cross-checks them against
:data:`~app.models.memory_migration.CANDIDATE_MEMORY_POLICY`. There is no code
path here that can emit an ``active``, ``verified``, ``human_confirmed``, or
``persistable`` record.

Bounds are honest. A parsed item longer than one candidate's content bound is
split into deterministically-ordered chunks carrying explicit chunk metadata;
content the parser had to cap is flagged and reported, never silently dropped;
and running out of candidate budget is reported as a typed count-overflow finding
rather than by quietly discarding records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.models.active_memory import MemorySource, MemoryScope
from app.models.memory_migration import (
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
)
from app.models.memory_migration_projection import (
    MAX_CANDIDATE_CONTENT_CHARS,
    MemoryMigrationCandidate,
    MigrationCandidateProvenance,
    MigrationProjectionDiagnostic,
    MigrationProjectionDiagnosticCode,
    ParsedMigrationItem,
    derive_candidate_content_digest,
    derive_candidate_id,
)


@dataclass(frozen=True)
class CandidateProjectionContext:
    """Everything a candidate needs about its origin that is not on the item.

    A frozen dataclass rather than a Pydantic model, matching the in-process
    service-config convention used by the intake assessor's limits: this is not a
    wire shape, it is the per-artifact context the orchestrator threads through the
    pure projector. The digest fields describe the *verified byte stream* the
    candidate came from — the artifact's actual bytes hashed to this value under
    this accepted algorithm — so a candidate's provenance always names a confirmed
    integrity result, never a mere declaration.
    """

    bundle_id: str
    bundle_fingerprint: str
    source_artifact_format: MigrationArtifactFormat
    source_container: MigrationContainerKind
    observed_digest_algorithm: MigrationDigestAlgorithm
    observed_digest_value: str
    custody: MigrationCustodyKind
    source: MemorySource
    target_scope: MemoryScope | None = None


@dataclass(frozen=True)
class ProjectionOutcome:
    """The result of projecting one artifact's parsed items.

    ``produced`` and ``omitted`` let the orchestrator maintain a global candidate
    budget across artifacts and, at the end, report the exact number of candidates
    that could not be created rather than silently dropping them.
    """

    candidates: list[MemoryMigrationCandidate] = field(default_factory=list)
    diagnostics: list[MigrationProjectionDiagnostic] = field(default_factory=list)
    produced: int = 0
    omitted: int = 0


def _chunk_content(content: str) -> list[str]:
    """Split content into deterministically-ordered bounded chunks.

    A fixed-width character split at :data:`MAX_CANDIDATE_CONTENT_CHARS`. It is
    deliberately *not* word- or sentence-aware: a fixed boundary is trivially
    deterministic and reproducible, whereas a "smart" split would risk producing
    different boundaries for inputs that differ only cosmetically. Order is
    preserved, so reassembling the chunks in ``chunk_index`` order reproduces the
    original bounded content exactly.
    """

    if len(content) <= MAX_CANDIDATE_CONTENT_CHARS:
        return [content]
    return [
        content[start : start + MAX_CANDIDATE_CONTENT_CHARS]
        for start in range(0, len(content), MAX_CANDIDATE_CONTENT_CHARS)
    ]


def _build_candidate(
    *,
    item: ParsedMigrationItem,
    context: CandidateProjectionContext,
    chunk_text: str,
    chunk_index: int,
    chunk_count: int,
    content_truncated: bool,
) -> MemoryMigrationCandidate:
    """Construct one candidate for one chunk.

    Every candidate is built through the candidate model, so the candidate-standing
    ceiling and the deterministic-identity checks are enforced at construction —
    this function cannot produce a record that exceeds the policy or carries a
    forged id even if it tried to.
    """

    provenance = MigrationCandidateProvenance(
        bundle_id=context.bundle_id,
        bundle_fingerprint=context.bundle_fingerprint,
        source_artifact_id=item.artifact_id,
        source_artifact_fingerprint=item.artifact_fingerprint,
        source_artifact_format=context.source_artifact_format,
        source_container=context.source_container,
        observed_digest_algorithm=context.observed_digest_algorithm,
        observed_digest_value=context.observed_digest_value,
        custody=context.custody,
        source=context.source,
        source_local_id=item.source_local_id,
        source_container_id=item.source_container_id,
        source_entry_id=item.source_entry_id,
        source_role=item.role,
        declared_source_timestamp=item.declared_source_timestamp,
    )
    content_digest = derive_candidate_content_digest(chunk_text)
    candidate_id = derive_candidate_id(
        bundle_fingerprint=context.bundle_fingerprint,
        artifact_fingerprint=item.artifact_fingerprint,
        source_local_id=item.source_local_id,
        role=item.role.value,
        chunk_index=chunk_index,
        content_digest=content_digest,
    )
    return MemoryMigrationCandidate(
        candidate_id=candidate_id,
        content=chunk_text,
        content_digest=content_digest,
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        source_sequence_index=item.source_sequence_index,
        content_truncated=content_truncated,
        provenance=provenance,
        target_scope=context.target_scope,
    )


def project_artifact_items(
    *,
    items: Sequence[ParsedMigrationItem],
    context: CandidateProjectionContext,
    remaining_budget: int,
) -> ProjectionOutcome:
    """Project one artifact's parsed items into candidates, within a budget.

    Pure and deterministic. Items are processed in the order the parser produced
    them (a stable traversal, never JSON insertion order), each item is split into
    ordered bounded chunks, and each chunk becomes one candidate until the global
    candidate budget is exhausted. Over-budget chunks are *counted*, not dropped
    silently: the orchestrator turns a non-zero ``omitted`` into a single typed
    count-overflow finding.

    A chunk-level budget boundary keeps ``chunk_count`` truthful even when an item
    straddles the limit — the candidate carries the item's full chunk count, and
    the chunks that did not fit are reported as omitted rather than renumbered.
    """

    candidates: list[MemoryMigrationCandidate] = []
    diagnostics: list[MigrationProjectionDiagnostic] = []
    produced = 0
    omitted = 0

    for item in items:
        chunks = _chunk_content(item.content)
        chunk_count = len(chunks)
        content_truncated = item.original_content_length > len(item.content)
        if content_truncated:
            diagnostics.append(
                MigrationProjectionDiagnostic(
                    code=MigrationProjectionDiagnosticCode.CANDIDATE_CONTENT_OVERFLOW,
                    message=(
                        "source item content exceeded the parser item bound and was "
                        "capped before chunking; the candidate set for this item is "
                        "bounded and explicitly marked truncated"
                    ),
                    subject_id=context.bundle_id,
                    artifact_id=item.artifact_id,
                    count=item.original_content_length - len(item.content),
                )
            )

        for chunk_index, chunk_text in enumerate(chunks):
            if produced >= remaining_budget:
                omitted += 1
                continue
            candidates.append(
                _build_candidate(
                    item=item,
                    context=context,
                    chunk_text=chunk_text,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    content_truncated=content_truncated,
                )
            )
            produced += 1

    return ProjectionOutcome(
        candidates=candidates,
        diagnostics=diagnostics,
        produced=produced,
        omitted=omitted,
    )
