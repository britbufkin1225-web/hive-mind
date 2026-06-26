"""Intelligence Report API tests (Phase 10C shape + Phase 11A demo fixtures).

Covers the read-only ``GET /api/intelligence/report`` endpoint: status,
top-level shape, contract-model validation, the guarantee that calling it never
mutates store state, and — for Phase 11A — that each section is populated with
stable, deterministic, clearly-tagged demo fixtures. No real intelligence
heuristics run yet; the populated content is static seed data only.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.hive_models import (
    DreamingSuggestionType,
    GraphNodeType,
    GraphRelationship,
    HiveGraphEdge,
    HiveGraphNode,
    IntelligenceReport,
)
from app.services.intelligence import build_intelligence_report
from app.store.store import store

client = TestClient(app)

_SECTIONS = (
    "dreaming_suggestions",
    "decay_statuses",
    "provenance_chains",
    "query_trail_entries",
)

# Phase 13A/14C: the Temporal Decay and Dreaming Suggestions sections are now
# backend-derived, not fixtures. The remaining sections stay fixture-backed.
_FIXTURE_SECTIONS = (
    "provenance_chains",
    "query_trail_entries",
)


def test_intelligence_report_returns_200() -> None:
    response = client.get("/api/intelligence/report")
    assert response.status_code == 200


def test_intelligence_report_top_level_shape() -> None:
    data = client.get("/api/intelligence/report").json()
    assert "generated_at" in data
    assert data["report_version"] == "0.1.0"
    assert data["read_only"] is True
    for section in _SECTIONS:
        assert section in data
        assert isinstance(data[section], list)
    assert "summary" in data


def test_intelligence_report_summary_counts_match_sections() -> None:
    data = client.get("/api/intelligence/report").json()
    # Summary counts always match the section lengths exactly. The fixture-backed
    # sections stay non-empty for demos; the derived sections (decay/dreaming)
    # are sized by real store state and may legitimately be empty.
    summary = data["summary"]
    assert summary["dreaming_suggestion_count"] == len(data["dreaming_suggestions"])
    assert summary["decay_status_count"] == len(data["decay_statuses"]) > 0
    assert summary["provenance_chain_count"] == len(data["provenance_chains"]) > 0
    assert summary["query_trail_entry_count"] == len(data["query_trail_entries"]) > 0


def test_intelligence_report_dreaming_section_is_backend_derived() -> None:
    data = client.get("/api/intelligence/report").json()
    # Phase 14C: the Dreaming section is derived from store state, never a
    # fixture. The clean seed store has no duplicates/orphans/stale links, so the
    # section is legitimately empty here — but whatever it contains must be
    # derived (tagged) and never fixture data.
    real_node_ids = {n.id for n in store.get_nodes()}
    for entry in data["dreaming_suggestions"]:
        assert entry["metadata"].get("derived") is True
        assert entry["metadata"].get("fixture") is not True
        assert entry["origin"] == "dreaming"
        # Derived suggestions reference real store nodes, not demo-* fixture ids.
        for node_id in entry["node_ids"]:
            assert node_id in real_node_ids
        # The blocked types are never emitted.
        assert entry["type"] not in {"unresolved_query", "source_coverage_gap"}


def test_intelligence_report_fixtures_are_tagged_as_demo_data() -> None:
    data = client.get("/api/intelligence/report").json()
    # Demo origin must be unambiguous in the payload itself: every fixture entry
    # carries metadata.fixture == True so consumers never mistake it for real
    # production intelligence. The Temporal Decay section is exempt — it is now
    # backend-derived (see test below), not fixture data.
    for section in _FIXTURE_SECTIONS:
        assert data[section], f"expected demo fixtures in {section}"
        for entry in data[section]:
            assert entry["metadata"].get("fixture") is True


def test_intelligence_report_decay_section_is_backend_derived() -> None:
    data = client.get("/api/intelligence/report").json()
    decay = data["decay_statuses"]
    assert decay, "expected derived decay rows from store nodes"

    # Decay rows reference real store nodes (not the demo-* fixture ids) and are
    # tagged as derived rather than fixture.
    real_node_ids = {n.id for n in store.get_nodes()}
    for entry in decay:
        assert entry["node_id"] in real_node_ids
        assert entry["metadata"].get("derived") is True
        assert entry["metadata"].get("fixture") is not True
        assert entry["status"] in {"fresh", "aging", "stale", "unknown"}


def test_intelligence_report_is_deterministic_apart_from_generated_at() -> None:
    first = client.get("/api/intelligence/report").json()
    second = client.get("/api/intelligence/report").json()
    # Only generated_at may differ between requests; all fixture content is
    # byte-for-byte stable (safe for screenshots).
    del first["generated_at"]
    del second["generated_at"]
    assert first == second


def test_intelligence_report_validates_against_contract_model() -> None:
    data = client.get("/api/intelligence/report").json()
    report = IntelligenceReport.model_validate(data)
    assert report.read_only is True
    # Summary counts stay consistent with the section lengths.
    assert report.summary.dreaming_suggestion_count == len(report.dreaming_suggestions)
    assert report.summary.decay_status_count == len(report.decay_statuses)
    assert report.summary.provenance_chain_count == len(report.provenance_chains)
    assert report.summary.query_trail_entry_count == len(report.query_trail_entries)


def test_intelligence_report_does_not_mutate_store() -> None:
    before = store.stats()
    client.get("/api/intelligence/report")
    client.get("/api/intelligence/report")
    assert store.stats() == before


class _DreamStore:
    """Tiny read-only store that triggers a backend-derived duplicate signal."""

    def __init__(self, nodes, edges=()):
        self._nodes = list(nodes)
        self._edges = list(edges)

    def get_nodes(self):
        return list(self._nodes)

    def get_edges(self):
        return list(self._edges)

    def get_sources(self):
        return []


def test_report_surfaces_backend_derived_dreaming_suggestions() -> None:
    # A store with two same-label nodes flows a derived `duplicate` suggestion all
    # the way through the report (and the summary count stays consistent).
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    nodes = [
        HiveGraphNode(
            id=f"dup-{i}",
            label="Shared Concept",
            type=GraphNodeType.NOTE,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        for i in (1, 2)
    ]
    # Link the pair so they surface only as a duplicate (not also as orphans).
    edges = [
        HiveGraphEdge(
            id="dup-link",
            source_node_id="dup-1",
            target_node_id="dup-2",
            relationship=GraphRelationship.LINKED_TO,
            created_at=now - timedelta(days=1),
        )
    ]
    report = build_intelligence_report(store=_DreamStore(nodes, edges))
    dreaming = report.dreaming_suggestions
    assert len(dreaming) == 1
    assert dreaming[0].type is DreamingSuggestionType.DUPLICATE
    assert dreaming[0].metadata["derived"] is True
    assert "evidence" in dreaming[0].metadata
    assert report.summary.dreaming_suggestion_count == 1
