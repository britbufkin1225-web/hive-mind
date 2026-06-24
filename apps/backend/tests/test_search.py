import pytest

from app.models.hive_models import GraphNodeType, GraphRelationship
from app.store.store import HiveStore


def fresh_store(tmp_path) -> HiveStore:
    """A seeded store backed by an isolated temp file."""
    return HiveStore(persistence_path=tmp_path / "store.json")


def test_search_by_query_matches_seed_data(tmp_path) -> None:
    store = fresh_store(tmp_path)
    results = store.search("markdown")
    assert any("markdown" in s.name.lower() for s in results["sources"])
    assert any("markdown" in n.id.lower() or "markdown" in n.label.lower() for n in results["nodes"])


def test_search_empty_query_returns_empty(tmp_path) -> None:
    store = fresh_store(tmp_path)
    results = store.search("   ")
    assert results == {"sources": [], "nodes": [], "models": [], "activity": []}


def test_search_matches_tags(tmp_path) -> None:
    store = fresh_store(tmp_path)
    node = store.create_note("Tag search target")
    store.add_tag(node.id, "uniquetag")
    results = store.search("uniquetag")
    assert any(n.id == node.id for n in results["nodes"])


def test_list_by_type(tmp_path) -> None:
    store = fresh_store(tmp_path)
    assert len(store.list_records("sources")) == 3
    assert len(store.list_records("nodes")) > 0
    # singular + alias forms work
    assert len(store.list_records("source")) == 3
    assert len(store.list_records("events")) > 0


def test_list_unknown_type_raises(tmp_path) -> None:
    store = fresh_store(tmp_path)
    with pytest.raises(ValueError, match="Unknown record type"):
        store.list_records("widgets")


def test_get_record_by_id(tmp_path) -> None:
    store = fresh_store(tmp_path)
    found = store.get_record("src-dev-markdown")
    assert found is not None
    record_type, record = found
    assert record_type == "source"
    assert record.id == "src-dev-markdown"


def test_get_record_unknown_returns_none(tmp_path) -> None:
    store = fresh_store(tmp_path)
    assert store.get_record("nope-nope") is None


def test_stats_counts(tmp_path) -> None:
    store = fresh_store(tmp_path)
    stats = store.stats()
    assert set(stats) == {"sources", "nodes", "edges", "models", "activity"}
    assert stats["sources"] == 3
    assert stats["nodes"] > 0


def test_filter_nodes_by_type(tmp_path) -> None:
    store = fresh_store(tmp_path)
    sources = store.filter_nodes(node_type=GraphNodeType.SOURCE)
    assert all(n.type == GraphNodeType.SOURCE for n in sources)
    assert len(sources) > 0


def test_add_tag_dedupes(tmp_path) -> None:
    store = fresh_store(tmp_path)
    node = store.create_note("note for tagging")
    store.add_tag(node.id, "alpha")
    store.add_tag(node.id, "alpha")
    updated = store.get_node(node.id)
    assert updated.tags.count("alpha") == 1


def test_add_tag_invalid_node_raises(tmp_path) -> None:
    store = fresh_store(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        store.add_tag("missing-node", "x")


def test_add_tag_empty_raises(tmp_path) -> None:
    store = fresh_store(tmp_path)
    node = store.create_note("note")
    with pytest.raises(ValueError, match="must not be empty"):
        store.add_tag(node.id, "   ")


def test_link_nodes_creates_and_dedupes(tmp_path) -> None:
    store = fresh_store(tmp_path)
    a = store.create_note("node a")
    b = store.create_note("node b")
    edge1 = store.link_nodes(a.id, b.id)
    edge2 = store.link_nodes(a.id, b.id)
    assert edge1.id == edge2.id  # duplicate link not created
    assert edge1.relationship == GraphRelationship.LINKED_TO


def test_link_invalid_node_raises(tmp_path) -> None:
    store = fresh_store(tmp_path)
    a = store.create_note("node a")
    with pytest.raises(ValueError, match="Target node .* not found"):
        store.link_nodes(a.id, "missing-target")


def test_create_note_persists_and_is_a_note(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    store = HiveStore(persistence_path=store_path)
    note = store.create_note("Phase 3C note")
    assert note.type == GraphNodeType.NOTE
    # durable across restart
    reloaded = HiveStore(persistence_path=store_path)
    assert reloaded.get_node(note.id) is not None


def test_create_note_empty_raises(tmp_path) -> None:
    store = fresh_store(tmp_path)
    with pytest.raises(ValueError, match="must not be empty"):
        store.create_note("   ")
