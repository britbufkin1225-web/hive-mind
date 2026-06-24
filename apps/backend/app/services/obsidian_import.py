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
    ImportedSourceRef,
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


def _resolve_source(registry, root: Path, source_name: str | None):
    """Reuse an existing Obsidian source for ``root`` or create a fresh one.

    Re-importing the same vault must not leave a trail of duplicate source
    records, so we key on (type, resolved root_path). The returned tuple is
    ``(record, reused)`` where ``reused`` is True when an existing record was
    found and refreshed rather than created.
    """
    name = (source_name or "").strip() or root.name or "Obsidian Vault"
    root_str = str(root)
    existing = next(
        (
            s
            for s in registry.list_sources()
            if s.type == RegistrySourceType.OBSIDIAN and s.root_path == root_str
        ),
        None,
    )
    if existing is not None:
        # Mark the run as pending; only refresh the name when one was explicitly
        # provided (passing name=None would otherwise blank the stored name).
        update = SourceRecordUpdate(status=RegistrySourceStatus.PENDING)
        if (source_name or "").strip():
            update.name = name
        updated = registry.update_source(existing.id, update)
        return updated or existing, True

    record = registry.create_source(
        SourceRecordCreate(
            name=name,
            type=RegistrySourceType.OBSIDIAN,
            root_path=root_str,
            status=RegistrySourceStatus.PENDING,
            metadata={"origin": "obsidian"},
        )
    )
    return record, False


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

    Hardening guarantees:
      * Re-importing the same vault reuses its source record and upserts the
        same stable node ids — no duplicate sources or junk nodes accumulate.
      * Empty-content notes are skipped (counted, never imported).
      * A file resolving to an already-seen node id within one run is counted as
        a duplicate and skipped rather than silently overwriting.
      * One bad note never aborts the run.
    """
    root = resolve_vault_root(vault_path)  # raises ValueError on bad paths

    record, reused = _resolve_source(registry, root, source_name)

    summary = ObsidianImportSummary(
        source_id=record.id,
        source_name=record.name,
        vault_path=str(root),
    )
    if reused:
        summary.notes.append(f"Reused existing source '{record.name}' for this vault.")

    seen_node_ids: set[str] = set()

    for full_path in scan_markdown_files(root):
        rel = relative_vault_path(full_path, root)
        node_id = _node_id_for(rel)

        if node_id in seen_node_ids:
            # Two files mapping to the same node id within one scan is not
            # expected (paths are unique), but guard against silent overwrites.
            summary.duplicate_count += 1
            summary.warnings.append(f"Skipped duplicate note id for '{rel}'.")
            continue

        try:
            text = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            summary.error_count += 1
            summary.warnings.append(f"Could not read '{rel}': {exc}")
            continue

        if not text.strip():
            summary.skipped_count += 1
            summary.warnings.append(f"Skipped empty note '{rel}'.")
            continue

        try:
            parsed = parse_markdown(text, fallback_title=full_path.stem)
            node = _to_node(
                parsed,
                full_path=full_path,
                rel=rel,
                node_id=node_id,
                source_id=record.id,
            )
            is_update = store.get_node(node.id) is not None
            store.upsert_node(node)
        except Exception as exc:  # defensive: one bad note must not abort the run
            summary.error_count += 1
            summary.warnings.append(f"Could not import '{rel}': {exc}")
            continue

        seen_node_ids.add(node.id)
        summary.imported_node_ids.append(node.id)
        summary.link_count += len(parsed.wiki_links) + len(parsed.markdown_links)
        if is_update:
            summary.updated_count += 1
        else:
            summary.imported_count += 1

    summary_line = (
        f"Imported {summary.imported_count}, updated {summary.updated_count}, "
        f"skipped {summary.skipped_count}, errors {summary.error_count}."
    )
    summary.notes.append(summary_line)

    # Final registry status reflects the run outcome: a run that scanned files
    # but wrote nothing while hitting errors is marked ERROR rather than a
    # misleading ACTIVE; anything that wrote at least one node (or scanned
    # cleanly) is ACTIVE.
    wrote_nodes = (summary.imported_count + summary.updated_count) > 0
    final_status = (
        RegistrySourceStatus.ERROR
        if summary.error_count > 0 and not wrote_nodes
        else RegistrySourceStatus.ACTIVE
    )
    imported_at = _now()

    updated_record = registry.update_source(
        record.id,
        SourceRecordUpdate(
            status=final_status,
            last_imported_at=imported_at,
            metadata={
                "origin": "obsidian",
                "vault_path": str(root),
                "import_status": final_status.value,
                "imported_count": summary.imported_count,
                "updated_count": summary.updated_count,
                "skipped_count": summary.skipped_count,
                "duplicate_count": summary.duplicate_count,
                "error_count": summary.error_count,
                "node_count": len(summary.imported_node_ids),
                "link_count": summary.link_count,
                "last_import_summary": summary_line,
            },
        ),
    )
    final_record = updated_record or record
    summary.source = ImportedSourceRef(
        id=final_record.id,
        name=final_record.name,
        type=final_record.type,
        status=final_record.status,
        root_path=final_record.root_path,
        last_imported_at=final_record.last_imported_at,
    )
    return summary


def _to_node(
    parsed, *, full_path: Path, rel: str, node_id: str, source_id: str
) -> HiveGraphNode:
    now = _now()
    try:
        last_modified = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        last_modified = None
    label = (parsed.title or "").strip() or "Untitled"
    return HiveGraphNode(
        id=node_id,
        label=label,
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
