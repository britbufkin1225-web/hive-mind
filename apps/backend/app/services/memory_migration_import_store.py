"""Bounded, integrity-sealed, atomic/CAS migration workflow ledger."""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from pydantic import ValidationError
from app.models.memory_migration_import import *
from app.services.migration_import_paths import resolve_migration_import_path

class MigrationImportStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or resolve_migration_import_path()
    def path(self) -> Path: return self._path
    def exists(self) -> bool: return self._path.exists()
    def empty(self) -> MigrationImportLedger:
        raw = {"envelope_type":"migration-import-ledger","schema_version":LEDGER_VERSION,"ledger_revision":0,"commit_generation":0,"review_decisions":[],"authorization_contexts":[],"authorization_revocations":[],"specifications":[],"attempts":[],"receipts":[],"quarantined":False,"quarantine_reason":None,"ledger_integrity_digest": ""}
        raw["ledger_integrity_digest"] = derive_ledger_integrity_digest(raw)
        return MigrationImportLedger.model_validate(raw)
    def load(self) -> MigrationImportLedger:
        try:
            if self._path.stat().st_size > MAX_IMPORT_FILE_BYTES:
                raise MemoryMigrationImportError(ImportDiagnosticCode.BOUNDED_INPUT_EXCEEDED, "ledger exceeds the bounded size")
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            ledger = MigrationImportLedger.model_validate(raw)
            if any(r.receipt_integrity_digest != derive_receipt_integrity_digest(r) for r in ledger.receipts):
                raise ValueError("receipt integrity mismatch")
            return ledger
        except FileNotFoundError: raise
        except MemoryMigrationImportError: raise
        except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            raise MemoryMigrationImportError(ImportDiagnosticCode.CORRUPT_LEDGER, "migration import ledger is corrupt or unreadable") from exc
    def persist(self, ledger: MigrationImportLedger, *, expected_revision: int | None = None) -> None:
        if self.exists() and expected_revision is not None and self.load().ledger_revision != expected_revision:
            raise MemoryMigrationImportError(ImportDiagnosticCode.REVISION_CONFLICT, "ledger revision changed")
        self._atomic_write(ledger.model_dump_json())
    def replace(self, ledger: MigrationImportLedger, **changes: object) -> MigrationImportLedger:
        raw = ledger.model_dump(mode="json")
        raw.update(changes); raw["ledger_revision"] = ledger.ledger_revision + 1
        raw["ledger_integrity_digest"] = ""
        raw["ledger_integrity_digest"] = derive_ledger_integrity_digest(raw)
        updated = MigrationImportLedger.model_validate(raw)
        self.persist(updated, expected_revision=ledger.ledger_revision)
        return updated
    def _atomic_write(self, payload: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=self._path.name + ".", suffix=".tmp", dir=self._path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(name, self._path)
        except OSError as exc:
            try: os.unlink(name)
            except OSError: pass
            raise MemoryMigrationImportError(ImportDiagnosticCode.PERSISTENCE_FAILURE, "atomic ledger persistence failed") from exc
