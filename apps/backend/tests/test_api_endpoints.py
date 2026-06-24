from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_status_returns_system_status() -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "hivemind-backend"
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "sources_count" in data
    assert data["sources_count"] > 0
    assert data["nodes_count"] > 0
    assert data["edges_count"] > 0


def test_vault_returns_counts() -> None:
    response = client.get("/api/vault")
    assert response.status_code == 200
    data = response.json()
    assert "total_sources" in data
    assert "total_nodes" in data
    assert "total_models" in data
    assert data["total_nodes"] > 0
    assert data["status"] == "ok"
    assert data["graph_mode"] == "initialized"


def test_sources_returns_array() -> None:
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0


def test_source_by_id_found() -> None:
    response = client.get("/api/sources/src-dev-markdown")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "src-dev-markdown"
    assert data["type"] == "markdown"


def test_source_by_id_not_found() -> None:
    response = client.get("/api/sources/does-not-exist")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_graph_returns_nodes_and_edges() -> None:
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


def test_graph_nodes_returns_array() -> None:
    response = client.get("/api/graph/nodes")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) > 0


def test_graph_edges_returns_array() -> None:
    response = client.get("/api/graph/edges")
    assert response.status_code == 200
    data = response.json()
    assert "edges" in data
    assert isinstance(data["edges"], list)
    assert len(data["edges"]) > 0


def test_activity_returns_events() -> None:
    response = client.get("/api/activity")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0


def test_models_returns_array() -> None:
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0


def test_export_returns_full_snapshot() -> None:
    response = client.get("/api/export")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "exported_at" in data
    assert "sources" in data
    assert "nodes" in data
    assert "edges" in data
    assert "activity" in data
    assert "models" in data
    assert len(data["sources"]) > 0
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


def test_import_roundtrip() -> None:
    export_resp = client.get("/api/export")
    assert export_resp.status_code == 200
    snapshot = export_resp.json()

    payload = {
        "sources": snapshot["sources"],
        "nodes": snapshot["nodes"],
        "edges": snapshot["edges"],
        "activity": snapshot["activity"],
        "models": snapshot["models"],
    }
    import_resp = client.post("/api/import", json=payload)
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["imported"] is True
    assert data["sources"] == len(snapshot["sources"])
    assert data["nodes"] == len(snapshot["nodes"])
    assert data["edges"] == len(snapshot["edges"])


def test_import_rejects_invalid_edge_node_reference() -> None:
    payload = {
        "sources": [],
        "nodes": [
            {
                "id": "node-a",
                "label": "Node A",
                "type": "concept",
                "tags": [],
                "weight": 1.0,
                "metadata": {},
                "created_at": "2026-06-23T12:00:00Z",
                "updated_at": "2026-06-23T12:00:00Z",
            }
        ],
        "edges": [
            {
                "id": "edge-bad",
                "source_node_id": "node-a",
                "target_node_id": "node-does-not-exist",
                "relationship": "references",
                "weight": 1.0,
                "metadata": {},
                "created_at": "2026-06-23T12:00:00Z",
            }
        ],
        "activity": [],
        "models": [],
    }
    response = client.post("/api/import", json=payload)
    assert response.status_code == 422
    assert "node-does-not-exist" in response.json()["detail"]


def test_obsidian_forward_compat_fields_present_and_default_safe() -> None:
    # Sources expose origin + vault_path placeholders, defaulting to None.
    sources = client.get("/api/sources").json()["sources"]
    assert all("origin" in s and "vault_path" in s for s in sources)
    assert all(s["origin"] is None and s["vault_path"] is None for s in sources)

    # Graph nodes expose a file_meta placeholder, defaulting to None.
    nodes = client.get("/api/graph/nodes").json()["nodes"]
    assert all("file_meta" in n for n in nodes)
    assert all(n["file_meta"] is None for n in nodes)

    # Activity events expose an origin placeholder.
    events = client.get("/api/activity").json()["events"]
    assert all("origin" in e for e in events)

    # Vault exposes vault_path + last_indexed placeholders.
    vault = client.get("/api/vault").json()
    assert "vault_path" in vault and "last_indexed" in vault


def test_obsidian_file_meta_roundtrips_through_import() -> None:
    payload = {
        "sources": [
            {
                "id": "src-obsidian",
                "name": "Vault Source",
                "type": "folder",
                "path": "/vault",
                "status": "active",
                "created_at": "2026-06-23T12:00:00Z",
                "updated_at": "2026-06-23T12:00:00Z",
                "metadata": {},
                "origin": "obsidian",
                "vault_path": "/vault",
            }
        ],
        "nodes": [
            {
                "id": "node-md",
                "label": "Note",
                "type": "file",
                "source_id": "src-obsidian",
                "tags": ["inbox"],
                "weight": 1.0,
                "metadata": {},
                "created_at": "2026-06-23T12:00:00Z",
                "updated_at": "2026-06-23T12:00:00Z",
                "file_meta": {
                    "file_path": "/vault/Note.md",
                    "vault_path": "Note.md",
                    "file_name": "Note.md",
                    "extension": ".md",
                    "frontmatter": {"title": "Note"},
                    "tags": ["inbox"],
                    "backlinks": ["node-other"],
                    "outlinks": [],
                    "last_modified": "2026-06-23T12:00:00Z",
                    "content_hash": "abc123",
                    "origin": "obsidian",
                },
            }
        ],
        "edges": [],
        "activity": [],
        "models": [],
    }
    assert client.post("/api/import", json=payload).status_code == 200

    nodes = client.get("/api/graph/nodes").json()["nodes"]
    imported = next(n for n in nodes if n["id"] == "node-md")
    assert imported["file_meta"]["vault_path"] == "Note.md"
    assert imported["file_meta"]["origin"] == "obsidian"
    assert imported["file_meta"]["backlinks"] == ["node-other"]

    sources = client.get("/api/sources").json()["sources"]
    imported_src = next(s for s in sources if s["id"] == "src-obsidian")
    assert imported_src["origin"] == "obsidian"


def test_health_still_passes() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_vault_summary_legacy_still_passes() -> None:
    response = client.get("/api/vault/summary")
    assert response.status_code == 200
    data = response.json()
    assert "totalFiles" in data
    assert data["graphMode"] == "not_initialized"
