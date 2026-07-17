"""Phase 37F read-only Active Memory context-packet endpoint tests.

Transport-boundary tests only: the deterministic packet rules themselves are
covered by ``test_active_memory_context_packet.py``; these tests prove the API
surfaces that existing behavior faithfully (contract shape, determinism,
timestamp handling, empty states, overflow fail-closed, validation, and
read-only / no-store-state guarantees).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.active_memory import (
    MAX_MEMORY_COLLECTION_ITEMS,
    ContextPacket,
    LifecycleState,
)
from app.store.active_memory_store import InMemoryActiveMemoryStore

client = TestClient(app)

URL = "/api/active-memory/context-packet"
GENERATED_AT = "2026-07-16T09:30:00"
TS = "2026-01-01T12:00:00"
TS_LATE = "2026-01-02T12:00:00"


def _record(
    record_id: str,
    *,
    kind: str = "project_fact",
    project_id: str = "hive-mind",
    subject: str = "subject",
    predicate: str = "state",
    value: str = "true",
    lifecycle_state: str = "active",
    verification_state: str = "unverified",
    evidence_ids: list[str] | None = None,
    created_at: str = TS,
    observed_at: str | None = None,
    scope: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    payload = {
        "record_id": record_id,
        "kind": kind,
        "claim": {
            "subject": subject,
            "predicate": predicate,
            "value": value,
            "value_kind": "string",
        },
        "project_id": project_id,
        "source": {"source_type": "codex", "source_id": "codex"},
        "lifecycle_state": lifecycle_state,
        "verification_state": verification_state,
        "evidence_ids": evidence_ids or [],
        "created_at": created_at,
        "metadata": metadata or {},
    }
    if observed_at is not None:
        payload["observed_at"] = observed_at
    if scope is not None:
        payload["scope"] = scope
    return payload


def _request(
    records: list[dict] | None = None,
    *,
    project_id: str = "hive-mind",
    generated_at: str = GENERATED_AT,
    scope: dict | None = None,
) -> dict:
    payload: dict = {
        "project_id": project_id,
        "generated_at": generated_at,
        "records": records or [],
    }
    if scope is not None:
        payload["scope"] = scope
    return payload


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# --------------------------------------------------------------------------- #
# Successful requests
# --------------------------------------------------------------------------- #
def test_valid_request_returns_packet_matching_typed_contract() -> None:
    response = client.post(
        URL,
        json=_request(
            [
                _record("fact", kind="project_fact", evidence_ids=["ev-1", "ev-2"]),
                _record("decision", kind="project_decision"),
                _record("constraint", kind="project_constraint"),
                _record("capability", kind="capability"),
                _record(
                    "phase",
                    kind="phase_status",
                    metadata={"active_phase": "Phase 37F", "active_track": "Track 2"},
                ),
                _record(
                    "repo",
                    kind="repository_state",
                    evidence_ids=["ev-tree"],
                    metadata={
                        "repository_baseline": {
                            "branch": "main",
                            "head_commit": "abc123",
                            "working_tree_clean": True,
                        }
                    },
                ),
            ]
        ),
    )

    assert response.status_code == 200
    data = response.json()
    # The response body must round-trip through the existing Phase 37B contract.
    packet = ContextPacket.model_validate(data)

    assert packet.packet_version == "active-memory.v1"
    assert packet.read_only is True
    assert packet.project_id == "hive-mind"
    assert [r.record_id for r in packet.active_facts] == ["fact"]
    assert [r.record_id for r in packet.active_decisions] == ["decision"]
    assert [r.record_id for r in packet.active_constraints] == ["constraint"]
    assert [r.record_id for r in packet.known_capabilities] == ["capability"]
    assert packet.active_phase == "Phase 37F"
    assert packet.active_track == "Track 2"
    assert packet.repository_baseline is not None
    assert packet.repository_baseline.branch == "main"
    assert packet.repository_baseline.head_commit == "abc123"
    assert packet.repository_baseline.working_tree_clean is True
    # Evidence and reason metadata survive serialization untouched.
    assert packet.active_facts[0].evidence_ids == ["ev-1", "ev-2"]
    assert packet.repository_baseline.evidence_ids == ["ev-tree"]
    assert packet.repository_baseline.metadata == {"source_record_id": "repo"}
    assert packet.verification_summary.unverified_count == 4
    assert (
        'Do not assume constraint "subject" may be violated.'
        in packet.prohibited_assumptions
    )


def test_lifecycle_warning_reason_metadata_is_preserved() -> None:
    response = client.post(
        URL,
        json=_request(
            [
                _record("stale", lifecycle_state="stale"),
                _record("sup", lifecycle_state="superseded"),
            ]
        ),
    )
    assert response.status_code == 200
    warnings = response.json()["warnings"]
    assert [w["record_id"] for w in warnings] == ["stale", "sup"]
    assert [w["lifecycle_state"] for w in warnings] == ["stale", "superseded"]
    assert all("excluded from the active baseline" in w["reason"] for w in warnings)


def test_contradictions_surface_with_request_supplied_timestamp() -> None:
    response = client.post(
        URL,
        json=_request(
            [
                _record("merged", subject="Phase 37D", value="merged"),
                _record("pending", subject="Phase 37D", value="pending"),
            ]
        ),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["unresolved_contradictions"]) == 1
    contradiction = data["unresolved_contradictions"][0]
    assert contradiction["contradiction_class"] == "pending_vs_merged"
    assert contradiction["resolution_state"] == "open"
    assert _parse_dt(contradiction["detected_at"]) == _parse_dt(GENERATED_AT)
    assert sorted(contradiction["involved_record_ids"]) == ["merged", "pending"]
    # No winner is picked: both records stay in the active baseline.
    assert [r["record_id"] for r in data["active_facts"]] == ["merged", "pending"]


def test_project_isolation_and_exact_scope_filter_apply() -> None:
    phase_scope = {"scope_type": "phase", "scope_id": "37F"}
    response = client.post(
        URL,
        json=_request(
            [
                _record("match", scope=phase_scope),
                _record("other-scope", scope={"scope_type": "phase", "scope_id": "37E"}),
                _record("global"),
                _record("theirs", project_id="other-project", scope=phase_scope),
            ],
            scope=phase_scope,
        ),
    )
    assert response.status_code == 200
    assert [r["record_id"] for r in response.json()["active_facts"]] == ["match"]


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_identical_requests_produce_identical_responses() -> None:
    payload = _request(
        [
            _record("b", created_at=TS_LATE),
            _record("a", created_at=TS),
        ]
    )
    first = client.post(URL, json=payload)
    second = client.post(URL, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.text == second.text


def test_input_record_ordering_does_not_change_output() -> None:
    records = [
        _record("b", created_at=TS),
        _record("late", created_at=TS_LATE),
        _record("a", created_at=TS),
    ]
    forward = client.post(URL, json=_request(records))
    reversed_ = client.post(URL, json=_request(list(reversed(records))))
    assert forward.status_code == reversed_.status_code == 200
    assert forward.json() == reversed_.json()
    # Equal created_at values tie-break on record_id (established store order).
    assert [r["record_id"] for r in forward.json()["active_facts"]] == [
        "a",
        "b",
        "late",
    ]


# --------------------------------------------------------------------------- #
# Timestamp handling at the serialization boundary
# --------------------------------------------------------------------------- #
def test_timezone_aware_offset_and_trailing_z_timestamps_are_accepted() -> None:
    with_offset = client.post(
        URL,
        json=_request(
            [_record("fact", created_at="2026-01-01T12:00:00+00:00")],
            generated_at="2026-07-16T09:30:00+00:00",
        ),
    )
    with_z = client.post(
        URL,
        json=_request(
            [_record("fact", created_at="2026-01-01T12:00:00Z")],
            generated_at="2026-07-16T09:30:00Z",
        ),
    )
    assert with_offset.status_code == with_z.status_code == 200
    assert with_offset.json() == with_z.json()
    assert _parse_dt(with_z.json()["generated_at"]) == datetime(
        2026, 7, 16, 9, 30, 0, tzinfo=timezone.utc
    )


def test_naive_timestamps_are_accepted_and_round_trip() -> None:
    response = client.post(URL, json=_request([_record("fact")]))
    assert response.status_code == 200
    assert _parse_dt(response.json()["generated_at"]) == datetime(2026, 7, 16, 9, 30, 0)
    assert _parse_dt(response.json()["active_facts"][0]["created_at"]) == datetime(
        2026, 1, 1, 12, 0, 0
    )


def test_missing_optional_observed_at_is_tolerated() -> None:
    response = client.post(URL, json=_request([_record("fact")]))
    assert response.status_code == 200
    assert response.json()["active_facts"][0]["observed_at"] is None


def test_missing_generated_at_is_rejected() -> None:
    payload = _request([_record("fact")])
    del payload["generated_at"]
    assert client.post(URL, json=payload).status_code == 422


def test_invalid_generated_at_is_rejected() -> None:
    payload = _request([_record("fact")], generated_at="not-a-timestamp")
    assert client.post(URL, json=payload).status_code == 422


def test_invalid_record_created_at_is_rejected() -> None:
    payload = _request([_record("fact", created_at="yesterday-ish")])
    assert client.post(URL, json=payload).status_code == 422


def test_serialized_baseline_observed_at_survives_api_serialization() -> None:
    response = client.post(
        URL,
        json=_request(
            [
                _record(
                    "repo",
                    kind="repository_state",
                    metadata={
                        "repository_baseline": {
                            "branch": "main",
                            "observed_at": "2026-01-02T12:00:00Z",
                        }
                    },
                )
            ]
        ),
    )
    assert response.status_code == 200
    baseline = response.json()["repository_baseline"]
    assert baseline["branch"] == "main"
    assert _parse_dt(baseline["observed_at"]) == datetime(
        2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc
    )


def test_invalid_baseline_observed_at_keeps_conservative_service_behavior() -> None:
    # The Phase 37E builder skips a structurally invalid baseline candidate
    # rather than guessing; the API must surface that unchanged (200 + null).
    response = client.post(
        URL,
        json=_request(
            [
                _record(
                    "repo",
                    kind="repository_state",
                    metadata={
                        "repository_baseline": {
                            "branch": "main",
                            "observed_at": "not a timestamp",
                        }
                    },
                )
            ]
        ),
    )
    assert response.status_code == 200
    assert response.json()["repository_baseline"] is None


def test_equal_observed_at_baselines_tie_break_deterministically() -> None:
    observed = "2026-01-02T12:00:00+00:00"
    records = [
        _record(
            "repo-a",
            kind="repository_state",
            metadata={
                "repository_baseline": {"branch": "tie-a", "observed_at": observed}
            },
        ),
        _record(
            "repo-z",
            kind="repository_state",
            metadata={
                "repository_baseline": {"branch": "tie-z", "observed_at": observed}
            },
        ),
    ]
    forward = client.post(URL, json=_request(records))
    reversed_ = client.post(URL, json=_request(list(reversed(records))))
    assert forward.status_code == reversed_.status_code == 200
    assert forward.json() == reversed_.json()
    assert forward.json()["repository_baseline"]["branch"] == "tie-z"
    assert forward.json()["repository_baseline"]["metadata"] == {
        "source_record_id": "repo-z"
    }


# --------------------------------------------------------------------------- #
# Empty states
# --------------------------------------------------------------------------- #
def test_empty_records_return_a_valid_empty_packet() -> None:
    response = client.post(URL, json=_request([]))
    assert response.status_code == 200
    data = response.json()
    packet = ContextPacket.model_validate(data)
    assert packet.repository_baseline is None
    assert packet.active_phase is None
    assert packet.active_track is None
    assert data["active_facts"] == []
    assert data["active_decisions"] == []
    assert data["active_constraints"] == []
    assert data["known_capabilities"] == []
    assert data["unresolved_contradictions"] == []
    assert data["warnings"] == []
    assert data["evidence_references"] == []
    assert data["prohibited_assumptions"] == []
    assert all(count == 0 for count in data["verification_summary"].values())


def test_omitted_records_field_defaults_to_empty() -> None:
    response = client.post(
        URL, json={"project_id": "hive-mind", "generated_at": GENERATED_AT}
    )
    assert response.status_code == 200
    assert response.json()["active_facts"] == []


# --------------------------------------------------------------------------- #
# Overflow behavior (owned by the Phase 37E service; the API never recalculates)
# --------------------------------------------------------------------------- #
def test_warning_collection_limit_boundary_survives_serialization() -> None:
    records = [
        _record(f"warning-{index:04}", lifecycle_state="stale")
        for index in range(MAX_MEMORY_COLLECTION_ITEMS)
    ]
    response = client.post(URL, json=_request(records))
    assert response.status_code == 200
    assert len(response.json()["warnings"]) == MAX_MEMORY_COLLECTION_ITEMS


def test_warning_overflow_fails_closed_as_422() -> None:
    records = [
        _record(f"warning-{index:04}", lifecycle_state="stale")
        for index in range(MAX_MEMORY_COLLECTION_ITEMS + 1)
    ]
    response = client.post(URL, json=_request(records))
    assert response.status_code == 422
    assert "warnings" in response.json()["detail"]
    assert "no truthful packet-level truncation warning" in response.json()["detail"]


def test_contradiction_overflow_fails_closed_as_422() -> None:
    # 46 same-subject phase_status records with distinct values yield
    # C(46, 2) = 1035 open duplicate_phase_status contradictions > the limit,
    # while no visible record collection exceeds its own bound.
    records = [
        _record(
            f"phase-{index:02}",
            kind="phase_status",
            subject="Current phase",
            value=f"Phase {index:02}",
        )
        for index in range(46)
    ]
    response = client.post(URL, json=_request(records))
    assert response.status_code == 422
    assert "unresolved_contradictions" in response.json()["detail"]


def test_prohibited_assumption_overflow_fails_closed_as_422() -> None:
    half = MAX_MEMORY_COLLECTION_ITEMS // 2 + 1
    records = [
        _record(f"constraint-{index:04}", kind="project_constraint")
        for index in range(half)
    ] + [
        _record(f"capability-{index:04}", kind="capability")
        for index in range(half)
    ]
    response = client.post(URL, json=_request(records))
    assert response.status_code == 422
    assert "prohibited_assumptions" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# Invalid input (established FastAPI/Pydantic validation path)
# --------------------------------------------------------------------------- #
def test_missing_project_id_is_rejected() -> None:
    payload = _request([])
    del payload["project_id"]
    assert client.post(URL, json=payload).status_code == 422


def test_blank_project_id_is_rejected() -> None:
    assert client.post(URL, json=_request([], project_id="   ")).status_code == 422


def test_non_list_records_are_rejected() -> None:
    payload = _request([])
    payload["records"] = {"record_id": "fact"}
    assert client.post(URL, json=payload).status_code == 422


def test_invalid_record_kind_enum_is_rejected() -> None:
    assert (
        client.post(URL, json=_request([_record("fact", kind="prophecy")])).status_code
        == 422
    )


def test_invalid_scope_type_enum_is_rejected() -> None:
    payload = _request([], scope={"scope_type": "galaxy", "scope_id": "x"})
    assert client.post(URL, json=payload).status_code == 422


def test_invalid_nested_claim_structure_is_rejected() -> None:
    record = _record("fact")
    record["claim"] = "branch is main"
    assert client.post(URL, json=_request([record])).status_code == 422


def test_duplicate_record_ids_return_clean_422() -> None:
    response = client.post(URL, json=_request([_record("dup"), _record("dup")]))
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "'dup'" in detail
    assert "already exists" in detail
    # No traceback, internal path, or raw exception object leaks.
    assert "Traceback" not in response.text
    assert "\\\\" not in detail and "C:\\" not in detail


# --------------------------------------------------------------------------- #
# Read-only behavior
# --------------------------------------------------------------------------- #
def test_router_module_holds_no_store_state() -> None:
    import app.routers.active_memory as module

    assert not any(
        isinstance(value, InMemoryActiveMemoryStore) for value in vars(module).values()
    )


def test_endpoint_uses_only_an_ephemeral_store_and_never_mutates_it(
    monkeypatch,
) -> None:
    import app.routers.active_memory as module

    instances: list[InMemoryActiveMemoryStore] = []

    class SpyStore(InMemoryActiveMemoryStore):
        def __init__(self) -> None:
            super().__init__()
            self.insert_ids: list[str] = []
            instances.append(self)

        def insert(self, record):  # type: ignore[override]
            self.insert_ids.append(record.record_id)
            return super().insert(record)

        def transition_lifecycle(self, record_id, target):  # type: ignore[override]
            raise AssertionError("endpoint must never transition record lifecycle")

    monkeypatch.setattr(module, "InMemoryActiveMemoryStore", SpyStore)

    payload = _request([_record("fact-1"), _record("fact-2", lifecycle_state="stale")])
    payload_before = json.dumps(payload, sort_keys=True)
    first = client.post(URL, json=payload)
    second = client.post(URL, json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    # The request payload itself was not rewritten by the call.
    assert json.dumps(payload, sort_keys=True) == payload_before
    # One fresh, request-scoped store per request — no reuse, no shared state.
    assert len(instances) == 2
    for store in instances:
        # Exactly the supplied records were inserted (transport conversion) and
        # nothing was created, updated, or deleted afterwards.
        assert store.insert_ids == ["fact-1", "fact-2"]
        assert len(store) == 2
        assert store.get("fact-1").lifecycle_state is LifecycleState.ACTIVE
        assert store.get("fact-2").lifecycle_state is LifecycleState.STALE
        assert store.get("fact-1").claim.value == "true"
