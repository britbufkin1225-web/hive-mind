"""Phase 39A — Repository Evidence Projection contract types.

Bounded request/result shapes for the deterministic projection service in
``app.services.repository_evidence_projection``. The projection consumes
existing Repository Observer results (``app.models.repository_observer``) and
produces *candidate* Active Memory records (``app.models.active_memory``)
without persisting, ingesting, mutating, observing, or exposing anything.

Design rationale:

* **No new wire-contract version.** The request wraps the existing
  ``repo-observer.v1`` input contracts and the result carries existing
  ``active-memory.v1`` records; there is no endpoint and no new wire surface,
  so the result records only a *service* version string (the Phase 37O
  ``observer_version`` convention), not a new contract family.
* **Caller-owned time, distinct axes.** The request carries no clock. The
  *observation* time is the input's own ``snapshot.observed_at`` (and
  ``drift.observed_at`` for drift evidence); the *recording* time is a
  caller-supplied ``recorded_at`` used only as the candidate ``created_at``.
  Observation time and recording time are separate axes (Phase 37A §13 —
  timestamps are never substituted), and the service never reads a clock.
* **Projection-specific bounds are named constants** on a dedicated limits
  model so tests and callers can tighten them without magic literals. The
  closed candidate vocabulary keeps normal file-count growth from ever
  flooding records; bounds exist for explicit, reportable overflow, never for
  silent truncation.
* **Overflow is its own bounded model.** The observer ``OverflowMetadata``
  vocabulary (file counts, snapshot bytes) does not describe projection
  collections, so a small dedicated kind enum is used instead of overloading
  ``OverflowLimitKind.UNKNOWN``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.models.active_memory import (
    MAX_MEMORY_COLLECTION_ITEMS,
    MAX_MEMORY_ID_LENGTH,
    MAX_MEMORY_SUMMARY_LENGTH,
    EvidenceRecord,
    MemoryRecord,
)
from app.models.repository_observer import (
    RepositoryDriftAnalysis,
    RepositorySnapshot,
    SnapshotCompleteness,
)

# Service version, following the Phase 37O ``observer_version`` convention
# ("repo-observer.v1-phase-37o"): provenance of which projection produced a
# result, not a new wire contract.
REPOSITORY_EVIDENCE_PROJECTION_SERVICE_VERSION = "repo-observer.v1-phase-39a"

# Default projection bounds. Small and explicit: the candidate vocabulary is
# closed (at most 14 claims), evidence stays a handful of anchors plus the
# observer's own bounded evidence list, and every overflow is reported.
DEFAULT_MAX_PROJECTED_EVIDENCE_RECORDS = 64
DEFAULT_MAX_PROJECTED_CANDIDATE_RECORDS = 32
DEFAULT_MAX_PROJECTION_WARNINGS = 64
DEFAULT_MAX_PROJECTION_SKIPPED_OBSERVATIONS = 64
DEFAULT_MAX_FILE_PATH_SUMMARY_ITEMS = 16


class ProjectionOverflowKind(StrEnum):
    """Which bounded projection collection exceeded its configured limit."""

    EVIDENCE_RECORD_COUNT = "evidence_record_count"
    CANDIDATE_RECORD_COUNT = "candidate_record_count"
    WARNING_COUNT = "warning_count"
    SKIPPED_OBSERVATION_COUNT = "skipped_observation_count"
    FILE_PATH_SUMMARY_COUNT = "file_path_summary_count"


class ProjectionOverflow(BaseModel):
    """Explicit record of a bounded projection collection exceeding its limit.

    Never silent: the exact omitted count and the documented deterministic
    cutoff rule are always reported.
    """

    overflow_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    kind: ProjectionOverflowKind
    configured_limit: int = Field(ge=0)
    observed_count: int = Field(ge=0)
    retained_count: int = Field(ge=0)
    omitted_count: int = Field(ge=1)
    deterministic_cutoff: str = Field(max_length=MAX_MEMORY_SUMMARY_LENGTH)

    @field_validator("overflow_id", "deterministic_cutoff")
    @classmethod
    def _overflow_text_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("overflow field must not be empty")
        return value.strip()


class RepositoryEvidenceProjectionLimits(BaseModel):
    """Named projection bounds (no magic literals in the service).

    Every bound is capped at ``MAX_MEMORY_COLLECTION_ITEMS`` — the same length
    ceiling the result collections enforce — so an over-large caller limit is
    rejected here, at the contract edge, with a clear validation error instead
    of surfacing as a late, generic Pydantic output-length failure once the
    projected collections are assembled (Phase 39A §9).
    """

    max_evidence_records: int = Field(
        default=DEFAULT_MAX_PROJECTED_EVIDENCE_RECORDS,
        ge=1,
        le=MAX_MEMORY_COLLECTION_ITEMS,
    )
    max_candidate_records: int = Field(
        default=DEFAULT_MAX_PROJECTED_CANDIDATE_RECORDS,
        ge=1,
        le=MAX_MEMORY_COLLECTION_ITEMS,
    )
    max_warnings: int = Field(
        default=DEFAULT_MAX_PROJECTION_WARNINGS, ge=1, le=MAX_MEMORY_COLLECTION_ITEMS
    )
    max_skipped_observations: int = Field(
        default=DEFAULT_MAX_PROJECTION_SKIPPED_OBSERVATIONS,
        ge=1,
        le=MAX_MEMORY_COLLECTION_ITEMS,
    )
    max_file_path_summary_items: int = Field(
        default=DEFAULT_MAX_FILE_PATH_SUMMARY_ITEMS,
        ge=1,
        le=MAX_MEMORY_COLLECTION_ITEMS,
    )


class RepositoryEvidenceProjectionRequest(BaseModel):
    """The narrowest projection input: a project scope plus observer results.

    Deliberately no Git adapter, no repository path to inspect, no command
    executor, and no clock — the projection is a pure transformation over the
    supplied models.

    ``recorded_at`` is the caller-supplied *recording* time used only as the
    deterministic ``created_at`` of projected candidates. It is the narrowest
    appropriate name (it records nothing but the moment of recording) and is
    kept strictly distinct from the observation time carried by the inputs'
    own ``observed_at`` fields: the service never substitutes one for the
    other and never reads a clock (Phase 37A §13, Phase 39A §3).
    """

    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    snapshot: RepositorySnapshot
    drift_analysis: RepositoryDriftAnalysis | None = None
    recorded_at: datetime
    limits: RepositoryEvidenceProjectionLimits = Field(
        default_factory=RepositoryEvidenceProjectionLimits
    )

    @field_validator("project_id")
    @classmethod
    def _project_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("project_id must not be empty")
        return value.strip()


class RepositoryEvidenceProjectionResult(BaseModel):
    """Bounded, deterministic projection output.

    ``candidate_records`` are *candidates only*: nothing here is inserted into
    an Active Memory store, deduplicated against one, contradiction-checked,
    or selected as active state — those remain separate, later concerns.
    """

    projection_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    projection_version: str = REPOSITORY_EVIDENCE_PROJECTION_SERVICE_VERSION
    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    repository_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    source_snapshot_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    source_drift_id: str | None = Field(default=None, max_length=MAX_MEMORY_ID_LENGTH)
    evidence_records: list[EvidenceRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    candidate_records: list[MemoryRecord] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    warnings: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    skipped_observations: list[str] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    completeness: SnapshotCompleteness
    overflow: list[ProjectionOverflow] = Field(
        default_factory=list, max_length=MAX_MEMORY_COLLECTION_ITEMS
    )
    read_only: bool = True

    @field_validator("projection_id", "project_id", "repository_id", "source_snapshot_id")
    @classmethod
    def _result_identifier_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("projection result identifier must not be empty")
        return value.strip()
