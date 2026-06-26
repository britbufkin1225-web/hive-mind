"""Phase 10B — Intelligence contract model tests.

Contract/validation only. These shapes have no endpoint, logic, or persistence
yet; the tests assert default values and additive, read-only shape stability.
"""

from datetime import datetime

from app.models.hive_models import (
    DecayStatus,
    DecayStatusBucket,
    DreamingSuggestion,
    DreamingSuggestionStatus,
    DreamingSuggestionType,
    ProvenanceChain,
    ProvenanceChainStatus,
    ProvenanceLink,
    ProvenanceLinkKind,
    QueryTrailEntry,
    QueryTrailKind,
    QueryTrailStatus,
)

FIXED_TS = datetime(2026, 1, 1, 12, 0, 0)


def test_dreaming_suggestion_defaults() -> None:
    suggestion = DreamingSuggestion(
        id="dream-1",
        type=DreamingSuggestionType.ORPHAN,
        rationale="Node has no edges.",
        created_at=FIXED_TS,
    )
    assert suggestion.status is DreamingSuggestionStatus.OPEN
    assert suggestion.node_ids == []
    assert suggestion.edge_ids == []
    assert suggestion.confidence_hint is None
    # Derived output is explicitly labeled with its origin.
    assert suggestion.origin == "dreaming"
    assert suggestion.metadata == {}


def test_decay_status_defaults() -> None:
    decay = DecayStatus(node_id="node-1")
    assert decay.status is DecayStatusBucket.UNKNOWN
    assert decay.last_imported_at is None
    assert decay.last_referenced_at is None
    assert decay.last_updated_at is None
    assert decay.source_reliability_hint is None
    assert decay.review_needed is False
    assert decay.metadata == {}


def test_provenance_chain_defaults() -> None:
    chain = ProvenanceChain(node_id="node-1")
    assert chain.id is None
    assert chain.title is None
    assert chain.summary is None
    assert chain.status is ProvenanceChainStatus.UNKNOWN
    assert chain.read_only is True
    assert chain.source_id is None
    assert chain.source_name is None
    assert chain.source_type is None
    assert chain.origin_path is None
    assert chain.links == []
    assert chain.linked_node_ids == []
    assert chain.derived_edge_ids == []
    assert chain.stored_edge_ids == []
    assert chain.created_at is None
    assert chain.updated_at is None
    assert chain.last_imported_at is None
    assert chain.metadata == {}


def test_provenance_chain_contract_supports_future_derived_records() -> None:
    chain = ProvenanceChain(
        id="prov-node-1",
        node_id="node-1",
        title="Source to imported note to knowledge node",
        summary="Explains how a source produced a knowledge node.",
        status=ProvenanceChainStatus.PARTIAL,
        source_id="source-1",
        source_name="Research Vault",
        links=[
            ProvenanceLink(
                kind=ProvenanceLinkKind.SOURCE,
                ref_id="source-1",
                label="Research Vault",
                metadata={"source_resolution": "resolved"},
            ),
            ProvenanceLink(
                kind=ProvenanceLinkKind.IMPORT,
                ref_id="import-source-1",
                label="Import metadata",
                metadata={"import_status": "completed"},
            ),
            ProvenanceLink(
                kind=ProvenanceLinkKind.NODE,
                ref_id="node-1",
                label="Knowledge Node",
            ),
            ProvenanceLink(
                kind=ProvenanceLinkKind.EDGE,
                ref_id="edge-1",
                label="references",
                origin="knowledge_graph_builder",
                metadata={"relationship": "references", "reason": "wiki_link"},
            ),
        ],
        linked_node_ids=["node-2"],
        derived_edge_ids=["edge-1"],
        metadata={
            "derivation_origin": "provenance_derivation",
            "chain_shape": "source_to_imported_note_to_knowledge_node",
            "source_resolution": "resolved",
            "warnings": [],
        },
    )

    dumped = chain.model_dump(mode="json")

    assert dumped["id"] == "prov-node-1"
    assert dumped["status"] == "partial"
    assert dumped["read_only"] is True
    assert dumped["source_name"] == "Research Vault"
    assert [link["kind"] for link in dumped["links"]] == [
        "source",
        "import",
        "node",
        "edge",
    ]
    assert dumped["metadata"]["derivation_origin"] == "provenance_derivation"


def test_provenance_link_origin_marker() -> None:
    link = ProvenanceLink(kind=ProvenanceLinkKind.EDGE, ref_id="edge-1")
    assert link.label is None
    assert link.origin is None
    assert link.metadata == {}


def test_query_trail_entry_defaults() -> None:
    entry = QueryTrailEntry(id="q-1", query="FastAPI", last_executed_at=FIXED_TS)
    assert entry.kind is QueryTrailKind.SEARCH
    assert entry.status is QueryTrailStatus.RESOLVED
    assert entry.result_node_ids == []
    assert entry.result_count == 0
    assert entry.occurrence_count == 1
    assert entry.pinned is False
    assert entry.metadata == {}


def test_intelligence_shapes_round_trip() -> None:
    # Additive, read-only wire shapes serialize and re-validate deterministically.
    suggestion = DreamingSuggestion(
        id="dream-1",
        type=DreamingSuggestionType.DUPLICATE,
        rationale="Two notes look near-identical.",
        node_ids=["a", "b"],
        created_at=FIXED_TS,
    )
    dumped = suggestion.model_dump()
    assert dumped["origin"] == "dreaming"
    assert DreamingSuggestion.model_validate(dumped) == suggestion
