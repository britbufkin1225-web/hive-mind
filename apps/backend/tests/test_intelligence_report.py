"""Phase 10C — Intelligence Report API foundation tests.

Covers the read-only ``GET /api/intelligence/report`` endpoint: status,
top-level shape, empty-state defaults, contract-model validation, and the
guarantee that calling it never mutates store state. No real intelligence
heuristics run yet, so the report is deterministic and empty.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models.hive_models import IntelligenceReport
from app.store.store import store

client = TestClient(app)

_SECTIONS = (
    "dreaming_suggestions",
    "decay_statuses",
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


def test_intelligence_report_empty_state() -> None:
    data = client.get("/api/intelligence/report").json()
    # Foundation phase: no derived intelligence -> empty sections, zeroed counts.
    for section in _SECTIONS:
        assert data[section] == []
    summary = data["summary"]
    assert summary["dreaming_suggestion_count"] == 0
    assert summary["decay_status_count"] == 0
    assert summary["provenance_chain_count"] == 0
    assert summary["query_trail_entry_count"] == 0


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
