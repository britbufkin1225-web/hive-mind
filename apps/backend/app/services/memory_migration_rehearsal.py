"""Fail-closed, test-owned storage boundary for migration rehearsals."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.services.migration_import_paths import (
    resolve_active_memory_snapshot_path,
    resolve_migration_import_lock_path,
    resolve_migration_import_path,
)


@dataclass(frozen=True)
class MigrationRehearsalPaths:
    """Exact disposable artifacts; never falls back to production path resolution."""

    root: Path
    ledger: Path
    snapshot: Path
    lock: Path

    @classmethod
    def isolated(cls, root: Path) -> "MigrationRehearsalPaths":
        resolved_root = root.resolve()
        paths = cls(
            root=resolved_root,
            ledger=resolved_root / "migration-import-ledger.json",
            snapshot=resolved_root / "active-memory-snapshot.json",
            lock=resolved_root / "migration-import.lock",
        )
        authoritative = {
            resolve_migration_import_path().resolve(),
            resolve_active_memory_snapshot_path().resolve(),
            resolve_migration_import_lock_path().resolve(),
        }
        if any(path in authoritative for path in (paths.ledger, paths.snapshot, paths.lock)):
            raise MemoryMigrationImportError(
                ImportDiagnosticCode.PERSISTENCE_FAILURE,
                "rehearsal storage resolves to an authoritative migration artifact",
            )
        if resolved_root in {path.parent for path in authoritative}:
            raise MemoryMigrationImportError(
                ImportDiagnosticCode.PERSISTENCE_FAILURE,
                "rehearsal storage root resolves to the authoritative storage root",
            )
        return paths

    def reset(self) -> None:
        """Remove only the three known disposable artifacts and empty root directory."""
        for path in (self.ledger, self.snapshot, self.lock):
            if path.parent != self.root:
                raise MemoryMigrationImportError(
                    ImportDiagnosticCode.PERSISTENCE_FAILURE,
                    "rehearsal artifact escaped its isolated root",
                )
            path.unlink(missing_ok=True)
        if self.root.exists() and not any(self.root.iterdir()):
            self.root.rmdir()
