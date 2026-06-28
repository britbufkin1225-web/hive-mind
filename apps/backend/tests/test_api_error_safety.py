"""Phase 18B — backend API defensive validation + error-safety regression tests.

These tests lock the negative-path behavior described in the Phase 18A threat
model and vulnerability test plan (``docs/security/...``), §5.1 (API negative
testing) and §5.3 (Intelligence Report read-only integrity). They assert the
*safe* behavior for malformed/unsafe input — clean status codes, structured
validation errors, and no leak of tracebacks, internal exception text, or local
filesystem paths.

No test here drives a destructive operation; every case exercises an existing
read/validation path against malformed input.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.vault_scanner import resolve_vault_root
from app.main import app
from app.models.hive_models import (
    MAX_CONSOLE_COMMAND_LENGTH,
    MAX_ROOT_PATH_LENGTH,
    MAX_VAULT_PATH_LENGTH,
)

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Unknown routes / wrong methods (clean 404 / 405, never a 500)
# --------------------------------------------------------------------------- #
def test_unknown_route_returns_404() -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    ["/api/console/execute", "/api/import", "/api/obsidian/import"],
)
def test_wrong_method_on_post_route_returns_405(path: str) -> None:
    # GET on a POST-only route is a method error, not a server error.
    response = client.get(path)
    assert response.status_code == 405


def test_wrong_method_on_get_route_returns_405() -> None:
    # POST on a read-only GET route is a method error.
    response = client.post("/api/status")
    assert response.status_code == 405


# --------------------------------------------------------------------------- #
# Malformed bodies / wrong types / missing fields / bad enums (clean 422)
# --------------------------------------------------------------------------- #
def test_malformed_json_body_is_client_error_not_500() -> None:
    response = client.post(
        "/api/console/execute",
        content=b"{not valid json",
        headers={"content-type": "application/json"},
    )
    # FastAPI reports a malformed body as a client validation error (400/422),
    # never an unhandled 500.
    assert response.status_code in (400, 422)
    assert response.status_code != 500


def test_console_missing_command_field_is_422() -> None:
    assert client.post("/api/console/execute", json={}).status_code == 422


def test_console_wrong_command_type_is_422() -> None:
    # command must be a string; a list/object is rejected at the contract edge.
    response = client.post("/api/console/execute", json={"command": ["not", "a", "string"]})
    assert response.status_code == 422


def test_import_wrong_field_type_is_422() -> None:
    # nodes must be a list; a scalar is rejected before any store work.
    response = client.post("/api/import", json={"nodes": "not-a-list"})
    assert response.status_code == 422


def test_obsidian_missing_vault_path_is_422() -> None:
    assert client.post("/api/obsidian/import", json={}).status_code == 422


def test_registry_invalid_enum_value_is_422() -> None:
    response = client.post(
        "/api/registry/sources",
        json={"name": "X", "type": "not_a_real_connector_type"},
    )
    assert response.status_code == 422


def test_registry_blank_name_is_422() -> None:
    response = client.post(
        "/api/registry/sources",
        json={"name": "   ", "type": "obsidian"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Oversized free-text inputs are rejected deterministically (Phase 18B bound)
# --------------------------------------------------------------------------- #
def test_oversized_console_command_is_422() -> None:
    huge = "a" * (MAX_CONSOLE_COMMAND_LENGTH + 1)
    response = client.post("/api/console/execute", json={"command": huge})
    assert response.status_code == 422


def test_console_command_at_limit_is_accepted() -> None:
    # The bound must not reject a realistic command; a max-length 'help'-padded
    # value still parses to a normal (unknown) console result at HTTP 200.
    at_limit = "x" * MAX_CONSOLE_COMMAND_LENGTH
    response = client.post("/api/console/execute", json={"command": at_limit})
    assert response.status_code == 200
    assert response.json()["ok"] is False  # unknown command, gracefully handled


def test_oversized_vault_path_is_422() -> None:
    huge = "a" * (MAX_VAULT_PATH_LENGTH + 1)
    response = client.post("/api/obsidian/import", json={"vault_path": huge})
    assert response.status_code == 422


def test_oversized_registry_root_path_is_422() -> None:
    huge = "a" * (MAX_ROOT_PATH_LENGTH + 1)
    response = client.post(
        "/api/registry/sources",
        json={"name": "X", "type": "obsidian", "root_path": huge},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Invalid object identifiers (clean 404, no crash, no traceback)
# --------------------------------------------------------------------------- #
def test_invalid_source_id_is_404() -> None:
    response = client.get("/api/sources/no-such-source")
    assert response.status_code == 404
    body = response.text
    assert "Traceback" not in body and "File \"" not in body


def test_invalid_registry_source_id_is_404() -> None:
    response = client.get("/api/registry/sources/no-such-record")
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Obsidian import path safety — malformed path strings stay client errors
# --------------------------------------------------------------------------- #
def test_resolve_vault_root_rejects_embedded_null_byte() -> None:
    # An embedded null byte is never a usable path. Depending on the OS the probe
    # either raises (→ wrapped "not a valid path") or reports the path as absent;
    # both paths yield a clean ValueError, never an unhandled error. The contract
    # under test is rejection-as-ValueError, which the router maps to a 400.
    with pytest.raises(ValueError):
        resolve_vault_root("bad\x00path")


def test_resolve_vault_root_wraps_oserror(monkeypatch, tmp_path) -> None:
    # Simulate an OS-level invalid-path error (e.g. Windows invalid syntax /
    # name too long) during the probe and confirm it becomes a clean ValueError.
    def boom(self: Path) -> bool:
        raise OSError("simulated invalid path syntax")

    monkeypatch.setattr(Path, "exists", boom)
    with pytest.raises(ValueError, match="not a valid path"):
        resolve_vault_root(str(tmp_path))


def test_api_obsidian_malformed_path_is_client_error_not_500() -> None:
    response = client.post("/api/obsidian/import", json={"vault_path": "bad\x00path"})
    assert response.status_code in (400, 422)
    assert response.status_code != 500
    body = response.text
    assert "Traceback" not in body


# --------------------------------------------------------------------------- #
# Intelligence Report is read-only (no store mutation across requests)
# --------------------------------------------------------------------------- #
def test_intelligence_report_does_not_mutate_store() -> None:
    before = client.get("/api/export").json()
    # Generate the report twice; a read-only surface must not change store state.
    assert client.get("/api/intelligence/report").status_code == 200
    assert client.get("/api/intelligence/report").status_code == 200
    after = client.get("/api/export").json()
    assert len(before["sources"]) == len(after["sources"])
    assert len(before["nodes"]) == len(after["nodes"])
    assert len(before["edges"]) == len(after["edges"])


# --------------------------------------------------------------------------- #
# Unhandled exceptions return a clean, client-safe JSON 500 with no leakage
# --------------------------------------------------------------------------- #
def test_unhandled_exception_returns_clean_json_without_leak(monkeypatch) -> None:
    from app.routers import api as api_module

    sentinel = "leak-/secret/internal/path-detail"

    def boom(*args, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(api_module, "build_knowledge_graph", boom)

    # raise_server_exceptions=False so we observe the client-facing response the
    # error handler produces (rather than the re-raised exception for logging).
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/api/knowledge-graph")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    body = response.text
    assert sentinel not in body
    assert "Traceback" not in body
    assert "RuntimeError" not in body
