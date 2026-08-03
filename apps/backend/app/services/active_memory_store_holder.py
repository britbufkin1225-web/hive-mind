"""Non-escaping, publish-last owner of the authoritative live memory store."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from app.models.active_memory import *
from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.store.active_memory_store import InMemoryActiveMemoryStore

@dataclass(frozen=True)
class QuarantineState:
    quarantined: bool = False
    reason: str | None = None

class AuthoritativeActiveMemoryStoreHolder:
    def __init__(self, initial: InMemoryActiveMemoryStore | None = None, generation: int = 0) -> None:
        self._guard=RLock(); self._store=initial or InMemoryActiveMemoryStore(); self._generation=generation; self._quarantine=QuarantineState()
    def find_record(self, record_id: str):
        with self._guard: return self._store.find(record_id)
    def get_record(self, record_id: str):
        with self._guard: return self._store.get(record_id)
    def list_records(self, **filters):
        with self._guard: return self._store.list_records(**filters)
    def snapshot_payload(self):
        with self._guard: return self._store.serialize()
    def current_generation(self):
        with self._guard: return self._generation
    def quarantine_state(self):
        with self._guard: return self._quarantine
    def quarantine(self, reason: str):
        with self._guard: self._quarantine=QuarantineState(True, reason[:128])
    def clear_quarantine(self):
        with self._guard: self._quarantine=QuarantineState()
    def publish(self, replacement: InMemoryActiveMemoryStore, expected_generation: int, new_generation: int):
        if not isinstance(replacement, InMemoryActiveMemoryStore):
            raise MemoryMigrationImportError(ImportDiagnosticCode.LIVE_STORE_REPLACEMENT_FAILURE, "replacement is not an Active Memory store")
        with self._guard:
            if self._generation != expected_generation or new_generation != expected_generation + 1:
                raise MemoryMigrationImportError(ImportDiagnosticCode.LIVE_STORE_REPLACEMENT_FAILURE, "live store generation changed")
            self._store=replacement; self._generation=new_generation
