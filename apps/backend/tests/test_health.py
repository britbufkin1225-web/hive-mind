from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_api_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "hivemind-backend",
        "version": "0.1.0",
    }


def test_root_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "hivemind-backend",
        "version": "0.1.0",
    }