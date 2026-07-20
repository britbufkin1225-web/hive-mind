"""Phase 39B - operator CLI behavior, exit codes, and JSON output."""

from __future__ import annotations

import json

import pytest

from app.console import repository_workspace_cli as cli
from app.services.repository_workspace_config import WORKSPACE_CONFIG_ENV


def _run(capsys, argv: list[str]) -> tuple[int, dict | None, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    payload = None
    if "--json" in argv and captured.out.strip():
        payload = json.loads(captured.out.strip().splitlines()[-1])
    return code, payload, captured.out + captured.err


def _cfg(tmp_path) -> list[str]:
    return ["--config-path", str(tmp_path / "repository-workspaces.json")]


def test_path_reports_resolution(tmp_path, capsys) -> None:
    code, payload, _ = _run(capsys, ["--json", *_cfg(tmp_path), "path"])
    assert code == cli.EXIT_OK
    assert payload["exists"] is False
    assert payload["config_path"].endswith("repository-workspaces.json")


def test_init_list_add_show_flow(tmp_path, capsys) -> None:
    assert _run(capsys, ["--json", *_cfg(tmp_path), "init"])[0] == cli.EXIT_OK
    add_argv = [
        "--json",
        *_cfg(tmp_path),
        "add",
        "--id",
        "hive-mind",
        "--name",
        "Hive Mind",
        "--repository-root",
        str(tmp_path / "hive-mind"),
        "--activate",
    ]
    code, payload, _ = _run(capsys, add_argv)
    assert code == cli.EXIT_OK
    assert payload["workspace"]["workspace_id"] == "hive-mind"

    code, payload, _ = _run(capsys, ["--json", *_cfg(tmp_path), "list"])
    assert code == cli.EXIT_OK
    assert payload["active_workspace_id"] == "hive-mind"
    assert len(payload["workspaces"]) == 1

    code, payload, _ = _run(
        capsys, ["--json", *_cfg(tmp_path), "show", "--id", "hive-mind"]
    )
    assert code == cli.EXIT_OK
    assert payload["active"] is True


def test_set_active_and_validate(tmp_path, capsys) -> None:
    _run(
        capsys,
        [
            *_cfg(tmp_path),
            "add",
            "--id",
            "a",
            "--name",
            "A",
            "--repository-root",
            str(tmp_path / "a"),
        ],
    )
    assert _run(capsys, [*_cfg(tmp_path), "set-active", "--id", "a"])[0] == cli.EXIT_OK
    code, payload, _ = _run(capsys, ["--json", *_cfg(tmp_path), "validate"])
    assert code == cli.EXIT_OK
    assert payload["active_workspace_id"] == "a"
    assert payload["workspace_count"] == 1


def test_duplicate_add_exits_operation_error(tmp_path, capsys) -> None:
    base = [
        *_cfg(tmp_path),
        "add",
        "--id",
        "a",
        "--name",
        "A",
        "--repository-root",
        str(tmp_path / "a"),
    ]
    assert _run(capsys, base)[0] == cli.EXIT_OK
    code, _, _ = _run(capsys, ["--json", *base])
    assert code == cli.EXIT_OPERATION_ERROR


def test_credential_remote_rejected(tmp_path, capsys) -> None:
    argv = [
        "--json",
        *_cfg(tmp_path),
        "add",
        "--id",
        "a",
        "--name",
        "A",
        "--repository-root",
        str(tmp_path / "a"),
        "--expected-remote",
        "https://user:token@github.com/x/y.git",
    ]
    code, payload, _ = _run(capsys, argv)
    assert code == cli.EXIT_OPERATION_ERROR
    assert payload["error"] == "CredentialBearingRemoteError"


def test_malformed_config_validate_exits_operation_error(tmp_path, capsys) -> None:
    path = tmp_path / "repository-workspaces.json"
    path.write_text("{broken", encoding="utf-8")
    code, _, _ = _run(capsys, ["--json", *_cfg(tmp_path), "validate"])
    assert code == cli.EXIT_OPERATION_ERROR


def test_show_missing_workspace_exits_operation_error(tmp_path, capsys) -> None:
    _run(capsys, [*_cfg(tmp_path), "init"])
    code, payload, _ = _run(capsys, ["--json", *_cfg(tmp_path), "show", "--id", "ghost"])
    assert code == cli.EXIT_OPERATION_ERROR
    assert payload["error"] == "WorkspaceNotFoundError"


def test_invalid_env_override_exits_usage_error(monkeypatch, capsys) -> None:
    monkeypatch.setenv(WORKSPACE_CONFIG_ENV, "   ")
    code, payload, _ = _run(capsys, ["--json", "path"])
    assert code == cli.EXIT_USAGE_ERROR
    assert payload["error"] == "WorkspaceConfigPathError"
