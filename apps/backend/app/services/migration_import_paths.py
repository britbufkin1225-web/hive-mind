"""Side-effect-free Phase 40I local persistence path resolution."""
from __future__ import annotations
import os
from pathlib import Path

def _base() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "HiveMind"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "hive-mind"

def resolve_migration_import_path() -> Path:
    return Path(os.environ.get("HIVEMIND_MIGRATION_IMPORT_PATH", _base() / "migration-import-ledger.json"))

def resolve_active_memory_snapshot_path() -> Path:
    return Path(os.environ.get("HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH", _base() / "active-memory-snapshot.json"))

def resolve_migration_import_lock_path() -> Path:
    return Path(os.environ.get("HIVEMIND_MIGRATION_IMPORT_LOCK_PATH", _base() / "migration-import.lock"))
