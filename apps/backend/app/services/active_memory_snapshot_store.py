"""Durable owner of integrity-sealed Active Memory snapshots."""
from __future__ import annotations
import json, os, tempfile
from dataclasses import dataclass
from pathlib import Path
from pydantic import ValidationError
from app.models.memory_migration_import import *
from app.services.migration_import_paths import resolve_active_memory_snapshot_path
from app.store.active_memory_store import InMemoryActiveMemoryStore, MalformedSnapshotError

@dataclass(frozen=True)
class LoadedActiveMemorySnapshot:
    store: InMemoryActiveMemoryStore
    commit_generation: int
    envelope: ActiveMemorySnapshotEnvelope

class ActiveMemorySnapshotStore:
    def __init__(self, path: Path | None = None) -> None: self._path = path or resolve_active_memory_snapshot_path()
    def path(self) -> Path: return self._path
    def exists(self) -> bool: return self._path.exists()
    def load(self) -> LoadedActiveMemorySnapshot:
        try:
            if self._path.stat().st_size > MAX_IMPORT_FILE_BYTES: raise ValueError("oversized")
            envelope = ActiveMemorySnapshotEnvelope.model_validate_json(self._path.read_text(encoding="utf-8"))
            store = InMemoryActiveMemoryStore.restore(envelope.active_memory)
            return LoadedActiveMemorySnapshot(store, envelope.commit_generation, envelope)
        except FileNotFoundError: raise
        except (OSError, ValueError, ValidationError, MalformedSnapshotError) as exc:
            raise MemoryMigrationImportError(ImportDiagnosticCode.CORRUPT_ACTIVE_MEMORY_SNAPSHOT, "active memory snapshot is corrupt or unreadable") from exc
    def persist(self, store: InMemoryActiveMemoryStore, commit_generation: int) -> ActiveMemorySnapshotEnvelope:
        raw = {"envelope_type":"active-memory-snapshot","schema_version":SNAPSHOT_VERSION,"commit_generation": commit_generation, "active_memory": store.serialize(), "snapshot_integrity_digest": ""}
        raw["snapshot_integrity_digest"] = derive_snapshot_integrity_digest(raw)
        envelope = ActiveMemorySnapshotEnvelope.model_validate(raw)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=self._path.name + ".", suffix=".tmp", dir=self._path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(envelope.model_dump_json()); handle.flush(); os.fsync(handle.fileno())
            os.replace(name, self._path)
        except OSError as exc:
            try: os.unlink(name)
            except OSError: pass
            raise MemoryMigrationImportError(ImportDiagnosticCode.PERSISTENCE_FAILURE, "atomic snapshot persistence failed") from exc
        return envelope
