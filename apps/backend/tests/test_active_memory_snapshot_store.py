import json, pytest
from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.services.active_memory_snapshot_store import ActiveMemorySnapshotStore
from app.store.active_memory_store import InMemoryActiveMemoryStore

def test_snapshot_round_trip_and_tamper_detection(tmp_path):
    storage=ActiveMemorySnapshotStore(tmp_path/"snapshot.json"); storage.persist(InMemoryActiveMemoryStore(),0)
    assert storage.load().commit_generation==0
    raw=json.loads(storage.path().read_text()); raw["commit_generation"]=1; storage.path().write_text(json.dumps(raw))
    with pytest.raises(MemoryMigrationImportError) as exc: storage.load()
    assert exc.value.code==ImportDiagnosticCode.CORRUPT_ACTIVE_MEMORY_SNAPSHOT
