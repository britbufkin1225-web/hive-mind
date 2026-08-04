"""Phase 40K.5 — read-only readiness CLI tests."""
from __future__ import annotations

import json
from pathlib import Path

from app.console.migration_readiness_cli import (
    EXIT_BLOCKED,
    EXIT_FAIL_CLOSED,
    EXIT_OPERATION_ERROR,
    EXIT_PASS,
    EXIT_USAGE_ERROR,
    main,
)
from test_migration_readiness_preflight import verified_manifest_dict

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs" / "operations" / "phase-40k-readiness.template.json"
)
FIXED_NOW = "2026-08-03T00:00:00Z"


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_template_is_blocked(capsys):
    code = main(["preflight", "--manifest", str(TEMPLATE_PATH), "--now", FIXED_NOW])
    assert code == EXIT_BLOCKED
    assert "outcome: blocked" in capsys.readouterr().out


def test_cli_verified_manifest_passes_json(tmp_path, capsys):
    path = _write(tmp_path, verified_manifest_dict())
    code = main(["preflight", "--manifest", str(path), "--now", FIXED_NOW, "--json"])
    assert code == EXIT_PASS
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "pass"
    assert payload["manifest_identity"].startswith("mm-readiness-")


def test_cli_malformed_manifest_is_fail_closed(tmp_path, capsys):
    raw = verified_manifest_dict()
    raw["unexpected"] = "x"
    path = _write(tmp_path, raw)
    code = main(["preflight", "--manifest", str(path), "--now", FIXED_NOW])
    assert code == EXIT_FAIL_CLOSED


def test_cli_missing_file_is_operation_error(tmp_path):
    code = main(["preflight", "--manifest", str(tmp_path / "nope.json"), "--now", FIXED_NOW])
    assert code == EXIT_OPERATION_ERROR


def test_cli_invalid_json_is_operation_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    code = main(["preflight", "--manifest", str(path), "--now", FIXED_NOW])
    assert code == EXIT_OPERATION_ERROR


def test_cli_invalid_now_is_usage_error(tmp_path):
    path = _write(tmp_path, verified_manifest_dict())
    code = main(["preflight", "--manifest", str(path), "--now", "not-a-time"])
    assert code == EXIT_USAGE_ERROR


def test_cli_output_carries_no_secret_like_text(tmp_path, capsys):
    raw = verified_manifest_dict()
    raw["authorization"]["non_secret_authorization_id"] = "bearer sk-supersecret000111222"
    path = _write(tmp_path, raw)
    code = main(["preflight", "--manifest", str(path), "--now", FIXED_NOW, "--json"])
    assert code == EXIT_FAIL_CLOSED
    out = capsys.readouterr().out
    assert "supersecret" not in out
