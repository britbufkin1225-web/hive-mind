"""Intelligence Report API tests (Phase 10C shape + Phase 11A demo fixtures).

Covers the read-only ``GET /api/intelligence/report`` endpoint: status,
top-level shape, contract-model validation, the guarantee that calling it never
mutates store state, and — for Phase 11A — that each section is populated with
stable, deterministic, clearly-tagged demo fixtures. No real intelligence
heuristics run yet; the populated content is static seed data only.
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


def test_intelligence_report_sections_are_populated_with_fixtures() -> None:
    data = client.get("/api/intelligence/report").json()
    # Phase 11A: every section returns demo fixtures (non-empty), and the
    # summary counts match the section lengths exactly.
    summary = data["summary"]
    assert summary["dreaming_suggestion_count"] == len(data["dreaming_suggestions"]) > 0
    assert summary["decay_status_count"] == len(data["decay_statuses"]) > 0
    assert summary["provenance_chain_count"] == len(data["provenance_chains"]) > 0
    assert summary["query_trail_entry_count"] == len(data["query_trail_entries"]) > 0


def test_intelligence_report_fixtures_are_tagged_as_demo_data() -> None:
    data = client.get("/api/intelligence/report").json()
    # Demo origin must be unambiguous in the payload itself: every fixture entry
    # carries metadata.fixture == True so consumers never mistake it for real
    # production intelligence.
    for section in _SECTIONS:
        assert data[section], f"expected demo fixtures in {section}"
        for entry in data[section]:
            assert entry["metadata"].get("fixture") is True


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


def test_intelligence_report_provenance_chains_expose_aligned_contract_fields() -> None:
    data = client.get("/api/intelligence/report").json()
    chain = data["provenance_chains"][0]

    assert chain["id"]
    assert chain["title"]
    assert chain["summary"]
    assert chain["status"] in {"complete", "partial", "unknown"}
    assert chain["read_only"] is True
    assert chain["source_name"]
    assert chain["source_id"]
    assert chain["source_type"]
    assert isinstance(chain["links"], list)
    assert {link["kind"] for link in chain["links"]} >= {"source", "node", "edge"}


def test_intelligence_report_does_not_mutate_store() -> None:
    before = store.stats()
    client.get("/api/intelligence/report")
    client.get("/api/intelligence/report")
    assert store.stats() == before
