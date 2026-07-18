"""Phase 37L - Repository Observer API transport schema.

This request model is the narrow HTTP boundary for the read-only repository
observation snapshot endpoint. The response remains the existing Phase 37I
``RepositorySnapshot`` contract; this module adds no duplicate snapshot,
evidence, warning, limitation, overflow, or completeness models.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
