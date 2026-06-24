from datetime import datetime, timezone

import pytest

from app.models.hive_models import (
    HiveImportRequest,
    HiveSource,
    SourceStatus,
    SourceType,
)
from app.store.store import HiveStore

NOW = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)


def _make_source(source_id: str, name: str = "Test Source") -> HiveSource:
    return HiveSource(
        id=source_id,
        name=name,
        type=SourceType.MARKDOWN,
        path=f"mem://{source_id}",
        status=SourceStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_persistence_file_is_created(tmp_path) -> None:
    store_path = tmp_path / "hivemind-store.json"
    assert not store_path.exists()

    HiveStore(persistence_path=store_path)

    assert store_path.exists()
    assert store_path.stat().st_size > 0


def test_seed_data_present_on_fresh_store(tmp_path) -> None:
    store = HiveStore(persistence_path=tmp_path / "store.json")
    # Falls back to seeded development data when no file exists yet.
    assert len(store.get_sources()) > 0
    assert len(store.get_nodes()) > 0
    assert len(store.get_edges()) > 0


def test_data_persists_across_store_restart(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store_a = HiveStore(persistence_path=store_path)
    store_a.upsert_source(_make_source("src-persisted", "Persisted Source"))

    # A brand-new store instance pointed at the same file loads prior data.
    store_b = HiveStore(persistence_path=store_path)
    loaded = store_b.get_source("src-persisted")
    assert loaded is not None
    assert loaded.name == "Persisted Source"


def test_missing_file_does_not_crash_and_seeds(tmp_path) -> None:
    # Path inside a directory that does not exist yet.
    store_path = tmp_path / "nested" / "deeper" / "store.json"
    store = HiveStore(persistence_path=store_path)
    assert store_path.exists()
    assert len(store.get_sources()) > 0


def test_corrupt_file_is_handled_safely(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store_path.write_text("{ this is not valid json ::::", encoding="utf-8")

    # Must not raise; should fall back to seed and overwrite with valid data.
    store = HiveStore(persistence_path=store_path)
    assert len(store.get_sources()) > 0

    # File is now valid JSON, so a fresh instance loads cleanly.
    reloaded = HiveStore(persistence_path=store_path)
    assert len(reloaded.get_sources()) > 0


def test_empty_file_is_handled_safely(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store_path.write_text("", encoding="utf-8")
    store = HiveStore(persistence_path=store_path)
    assert len(store.get_sources()) > 0


def test_upsert_updates_in_place_no_duplicates(tmp_path) -> None:
    store = HiveStore(persistence_path=tmp_path / "store.json")
    store.import_snapshot(HiveImportRequest())  # reset to empty collections

    store.upsert_source(_make_source("src-1", "Original"))
    store.upsert_source(_make_source("src-1", "Updated"))

    sources = store.get_sources()
    assert len(sources) == 1
    assert sources[0].name == "Updated"


def test_delete_source_removes_and_persists(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store = HiveStore(persistence_path=store_path)
    store.upsert_source(_make_source("src-del"))
    assert store.get_source("src-del") is not None

    assert store.delete_source("src-del") is True
    assert store.get_source("src-del") is None
    # Deletion is durable.
    assert HiveStore(persistence_path=store_path).get_source("src-del") is None
    # Deleting a non-existent id is a safe no-op.
    assert store.delete_source("does-not-exist") is False


def test_import_returns_empty_collections_when_emptied(tmp_path) -> None:
    store = HiveStore(persistence_path=tmp_path / "store.json")
    store.import_snapshot(HiveImportRequest())
    assert store.get_sources() == []
    assert store.get_nodes() == []
    assert store.get_edges() == []


def test_import_rejects_duplicate_source_ids(tmp_path) -> None:
    store = HiveStore(persistence_path=tmp_path / "store.json")
    payload = HiveImportRequest(sources=[_make_source("dup"), _make_source("dup")])
    with pytest.raises(ValueError, match="Duplicate source id"):
        store.import_snapshot(payload)


def test_atomic_write_leaves_no_temp_files(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store = HiveStore(persistence_path=store_path)
    store.upsert_source(_make_source("src-x"))
    leftovers = list(tmp_path.glob(".hivemind-store-*"))
    assert leftovers == []
