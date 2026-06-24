"""Phase 6B — one-shot Obsidian vault import service.

Imports markdown notes from an explicitly provided vault path into the graph
``HiveStore``, registering the run with the Phase 5A source registry. This is a
read-only operation over the vault: it never creates, modifies, or deletes any
file inside the user's vault.

Scope is intentionally small (MVP): scan ``.md`` files, parse a minimal
normalized note shape, convert each note into a ``HiveGraphNode``, and return a
deterministic summary. There is no watcher, no background sync, and no edge
generation in this phase — extracted wiki/markdown links are captured on the
node for a future linking phase.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.markdown_parser import parse_markdown
from app.adapters.vault_scanner import (
    relative_vault_path,
    resolve_vault_root,
    scan_markdown_files,
)
from app.models.hive_models import (
    GraphNodeType,
    HiveGraphNode,
    ObsidianImportSummary,
    RegistrySourceStatus,
    RegistrySourceType,
    SourceRecordCreate,
    SourceRecordUpdate,
    VaultFileMeta,
)
from app.store.registry import registry as default_registry
from app.store.store import store as default_store

# Node ids are derived deterministically from the relative vault path so that
# re-importing the same vault upserts the same nodes (stable across OSes/runs).
_NODE_ID_PREFIX = "obsidian"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _node_id_for(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]
    return f"{_NODE_ID_PREFIX}-{digest}"


def import_vault(
    vault_path: str,
    source_name: str | None = None,
    *,
    store=default_store,
    registry=default_registry,
) -> ObsidianImportSummary:
    """Import a vault at ``vault_path`` into ``store`` and return a summary.

    Raises ``ValueError`` if ``vault_path`` is empty, missing, or not a
    directory (the caller maps this to an HTTP 400). Per-file read/parse
    failures are captured as warnings and counted, never raised.
    """
    root = resolve_vault_root(vault_path)  # raises ValueError on bad paths

    name = (source_name or "").strip() or root.name or "Obsidian Vault"
    record = registry.create_source(
        SourceRecordCreate(
            name=name,
            type=RegistrySourceType.OBSIDIAN,
            root_path=str(root),
            status=RegistrySourceStatus.PENDING,
            metadata={"origin": "obsidian"},
        )
    )

    summary = ObsidianImportSummary(source_id=record.id, vault_path=str(root))

    for full_path in scan_markdown_files(root):
        rel = relative_vault_path(full_path, root)
        try:
            text = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            summary.error_count += 1
            summary.warnings.append(f"Could not read '{rel}': {exc}")
            continue

        try:
            parsed = parse_markdown(text, fallback_title=full_path.stem)
            node = _to_node(parsed, full_path=full_path, rel=rel, source_id=record.id)
            store.upsert_node(node)
        except Exception as exc:  # defensive: one bad note must not abort the run
            summary.error_count += 1
            summary.warnings.append(f"Could not import '{rel}': {exc}")
            continue

        summary.imported_count += 1
        summary.imported_node_ids.append(node.id)

    registry.update_source(
        record.id,
        SourceRecordUpdate(
            status=RegistrySourceStatus.ACTIVE,
            last_imported_at=_now(),
            metadata={
                "origin": "obsidian",
                "imported_count": summary.imported_count,
                "error_count": summary.error_count,
            },
        ),
    )
    return summary


def _to_node(parsed, *, full_path: Path, rel: str, source_id: str) -> HiveGraphNode:
    now = _now()
    try:
        last_modified = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        last_modified = None
    return HiveGraphNode(
        id=_node_id_for(rel),
        label=parsed.title,
        type=GraphNodeType.NOTE,
        source_id=source_id,
        tags=parsed.tags,
        metadata={
            "origin": "obsidian",
            "wiki_links": parsed.wiki_links,
            "markdown_links": parsed.markdown_links,
        },
        created_at=now,
        updated_at=now,
        file_meta=VaultFileMeta(
            file_path=str(full_path),
            vault_path=rel,
            file_name=full_path.name,
            extension=full_path.suffix,
            frontmatter=parsed.frontmatter,
            tags=parsed.tags,
            outlinks=parsed.wiki_links,
            last_modified=last_modified,
            origin="obsidian",
        ),
    )
