"""Phase 37L - read-only Repository Observer API tests."""

from __future__ import annotations

from datetime import datetime
import inspect
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from app.main import app
from app.models.repository_observer import (
    EvidenceAuthority,
    EvidenceCategory,
    FileChangeKind,
    FileContentKind,
    FileObservationCategory,
    FileObservationSummary,
    ObserverLimitation,
    ObserverLimitationCategory,
    ObserverWarning,
    ObserverWarningCategory,
    OverflowLimitKind,
    OverflowMetadata,
    PathRelationship,
    RepositoryEvidence,
    RepositoryIdentity,
    RepositoryIdentityStatus,
    RepositoryRemote,
    RepositorySnapshot,
    SnapshotCompleteness,
    TruncationState,
    WorkingTreeState,
    WorkingTreeStatus,
)
from app.routers import repository_observer as router_module
from app.services.repository_git_adapter import (
    GitCommandFailedError,
    GitCommandTimeoutError,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
)
from app.services.repository_observation_snapshot import (
    RepositoryObservationScopeError,
    RepositoryObservationSnapshotRequest,
)


FIXED_TS = datetime(2026, 7, 18, 14, 0, 0)


class FakeSnapshotService:
    def __init__(
        self,
        snapshot: RepositorySnapshot | None = None,
        error: Exception | None = None,
    ) -> None:
        self.snapshot = snapshot or _snapshot()
        self.error = error
        self.calls: list[RepositoryObservationSnapshotRequest] = []

    def observe(self, request: RepositoryObservationSnapshotRequest) -> RepositorySnapshot:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.snapshot


def _snapshot(
    *,
    states: list[WorkingTreeState] | None = None,
    changed_files: list[FileObservationSummary] | None = None,
    warnings: list[ObserverWarning] | None = None,
    limitations: list[ObserverLimitation] | None = None,
    overflow: list[OverflowMetadata] | None = None,
    completeness: SnapshotCompleteness = SnapshotCompleteness.COMPLETE,
) -> RepositorySnapshot:
    observed_at = FIXED_TS
    evidence = [
        RepositoryEvidence(
            evidence_id="evidence-git-status",
            category=EvidenceCategory.GIT_METADATA,
            authority=EvidenceAuthority.DIRECT_GIT_OUTPUT,
            source="git status --porcelain=v2 -z --branch --untracked-files=all",
            summary="Bounded porcelain-v2 Git status output.",
            bounded_excerpt="# branch.head main",
            excerpt_limit=512,
            captured_at=observed_at,
            truncation_state=(
                TruncationState.TRUNCATED
                if overflow
                else TruncationState.NOT_TRUNCATED
            ),
        )
    ]
    return RepositorySnapshot(
        snapshot_id="snapshot-api-test",
        repository_identity=RepositoryIdentity(
            repository_id="repo-api-test",
            canonical_root="C:/repo",
            normalized_root="c:/repo",
            repository_name="repo",
            remotes=[
                RepositoryRemote(
                    name="origin",
                    url="https://github.com/example/repo.git",
                    normalized_url="github.com/example/repo",
                )
            ],
            primary_remote_url="github.com/example/repo",
            current_branch="main",
            current_commit="abc123",
            status=RepositoryIdentityStatus.VERIFIED,
            warning_ids=[warning.warning_id for warning in warnings or []],
        ),
        observed_at=observed_at,
        observer_version="repo-observer.v1-phase-37k",
        branch="main",
        commit="abc123",
        working_tree=WorkingTreeStatus(states=states or [WorkingTreeState.CLEAN]),
        changed_files=changed_files or [],
        evidence=evidence,
        warnings=warnings or [],
        limitations=limitations
        or [
            ObserverLimitation(
                limitation_id="limitation-metadata-only",
                category=ObserverLimitationCategory.METADATA_ONLY,
                summary="Metadata-only observation.",
            )
        ],
        omitted_paths=["docs/omitted.md"] if overflow else [],
        overflow=overflow or [],
        completeness=completeness,
        read_only=True,
    )


def _file(path: str, kind: FileChangeKind) -> FileObservationSummary:
    relationship = None
    if kind is FileChangeKind.RENAMED:
        relationship = PathRelationship(
            change_kind=kind,
            prior_path="docs/old.md",
            current_path=path,
        )
    if kind is FileChangeKind.COPIED:
        relationship = PathRelationship(
            change_kind=kind,
            prior_path="docs/source.md",
            current_path=path,
        )
    return FileObservationSummary(
        file_id=f"file-{path.replace('/', '-')}",
        repository_relative_path=path,
        normalized_path=path,
        change_kind=kind,
        observation_category=FileObservationCategory.GIT_STATUS,
        content_kind=FileContentKind.UNKNOWN,
        tracked=kind is not FileChangeKind.UNTRACKED,
        staged=kind in (FileChangeKind.RENAMED, FileChangeKind.COPIED),
        path_relationship=relationship,
        evidence_ids=["evidence-git-status"],
    )


def _post_with_service(tmp_path: Path, service: FakeSnapshotService, payload: dict | None = None):
    app.dependency_overrides[
        router_module.get_repository_observation_snapshot_service
    ] = lambda: service
    try:
        request = {
            "repository_root": str(tmp_path),
            "observed_at": FIXED_TS.isoformat(),
        }
        if payload:
            request.update(payload)
        return TestClient(app).post("/api/repository-observer/snapshot", json=request)
    finally:
        app.dependency_overrides.clear()


def test_valid_repository_observation_request_returns_existing_snapshot_structure(tmp_path: Path) -> None:
    service = FakeSnapshotService()
    response = _post_with_service(tmp_path, service)

    assert response.status_code == 200
    body = response.json()
    assert body["repository_identity"]["repository_id"] == "repo-api-test"
    assert body["repository_identity"]["status"] == "verified"
    assert body["working_tree"]["states"] == ["clean"]
    assert body["evidence"][0]["authority"] == "direct_git_output"
    assert body["limitations"][0]["category"] == "metadata_only"
    assert body["completeness"] == "complete"
    assert body["read_only"] is True
    assert len(service.calls) == 1
    assert service.calls[0].repository_path == tmp_path


def test_router_invokes_snapshot_service_without_calling_git_directly(
    monkeypatch, tmp_path: Path
) -> None:
    service = FakeSnapshotService()

    def fail_subprocess(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("router must not invoke subprocess")

    monkeypatch.setattr(subprocess, "run", fail_subprocess)
    response = _post_with_service(tmp_path, service)

    assert response.status_code == 200
    assert len(service.calls) == 1


def test_clean_and_dirty_repository_responses_are_preserved(tmp_path: Path) -> None:
    clean = _post_with_service(
        tmp_path,
        FakeSnapshotService(_snapshot(states=[WorkingTreeState.CLEAN])),
    ).json()
    dirty = _post_with_service(
        tmp_path,
        FakeSnapshotService(
            _snapshot(
                states=[WorkingTreeState.MODIFIED, WorkingTreeState.UNTRACKED],
                changed_files=[
                    _file("apps/backend/app.py", FileChangeKind.MODIFIED),
                    _file("docs/new.md", FileChangeKind.UNTRACKED),
                ],
            )
        ),
    ).json()

    assert clean["working_tree"]["states"] == ["clean"]
    assert dirty["working_tree"]["states"] == ["modified", "untracked"]
    assert [item["change_kind"] for item in dirty["changed_files"]] == [
        "modified",
        "untracked",
    ]


def test_bounded_files_rename_copy_warning_overflow_and_completeness_survive_api(
    tmp_path: Path,
) -> None:
    overflow = [
        OverflowMetadata(
            overflow_id="overflow-file-observations",
            limit_kind=OverflowLimitKind.FILE_COUNT,
            truncated=True,
            configured_limit=2,
            observed_count=4,
            retained_count=2,
            omitted_count=2,
            deterministic_cutoff="first N paths by normalized path",
            snapshot_partial=True,
        )
    ]
    warning = ObserverWarning(
        warning_id="warning-file-limit-reached",
        category=ObserverWarningCategory.FILE_LIMIT_REACHED,
        summary="Changed-file observation count exceeded the configured limit.",
    )
    response = _post_with_service(
        tmp_path,
        FakeSnapshotService(
            _snapshot(
                changed_files=[
                    _file("docs/copied.md", FileChangeKind.COPIED),
                    _file("docs/new.md", FileChangeKind.RENAMED),
                ],
                warnings=[warning],
                overflow=overflow,
                completeness=SnapshotCompleteness.PARTIAL,
            )
        ),
        {"max_file_count": 2},
    )

    assert response.status_code == 200
    body = response.json()
    copied, renamed = body["changed_files"]
    assert copied["path_relationship"]["prior_path"] == "docs/source.md"
    assert renamed["path_relationship"]["prior_path"] == "docs/old.md"
    assert body["warnings"][0]["category"] == "file_limit_reached"
    assert body["overflow"][0]["truncated"] is True
    assert body["evidence"][0]["truncation_state"] == "truncated"
    assert body["omitted_paths"] == ["docs/omitted.md"]
    assert body["completeness"] == "partial"


def test_request_limits_are_passed_to_service(tmp_path: Path) -> None:
    service = FakeSnapshotService()
    response = _post_with_service(
        tmp_path,
        service,
        {"max_file_count": 7, "max_snapshot_bytes": 4096},
    )

    assert response.status_code == 200
    assert service.calls[0].limits.max_file_observations == 7
    assert service.calls[0].limits.stdout_bytes == 4096


def test_validation_rejects_empty_repository_root() -> None:
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={"repository_root": "   ", "observed_at": FIXED_TS.isoformat()},
    )
    assert response.status_code == 422


def test_validation_rejects_parent_traversal_attempt(tmp_path: Path) -> None:
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={
            "repository_root": f"{tmp_path}/../secret",
            "observed_at": FIXED_TS.isoformat(),
        },
    )
    assert response.status_code == 422


def test_validation_rejects_malformed_or_relative_path() -> None:
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={"repository_root": "relative/repo", "observed_at": FIXED_TS.isoformat()},
    )
    assert response.status_code == 422


def test_validation_rejects_unsupported_scope(tmp_path: Path) -> None:
    service = FakeSnapshotService(
        error=RepositoryObservationScopeError(
            "included_paths and excluded_paths are deferred for the snapshot service MVP"
        )
    )
    response = _post_with_service(
        tmp_path,
        service,
        {"scope": {"repository_root": str(tmp_path), "included_paths": ["docs"]}},
    )
    assert response.status_code == 422
    assert "deferred" in response.json()["detail"]


def test_validation_rejects_negative_and_oversized_bounds(tmp_path: Path) -> None:
    client = TestClient(app)
    assert client.post(
        "/api/repository-observer/snapshot",
        json={
            "repository_root": str(tmp_path),
            "observed_at": FIXED_TS.isoformat(),
            "max_file_count": -1,
        },
    ).status_code == 422
    assert client.post(
        "/api/repository-observer/snapshot",
        json={
            "repository_root": str(tmp_path),
            "observed_at": FIXED_TS.isoformat(),
            "max_file_count": 1025,
        },
    ).status_code == 422


def test_validation_rejects_unexpected_request_fields(tmp_path: Path) -> None:
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={
            "repository_root": str(tmp_path),
            "observed_at": FIXED_TS.isoformat(),
            "command": "git status",
        },
    )
    assert response.status_code == 422


def test_repository_not_found_returns_404(tmp_path: Path) -> None:
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={
            "repository_root": str(tmp_path / "missing"),
            "observed_at": FIXED_TS.isoformat(),
        },
    )
    assert response.status_code == 404


def test_non_git_directory_returns_client_safe_400(tmp_path: Path) -> None:
    response = _post_with_service(
        tmp_path,
        FakeSnapshotService(error=GitCommandFailedError("fatal: not a git repository")),
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Repository root is not an observable Git repository"
    }


def test_access_denied_returns_client_safe_403(monkeypatch, tmp_path: Path) -> None:
    def denied(self: Path) -> bool:
        raise PermissionError("C:/secret/token")

    monkeypatch.setattr(router_module.Path, "exists", denied)
    response = TestClient(app).post(
        "/api/repository-observer/snapshot",
        json={"repository_root": str(tmp_path), "observed_at": FIXED_TS.isoformat()},
    )
    assert response.status_code == 403
    assert "secret" not in response.text
    assert "token" not in response.text


def test_expected_adapter_and_service_failures_are_client_safe(tmp_path: Path) -> None:
    for error in (
        GitCommandTimeoutError("raw command timeout C:/secret"),
        GitOutputLimitExceededError("stdout from git status --porcelain exceeded"),
        GitPorcelainParseError("Traceback-ish parser detail"),
    ):
        response = _post_with_service(tmp_path, FakeSnapshotService(error=error))
        assert response.status_code == 502
        body = response.text
        assert "C:/secret" not in body
        assert "git status" not in body
        assert "Traceback" not in body


def test_unexpected_internal_exception_has_no_traceback_or_sensitive_leakage(
    tmp_path: Path,
) -> None:
    response = _post_with_service(
        tmp_path,
        FakeSnapshotService(
            error=RuntimeError(
                "credential=ghp_SUPERSECRET C:/private/.ssh/id_rsa PATH=secret"
            )
        ),
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "ghp_SUPERSECRET" not in response.text
    assert "id_rsa" not in response.text
    assert "PATH=secret" not in response.text
    assert "RuntimeError" not in response.text


def test_router_source_does_not_parse_git_output_or_use_subprocess() -> None:
    source = inspect.getsource(router_module)
    assert "subprocess" not in source
    assert "parse_porcelain" not in source
    assert "git status" not in source
    assert "READ_ONLY_GIT_COMMANDS" not in source


def test_service_dependency_can_be_replaced_in_tests(tmp_path: Path) -> None:
    service = FakeSnapshotService()
    response = _post_with_service(tmp_path, service)

    assert response.status_code == 200
    assert len(service.calls) == 1
