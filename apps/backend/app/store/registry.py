"""Phase 5A — Source Registry store.

A small, durable registry of future import connectors (Obsidian, local files,
GitHub, PDF, web, API). It is intentionally independent of the graph `HiveStore`
so it cannot disturb existing store/search/console/export behavior.

This module registers source *records* only. It does NOT scan vaults, parse
markdown, watch the filesystem, or import any data — that is out of scope for
this phase.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models.hive_models import (
    RegistrySourceStatus,
    SourceRecord,
    SourceRecordCreate,
    SourceRecordUpdate,
)

logger = logging.getLogger("hivemind.registry")

# Default on-disk location: apps/backend/data/source-registry.json
# (registry.py lives at apps/backend/app/store/registry.py -> parents[2] == apps/backend)
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "source-registry.json"

# Environment override (tests point this at a throwaway temp file).
REGISTRY_PATH_ENV = "HIVEMIND_REGISTRY_PATH"


def resolve_registry_path() -> Path:
    override = os.environ.get(REGISTRY_PATH_ENV)
    return Path(override) if override else DEFAULT_REGISTRY_PATH


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class SourceRegistry:
    """In-memory registry of source records with durable JSON persistence.

    Starts empty when no file exists. A missing/empty/corrupt file never
    crashes — it falls back to an empty registry. Writes are atomic
    (temp file + os.replace).
    """

    def __init__(self, persistence_path: Path | str | None = None) -> None:
        self._path: Path = (
            Path(persistence_path) if persistence_path else resolve_registry_path()
        )
        self._sources: dict[str, SourceRecord] = {}
        self._load()

    @property
    def persistence_path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> bool:
        try:
            if not self._path.exists():
                return False
            raw = self._path.read_text(encoding="utf-8")
            if not raw.strip():
                return False
            data = json.loads(raw)
            records = [SourceRecord.model_validate(item) for item in data]
        except (OSError, ValueError) as exc:
            logger.warning(
                "Could not load source registry from %s (%s); starting empty",
                self._path,
                exc,
            )
            return False
        self._sources = {record.id: record for record in records}
        return True

    def _persist(self) -> None:
        payload = [record.model_dump(mode="json") for record in self._sources.values()]
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self._path.parent), prefix=".source-registry-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self._path)
            except BaseException:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise
        except OSError as exc:
            logger.error("Could not persist source registry to %s (%s)", self._path, exc)

    # ------------------------------------------------------------------ #
    # Operations
    # ------------------------------------------------------------------ #
    def list_sources(self) -> list[SourceRecord]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> SourceRecord | None:
        return self._sources.get(source_id)

    def create_source(self, payload: SourceRecordCreate) -> SourceRecord:
        now = _now()
        record = SourceRecord(
            id=f"reg-{uuid4().hex[:12]}",
            name=payload.name,
            type=payload.type,
            root_path=payload.root_path,
            status=payload.status,
            last_imported_at=None,
            created_at=now,
            updated_at=now,
            metadata=payload.metadata,
        )
        self._sources[record.id] = record
        self._persist()
        return record

    def update_source(
        self, source_id: str, payload: SourceRecordUpdate
    ) -> SourceRecord | None:
        existing = self._sources.get(source_id)
        if existing is None:
            return None
        changes = payload.model_dump(exclude_unset=True)
        updated = existing.model_copy(update={**changes, "updated_at": _now()})
        self._sources[source_id] = updated
        self._persist()
        return updated


registry = SourceRegistry()
