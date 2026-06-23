from app.mock.mock_data import (
    MOCK_ACTIVITY_EVENTS,
    MOCK_GRAPH_EDGES,
    MOCK_GRAPH_NODES,
    MOCK_GRAPH_RESPONSE,
    MOCK_SOURCES,
    MOCK_SYSTEM_STATUS,
)
from app.models.hive_models import SystemStatusValue


def test_phase_2_mock_data_counts() -> None:
    assert len(MOCK_SOURCES) == 3
    assert 6 <= len(MOCK_GRAPH_NODES) <= 10
    assert 5 <= len(MOCK_GRAPH_EDGES) <= 8
    assert len(MOCK_ACTIVITY_EVENTS) == 5


def test_graph_response_uses_mock_nodes_and_edges() -> None:
    assert MOCK_GRAPH_RESPONSE.nodes == MOCK_GRAPH_NODES
    assert MOCK_GRAPH_RESPONSE.edges == MOCK_GRAPH_EDGES
    assert MOCK_GRAPH_RESPONSE.metadata["mock"] is True


def test_system_status_matches_mock_contract() -> None:
    assert MOCK_SYSTEM_STATUS.status == SystemStatusValue.OK
    assert MOCK_SYSTEM_STATUS.sources_count == len(MOCK_SOURCES)
    assert MOCK_SYSTEM_STATUS.nodes_count == len(MOCK_GRAPH_NODES)
    assert MOCK_SYSTEM_STATUS.edges_count == len(MOCK_GRAPH_EDGES)
