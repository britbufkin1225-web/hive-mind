import pytest
from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.services.migration_import_lock import MigrationImportLock

def test_o_excl_lock_is_bounded_and_exclusive(tmp_path):
    path=tmp_path/"import.lock"; first=MigrationImportLock(path,timeout=.01).acquire("one")
    try:
        with pytest.raises(MemoryMigrationImportError) as exc: MigrationImportLock(path,timeout=.01,poll_interval=.001).acquire("two")
        assert exc.value.code==ImportDiagnosticCode.LOCK_UNAVAILABLE
    finally: first.release()
