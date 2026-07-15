"""Phase 37C — Deterministic Active Memory store (MVP).

The first runtime storage layer for the Active Agent Memory + Verification Layer
designed in Phase 37A
(``docs/planning/phase-37a-active-agent-memory-verification-layer-planning.md``)
and contract-typed in Phase 37B (``app.models.active_memory``). This module adds
**deterministic storage and lifecycle behavior only**. It deliberately does
**not** implement: API endpoints, ingestion, contradiction detection,
active-state calculation, context-packet generation, or any AI/LLM logic — those
are later phases (37D–37H) built on top of this store.

Design (grounded in the planning + contract docs, not invented here):

* **In-memory + a serialization boundary**, not a database. Phase 37A/37B fix the
  *record contracts* but leave the 37C persistence medium open; per the phase
  brief, an undecided medium defaults to a clean in-memory store plus a
  deterministic serialize/restore boundary rather than committing permanent
  infrastructure (SQLite, migrations, remote storage) prematurely. Callers that
  want durability own the read/write of the serialized snapshot.
* **Caller-supplied identity.** ``MemoryRecord.record_id`` is a required contract
  field, so the store never generates ids. There is no random UUID minting inside
  core logic (Phase 37C determinism requirement); duplicate ids are rejected
  deterministically.
* **No unpredictable timestamps in storage operations.** ``created_at`` rides on
  the record; the store neither stamps nor rewrites it. Ordering is derived from
  contract fields only, so repeated runs produce identical output.
* **Records are treated as immutable** (Phase 37A §9). Reads return defensive deep
  copies so a caller can never mutate stored state, and a lifecycle transition
  produces a *new* record snapshot (``model_copy``) that preserves every evidence,
  provenance, verification, and claim field — it never silently rewrites them.
* **Explicit lifecycle transition table** (:data:`LIFECYCLE_TRANSITIONS`) rather
  than scattered conditionals, mirroring the Phase 37A §7.2/§9 transition rules;
  invalid transitions fail consistently.

Boundaries honored: no filesystem watching, ingestion, repository scanning, graph
or source mutation, background behavior, or new dependencies.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Protocol, runtime_checkable

from pydantic import ValidationError

from app.models.active_memory import (
    ACTIVE_MEMORY_CONTRACT_VERSION,
    LifecycleState,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScopeType,
    VerificationState,
)

# --------------------------------------------------------------------------- #
# Snapshot format constants.
#
# The serialized representation is a small, explicit JSON-compatible document:
# a contract version (so a restore can reject a foreign/incompatible snapshot)
# plus a list of contract-dumped records. Kept in this module — not added to the
# frozen Phase 37B contract file — because it is a 37C storage concern, not a wire
# contract the frontend mirrors.
# --------------------------------------------------------------------------- #
SNAPSHOT_VERSION_KEY = "contract_version"
SNAPSHOT_RECORDS_KEY = "records"


# --------------------------------------------------------------------------- #
# Explicit lifecycle transition table (Phase 37A §7.2, §9).
#
# The in-force axis is LifecycleState: active / inactive / superseded / retracted
# / stale / archived. Allowed non-identity transitions, grounded in the planning
# doc:
#
#   * ``active`` may move to any leaving state: general deactivation
#     (``inactive``), orderly replacement (``superseded``), explicit withdrawal
#     (``retracted``), freshness lapse (``stale``), or retention (``archived``).
#   * ``inactive`` is a soft, non-terminal deactivation: it may be reactivated
#     (``active``) or archived.
#   * ``stale`` left the active baseline on a freshness lapse; it may be
#     superseded/retracted by a later record-driven event, or archived. It is not
#     silently reverted to ``active`` — re-verification is expressed as a *new*
#     record (§9.2), not an in-place resurrection.
#   * ``superseded`` and ``retracted`` are terminal-ish (§7.2: "not silently
#     reverted; a new record is created instead"); the only onward move is
#     retention (``archived``).
#   * ``archived`` is terminal (a retention/view state, never deletion — §9.1).
#
# A transition to the *same* state is always allowed and idempotent (handled in
# :meth:`InMemoryActiveMemoryStore.transition_lifecycle`), so it is not duplicated
# into every row here.
# --------------------------------------------------------------------------- #
LIFECYCLE_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.ACTIVE: frozenset(
        {
            LifecycleState.INACTIVE,
            LifecycleState.SUPERSEDED,
            LifecycleState.RETRACTED,
            LifecycleState.STALE,
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.INACTIVE: frozenset(
        {LifecycleState.ACTIVE, LifecycleState.ARCHIVED}
    ),
    LifecycleState.STALE: frozenset(
        {
            LifecycleState.SUPERSEDED,
            LifecycleState.RETRACTED,
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.SUPERSEDED: frozenset({LifecycleState.ARCHIVED}),
    LifecycleState.RETRACTED: frozenset({LifecycleState.ARCHIVED}),
    LifecycleState.ARCHIVED: frozenset(),
}


# =========================================================================== #
# Errors (deterministic, typed, catchable per failure mode)
# =========================================================================== #
class ActiveMemoryStoreError(Exception):
    """Base class for all Active Memory store errors."""


class DuplicateRecordError(ActiveMemoryStoreError):
    """Raised when inserting a record whose ``record_id`` already exists."""


class RecordNotFoundError(ActiveMemoryStoreError):
    """Raised when a lookup/transition targets an unknown ``record_id``."""


class InvalidLifecycleTransitionError(ActiveMemoryStoreError):
    """Raised when a lifecycle transition is not permitted by the table."""

    def __init__(self, source: LifecycleState, target: LifecycleState) -> None:
        self.source = source
        self.target = target
        super().__init__(
            f"invalid lifecycle transition {source.value!r} -> {target.value!r}"
        )


class MalformedSnapshotError(ActiveMemoryStoreError):
    """Raised when a serialized snapshot is structurally invalid or corrupt."""


# =========================================================================== #
# Store protocol (small explicit abstraction)
# =========================================================================== #
@runtime_checkable
class MemoryStore(Protocol):
    """The minimal Active Memory storage contract 37D+ will consume.

    Kept intentionally small: insert, retrieve, list/filter, lifecycle
    transition, and a serialize/restore boundary. Future phases (contradiction
    detection, active-state calculation, context-packet generation) read through
    this surface and must not require rewriting its core semantics.
    """

    def insert(self, record: MemoryRecord) -> MemoryRecord: ...

    def get(self, record_id: str) -> MemoryRecord: ...

    def find(self, record_id: str) -> MemoryRecord | None: ...

    def list_records(
        self,
        *,
        project_id: str | None = ...,
        kind: MemoryRecordKind | None = ...,
        lifecycle_state: LifecycleState | None = ...,
        verification_state: VerificationState | None = ...,
        scope_type: MemoryScopeType | None = ...,
    ) -> list[MemoryRecord]: ...

    def transition_lifecycle(
        self, record_id: str, target: LifecycleState
    ) -> MemoryRecord: ...

    def serialize(self) -> dict[str, Any]: ...


# =========================================================================== #
# In-memory deterministic implementation
# =========================================================================== #
class InMemoryActiveMemoryStore:
    """Deterministic in-memory Active Memory store with a serialization boundary.

    Records are keyed by ``record_id``. Every value crossing the boundary — on
    insert, on read, and on lifecycle transition — is a defensive **deep copy** so
    internal state cannot be mutated by reference from the outside (and stored
    records cannot be mutated by a caller that kept a handle to what it inserted).
    """

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    def insert(self, record: MemoryRecord) -> MemoryRecord:
        """Insert a new record, keyed by its stable ``record_id``.

        Rejects a duplicate id deterministically. Stores a deep copy so a later
        mutation of the caller's instance cannot leak into the store. Returns a
        fresh defensive copy of what was stored.
        """
        if not isinstance(record, MemoryRecord):  # defensive: contract type only
            raise ActiveMemoryStoreError(
                "insert() requires a MemoryRecord instance"
            )
        record_id = record.record_id
        if record_id in self._records:
            raise DuplicateRecordError(
                f"record_id {record_id!r} already exists in the store"
            )
        self._records[record_id] = record.model_copy(deep=True)
        return self._records[record_id].model_copy(deep=True)

    def transition_lifecycle(
        self, record_id: str, target: LifecycleState
    ) -> MemoryRecord:
        """Move a record to ``target`` lifecycle state via the transition table.

        Deterministic and evidence-preserving: the transition produces a *new*
        record snapshot (``model_copy``) that changes only ``lifecycle_state`` and
        carries every claim, evidence, provenance, verification, and supersession
        field forward untouched (Phase 37A §9 immutability / append-only intent).

        * A transition to the record's current state is an idempotent no-op that
          returns the record unchanged.
        * Any other transition must be listed in :data:`LIFECYCLE_TRANSITIONS`;
          otherwise :class:`InvalidLifecycleTransitionError` is raised and the
          stored record is left untouched.
        """
        stored = self._records.get(record_id)
        if stored is None:
            raise RecordNotFoundError(f"record_id {record_id!r} not found")

        current = stored.lifecycle_state
        if target == current:
            # Idempotent self-transition: no rewrite, deterministic.
            return stored.model_copy(deep=True)

        if target not in LIFECYCLE_TRANSITIONS.get(current, frozenset()):
            raise InvalidLifecycleTransitionError(current, target)

        updated = stored.model_copy(deep=True, update={"lifecycle_state": target})
        self._records[record_id] = updated
        return updated.model_copy(deep=True)

    # ------------------------------------------------------------------ #
    # Reads (never mutate stored state)
    # ------------------------------------------------------------------ #
    def find(self, record_id: str) -> MemoryRecord | None:
        """Return a defensive copy of a record by id, or ``None`` if absent."""
        stored = self._records.get(record_id)
        return stored.model_copy(deep=True) if stored is not None else None

    def get(self, record_id: str) -> MemoryRecord:
        """Return a defensive copy of a record by id, or raise if absent."""
        record = self.find(record_id)
        if record is None:
            raise RecordNotFoundError(f"record_id {record_id!r} not found")
        return record

    def __contains__(self, record_id: object) -> bool:
        return record_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def list_records(
        self,
        *,
        project_id: str | None = None,
        kind: MemoryRecordKind | None = None,
        lifecycle_state: LifecycleState | None = None,
        verification_state: VerificationState | None = None,
        scope_type: MemoryScopeType | None = None,
    ) -> list[MemoryRecord]:
        """List records in a stable, deterministic order, optionally filtered.

        Ordering is explicit and total: ascending ``created_at`` with
        ``record_id`` as a stable tiebreak, so equal-timestamp records never
        reorder between runs. Filters are AND-combined over contract-backed fields
        only (project, kind, lifecycle state, verification state, and narrower
        scope type); a ``None`` filter is ignored. Every returned record is a
        defensive deep copy.
        """
        records = self._records.values()

        if project_id is not None:
            records = [r for r in records if r.project_id == project_id]
        if kind is not None:
            records = [r for r in records if r.kind == kind]
        if lifecycle_state is not None:
            records = [r for r in records if r.lifecycle_state == lifecycle_state]
        if verification_state is not None:
            records = [
                r for r in records if r.verification_state == verification_state
            ]
        if scope_type is not None:
            records = [
                r
                for r in records
                if r.scope is not None and r.scope.scope_type == scope_type
            ]

        ordered = sorted(records, key=lambda r: (r.created_at, r.record_id))
        return [r.model_copy(deep=True) for r in ordered]

    # ------------------------------------------------------------------ #
    # Serialization boundary (deterministic encode / decode)
    # ------------------------------------------------------------------ #
    def serialize(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible snapshot of the store.

        Records are emitted in the same stable order as :meth:`list_records`
        (created_at, then record_id) so repeated serialization of unchanged state
        is byte-stable. Each record is contract-dumped via Pydantic's JSON mode.
        """
        return {
            SNAPSHOT_VERSION_KEY: ACTIVE_MEMORY_CONTRACT_VERSION,
            SNAPSHOT_RECORDS_KEY: [
                record.model_dump(mode="json") for record in self.list_records()
            ],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the store to a stable JSON string (sorted keys)."""
        return json.dumps(self.serialize(), indent=indent, sort_keys=True)

    @classmethod
    def restore(cls, snapshot: dict[str, Any]) -> "InMemoryActiveMemoryStore":
        """Rebuild a store from a :meth:`serialize` snapshot.

        Validates structure and every record against the Phase 37B contract, and
        rejects: a non-mapping snapshot, a missing/foreign ``contract_version``, a
        non-list records section, a record that fails contract validation, and a
        duplicate ``record_id`` — each as :class:`MalformedSnapshotError`. Load is
        all-or-nothing: a corrupt snapshot never yields a partially populated
        store.
        """
        if not isinstance(snapshot, dict):
            raise MalformedSnapshotError("snapshot must be a JSON object")

        version = snapshot.get(SNAPSHOT_VERSION_KEY)
        if version != ACTIVE_MEMORY_CONTRACT_VERSION:
            raise MalformedSnapshotError(
                f"snapshot contract version {version!r} does not match "
                f"{ACTIVE_MEMORY_CONTRACT_VERSION!r}"
            )

        raw_records = snapshot.get(SNAPSHOT_RECORDS_KEY)
        if not isinstance(raw_records, list):
            raise MalformedSnapshotError(
                f"snapshot {SNAPSHOT_RECORDS_KEY!r} must be a list"
            )

        store = cls()
        for index, raw in enumerate(raw_records):
            try:
                record = MemoryRecord.model_validate(raw)
            except ValidationError as exc:
                raise MalformedSnapshotError(
                    f"record at index {index} failed contract validation: {exc}"
                ) from exc
            if record.record_id in store._records:
                raise MalformedSnapshotError(
                    f"duplicate record_id {record.record_id!r} in snapshot"
                )
            store._records[record.record_id] = record
        return store

    @classmethod
    def from_json(cls, payload: str) -> "InMemoryActiveMemoryStore":
        """Rebuild a store from a JSON string produced by :meth:`to_json`."""
        try:
            data = json.loads(payload)
        except (TypeError, ValueError) as exc:
            raise MalformedSnapshotError(f"snapshot is not valid JSON: {exc}") from exc
        return cls.restore(data)

    @classmethod
    def from_records(cls, records: Iterable[MemoryRecord]) -> "InMemoryActiveMemoryStore":
        """Build a store from an iterable of records (duplicate ids rejected)."""
        store = cls()
        for record in records:
            store.insert(record)
        return store
