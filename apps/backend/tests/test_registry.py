from fastapi.testclient import TestClient

from app.main import app
from app.models.hive_models import (
    RegistrySourceStatus,
    RegistrySourceType,
    SourceRecordCreate,
    SourceRecordUpdate,
)
from app.store.registry import SourceRegistry

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Direct store tests (isolated temp files)
# --------------------------------------------------------------------------- #
def fresh_registry(tmp_path) -> SourceRegistry:
    return SourceRegistry(persistence_path=tmp_path / "source-registry.json")


def test_registry_starts_empty(tmp_path) -> None:
    reg = fresh_registry(tmp_path)
    assert reg.list_sources() == []


def test_create_and_get(tmp_path) -> None:
    reg = fresh_registry(tmp_path)
    record = reg.create_source(
        SourceRecordCreate(name="My Vault", type=RegistrySourceType.OBSIDIAN)
    )
    assert record.id.startswith("reg-")
    assert record.status == RegistrySourceStatus.PENDING  # default
    assert record.created_at == record.updated_at
    assert reg.get_source(record.id) == record


def test_update_changes_fields_and_timestamp(tmp_path) -> None:
    reg = fresh_registry(tmp_path)
    record = reg.create_source(
        SourceRecordCreate(name="Repo", type=RegistrySourceType.GITHUB)
    )
    updated = reg.update_source(
        record.id,
        SourceRecordUpdate(status=RegistrySourceStatus.ACTIVE, root_path="/repos/x"),
    )
    assert updated is not None
    assert updated.status == RegistrySourceStatus.ACTIVE
    assert updated.root_path == "/repos/x"
    assert updated.name == "Repo"  # untouched
    assert updated.updated_at >= record.updated_at
    assert updated.created_at == record.created_at


def test_update_missing_returns_none(tmp_path) -> None:
    reg = fresh_registry(tmp_path)
    assert reg.update_source("nope", SourceRecordUpdate(name="x")) is None


def test_persists_across_restart(tmp_path) -> None:
    path = tmp_path / "source-registry.json"
    reg_a = SourceRegistry(persistence_path=path)
    created = reg_a.create_source(
        SourceRecordCreate(name="PDF Set", type=RegistrySourceType.PDF)
    )
    reg_b = SourceRegistry(persistence_path=path)
    assert reg_b.get_source(created.id) is not None


def test_corrupt_file_starts_empty(tmp_path) -> None:
    path = tmp_path / "source-registry.json"
    path.write_text("{ not valid json :::", encoding="utf-8")
    reg = SourceRegistry(persistence_path=path)
    assert reg.list_sources() == []


# --------------------------------------------------------------------------- #
# API tests (via the registry router)
# --------------------------------------------------------------------------- #
def test_api_create_source() -> None:
    response = client.post(
        "/api/registry/sources",
        json={"name": "API Source", "type": "api", "metadata": {"k": "v"}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("reg-")
    assert data["name"] == "API Source"
    assert data["type"] == "api"
    assert data["status"] == "pending"
    assert data["metadata"] == {"k": "v"}
    assert data["last_imported_at"] is None


def test_api_list_sources_contains_created() -> None:
    created = client.post(
        "/api/registry/sources", json={"name": "Listed", "type": "web"}
    ).json()
    response = client.get("/api/registry/sources")
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert isinstance(sources, list)
    assert any(s["id"] == created["id"] for s in sources)


def test_api_get_source_found_and_not_found() -> None:
    created = client.post(
        "/api/registry/sources", json={"name": "Findme", "type": "local_files"}
    ).json()
    found = client.get(f"/api/registry/sources/{created['id']}")
    assert found.status_code == 200
    assert found.json()["id"] == created["id"]

    missing = client.get("/api/registry/sources/does-not-exist")
    assert missing.status_code == 404


def test_api_update_source() -> None:
    created = client.post(
        "/api/registry/sources", json={"name": "Updatable", "type": "obsidian"}
    ).json()
    response = client.patch(
        f"/api/registry/sources/{created['id']}",
        json={"status": "active", "root_path": "/vault"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["root_path"] == "/vault"
    assert data["name"] == "Updatable"


def test_api_update_missing_is_404() -> None:
    response = client.patch(
        "/api/registry/sources/nope", json={"status": "active"}
    )
    assert response.status_code == 404


def test_api_invalid_payloads_are_422() -> None:
    # missing name
    assert client.post("/api/registry/sources", json={"type": "api"}).status_code == 422
    # missing type
    assert client.post("/api/registry/sources", json={"name": "x"}).status_code == 422
    # invalid type
    assert (
        client.post(
            "/api/registry/sources", json={"name": "x", "type": "spreadsheet"}
        ).status_code
        == 422
    )
    # invalid status
    assert (
        client.post(
            "/api/registry/sources",
            json={"name": "x", "type": "api", "status": "running"},
        ).status_code
        == 422
    )
    # blank name
    assert (
        client.post(
            "/api/registry/sources", json={"name": "   ", "type": "api"}
        ).status_code
        == 422
    )


def test_api_update_invalid_status_is_422() -> None:
    created = client.post(
        "/api/registry/sources", json={"name": "Valid", "type": "api"}
    ).json()
    response = client.patch(
        f"/api/registry/sources/{created['id']}", json={"status": "bogus"}
    )
    assert response.status_code == 422
