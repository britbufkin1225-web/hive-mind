"""Phase 18E — API edge-case defensive validation regression tests.

Phase 18D triaged the API edge cases Phase 18B did not implement and selected the
highest-value one — a bounded request-body nesting-depth guard — for this phase
(threat model §5.1, "deeply nested objects -> no uncontrolled recursion"). These
tests lock that guard plus the explicit value-handling decisions Phase 18D asked
to document and test:

* Over-depth bodies are rejected with a clean ``422`` *before* downstream
  processing; an at-limit body still succeeds (no valid request regressed).
* The rejection uses the existing validation-error shape and leaks no traceback,
  internal field, or filesystem path (no regression of Phase 18C cat. 3 / 10).
* Null-like sentinel strings (``"null"``, ``"None"``, ``"undefined"``) remain
  ordinary string values (the documented, low-risk decision), and empty /
  whitespace-only values keep their existing clean ``4xx`` handling.

The guard helper is also unit-tested in isolation so the exact depth boundary is
pinned independently of any route.

No test here drives a destructive operation; every case exercises an existing
validation path against malformed or boundary input.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.validation import (
    MAX_REQUEST_NESTING_DEPTH,
    assert_within_nesting_depth,
)

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _nested_dict(container_depth: int) -> object:
    """Build a value whose deepest container sits at ``container_depth``.

    ``container_depth == 1`` -> ``{"k": "leaf"}`` (one container); each extra
    level wraps the previous value in another single-key dict.
    """
    value: object = "leaf"
    for _ in range(container_depth):
        value = {"k": value}
    return value


# --------------------------------------------------------------------------- #
# Unit: the pure depth guard pins the exact boundary and never recurses
# --------------------------------------------------------------------------- #
def test_depth_guard_allows_at_limit() -> None:
    # Deepest container exactly at the limit is accepted.
    assert_within_nesting_depth(_nested_dict(MAX_REQUEST_NESTING_DEPTH))


def test_depth_guard_rejects_over_limit() -> None:
    with pytest.raises(ValueError, match="too deeply nested"):
        assert_within_nesting_depth(_nested_dict(MAX_REQUEST_NESTING_DEPTH + 1))


def test_depth_guard_counts_list_nesting() -> None:
    # Lists contribute to depth just like dicts.
    deep_list: object = "leaf"
    for _ in range(MAX_REQUEST_NESTING_DEPTH + 1):
        deep_list = [deep_list]
    with pytest.raises(ValueError):
        assert_within_nesting_depth(deep_list)


def test_depth_guard_allows_flat_and_scalar_values() -> None:
    # Scalars and shallow structures never trip the guard.
    assert_within_nesting_depth("a string")
    assert_within_nesting_depth(42)
    assert_within_nesting_depth({"a": 1, "b": [1, 2, 3], "c": {"d": "e"}})
    assert_within_nesting_depth([])


def test_depth_guard_survives_pathologically_deep_input() -> None:
    # A recursive implementation would overflow the stack here; the iterative
    # guard must reject cleanly with a ValueError instead.
    with pytest.raises(ValueError):
        assert_within_nesting_depth(_nested_dict(50_000))


# --------------------------------------------------------------------------- #
# API: deeply nested bodies are a clean 422, not a 500 / crash / leak
# --------------------------------------------------------------------------- #
def test_registry_create_rejects_deeply_nested_metadata() -> None:
    response = client.post(
        "/api/registry/sources",
        json={
            "name": "Deep",
            "type": "obsidian",
            "metadata": _nested_dict(MAX_REQUEST_NESTING_DEPTH + 5),
        },
    )
    assert response.status_code == 422
    assert response.status_code != 500


def test_registry_create_accepts_at_limit_metadata() -> None:
    # The body dict is depth 1, so a metadata value nested to (limit - 1)
    # containers puts the deepest container exactly at the limit — which is
    # inclusive and must still create the record (the bound rejects no realistic
    # payload, mirroring Phase 18B's at-limit acceptance test).
    response = client.post(
        "/api/registry/sources",
        json={
            "name": "At Limit",
            "type": "obsidian",
            "metadata": _nested_dict(MAX_REQUEST_NESTING_DEPTH - 1),
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "At Limit"


def test_import_rejects_deeply_nested_node_metadata() -> None:
    response = client.post(
        "/api/import",
        json={
            "nodes": [
                {
                    "id": "n1",
                    "label": "n1",
                    "type": "concept",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "metadata": _nested_dict(MAX_REQUEST_NESTING_DEPTH + 5),
                }
            ]
        },
    )
    assert response.status_code == 422
    assert response.status_code != 500


def test_import_accepts_shallow_valid_body() -> None:
    # A normal, shallow import body is unaffected by the depth guard. The import
    # endpoint replaces the shared store, so snapshot the current state first and
    # restore it after, leaving global fixtures intact for other tests.
    snapshot = client.get("/api/export").json()
    try:
        response = client.post(
            "/api/import",
            json={
                "sources": [],
                "nodes": [
                    {
                        "id": "n1",
                        "label": "Concept",
                        "type": "concept",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "metadata": {"note": {"detail": "shallow"}},
                    }
                ],
                "edges": [],
                "activity": [],
                "models": [],
            },
        )
        assert response.status_code == 200
        assert response.json()["nodes"] == 1
    finally:
        restore = client.post(
            "/api/import",
            json={
                "sources": snapshot["sources"],
                "nodes": snapshot["nodes"],
                "edges": snapshot["edges"],
                "activity": snapshot["activity"],
                "models": snapshot["models"],
            },
        )
        assert restore.status_code == 200


def test_registry_update_rejects_deeply_nested_metadata() -> None:
    created = client.post(
        "/api/registry/sources",
        json={"name": "To Update", "type": "obsidian"},
    )
    assert created.status_code == 201
    source_id = created.json()["id"]

    response = client.patch(
        f"/api/registry/sources/{source_id}",
        json={"metadata": _nested_dict(MAX_REQUEST_NESTING_DEPTH + 5)},
    )
    assert response.status_code == 422
    assert response.status_code != 500


def test_deep_nesting_rejection_leaks_nothing() -> None:
    response = client.post(
        "/api/registry/sources",
        json={
            "name": "NoLeak",
            "type": "obsidian",
            "metadata": _nested_dict(MAX_REQUEST_NESTING_DEPTH + 5),
        },
    )
    assert response.status_code == 422
    # Same structured validation-error contract as existing Phase 18B guards…
    assert "detail" in response.json()
    body = response.text
    # …and no traceback / source path / internal exception class leaks out.
    assert "Traceback" not in body
    assert 'File "' not in body
    assert "ValueError" not in body


# --------------------------------------------------------------------------- #
# Value-handling decisions Phase 18D asked to document and lock
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sentinel", ["null", "None", "undefined", "nil", "NaN"])
def test_null_like_strings_are_ordinary_values(sentinel: str) -> None:
    # Decision: null-like sentinel strings are plain strings, not a magic
    # "absent" marker. A source named "null" is a valid create, not a 4xx.
    response = client.post(
        "/api/registry/sources",
        json={"name": sentinel, "type": "obsidian"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == sentinel


def test_console_null_like_command_is_graceful_200() -> None:
    # A null-like command string is an ordinary (unknown) console command, not a
    # transport error: HTTP 200 with ok=false, consistent with Phase 18B.
    response = client.post("/api/console/execute", json={"command": "null"})
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_whitespace_only_vault_path_is_clean_client_error() -> None:
    # Decision: a whitespace-only vault path is not a usable location; it stays a
    # clean 400 (never a 500 / traceback), matching the empty-path handling.
    response = client.post("/api/obsidian/import", json={"vault_path": "   "})
    assert response.status_code == 400
    assert response.status_code != 500
    assert "Traceback" not in response.text
