import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.mock.mock_data import (
    MOCK_ACTIVITY_EVENTS,
    MOCK_GRAPH_EDGES,
    MOCK_GRAPH_NODES,
    MOCK_SOURCES,
)
from app.models.hive_models import (
    ActivityEventType,
    ActivitySeverity,
    GraphNodeType,
    GraphRelationship,
    HiveActivityEvent,
    HiveExportSnapshot,
    HiveGraphEdge,
    HiveGraphNode,
    HiveImportRequest,
    HiveModel,
    HiveSource,
    HiveSystemStatus,
    ModelStatus,
    SourceStatus,
    SourceType,
    SystemStatusValue,
)

logger = logging.getLogger("hivemind.store")

_SEED_STARTED = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)

# Default on-disk persistence location: apps/backend/data/hivemind-store.json
# (store.py lives at apps/backend/app/store/store.py -> parents[2] == apps/backend)
DEFAULT_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "hivemind-store.json"

# Environment variable that overrides the persistence path (useful for tests/deploys).
STORE_PATH_ENV = "HIVEMIND_STORE_PATH"

_SEED_MODELS: list[HiveModel] = [
    HiveModel(
        id="model-local-placeholder",
        name="Local Model (placeholder)",
        provider="local",
        status=ModelStatus.UNAVAILABLE,
        metadata={"mock": True, "description": "Placeholder for future local model registry"},
        created_at=_SEED_STARTED,
    )
]


def resolve_store_path() -> Path:
    """Resolve the persistence path from the env override or the default location."""
    override = os.environ.get(STORE_PATH_ENV)
    return Path(override) if override else DEFAULT_STORE_PATH


def _check_no_duplicate_ids(items: list, label: str) -> None:
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            raise ValueError(f"Duplicate {label} id '{item.id}' in payload")
        seen.add(item.id)


class HiveStore:
    """In-memory store with durable local JSON persistence.

    The on-disk format is a ``HiveExportSnapshot`` document. On construction the
    store loads from ``persistence_path`` if present and valid; on a missing or
    corrupt file it falls back to seeded development data and (re)writes the file
    so subsequent restarts load cleanly. Writes are atomic (temp file + rename).
    """

    def __init__(self, persistence_path: Path | str | None = None) -> None:
        self._started_at: datetime = datetime.now(tz=timezone.utc)
        self._path: Path = Path(persistence_path) if persistence_path else resolve_store_path()

        self._sources: dict[str, HiveSource] = {}
        self._nodes: dict[str, HiveGraphNode] = {}
        self._edges: dict[str, HiveGraphEdge] = {}
        self._activity: list[HiveActivityEvent] = []
        self._models: dict[str, HiveModel] = {}

        if not self._load():
            self._seed()
            self._persist()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    @property
    def persistence_path(self) -> Path:
        return self._path

    def _seed(self) -> None:
        self._sources = {s.id: s for s in MOCK_SOURCES}
        self._nodes = {n.id: n for n in MOCK_GRAPH_NODES}
        self._edges = {e.id: e for e in MOCK_GRAPH_EDGES}
        self._activity = list(MOCK_ACTIVITY_EVENTS)
        self._models = {m.id: m for m in _SEED_MODELS}

    def _load(self) -> bool:
        """Load state from disk. Returns True on success, False on missing/corrupt.

        Never raises: a missing directory, missing file, malformed JSON, or a
        document that fails validation all result in a safe False so the caller
        can fall back to seed data instead of crashing the API.
        """
        try:
            if not self._path.exists():
                return False
            raw = self._path.read_text(encoding="utf-8")
            if not raw.strip():
                return False
            data = json.loads(raw)
            snapshot = HiveExportSnapshot.model_validate(data)
        except (OSError, ValueError) as exc:  # ValueError covers JSONDecodeError + pydantic
            logger.warning("Could not load store from %s (%s); falling back to seed", self._path, exc)
            return False

        self._sources = {s.id: s for s in snapshot.sources}
        self._nodes = {n.id: n for n in snapshot.nodes}
        self._edges = {e.id: e for e in snapshot.edges}
        self._activity = list(snapshot.activity)
        self._models = {m.id: m for m in snapshot.models}
        return True

    def _persist(self) -> None:
        """Atomically write the current state to disk (temp file + os.replace)."""
        snapshot = self.export_snapshot()
        payload = snapshot.model_dump(mode="json")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self._path.parent), prefix=".hivemind-store-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self._path)  # atomic on POSIX and Windows
            except BaseException:
                # Clean up the temp file if the swap did not complete.
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise
        except OSError as exc:
            logger.error("Could not persist store to %s (%s)", self._path, exc)

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def uptime_seconds(self) -> int:
        return int((datetime.now(tz=timezone.utc) - self._started_at).total_seconds())

    def get_sources(self) -> list[HiveSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> HiveSource | None:
        return self._sources.get(source_id)

    def get_nodes(self) -> list[HiveGraphNode]:
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> HiveGraphNode | None:
        return self._nodes.get(node_id)

    def get_edges(self) -> list[HiveGraphEdge]:
        return list(self._edges.values())

    def get_activity(self) -> list[HiveActivityEvent]:
        return list(self._activity)

    def get_models(self) -> list[HiveModel]:
        return list(self._models.values())

    def system_status(self) -> HiveSystemStatus:
        return HiveSystemStatus(
            service="hivemind-backend",
            status=SystemStatusValue.OK,
            uptime_seconds=self.uptime_seconds(),
            version="0.1.0",
            environment="development",
            sources_count=len(self._sources),
            nodes_count=len(self._nodes),
            edges_count=len(self._edges),
            last_updated=datetime.now(tz=timezone.utc),
        )

    def export_snapshot(self) -> HiveExportSnapshot:
        return HiveExportSnapshot(
            version="0.1.0",
            exported_at=datetime.now(tz=timezone.utc),
            sources=self.get_sources(),
            nodes=self.get_nodes(),
            edges=self.get_edges(),
            activity=self.get_activity(),
            models=self.get_models(),
        )

    # ------------------------------------------------------------------ #
    # Writes (each mutation persists atomically)
    # ------------------------------------------------------------------ #
    def upsert_source(self, source: HiveSource) -> HiveSource:
        """Create or update a source by stable id, then persist."""
        self._sources[source.id] = source
        self._persist()
        return source

    def delete_source(self, source_id: str) -> bool:
        """Delete a source by id. Returns True if a record was removed."""
        existed = self._sources.pop(source_id, None) is not None
        if existed:
            self._persist()
        return existed

    def upsert_node(self, node: HiveGraphNode) -> HiveGraphNode:
        """Create or update a graph node by stable id, then persist."""
        self._nodes[node.id] = node
        self._persist()
        return node

    def delete_node(self, node_id: str) -> bool:
        """Delete a graph node by id. Returns True if a record was removed."""
        existed = self._nodes.pop(node_id, None) is not None
        if existed:
            self._persist()
        return existed

    def import_snapshot(self, payload: HiveImportRequest) -> None:
        _check_no_duplicate_ids(payload.sources, "source")
        _check_no_duplicate_ids(payload.nodes, "node")
        _check_no_duplicate_ids(payload.edges, "edge")
        _check_no_duplicate_ids(payload.models, "model")

        node_ids = {n.id for n in payload.nodes}
        for edge in payload.edges:
            if edge.source_node_id not in node_ids:
                raise ValueError(
                    f"Edge '{edge.id}' source_node_id '{edge.source_node_id}' not in provided nodes"
                )
            if edge.target_node_id not in node_ids:
                raise ValueError(
                    f"Edge '{edge.id}' target_node_id '{edge.target_node_id}' not in provided nodes"
                )

        self._sources = {s.id: s for s in payload.sources}
        self._nodes = {n.id: n for n in payload.nodes}
        self._edges = {e.id: e for e in payload.edges}
        self._activity = list(payload.activity)
        self._models = {m.id: m for m in payload.models}
        self._activity.append(
            HiveActivityEvent(
                id=f"event-import-{int(datetime.now(tz=timezone.utc).timestamp())}",
                timestamp=datetime.now(tz=timezone.utc),
                event_type=ActivityEventType.IMPORT,
                severity=ActivitySeverity.SUCCESS,
                message=f"Snapshot imported: {len(payload.sources)} sources, {len(payload.nodes)} nodes, {len(payload.edges)} edges.",
            )
        )
        self._persist()

    # ------------------------------------------------------------------ #
    # Search / query helpers (read-only, deterministic)
    # ------------------------------------------------------------------ #
    def stats(self) -> dict[str, int]:
        """Return counts of each record collection."""
        return {
            "sources": len(self._sources),
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "models": len(self._models),
            "activity": len(self._activity),
        }

    def list_records(self, record_type: str) -> list[BaseModel]:
        """List records of a given type. Raises ValueError on unknown type."""
        getters = {
            "sources": self.get_sources,
            "source": self.get_sources,
            "nodes": self.get_nodes,
            "node": self.get_nodes,
            "edges": self.get_edges,
            "edge": self.get_edges,
            "models": self.get_models,
            "model": self.get_models,
            "activity": self.get_activity,
            "events": self.get_activity,
            "event": self.get_activity,
        }
        getter = getters.get(record_type.lower())
        if getter is None:
            raise ValueError(
                f"Unknown record type '{record_type}'. "
                "Valid types: sources, nodes, edges, models, activity."
            )
        return list(getter())

    def get_record(self, record_id: str) -> tuple[str, BaseModel] | None:
        """Find a record by id across all collections. Returns (type, record)."""
        if record_id in self._sources:
            return ("source", self._sources[record_id])
        if record_id in self._nodes:
            return ("node", self._nodes[record_id])
        if record_id in self._edges:
            return ("edge", self._edges[record_id])
        if record_id in self._models:
            return ("model", self._models[record_id])
        for event in self._activity:
            if event.id == record_id:
                return ("activity", event)
        return None

    def search(self, query: str) -> dict[str, list[BaseModel]]:
        """Case-insensitive text search across persisted records.

        Matches source/model names, node labels and tags, activity messages,
        and ids. An empty query returns empty result lists.
        """
        q = query.lower().strip()
        if not q:
            return {"sources": [], "nodes": [], "models": [], "activity": []}
        return {
            "sources": [
                s for s in self._sources.values()
                if q in s.name.lower() or q in s.id.lower()
            ],
            "nodes": [
                n for n in self._nodes.values()
                if q in n.label.lower()
                or q in n.id.lower()
                or any(q in tag.lower() for tag in n.tags)
            ],
            "models": [
                m for m in self._models.values()
                if q in m.name.lower() or q in m.id.lower()
            ],
            "activity": [
                e for e in self._activity
                if q in e.message.lower() or q in e.id.lower()
            ],
        }

    def filter_nodes(
        self,
        *,
        tag: str | None = None,
        node_type: GraphNodeType | None = None,
    ) -> list[HiveGraphNode]:
        nodes = self.get_nodes()
        if tag is not None:
            nodes = [n for n in nodes if tag in n.tags]
        if node_type is not None:
            nodes = [n for n in nodes if n.type == node_type]
        return nodes

    def filter_sources(
        self,
        *,
        status: SourceStatus | None = None,
        source_type: SourceType | None = None,
    ) -> list[HiveSource]:
        sources = self.get_sources()
        if status is not None:
            sources = [s for s in sources if s.status == status]
        if source_type is not None:
            sources = [s for s in sources if s.type == source_type]
        return sources

    # ------------------------------------------------------------------ #
    # Safe mutation helpers (validate, dedupe, persist)
    # ------------------------------------------------------------------ #
    def add_tag(self, node_id: str, tag: str) -> HiveGraphNode:
        """Add a tag to a node, deduplicating. Raises ValueError on bad input."""
        node = self._nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found")
        tag = tag.strip()
        if not tag:
            raise ValueError("Tag must not be empty")
        if tag not in node.tags:
            node.tags.append(tag)
            node.updated_at = datetime.now(tz=timezone.utc)
            self._persist()
        return node

    def link_nodes(
        self,
        source_node_id: str,
        target_node_id: str,
        relationship: GraphRelationship = GraphRelationship.LINKED_TO,
    ) -> HiveGraphEdge:
        """Create an edge between two existing nodes, deduplicating identical links."""
        if source_node_id not in self._nodes:
            raise ValueError(f"Source node '{source_node_id}' not found")
        if target_node_id not in self._nodes:
            raise ValueError(f"Target node '{target_node_id}' not found")
        for edge in self._edges.values():
            if (
                edge.source_node_id == source_node_id
                and edge.target_node_id == target_node_id
                and edge.relationship == relationship
            ):
                return edge  # link already exists; do not duplicate
        edge = HiveGraphEdge(
            id=f"edge-{uuid4().hex[:12]}",
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship=relationship,
            metadata={"origin": "console"},
            created_at=datetime.now(tz=timezone.utc),
        )
        self._edges[edge.id] = edge
        self._persist()
        return edge

    def create_note(self, text: str, *, source_id: str | None = None) -> HiveGraphNode:
        """Create a simple note node from text. Raises ValueError on empty text."""
        text = text.strip()
        if not text:
            raise ValueError("Note text must not be empty")
        now = datetime.now(tz=timezone.utc)
        node = HiveGraphNode(
            id=f"note-{uuid4().hex[:12]}",
            label=text,
            type=GraphNodeType.NOTE,
            source_id=source_id,
            tags=[],
            metadata={"origin": "console"},
            created_at=now,
            updated_at=now,
        )
        self._nodes[node.id] = node
        self._persist()
        return node


store = HiveStore()
