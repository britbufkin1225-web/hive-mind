import json
import pytest
from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.services.memory_migration_import_store import MigrationImportStore

def test_ledger_round_trip_cas_and_tamper_detection(tmp_path):
    store=MigrationImportStore(tmp_path/"ledger.json"); ledger=store.empty(); store.persist(ledger)
    updated=store.replace(ledger,quarantine_reason="test")
    assert store.load()==updated and updated.ledger_revision==1
    raw=json.loads(store.path().read_text()); raw["commit_generation"]=99; store.path().write_text(json.dumps(raw))
    with pytest.raises(MemoryMigrationImportError) as exc: store.load()
    assert exc.value.code==ImportDiagnosticCode.CORRUPT_LEDGER
