"""Phase 39D - Repository Observer end-to-end hardening + failure-state QA.

Unlike ``test_repository_observer_api.py`` (which overrides the service with an
in-memory fake) and ``test_repository_drift_analysis.py`` (which calls the
service directly), these tests drive the **real** router -> snapshot/drift
service -> Git adapter path over HTTP against a **real** temporary Git
repository. They verify the composed workflow the operator actually exercises:
deterministic evidence, credential-safe output, and correct handling of clean,
dirty, detached-HEAD, unborn, and non-repository states.

Every repository is created under pytest's ``tmp_path`` and is fully
self-contained; no test mutates the canonical Hive|Mind repository.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app


FIXED_TS = datetime(2026, 7, 21, 12, 0, 0)
SNAPSHOT_URL = "/api/repository-observer/snapshot"
DRIFT_URL = "/api/repository-observer/drift"

# A deliberately secret-shaped token embedded in a remote URL. It must never
# survive into any API response; the redaction is asserted against the full
# serialized body so a leak anywhere (structured field, excerpt, warning) fails.
SECRET_TOKEN = "ghp_E2ETESTONLYSECRET0000"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_repo(tmp_path: Path, *, with_commit: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", str(repo)], shell=False, check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "tester@example.invalid")
    _git(repo, "config", "user.name", "Test User")
    if with_commit:
        _write(repo / "README.md", "hello\n")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-m", "initial")
    return repo


def _snapshot_payload(repo: Path, **overrides: object) -> dict:
    payload: dict = {
        "repository_root": str(repo),
        "observed_at": FIXED_TS.isoformat(),
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_clean_repository_snapshot_is_observable_and_deterministic(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path)

    first = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))
    second = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))

    assert first.status_code == 200
    assert second.status_code == 200
    body = first.json()
    assert body["working_tree"]["states"] == ["clean"]
    assert body["changed_files"] == []
    assert body["read_only"] is True
    assert body["completeness"] == "complete"
    # Two identical requests against an unchanged repository must produce a
    # byte-for-byte identical response (no wall-clock or nondeterministic
    # ordering leaks into the snapshot).
    assert first.json() == second.json()


def test_dirty_repository_is_evidence_not_an_application_error(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path)
    _write(repo / "README.md", "hello changed\n")
    _write(repo / "staged.md", "staged\n")
    _git(repo, "add", "staged.md")
    _write(repo / "untracked.md", "loose\n")

    response = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))

    # A dirty tree is a successful observation (HTTP 200), never a 4xx/5xx.
    assert response.status_code == 200
    body = response.json()
    states = set(body["working_tree"]["states"])
    assert "clean" not in states
    assert {"modified", "staged", "untracked"} & states
    observed = {f["repository_relative_path"] for f in body["changed_files"]}
    assert {"README.md", "staged.md", "untracked.md"} <= observed


def test_credential_bearing_remote_is_redacted_end_to_end(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path)
    _git(
        repo,
        "remote",
        "add",
        "origin",
        f"https://{SECRET_TOKEN}@github.com/acme/widget.git",
    )

    response = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))

    assert response.status_code == 200
    # The secret must not appear anywhere in the serialized response...
    assert SECRET_TOKEN not in response.text
    # ...while the non-sensitive remote identity is preserved for the operator.
    remotes = response.json()["repository_identity"]["remotes"]
    assert any(r["url"] == "https://github.com/acme/widget.git" for r in remotes)


def test_detached_head_is_observable_with_a_warning(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "-c", "advice.detachedHead=false", "checkout", head)

    response = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))

    assert response.status_code == 200
    body = response.json()
    assert body["repository_identity"]["operation_state"] == "detached"
    assert body["branch"] is None
    warning_ids = {w["warning_id"] for w in body["warnings"]}
    assert "warning-detached-head" in warning_ids


def test_repository_without_commits_is_observable(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path, with_commit=False)

    response = client.post(SNAPSHOT_URL, json=_snapshot_payload(repo))

    assert response.status_code == 200
    body = response.json()
    assert body["commit"] is None
    warning_ids = {w["warning_id"] for w in body["warnings"]}
    assert "warning-unborn-branch" in warning_ids


def test_non_git_directory_returns_client_safe_400(
    client: TestClient, tmp_path: Path
) -> None:
    plain = tmp_path / "not-a-repo"
    plain.mkdir()

    response = client.post(SNAPSHOT_URL, json=_snapshot_payload(plain))

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Repository root is not an observable Git repository"
    }


def test_drift_clean_and_dirty_are_deterministic_over_real_git(
    client: TestClient, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path)

    clean_first = client.post(DRIFT_URL, json=_snapshot_payload(repo))
    clean_second = client.post(DRIFT_URL, json=_snapshot_payload(repo))
    assert clean_first.status_code == 200
    assert clean_first.json()["drift_status"] == "clean"
    assert clean_first.json() == clean_second.json()

    _write(repo / "README.md", "hello changed\n")
    dirty = client.post(DRIFT_URL, json=_snapshot_payload(repo))
    assert dirty.status_code == 200
    dirty_body = dirty.json()
    assert dirty_body["drift_status"] != "clean"
    assert dirty_body["read_only"] is True
    assert any(
        f["current_path"] == "README.md" for f in dirty_body["files"]
    )
