"""Phase 37L - read-only Repository Observer snapshot endpoint.

The router is intentionally thin: it validates HTTP transport input, builds the
existing Phase 37K service request, and returns the existing Phase 37I
``RepositorySnapshot`` contract. Snapshot derivation stays in the service; Git
execution and parsing stay in the adapter.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.models.repository_observer import RepositoryDriftAnalysis, RepositorySnapshot
from app.models.repository_observer_api import (
    RepositoryDriftAnalysisRequest,
    RepositoryObservationSnapshotRequest,
)
from app.services.repository_git_adapter import (
    GitAdapterLimits,
    GitCommandFailedError,
    GitCommandTimeoutError,
    GitExecutableUnavailableError,
    GitOutputLimitExceededError,
    GitPorcelainParseError,
)
from app.services.repository_observation_snapshot import (
    RepositoryObservationScopeError,
    RepositoryObservationSnapshotRequest as SnapshotServiceRequest,
    RepositoryObservationSnapshotService,
)
from app.services.repository_drift_analysis import (
    RepositoryDriftAnalysisRequest as DriftServiceRequest,
    RepositoryDriftAnalysisService,
    RepositoryDriftBaselineError,
    RepositoryDriftPathError,
)

logger = logging.getLogger("hivemind.repository_observer")

router = APIRouter(prefix="/api/repository-observer")


def get_repository_observation_snapshot_service() -> RepositoryObservationSnapshotService:
    """Return a request-usable snapshot service instance."""

    return RepositoryObservationSnapshotService()


def get_repository_drift_analysis_service() -> RepositoryDriftAnalysisService:
    """Return a request-usable drift analysis service instance."""

    return RepositoryDriftAnalysisService()


@router.post("/snapshot", response_model=RepositorySnapshot)
def post_repository_observation_snapshot(
    payload: RepositoryObservationSnapshotRequest,
    service: RepositoryObservationSnapshotService = Depends(
        get_repository_observation_snapshot_service
    ),
) -> RepositorySnapshot:
    """Observe a bounded, read-only repository snapshot through Phase 37K."""

    repository_root = _probe_repository_root(payload.repository_root)
    limits = GitAdapterLimits(
        max_file_observations=payload.max_file_count,
        stdout_bytes=payload.max_snapshot_bytes,
    )
    try:
        return service.observe(
            SnapshotServiceRequest(
                repository_path=repository_root,
                observed_at=payload.observed_at,
                scope=payload.scope,
                limits=limits,
            )
        )
    except RepositoryObservationScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except GitCommandFailedError as exc:
        logger.info("Repository observation rejected by Git adapter: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Repository root is not an observable Git repository",
        )
    except (
        GitCommandTimeoutError,
        GitOutputLimitExceededError,
        GitPorcelainParseError,
    ) as exc:
        logger.info("Repository observation failed within configured bounds: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Repository observation failed within configured bounds",
        )
    except GitExecutableUnavailableError:
        logger.info("Repository observation unavailable because Git is not installed")
        raise HTTPException(
            status_code=503,
            detail="Repository observation capability is unavailable",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Repository access denied")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected repository observation API failure")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/drift", response_model=RepositoryDriftAnalysis)
def post_repository_drift_analysis(
    payload: RepositoryDriftAnalysisRequest,
    service: RepositoryDriftAnalysisService = Depends(
        get_repository_drift_analysis_service
    ),
) -> RepositoryDriftAnalysis:
    """Analyze deterministic, read-only drift from the supported Git baseline."""

    repository_root = _probe_repository_root(payload.repository_root)
    limits = GitAdapterLimits(
        max_file_observations=payload.max_file_count,
        stdout_bytes=payload.max_snapshot_bytes,
    )
    try:
        return service.analyze(
            DriftServiceRequest(
                repository_path=repository_root,
                observed_at=payload.observed_at,
                baseline_reference=payload.baseline_reference,
                max_file_count=payload.max_file_count,
                limits=limits,
            )
        )
    except (RepositoryDriftBaselineError, RepositoryDriftPathError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except GitCommandFailedError as exc:
        logger.info("Repository drift analysis rejected by Git adapter: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Repository root is not an observable Git repository",
        )
    except (
        GitCommandTimeoutError,
        GitOutputLimitExceededError,
        GitPorcelainParseError,
    ) as exc:
        logger.info("Repository drift analysis failed within configured bounds: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Repository drift analysis failed within configured bounds",
        )
    except GitExecutableUnavailableError:
        logger.info("Repository drift analysis unavailable because Git is not installed")
        raise HTTPException(
            status_code=503,
            detail="Repository observation capability is unavailable",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Repository access denied")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected repository drift analysis API failure")
        raise HTTPException(status_code=500, detail="Internal server error")


def _probe_repository_root(repository_root: str) -> Path:
    path = Path(repository_root)
    try:
        exists = path.exists()
        is_directory = path.is_dir() if exists else False
    except PermissionError:
        raise HTTPException(status_code=403, detail="Repository access denied")
    except OSError:
        raise HTTPException(status_code=422, detail="Repository root is malformed")

    if not exists:
        raise HTTPException(status_code=404, detail="Repository root not found")
    if not is_directory:
        raise HTTPException(status_code=400, detail="Repository root is not a directory")
    return path
