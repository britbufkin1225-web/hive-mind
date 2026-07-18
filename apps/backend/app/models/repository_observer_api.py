"""Phase 37L - Repository Observer API transport schema.

This request model is the narrow HTTP boundary for the read-only repository
observation snapshot endpoint. The response remains the existing Phase 37I
``RepositorySnapshot`` contract; this module adds no duplicate snapshot,
evidence, warning, limitation, overflow, or completeness models.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.repository_observer import (
    MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS,
    MAX_REPOSITORY_OBSERVER_PATH_LENGTH,
    ObserverScope,
)


MAX_REPOSITORY_OBSERVER_API_SNAPSHOT_BYTES = 262_144


class RepositoryObservationSnapshotRequest(BaseModel):
    """Structured input for one deterministic, read-only repository snapshot."""

    model_config = ConfigDict(extra="forbid")

    repository_root: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    observed_at: datetime
    max_file_count: int = Field(
        default=200,
        ge=0,
        le=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS,
    )
    max_snapshot_bytes: int = Field(
        default=MAX_REPOSITORY_OBSERVER_API_SNAPSHOT_BYTES,
        ge=0,
        le=MAX_REPOSITORY_OBSERVER_API_SNAPSHOT_BYTES,
    )
    scope: ObserverScope | None = None

    @field_validator("repository_root")
    @classmethod
    def _repository_root_is_safe_absolute_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("repository_root must not be empty")
        root = value.strip()
        if "\x00" in root:
            raise ValueError("repository_root is malformed")

        windows_path = PureWindowsPath(root)
        posix_path = PurePosixPath(root)
        is_absolute = windows_path.is_absolute() or posix_path.is_absolute()
        if not is_absolute:
            raise ValueError("repository_root must be an absolute local path")

        path_parts = set(windows_path.parts) | set(posix_path.parts)
        if ".." in path_parts:
            raise ValueError("repository_root must not traverse parents")

        return root

    @model_validator(mode="after")
    def _scope_limits_within_api_bounds(self) -> "RepositoryObservationSnapshotRequest":
        # The optional ``ObserverScope`` (Phase 37I) leaves ``max_file_count`` and
        # ``max_snapshot_bytes`` unbounded above, and the Phase 37K service adopts
        # ``scope.max_file_count`` as the retained-observation limit. Without this
        # guard a caller could pass a scope whose limits exceed the API's own
        # ``max_file_count``/``max_snapshot_bytes`` caps, silently bypassing the
        # bound advertised on the top-level request fields. Reject out-of-range
        # scope limits at the transport boundary so both channels honor the same
        # ceiling.
        scope = self.scope
        if scope is None:
            return self
        if scope.max_file_count > MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS:
            raise ValueError(
                "scope.max_file_count must not exceed the request max_file_count bound"
            )
        if scope.max_snapshot_bytes > MAX_REPOSITORY_OBSERVER_API_SNAPSHOT_BYTES:
            raise ValueError(
                "scope.max_snapshot_bytes must not exceed the request max_snapshot_bytes bound"
            )
        return self
