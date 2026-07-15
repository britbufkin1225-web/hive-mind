"""Phase 37D — Deterministic Active Memory contradiction detection (MVP).

A **read-only** derivation service over the Phase 37C Active Memory store
(``app.store.active_memory_store``) and the Phase 37B contracts
(``app.models.active_memory``). Given the records the store already holds, it
derives contract-valid :class:`ContradictionRecord` results for the subset of the
five Phase 37A §8.1 / Phase 37B ``ContradictionClass`` values that can be
established *deterministically from stored record fields alone* — no semantic
inference, no language model, no fuzzy matching, no external services.

What this module deliberately is **not** (kept out per the Phase 37D brief):

* It never mutates, deletes, supersedes, or resolves a record. It reads records
  through the store's public :class:`~app.store.active_memory_store.MemoryStore`
  surface (or a plain iterable) and returns new derived results; the store is
  untouched.
* It adds no API router, endpoint, frontend surface, persistence, ingestion,
  repository/git observer, active-state calculation, context-packet generation,
  or AI/LLM behavior — those are separate phases (37E+).
* It never *auto-resolves* a contradiction: every result is emitted ``open`` and
  the layer never picks a winner (Phase 37A §1.5, §13).

Design (grounded in the planning/contract docs, not invented here):

* **Contract classes only.** Results only ever use a Phase 37B
  :class:`ContradictionClass`; the detector never invents a parallel taxonomy.
* **Deterministic and order-independent.** Input is de-duplicated by
  ``record_id`` and every derived value (the assertion target, the sorted
  supporting ids, the stable contradiction id, and the final ordering) comes from
  record *content*, never insertion order, wall-clock time, RNG, or dict
  iteration order. Reversing the input reproduces identical results byte-for-byte.
* **Caller owns the clock.** Exactly like the 37C store ("the store never
  generates its own timestamps"), this service never reads the wall clock: the
  caller supplies ``detected_at`` so repeated detection is reproducible.
* **Conservative.** A contradiction is only reported when stored fields establish
  it; missing/mismatched comparison data yields *nothing*, never a guess
  (Phase 37A §6 "prefer unresolved / needs-attention over a false positive").

Supported classes and their exact deterministic rules are documented on
:class:`ActiveMemoryContradictionDetector` and in
``docs/active-agent-memory-verification-layer.md`` §13.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Iterable

from app.models.active_memory import (
    ContradictionClass,
    ContradictionRecord,
    ContradictionResolutionState,
    ContradictionSeverity,
    LifecycleState,
    MemoryRecord,
    MemoryRecordKind,
    MemorySource,
    MemorySourceType,
    SupersessionKind,
)
from app.store.active_memory_store import MemoryStore

# --------------------------------------------------------------------------- #
# Recognized, closed value vocabularies for the mutually-exclusive-state classes.
#
# These are *value tokens*, compared after conservative normalization (trim +
# Unicode casefold). They are deliberately NOT a natural-language ontology and
# carry no synonym expansion or fuzzy matching (Phase 37D "avoid speculative
# semantic inference"): a token conflicts with another only if both appear here in
# opposing sets. Extending a set is a conscious, reviewable vocabulary change.
# --------------------------------------------------------------------------- #
MERGED_VALUE_TOKENS = frozenset({"merged"})
NOT_MERGED_VALUE_TOKENS = frozenset({"pending", "unmerged", "not_merged"})
CLEAN_VALUE_TOKENS = frozenset({"clean"})
DIRTY_VALUE_TOKENS = frozenset({"dirty"})

# Field separator for canonical key construction. The unit-separator control
# character cannot appear in a contract identifier/subject/predicate (they are
# bounded printable text), so it can never be forged by field contents.
_KEY_SEP = "\x1f"

# Stable, deterministic per-class severity (Phase 37A §4.8 "severity where
# justified"; the contract rationale on ``ContradictionSeverity`` gives exactly
# this guidance): a ``pending_vs_merged`` conflict can invalidate an agent's whole
# baseline (critical); a stale clean/dirty working-tree conflict is informational.
# Severity is assigned by class, never *calculated* from evidence, and drives the
# documented result ordering.
CLASS_SEVERITY: dict[ContradictionClass, ContradictionSeverity] = {
    ContradictionClass.PENDING_VS_MERGED: ContradictionSeverity.CRITICAL,
    ContradictionClass.DUPLICATE_PHASE_STATUS: ContradictionSeverity.WARNING,
    ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION: ContradictionSeverity.WARNING,
    ContradictionClass.CLEAN_VS_DIRTY_WORKING_TREE: ContradictionSeverity.INFO,
}

# Most-severe-first ordering rank for the deterministic result order.
_SEVERITY_RANK: dict[ContradictionSeverity | None, int] = {
    ContradictionSeverity.CRITICAL: 0,
    ContradictionSeverity.WARNING: 1,
    ContradictionSeverity.INFO: 2,
    None: 3,
}

# The identity of this detector as a memory source. It is a deterministic backend
# derivation, not a trusted authority; ``MemorySource`` carries no trust flag by
# contract, so this only records provenance ("who derived this result").
DEFAULT_DETECTION_SOURCE = MemorySource(
    source_type=MemorySourceType.CLI_REPORT,
    source_id="active-memory-contradiction-detector",
    display_label="Active Memory Contradiction Detector",
)


def _normalize(text: str) -> str:
    """Conservative, deterministic text normalization: trim + Unicode casefold.

    Used for both assertion-target identity (subject/predicate/scope) and value
    comparison. Casefold makes ``"Merged"`` and ``"merged"`` equivalent (so an
    equal assertion never looks like a conflict) and makes ``"Phase 37B"`` and
    ``"phase 37b"`` group onto the same target — but it performs **no** stemming,
    synonym expansion, or fuzzy matching, so genuinely different strings
    (``"complete"`` vs ``"completed"``) stay distinct.
    """
    return text.strip().casefold()


@dataclass(frozen=True)
class _AssertionTarget:
    """The canonical identity of *what* a record asserts about.

    Two records are only ever compared when their targets are equal: same
    project, same (narrower) scope, same normalized subject and predicate. Scope
    is part of identity and is **not** inherited (Phase 37A "no scope inheritance
    in this phase"), so a global claim and a phase-scoped claim about the same
    subject are different targets — an unrelated-scope pair can never conflict.
    """

    project_id: str
    scope_type: str
    scope_id: str
    subject: str
    predicate: str

    def key(self) -> str:
        """A stable, collision-resistant serialization for grouping and hashing."""
        return _KEY_SEP.join(
            (
                self.project_id,
                self.scope_type,
                self.scope_id,
                self.subject,
                self.predicate,
            )
        )


def _target_of(record: MemoryRecord) -> _AssertionTarget:
    """Derive a record's canonical assertion target from contract fields only."""
    scope_type = record.scope.scope_type.value if record.scope is not None else ""
    scope_id = _normalize(record.scope.scope_id) if record.scope is not None else ""
    return _AssertionTarget(
        project_id=record.project_id,
        scope_type=scope_type,
        scope_id=scope_id,
        subject=_normalize(record.claim.subject),
        predicate=_normalize(record.claim.predicate),
    )


def _stable_contradiction_id(
    contradiction_class: ContradictionClass,
    target: _AssertionTarget,
    record_ids: Iterable[str],
) -> str:
    """Build a stable, content-derived contradiction id.

    The id is a function of the fired class, the canonical assertion target, and
    the **sorted** supporting record ids — nothing else. It therefore never
    depends on insertion order, process memory addresses, RNG, wall-clock time, or
    dict iteration order, so reversing the input or re-running detection over
    unchanged records reproduces the same id. Uses the repository's existing
    sha1-hexdigest derived-id convention (cf.
    ``app.services.knowledge_graph._derived_edge_id``).
    """
    canonical = _KEY_SEP.join(
        (
            contradiction_class.value,
            target.key(),
            ",".join(sorted(record_ids)),
        )
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return f"contradiction-{digest}"


def _classify_value_conflict(
    record_a: MemoryRecord, record_b: MemoryRecord
) -> ContradictionClass | None:
    """Classify a same-target pair by comparing their normalized claim values.

    Returns the fired :class:`ContradictionClass`, or ``None`` when the pair is
    not a reportable contradiction. Rules (evaluated most-specific first):

    * The two claims must share the same :class:`ClaimValueKind` — comparison is
      like-with-like. A kind mismatch is *missing comparison basis*, not a
      conflict, so it yields ``None``.
    * Equal normalized values are the *same assertion* → ``None`` (a duplicate,
      never a contradiction).
    * One value in ``MERGED`` and the other in ``NOT_MERGED`` → mutually-exclusive
      state ``PENDING_VS_MERGED``.
    * One value ``clean`` and the other ``dirty`` → mutually-exclusive state
      ``CLEAN_VS_DIRTY_WORKING_TREE``.
    * Otherwise, if *both* records are ``PHASE_STATUS`` and the values differ,
      it is an incompatible phase-status assertion → ``DUPLICATE_PHASE_STATUS``.
    * Any other differing-value pair yields ``None``: there is no general-purpose
      "values differ" contradiction class, and inventing one would require an
      ontology the contract deliberately omits.
    """
    if record_a.claim.value_kind is not record_b.claim.value_kind:
        return None

    value_a = _normalize(record_a.claim.value)
    value_b = _normalize(record_b.claim.value)
    if value_a == value_b:
        return None  # identical assertion — a duplicate, not a contradiction

    values = {value_a, value_b}
    if values & MERGED_VALUE_TOKENS and values & NOT_MERGED_VALUE_TOKENS:
        return ContradictionClass.PENDING_VS_MERGED
    if values & CLEAN_VALUE_TOKENS and values & DIRTY_VALUE_TOKENS:
        return ContradictionClass.CLEAN_VS_DIRTY_WORKING_TREE
    if (
        record_a.kind is MemoryRecordKind.PHASE_STATUS
        and record_b.kind is MemoryRecordKind.PHASE_STATUS
    ):
        return ContradictionClass.DUPLICATE_PHASE_STATUS
    return None


class ActiveMemoryContradictionDetector:
    """Deterministic, read-only contradiction detector over Active Memory records.

    Two detection passes, both pure functions of stored fields:

    **1. Incompatible / mutually-exclusive value assertions.** Eligible records
    are grouped by canonical assertion target (project + scope + normalized
    subject + predicate). Every unordered pair within a group is compared by
    :func:`_classify_value_conflict`, producing ``pending_vs_merged`` (merged vs
    a not-merged token), ``clean_vs_dirty_working_tree`` (clean vs dirty), or
    ``duplicate_phase_status`` (two ``phase_status`` records disagreeing on the
    same phase). Equal values, kind mismatches, and unrelated
    subjects/scopes/keys never fire.

    **2. Active-vs-superseded decision.** For every eligible record ``S`` that
    authors a ``supersedes`` link at a target record ``R`` that is itself an
    eligible ``project_decision``, a ``current_vs_superseded_decision`` is
    reported: ``R`` is presented as current (active) yet a standing record already
    supersedes it. This uses only ``supersession_refs`` + ``lifecycle_state`` — no
    value inference.

    **Eligibility.** Only ``lifecycle_state == active`` records participate.
    Records that have left the active baseline (``inactive`` / ``superseded`` /
    ``retracted`` / ``stale`` / ``archived``) are stored, queryable *history*
    (Phase 37A §9) and are excluded so detection never resurfaces withdrawn or
    replaced claims. Verification state does **not** affect eligibility: a
    contradiction is a structural fact about assertions, independent of how
    strongly either claim is currently believed (an ``unverified`` active claim
    can still contradict another active claim).

    **Deferred class.** ``frontend_only_vs_backend_modification`` is *not*
    implemented: it requires mapping a decision/constraint's scope onto observed
    file-modification paths, i.e. a path/domain ontology, which is exactly the
    speculative semantic inference this phase forbids. It stays deferred until a
    contract carries a deterministic shared target for it.
    """

    def detect(
        self,
        records: Iterable[MemoryRecord],
        *,
        detected_at: datetime,
        detection_source: MemorySource | None = None,
    ) -> list[ContradictionRecord]:
        """Derive contradictions from ``records`` (read-only).

        ``detected_at`` is caller-supplied for reproducibility; the detector never
        reads the wall clock. ``detection_source`` defaults to
        :data:`DEFAULT_DETECTION_SOURCE`. The input is de-duplicated by
        ``record_id`` (so a record is never compared with itself and a duplicated
        record cannot duplicate output), then filtered to eligible records. The
        returned list is in the documented deterministic order.
        """
        source = detection_source or DEFAULT_DETECTION_SOURCE
        eligible = self._eligible_records(records)

        results: dict[str, ContradictionRecord] = {}
        for contradiction in self._detect_value_conflicts(eligible, detected_at, source):
            results[contradiction.contradiction_id] = contradiction
        for contradiction in self._detect_superseded_decisions(
            eligible, detected_at, source
        ):
            results[contradiction.contradiction_id] = contradiction

        return self._ordered(results.values())

    def detect_from_store(
        self,
        store: MemoryStore,
        *,
        detected_at: datetime,
        detection_source: MemorySource | None = None,
    ) -> list[ContradictionRecord]:
        """Detect over every record the ``store`` holds, via its public surface.

        Reads through :meth:`MemoryStore.list_records` (which already returns
        defensive deep copies in a deterministic order) and never reaches into
        store internals or mutates it.
        """
        return self.detect(
            store.list_records(),
            detected_at=detected_at,
            detection_source=detection_source,
        )

    # ------------------------------------------------------------------ #
    # Input preparation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _eligible_records(records: Iterable[MemoryRecord]) -> list[MemoryRecord]:
        """De-duplicate by ``record_id`` and keep only ``active`` records.

        De-duplication is order-independent: inputs are first sorted by
        ``record_id`` then by a canonical JSON serialization, and the first entry
        per id is kept. Identical duplicates collapse to one; the pathological
        "same id, different content" case (which the store itself rejects on
        insert) resolves deterministically regardless of input order.
        """
        ordered_inputs = sorted(
            records,
            key=lambda r: (r.record_id, r.model_dump_json()),
        )
        deduped: dict[str, MemoryRecord] = {}
        for record in ordered_inputs:
            deduped.setdefault(record.record_id, record)
        return [
            record
            for record in deduped.values()
            if record.lifecycle_state is LifecycleState.ACTIVE
        ]

    # ------------------------------------------------------------------ #
    # Pass 1 — value conflicts
    # ------------------------------------------------------------------ #
    def _detect_value_conflicts(
        self,
        eligible: list[MemoryRecord],
        detected_at: datetime,
        source: MemorySource,
    ) -> list[ContradictionRecord]:
        groups: dict[str, list[MemoryRecord]] = {}
        target_by_key: dict[str, _AssertionTarget] = {}
        for record in eligible:
            target = _target_of(record)
            key = target.key()
            groups.setdefault(key, []).append(record)
            target_by_key.setdefault(key, target)

        out: list[ContradictionRecord] = []
        for key, members in groups.items():
            if len(members) < 2:
                continue
            target = target_by_key[key]
            # Deterministic pairing: sort members by id, then take unordered pairs.
            members_sorted = sorted(members, key=lambda r: r.record_id)
            for record_a, record_b in combinations(members_sorted, 2):
                contradiction_class = _classify_value_conflict(record_a, record_b)
                if contradiction_class is None:
                    continue
                out.append(
                    self._build_value_contradiction(
                        contradiction_class,
                        target,
                        record_a,
                        record_b,
                        detected_at,
                        source,
                    )
                )
        return out

    def _build_value_contradiction(
        self,
        contradiction_class: ContradictionClass,
        target: _AssertionTarget,
        record_a: MemoryRecord,
        record_b: MemoryRecord,
        detected_at: datetime,
        source: MemorySource,
    ) -> ContradictionRecord:
        involved = sorted((record_a.record_id, record_b.record_id))
        # Present the conflicting values keyed to their record for stable, factual
        # evidence — sorted by record id so the evidence is order-independent.
        by_id = {record_a.record_id: record_a, record_b.record_id: record_b}
        conflicting_values = [
            {
                "record_id": rid,
                "value": by_id[rid].claim.value,
                "normalized_value": _normalize(by_id[rid].claim.value),
                "value_kind": by_id[rid].claim.value_kind.value,
            }
            for rid in involved
        ]
        summary = (
            f"Records {involved[0]!r} and {involved[1]!r} make incompatible "
            f"assertions about {target.subject!r}/{target.predicate!r}: "
            f"{conflicting_values[0]['normalized_value']!r} vs "
            f"{conflicting_values[1]['normalized_value']!r} "
            f"({contradiction_class.value})."
        )
        return ContradictionRecord(
            contradiction_id=_stable_contradiction_id(
                contradiction_class, target, involved
            ),
            contradiction_class=contradiction_class,
            involved_record_ids=involved,
            summary=summary,
            detection_source=source,
            detected_at=detected_at,
            resolution_state=ContradictionResolutionState.OPEN,
            evidence_ids=self._merge_evidence_ids(record_a, record_b),
            severity=CLASS_SEVERITY.get(contradiction_class),
            metadata={
                "reason_code": "incompatible_value_assertion",
                "assertion_target": self._target_metadata(target),
                "conflicting_values": conflicting_values,
            },
        )

    # ------------------------------------------------------------------ #
    # Pass 2 — active decision superseded by a standing record
    # ------------------------------------------------------------------ #
    def _detect_superseded_decisions(
        self,
        eligible: list[MemoryRecord],
        detected_at: datetime,
        source: MemorySource,
    ) -> list[ContradictionRecord]:
        by_id = {record.record_id: record for record in eligible}
        out: list[ContradictionRecord] = []
        # Iterate in a deterministic order (eligible is already id-sorted).
        for superseding in eligible:
            for ref in superseding.supersession_refs:
                if ref.kind is not SupersessionKind.SUPERSEDES:
                    continue
                target_record = by_id.get(ref.target_record_id)
                if target_record is None:
                    continue  # target absent or not eligible/active
                if target_record.kind is not MemoryRecordKind.PROJECT_DECISION:
                    continue
                if target_record.record_id == superseding.record_id:
                    continue  # never a self-supersession contradiction
                out.append(
                    self._build_superseded_decision_contradiction(
                        superseding, target_record, detected_at, source
                    )
                )
        return out

    def _build_superseded_decision_contradiction(
        self,
        superseding: MemoryRecord,
        superseded_decision: MemoryRecord,
        detected_at: datetime,
        source: MemorySource,
    ) -> ContradictionRecord:
        target = _target_of(superseded_decision)
        involved = sorted((superseding.record_id, superseded_decision.record_id))
        summary = (
            f"Decision {superseded_decision.record_id!r} is still active yet "
            f"record {superseding.record_id!r} supersedes it "
            f"({ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION.value})."
        )
        return ContradictionRecord(
            contradiction_id=_stable_contradiction_id(
                ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION, target, involved
            ),
            contradiction_class=ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION,
            involved_record_ids=involved,
            summary=summary,
            detection_source=source,
            detected_at=detected_at,
            resolution_state=ContradictionResolutionState.OPEN,
            evidence_ids=self._merge_evidence_ids(superseding, superseded_decision),
            severity=CLASS_SEVERITY.get(
                ContradictionClass.CURRENT_VS_SUPERSEDED_DECISION
            ),
            metadata={
                "reason_code": "active_decision_has_supersedes_link",
                "assertion_target": self._target_metadata(target),
                "superseded_record_id": superseded_decision.record_id,
                "superseding_record_id": superseding.record_id,
            },
        )

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _merge_evidence_ids(*records: MemoryRecord) -> list[str]:
        """Union the supporting evidence ids of the involved records.

        Sorted and de-duplicated so the evidence set is stable regardless of which
        record is considered first. References original evidence via the
        contract-defined ``evidence_ids`` — the detector never fabricates evidence.
        """
        merged: set[str] = set()
        for record in records:
            merged.update(record.evidence_ids)
        return sorted(merged)

    @staticmethod
    def _target_metadata(target: _AssertionTarget) -> dict[str, str]:
        return {
            "project_id": target.project_id,
            "scope_type": target.scope_type,
            "scope_id": target.scope_id,
            "subject": target.subject,
            "predicate": target.predicate,
        }

    @staticmethod
    def _ordered(
        contradictions: Iterable[ContradictionRecord],
    ) -> list[ContradictionRecord]:
        """Stable, documented result order.

        Sort key (all fields available on the contract): severity (most severe
        first), then contradiction class, then the canonical assertion target
        recovered from metadata, then the stable contradiction id as a total
        tiebreak. Insertion order of the underlying records can never change this.
        """

        def sort_key(c: ContradictionRecord) -> tuple[int, str, str, str]:
            target_meta = c.metadata.get("assertion_target", {})
            target_key = _KEY_SEP.join(
                (
                    str(target_meta.get("project_id", "")),
                    str(target_meta.get("scope_type", "")),
                    str(target_meta.get("scope_id", "")),
                    str(target_meta.get("subject", "")),
                    str(target_meta.get("predicate", "")),
                )
            )
            return (
                _SEVERITY_RANK[c.severity],
                c.contradiction_class.value,
                target_key,
                c.contradiction_id,
            )

        return sorted(contradictions, key=sort_key)


def detect_contradictions(
    records: Iterable[MemoryRecord],
    *,
    detected_at: datetime,
    detection_source: MemorySource | None = None,
) -> list[ContradictionRecord]:
    """Module-level convenience over :class:`ActiveMemoryContradictionDetector`.

    A pure function accepting a deterministic collection of memory records, for
    callers that do not need to hold a detector instance.
    """
    return ActiveMemoryContradictionDetector().detect(
        records, detected_at=detected_at, detection_source=detection_source
    )
