"""Phase 6B — Obsidian import MVP tests.

Covers the markdown parser, the vault scanner, the import service, and the
``POST /api/obsidian/import`` endpoint against temporary fixture vaults. No test
touches a real user vault, and the import never mutates fixture files.
"""

import pytest
from fastapi.testclient import TestClient

from app.adapters.markdown_parser import parse_markdown
from app.adapters.vault_scanner import resolve_vault_root, scan_markdown_files
from app.main import app
from app.models.hive_models import GraphNodeType
from app.services.obsidian_import import import_vault
from app.store.registry import SourceRegistry
from app.store.store import HiveStore

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def build_vault(root) -> None:
    """Create a small, deterministic fixture vault under ``root``."""
    (root / "Welcome.md").write_text(
        "---\n"
        "title: Welcome Home\n"
        "tags: [intro, start]\n"
        "---\n\n"
        "# Ignored Heading\n\n"
        "Jump to [[Project Alpha]] and [[Notes/Daily|today]].\n"
        "See the [docs](https://example.com/docs) too. #welcome\n",
        encoding="utf-8",
    )
    notes = root / "Notes"
    notes.mkdir()
    (notes / "Daily.md").write_text(
        "# Daily Log\n\nWorked on #project/alpha and linked [[Welcome]].\n",
        encoding="utf-8",
    )
    (root / "Project Alpha.md").write_text(
        "Some content with no frontmatter and no heading.\n",
        encoding="utf-8",
    )

    # Things the scanner must ignore.
    obsidian = root / ".obsidian"
    obsidian.mkdir()
    (obsidian / "config.md").write_text("# should be ignored\n", encoding="utf-8")
    git = root / ".git"
    git.mkdir()
    (git / "HEAD.md").write_text("# ignored\n", encoding="utf-8")
    (root / "image.png").write_text("not markdown", encoding="utf-8")
    (root / ".hidden.md").write_text("# hidden file\n", encoding="utf-8")


@pytest.fixture()
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    build_vault(root)
    return root


def fresh_store(tmp_path) -> HiveStore:
    return HiveStore(persistence_path=tmp_path / "store.json")


def fresh_registry(tmp_path) -> SourceRegistry:
    return SourceRegistry(persistence_path=tmp_path / "registry.json")


# --------------------------------------------------------------------------- #
# Markdown parser
# --------------------------------------------------------------------------- #
def test_title_from_frontmatter_wins() -> None:
    parsed = parse_markdown(
        "---\ntitle: From FM\n---\n# Heading\n", fallback_title="stem"
    )
    assert parsed.title == "From FM"


def test_title_from_first_heading_when_no_frontmatter_title() -> None:
    parsed = parse_markdown("# The Heading\n\nbody", fallback_title="stem")
    assert parsed.title == "The Heading"


def test_title_falls_back_to_stem() -> None:
    parsed = parse_markdown("just body, no heading", fallback_title="my-note")
    assert parsed.title == "my-note"


def test_extracts_frontmatter_and_inline_tags() -> None:
    parsed = parse_markdown(
        "---\ntags: [a, b]\n---\nbody #c #area/sub\n", fallback_title="x"
    )
    assert parsed.tags == ["a", "b", "c", "area/sub"]


def test_block_list_frontmatter_tags() -> None:
    parsed = parse_markdown(
        "---\ntags:\n  - one\n  - two\n---\nbody\n", fallback_title="x"
    )
    assert parsed.tags == ["one", "two"]


def test_extracts_wiki_and_markdown_links() -> None:
    parsed = parse_markdown(
        "[[Note A]] and [[Note B|alias]] and [[Note C#sec]] "
        "plus [text](http://x) and ![img](y.png)\n",
        fallback_title="x",
    )
    assert parsed.wiki_links == ["Note A", "Note B", "Note C"]
    assert parsed.markdown_links == ["http://x", "y.png"]


def test_heading_is_not_an_inline_tag() -> None:
    parsed = parse_markdown("# Heading\n\nno tags here\n", fallback_title="x")
    assert parsed.tags == []


# --------------------------------------------------------------------------- #
# Vault scanner
# --------------------------------------------------------------------------- #
def test_scanner_finds_only_markdown_and_ignores_system(vault) -> None:
    rels = sorted(p.relative_to(vault).as_posix() for p in scan_markdown_files(vault))
    assert rels == ["Notes/Daily.md", "Project Alpha.md", "Welcome.md"]


def test_scanner_ignores_obsidian_git_hidden_and_nonmarkdown(vault) -> None:
    rels = {p.name for p in scan_markdown_files(vault)}
    assert "config.md" not in rels  # inside .obsidian
    assert "HEAD.md" not in rels  # inside .git
    assert ".hidden.md" not in rels  # hidden file
    assert "image.png" not in rels  # not markdown


def test_resolve_vault_root_rejects_missing_path(tmp_path) -> None:
    with pytest.raises(ValueError):
        resolve_vault_root(str(tmp_path / "does-not-exist"))


def test_resolve_vault_root_rejects_file_path(vault) -> None:
    with pytest.raises(ValueError):
        resolve_vault_root(str(vault / "Welcome.md"))


# --------------------------------------------------------------------------- #
# Import service
# --------------------------------------------------------------------------- #
def test_import_vault_counts_and_nodes(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), "My Vault", store=store, registry=registry)

    assert summary.imported_count == 3
    assert summary.error_count == 0
    assert summary.skipped_count == 0
    assert len(summary.imported_node_ids) == 3
    assert summary.source_id is not None
    assert summary.vault_path == str(vault.resolve())

    # Nodes landed in the store as NOTE nodes tied to the source.
    nodes = {n.id: n for n in store.get_nodes() if n.id in summary.imported_node_ids}
    assert len(nodes) == 3
    for node in nodes.values():
        assert node.type == GraphNodeType.NOTE
        assert node.source_id == summary.source_id
        assert node.metadata["origin"] == "obsidian"


def test_import_vault_extracts_title_tags_and_links(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), store=store, registry=registry)

    by_label = {n.label: n for n in store.get_nodes()}
    welcome = by_label["Welcome Home"]  # title from frontmatter
    assert "intro" in welcome.tags and "welcome" in welcome.tags
    assert welcome.metadata["wiki_links"] == ["Project Alpha", "Notes/Daily"]
    assert "https://example.com/docs" in welcome.metadata["markdown_links"]
    assert welcome.file_meta is not None
    assert welcome.file_meta.vault_path == "Welcome.md"
    assert welcome.file_meta.extension == ".md"


def test_import_registers_source_in_registry(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), "Named Vault", store=store, registry=registry)

    record = registry.get_source(summary.source_id)
    assert record is not None
    assert record.name == "Named Vault"
    assert record.type.value == "obsidian"
    assert record.status.value == "active"
    assert record.last_imported_at is not None
    assert record.root_path == str(vault.resolve())


def test_import_default_source_name_uses_vault_folder(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), store=store, registry=registry)
    assert registry.get_source(summary.source_id).name == "vault"


def test_import_is_deterministic(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    first = import_vault(str(vault), store=store, registry=registry)
    second = import_vault(str(vault), store=store, registry=registry)
    # Same node ids on re-import (derived from the relative path).
    assert first.imported_node_ids == second.imported_node_ids


def test_import_rejects_missing_path(tmp_path) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    with pytest.raises(ValueError):
        import_vault(str(tmp_path / "nope"), store=store, registry=registry)


def test_import_rejects_file_path(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    with pytest.raises(ValueError):
        import_vault(str(vault / "Welcome.md"), store=store, registry=registry)


def test_import_handles_unreadable_file_gracefully(tmp_path, vault) -> None:
    # A file with invalid UTF-8 must be counted as an error, not crash the run.
    (vault / "Broken.md").write_bytes(b"\xff\xfe\x00bad bytes")
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), store=store, registry=registry)
    assert summary.error_count == 1
    assert summary.imported_count == 3
    assert any("Broken.md" in w for w in summary.warnings)


def test_import_does_not_modify_vault_files(tmp_path, vault) -> None:
    before = {p.name: p.read_bytes() for p in vault.rglob("*.md")}
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    import_vault(str(vault), store=store, registry=registry)
    after = {p.name: p.read_bytes() for p in vault.rglob("*.md")}
    assert before == after


# --------------------------------------------------------------------------- #
# API endpoint
# --------------------------------------------------------------------------- #
def test_api_import_success(vault) -> None:
    response = client.post(
        "/api/obsidian/import",
        json={"vault_path": str(vault), "source_name": "API Vault"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 3
    assert data["error_count"] == 0
    assert data["source_id"].startswith("reg-")
    assert len(data["imported_node_ids"]) == 3


def test_api_import_missing_path_is_400(tmp_path) -> None:
    response = client.post(
        "/api/obsidian/import", json={"vault_path": str(tmp_path / "ghost")}
    )
    assert response.status_code == 400


def test_api_import_file_path_is_400(vault) -> None:
    response = client.post(
        "/api/obsidian/import", json={"vault_path": str(vault / "Welcome.md")}
    )
    assert response.status_code == 400


def test_api_import_missing_vault_path_field_is_422() -> None:
    assert client.post("/api/obsidian/import", json={}).status_code == 422


# --------------------------------------------------------------------------- #
# Phase 6C — import hardening + summary
# --------------------------------------------------------------------------- #
def test_summary_includes_name_and_notes(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    summary = import_vault(str(vault), "My Vault", store=store, registry=registry)

    assert summary.source_name == "My Vault"
    assert summary.imported_count == 3
    assert summary.updated_count == 0
    assert summary.duplicate_count == 0
    assert summary.notes  # human-readable line(s) present
    assert any("Imported 3" in note for note in summary.notes)


def test_empty_string_vault_path_is_rejected(tmp_path) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)
    with pytest.raises(ValueError):
        import_vault("", store=store, registry=registry)
    with pytest.raises(ValueError):
        import_vault("   ", store=store, registry=registry)


def test_api_empty_string_vault_path_is_400() -> None:
    response = client.post("/api/obsidian/import", json={"vault_path": "   "})
    assert response.status_code == 400


def test_reimport_updates_without_duplicating_nodes_or_sources(tmp_path, vault) -> None:
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    first = import_vault(str(vault), "Vault", store=store, registry=registry)
    assert first.imported_count == 3 and first.updated_count == 0

    second = import_vault(str(vault), "Vault", store=store, registry=registry)
    # Re-import refreshes existing nodes instead of creating new ones.
    assert second.imported_count == 0
    assert second.updated_count == 3
    assert second.imported_node_ids == first.imported_node_ids
    assert any("Reused existing source" in note for note in second.notes)

    # No duplicate node records, and exactly one Obsidian source registered.
    note_nodes = [n for n in store.get_nodes() if n.id.startswith("obsidian-")]
    assert len(note_nodes) == 3
    obsidian_sources = [s for s in registry.list_sources() if s.type.value == "obsidian"]
    assert len(obsidian_sources) == 1
    assert second.source_id == first.source_id


def test_notes_without_tags_or_links_still_import(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "Plain.md").write_text("Just plain prose, nothing else.\n", encoding="utf-8")
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    summary = import_vault(str(root), store=store, registry=registry)
    assert summary.imported_count == 1
    plain = next(n for n in store.get_nodes() if n.label == "Plain")
    assert plain.tags == []
    assert plain.metadata["wiki_links"] == []
    assert plain.metadata["markdown_links"] == []


def test_repeated_tags_and_links_are_normalized(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "Dupes.md").write_text(
        "---\ntags: [alpha, alpha, beta]\n---\n"
        "#alpha #alpha body [[Target]] and [[Target]] again "
        "plus [d](http://x) and [d2](http://x)\n",
        encoding="utf-8",
    )
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    import_vault(str(root), store=store, registry=registry)
    node = next(n for n in store.get_nodes() if n.label == "Dupes")
    assert node.tags == ["alpha", "beta"]
    assert node.metadata["wiki_links"] == ["Target"]
    assert node.metadata["markdown_links"] == ["http://x"]


def test_empty_note_is_skipped(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "Real.md").write_text("# Real\n\nbody\n", encoding="utf-8")
    (root / "Empty.md").write_text("   \n\n", encoding="utf-8")
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    summary = import_vault(str(root), store=store, registry=registry)
    assert summary.imported_count == 1
    assert summary.skipped_count == 1
    assert any("Empty.md" in w for w in summary.warnings)
    assert not any(n.label == "Empty" for n in store.get_nodes())


def test_bad_frontmatter_like_input_does_not_crash(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    # Unterminated frontmatter, odd brackets, control-ish chars — must not raise.
    (root / "Weird.md").write_text(
        "---\ntags: [unclosed\nweird: : :\n"
        "body with [[ ]] and [](  ) and ![x](y) — émojis 🐝 and ünïcode\n",
        encoding="utf-8",
    )
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    summary = import_vault(str(root), store=store, registry=registry)
    assert summary.error_count == 0
    assert summary.imported_count == 1


def test_unusual_filename_imports_with_stable_id(tmp_path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "Wëird & Náme (v2).md").write_text("content\n", encoding="utf-8")
    store = fresh_store(tmp_path)
    registry = fresh_registry(tmp_path)

    first = import_vault(str(root), store=store, registry=registry)
    second = import_vault(str(root), store=store, registry=registry)
    assert first.imported_count == 1
    assert second.updated_count == 1
    assert first.imported_node_ids == second.imported_node_ids


def test_api_summary_exposes_new_fields(vault) -> None:
    response = client.post(
        "/api/obsidian/import",
        json={"vault_path": str(vault), "source_name": "Fields Vault"},
    )
    assert response.status_code == 200
    data = response.json()
    for key in (
        "source_name",
        "imported_count",
        "updated_count",
        "skipped_count",
        "duplicate_count",
        "error_count",
        "notes",
    ):
        assert key in data
    assert data["source_name"] == "Fields Vault"
