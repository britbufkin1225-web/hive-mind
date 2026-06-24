from datetime import datetime, timezone

from app.mock.mock_data import (
    MOCK_ACTIVITY_EVENTS,
    MOCK_GRAPH_EDGES,
    MOCK_GRAPH_NODES,
    MOCK_SOURCES,
)
from app.models.hive_models import (
    ActivityEventType,
    ActivitySeverity,
    HiveActivityEvent,
    HiveExportSnapshot,
    HiveGraphEdge,
    HiveGraphNode,
    HiveImportRequest,
    HiveModel,
    HiveSource,
    HiveSystemStatus,
    ModelStatus,
    SystemStatusValue,
)

_SEED_STARTED = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)

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


class HiveStore:
    def __init__(self) -> None:
        self._started_at: datetime = datetime.now(tz=timezone.utc)
        self._sources: dict[str, HiveSource] = {s.id: s for s in MOCK_SOURCES}
        self._nodes: dict[str, HiveGraphNode] = {n.id: n for n in MOCK_GRAPH_NODES}
        self._edges: dict[str, HiveGraphEdge] = {e.id: e for e in MOCK_GRAPH_EDGES}
        self._activity: list[HiveActivityEvent] = list(MOCK_ACTIVITY_EVENTS)
        self._models: dict[str, HiveModel] = {m.id: m for m in _SEED_MODELS}

    def uptime_seconds(self) -> int:
        return int((datetime.now(tz=timezone.utc) - self._started_at).total_seconds())

    def get_sources(self) -> list[HiveSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> HiveSource | None:
        return self._sources.get(source_id)

    def get_nodes(self) -> list[HiveGraphNode]:
        return list(self._nodes.values())

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

    def import_snapshot(self, payload: HiveImportRequest) -> None:
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


store = HiveStore()
