from fastapi import APIRouter, HTTPException

from app.console.console import HiveConsole
from app.models.hive_models import (
    ActivityResponse,
    ConsoleExecuteRequest,
    ConsoleExecuteResponse,
    GraphEdgesResponse,
    GraphNodesResponse,
    HiveExportSnapshot,
    HiveGraphResponse,
    HiveImportRequest,
    HiveModel,
    HiveSource,
    HiveSystemStatus,
    HiveVault,
    ImportResponse,
    IntelligenceReport,
    KnowledgeGraphResponse,
    ModelsResponse,
    SourcesResponse,
    GraphNodeType,
)
from app.services.intelligence import build_intelligence_report
from app.services.knowledge_graph import build_knowledge_graph
from app.store.store import store

router = APIRouter(prefix="/api")


@router.get("/status", response_model=HiveSystemStatus)
def get_status() -> HiveSystemStatus:
    return store.system_status()


@router.get("/vault", response_model=HiveVault)
def get_vault() -> HiveVault:
    nodes = store.get_nodes()
    file_count = sum(1 for n in nodes if n.type == GraphNodeType.FILE)
    return HiveVault(
        total_files=file_count,
        total_sources=len(store.get_sources()),
        total_models=len(store.get_models()),
        total_nodes=len(nodes),
        graph_mode="initialized",
        status="ok",
    )


@router.get("/sources", response_model=SourcesResponse)
def get_sources() -> SourcesResponse:
    return SourcesResponse(sources=store.get_sources())


@router.get("/sources/{source_id}", response_model=HiveSource)
def get_source(source_id: str) -> HiveSource:
    source = store.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return source


@router.get("/graph", response_model=HiveGraphResponse)
def get_graph() -> HiveGraphResponse:
    return HiveGraphResponse(
        nodes=store.get_nodes(),
        edges=store.get_edges(),
        metadata={"storage": "in_memory"},
    )


@router.get("/graph/nodes", response_model=GraphNodesResponse)
def get_graph_nodes() -> GraphNodesResponse:
    return GraphNodesResponse(nodes=store.get_nodes())


@router.get("/graph/edges", response_model=GraphEdgesResponse)
def get_graph_edges() -> GraphEdgesResponse:
    return GraphEdgesResponse(edges=store.get_edges())


@router.get("/knowledge-graph", response_model=KnowledgeGraphResponse)
def get_knowledge_graph() -> KnowledgeGraphResponse:
    """Return the deterministic knowledge graph projection (nodes, edges, summary).

    Nodes come from stored/imported records; edges are existing stored edges plus
    link edges derived from imported Obsidian notes. The shape is stable even when
    there is no graph data (empty lists, zeroed summary).
    """
    return build_knowledge_graph(store=store)


@router.get("/intelligence/report", response_model=IntelligenceReport)
def get_intelligence_report() -> IntelligenceReport:
    """Return the read-only intelligence report (Phase 10C foundation).

    Surfaces the Phase 10B intelligence contracts — Dreaming suggestions, decay
    statuses, provenance chains, and query trail entries — under one stable
    shape. The Temporal Decay section is backend-derived from real store
    timestamps (Phase 13A, deterministic thresholds, no AI); the remaining
    sections are still deterministic demo fixtures pending their own phases. The
    report is read-only and never mutates store state.
    """
    return build_intelligence_report(store=store)


@router.get("/activity", response_model=ActivityResponse)
def get_activity() -> ActivityResponse:
    return ActivityResponse(events=store.get_activity())


@router.get("/models", response_model=ModelsResponse)
def get_models() -> ModelsResponse:
    return ModelsResponse(models=store.get_models())


@router.get("/export", response_model=HiveExportSnapshot)
def get_export() -> HiveExportSnapshot:
    return store.export_snapshot()


@router.post("/import", response_model=ImportResponse)
def post_import(payload: HiveImportRequest) -> ImportResponse:
    try:
        store.import_snapshot(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ImportResponse(
        imported=True,
        sources=len(payload.sources),
        nodes=len(payload.nodes),
        edges=len(payload.edges),
        activity=len(payload.activity),
        models=len(payload.models),
    )


@router.post("/console/execute", response_model=ConsoleExecuteResponse)
def post_console_execute(payload: ConsoleExecuteRequest) -> ConsoleExecuteResponse:
    """Execute a safe, app-controlled Hive Console command.

    Command-level problems (unknown, malformed, unsafe, not-found) return HTTP
    200 with ``ok: false`` and an ``error`` message — they are valid console
    interactions, not transport errors. The console never executes OS commands.
    """
    console = HiveConsole(store)
    return ConsoleExecuteResponse(**console.execute(payload.command))
