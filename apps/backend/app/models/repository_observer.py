"""Phase 37I - Repository Observer contract types.

Contract/schema-alignment only. These are stable wire models for the future
Repository Observer planned in
``docs/planning/phase-37h-repository-observer-planning.md``. This module adds no
filesystem traversal, Git command execution, repository polling, persistence,
API routes, Active Memory ingestion, contradiction logic, or runtime observer
behavior. It defines bounded, read-only shapes only.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

REPOSITORY_OBSERVER_CONTRACT_VERSION = "repo-observer.v1"

MAX_REPOSITORY_OBSERVER_ID_LENGTH = 256
MAX_REPOSITORY_OBSERVER_LABEL_LENGTH = 512
MAX_REPOSITORY_OBSERVER_PATH_LENGTH = 2048
MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH = 2048
MAX_REPOSITORY_OBSERVER_EXCERPT_LENGTH = 8192
MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS = 1024


class RepositoryIdentityStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MISMATCHED_ROOT = "mismatched_root"
    MISMATCHED_REMOTE = "mismatched_remote"
    MISSING_GIT_METADATA = "missing_git_metadata"
    UNSAFE_LOCATION = "unsafe_location"


class RepositoryOperationState(StrEnum):
    NORMAL = "normal"
    MERGING = "merging"
    REBASING = "rebasing"
    CHERRY_PICKING = "cherry_picking"
    BISECTING = "bisecting"
    DETACHED = "detached"
    BARE = "bare"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class WorkingTreeState(StrEnum):
    CLEAN = "clean"
    MODIFIED = "modified"
    STAGED = "staged"
    UNTRACKED = "untracked"
    CONFLICTED = "conflicted"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class FileChangeKind(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    UNTRACKED = "untracked"
    CONFLICTED = "conflicted"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class FileObservationCategory(StrEnum):
    GIT_STATUS = "git_status"
    FILE_METADATA = "file_metadata"
    BOUNDED_TEXT_EXCERPT = "bounded_text_excerpt"
    REPOSITORY_CONFIGURATION = "repository_configuration"
    EXCLUSION_RECORD = "exclusion_record"
    UNSUPPORTED_DATA = "unsupported_data"
    UNKNOWN = "unknown"


class FileContentKind(StrEnum):
    TEXT = "text"
    BINARY = "binary"
    SYMLINK = "symlink"
    DIRECTORY = "directory"
    SUBMODULE = "submodule"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class EvidenceCategory(StrEnum):
    GIT_METADATA = "git_metadata"
    WORKING_TREE_METADATA = "working_tree_metadata"
    FILE_METADATA = "file_metadata"
    BOUNDED_TEXT_EXCERPT = "bounded_text_excerpt"
    REPOSITORY_CONFIGURATION = "repository_configuration"
    VALIDATION_RESULT = "validation_result"
    EXCLUSION_RECORD = "exclusion_record"
    EXTERNALLY_SUPPLIED_CLAIM = "externally_supplied_claim"
    UNSUPPORTED_DATA = "unsupported_data"


class EvidenceAuthority(StrEnum):
    DIRECT_GIT_OUTPUT = "direct_git_output"
    DIRECT_FILESYSTEM_METADATA = "direct_filesystem_metadata"
    PARSED_REPOSITORY_DOCUMENT = "parsed_repository_document"
    VALIDATED_EXECUTION_SOURCE = "validated_execution_source"
    USER_SUPPLIED_STATEMENT = "user_supplied_statement"
    AGENT_GENERATED_SUMMARY = "agent_generated_summary"
    UNSUPPORTED_ASSUMPTION = "unsupported_assumption"
    UNAVAILABLE_INFORMATION = "unavailable_information"


class TruncationState(StrEnum):
    NOT_TRUNCATED = "not_truncated"
    TRUNCATED = "truncated"
    OMITTED = "omitted"
    UNKNOWN = "unknown"


class ObserverWarningCategory(StrEnum):
    REPOSITORY_IDENTITY_MISMATCH = "repository_identity_mismatch"
    UNSAFE_REPOSITORY_PATH = "unsafe_repository_path"
    INACCESSIBLE_PATH = "inaccessible_path"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    BINARY_CONTENT_OMITTED = "binary_content_omitted"
    IGNORED_CONTENT_OMITTED = "ignored_content_omitted"
    EXCLUDED_PATH = "excluded_path"
    EVIDENCE_TRUNCATED = "evidence_truncated"
    FILE_LIMIT_REACHED = "file_limit_reached"
    BYTE_LIMIT_REACHED = "byte_limit_reached"
    EVIDENCE_LIMIT_REACHED = "evidence_limit_reached"
    GIT_METADATA_UNAVAILABLE = "git_metadata_unavailable"
    PARTIAL_SNAPSHOT = "partial_snapshot"
    OBSERVER_CAPABILITY_UNAVAILABLE = "observer_capability_unavailable"
    TIMESTAMP_AMBIGUITY = "timestamp_ambiguity"
    UNKNOWN_OBSERVER_ERROR = "unknown_observer_error"


class ObserverLimitationCategory(StrEnum):
    METADATA_ONLY = "metadata_only"
    FILE_CONTENTS_NOT_ALLOWED = "file_contents_not_allowed"
    IGNORED_FILES_NOT_INCLUDED = "ignored_files_not_included"
    UNTRACKED_FILES_NOT_INCLUDED = "untracked_files_not_included"
    BINARY_FILES_NOT_INCLUDED = "binary_files_not_included"
    EXCLUDED_PATHS_APPLIED = "excluded_paths_applied"
    BOUNDED_COLLECTION = "bounded_collection"
    UNSUPPORTED_DATA = "unsupported_data"
    UNAVAILABLE_INFORMATION = "unavailable_information"


class OverflowLimitKind(StrEnum):
    FILE_COUNT = "file_count"
    EVIDENCE_COUNT = "evidence_count"
    TEXT_BYTES = "text_bytes"
    SNAPSHOT_BYTES = "snapshot_bytes"
    WARNING_COUNT = "warning_count"
    LIMITATION_COUNT = "limitation_count"
    UNKNOWN = "unknown"


class SnapshotCompleteness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    REJECTED = "rejected"


def _clean_identifier(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


def _validate_relative_path(value: str) -> str:
    value = _clean_identifier(value, "repository-relative path")
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError("repository-relative path must not be absolute")
    if len(normalized) >= 2 and normalized[1] == ":":
        raise ValueError("repository-relative path must not include a drive")
    parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("repository-relative path must not traverse parents")
    if any(part == "." for part in parts):
        raise ValueError("repository-relative path must not contain '.' segments")
    if not parts:
        raise ValueError("repository-relative path must not be empty")
    return normalized


class RepositoryRemote(BaseModel):
    name: str = Field(max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH)
    url: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    normalized_url: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH
    )

    @field_validator("name", "url")
    @classmethod
    def _required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "remote field")


class RepositoryIdentity(BaseModel):
    repository_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    canonical_root: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    normalized_root: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    repository_name: str = Field(max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH)
    remotes: list[RepositoryRemote] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    primary_remote_url: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH
    )
    current_branch: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH
    )
    current_commit: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH
    )
    upstream_reference: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH
    )
    default_branch: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH
    )
    operation_state: RepositoryOperationState = RepositoryOperationState.UNKNOWN
    status: RepositoryIdentityStatus = RepositoryIdentityStatus.UNVERIFIED
    warning_ids: list[str] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )

    @field_validator("repository_id", "canonical_root", "normalized_root", "repository_name")
    @classmethod
    def _identity_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "repository identity field")


class ObserverScope(BaseModel):
    repository_root: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    included_paths: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    max_file_count: int = Field(default=200, ge=0)
    max_evidence_entries: int = Field(default=200, ge=0)
    max_text_bytes: int = Field(default=0, ge=0)
    max_snapshot_bytes: int = Field(default=262_144, ge=0)
    include_untracked_files: bool = False
    include_ignored_files: bool = False
    include_binary_files: bool = False
    allow_file_contents: bool = False
    metadata_only: bool = True

    @field_validator("repository_root")
    @classmethod
    def _repository_root_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "repository_root")

    @field_validator("included_paths", "excluded_paths")
    @classmethod
    def _paths_are_relative(cls, value: list[str]) -> list[str]:
        return [_validate_relative_path(item) for item in value]

    @model_validator(mode="after")
    def _metadata_only_cannot_allow_contents(self) -> "ObserverScope":
        if self.metadata_only and self.allow_file_contents:
            raise ValueError("metadata_only scope cannot allow file contents")
        if not self.allow_file_contents and self.max_text_bytes > 0:
            raise ValueError("max_text_bytes requires allow_file_contents")
        return self


class WorkingTreeStatus(BaseModel):
    states: list[WorkingTreeState] = Field(default_factory=lambda: [WorkingTreeState.UNKNOWN])
    staged_count: int = Field(default=0, ge=0)
    unstaged_count: int = Field(default=0, ge=0)
    untracked_count: int = Field(default=0, ge=0)
    conflicted_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _clean_state_stands_alone(self) -> "WorkingTreeStatus":
        if WorkingTreeState.CLEAN in self.states and len(set(self.states)) > 1:
            raise ValueError("clean working-tree state cannot coexist with dirty states")
        return self


class PathRelationship(BaseModel):
    change_kind: FileChangeKind
    prior_path: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    current_path: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)

    @field_validator("prior_path", "current_path")
    @classmethod
    def _relationship_paths_are_relative(cls, value: str) -> str:
        return _validate_relative_path(value)

    @model_validator(mode="after")
    def _relationship_matches_change_kind(self) -> "PathRelationship":
        if self.change_kind not in (FileChangeKind.RENAMED, FileChangeKind.COPIED):
            raise ValueError("path relationships are only valid for renamed or copied files")
        if self.prior_path == self.current_path:
            raise ValueError("path relationship requires different prior and current paths")
        return self


class FileObservationSummary(BaseModel):
    file_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    repository_relative_path: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    normalized_path: str = Field(max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    change_kind: FileChangeKind = FileChangeKind.UNKNOWN
    observation_category: FileObservationCategory = FileObservationCategory.UNKNOWN
    size_bytes: int | None = Field(default=None, ge=0)
    content_kind: FileContentKind = FileContentKind.UNKNOWN
    tracked: bool | None = None
    ignored: bool | None = None
    staged: bool | None = None
    content_digest: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH
    )
    path_relationship: PathRelationship | None = None
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    omission_reason: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH
    )
    warning_ids: list[str] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )

    @field_validator("file_id")
    @classmethod
    def _file_id_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "file_id")

    @field_validator("repository_relative_path", "normalized_path")
    @classmethod
    def _file_paths_are_relative(cls, value: str) -> str:
        return _validate_relative_path(value)

    @model_validator(mode="after")
    def _relationship_required_for_rename_or_copy(self) -> "FileObservationSummary":
        if self.change_kind in (FileChangeKind.RENAMED, FileChangeKind.COPIED):
            if self.path_relationship is None:
                raise ValueError("renamed or copied files require a path relationship")
            if self.path_relationship.change_kind != self.change_kind:
                raise ValueError("path relationship change kind must match file change kind")
        if self.path_relationship is not None and self.change_kind not in (
            FileChangeKind.RENAMED,
            FileChangeKind.COPIED,
        ):
            raise ValueError("path relationship is only valid for renamed or copied files")
        return self


class RepositoryEvidence(BaseModel):
    evidence_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    category: EvidenceCategory
    authority: EvidenceAuthority
    source: str = Field(max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH)
    repository_relative_path: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH
    )
    summary: str = Field(max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH)
    bounded_excerpt: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_EXCERPT_LENGTH
    )
    excerpt_limit: int | None = Field(default=None, ge=0)
    digest: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH
    )
    captured_at: datetime | None = None
    truncation_state: TruncationState = TruncationState.NOT_TRUNCATED
    omission_reason: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH
    )
    related_file_ids: list[str] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )

    @field_validator("evidence_id", "source", "summary")
    @classmethod
    def _evidence_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "evidence field")

    @field_validator("repository_relative_path")
    @classmethod
    def _evidence_path_is_relative(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_relative_path(value)

    @model_validator(mode="after")
    def _excerpt_must_be_explicitly_bounded(self) -> "RepositoryEvidence":
        if self.bounded_excerpt is not None:
            if self.excerpt_limit is None:
                raise ValueError("bounded_excerpt requires excerpt_limit")
            if len(self.bounded_excerpt) > self.excerpt_limit:
                raise ValueError("bounded_excerpt must not exceed excerpt_limit")
        return self


class ObserverWarning(BaseModel):
    warning_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    category: ObserverWarningCategory
    summary: str = Field(max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH)
    path: str | None = Field(default=None, max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)
    evidence_ids: list[str] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )

    @field_validator("warning_id", "summary")
    @classmethod
    def _warning_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "warning field")

    @field_validator("path")
    @classmethod
    def _warning_path_is_relative(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_relative_path(value)


class ObserverLimitation(BaseModel):
    limitation_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    category: ObserverLimitationCategory
    summary: str = Field(max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH)
    path: str | None = Field(default=None, max_length=MAX_REPOSITORY_OBSERVER_PATH_LENGTH)

    @field_validator("limitation_id", "summary")
    @classmethod
    def _limitation_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "limitation field")

    @field_validator("path")
    @classmethod
    def _limitation_path_is_relative(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_relative_path(value)


class OverflowMetadata(BaseModel):
    overflow_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    limit_kind: OverflowLimitKind
    truncated: bool = False
    configured_limit: int = Field(ge=0)
    observed_count: int | None = Field(default=None, ge=0)
    observed_size_bytes: int | None = Field(default=None, ge=0)
    retained_count: int = Field(default=0, ge=0)
    omitted_count: int | None = Field(default=None, ge=0)
    deterministic_cutoff: str = Field(max_length=MAX_REPOSITORY_OBSERVER_SUMMARY_LENGTH)
    snapshot_partial: bool = False

    @field_validator("overflow_id", "deterministic_cutoff")
    @classmethod
    def _overflow_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "overflow field")

    @model_validator(mode="after")
    def _overflow_counts_are_possible(self) -> "OverflowMetadata":
        if self.omitted_count is not None and not self.truncated and self.omitted_count > 0:
            raise ValueError("omitted_count requires truncated overflow metadata")
        if self.truncated and self.omitted_count == 0:
            raise ValueError("truncated overflow must omit at least one item when known")
        if self.observed_count is not None:
            omitted = self.omitted_count or 0
            if self.retained_count + omitted > self.observed_count:
                raise ValueError("retained and omitted counts cannot exceed observed_count")
        if self.snapshot_partial and not self.truncated:
            raise ValueError("snapshot_partial overflow metadata requires truncation")
        return self


class RepositorySnapshot(BaseModel):
    snapshot_id: str = Field(max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH)
    contract_version: str = REPOSITORY_OBSERVER_CONTRACT_VERSION
    repository_identity: RepositoryIdentity
    observed_at: datetime
    observer_version: str = REPOSITORY_OBSERVER_CONTRACT_VERSION
    branch: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_LABEL_LENGTH
    )
    commit: str | None = Field(
        default=None, max_length=MAX_REPOSITORY_OBSERVER_ID_LENGTH
    )
    working_tree: WorkingTreeStatus = Field(default_factory=WorkingTreeStatus)
    changed_files: list[FileObservationSummary] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    evidence: list[RepositoryEvidence] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    warnings: list[ObserverWarning] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    limitations: list[ObserverLimitation] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    omitted_paths: list[str] = Field(default_factory=list)
    overflow: list[OverflowMetadata] = Field(
        default_factory=list, max_length=MAX_REPOSITORY_OBSERVER_COLLECTION_ITEMS
    )
    deterministic_ordering: list[str] = Field(
        default_factory=lambda: [
            "paths_by_normalized_path",
            "evidence_by_authority_category_id",
            "warnings_by_category_id",
            "limitations_by_category_id",
            "overflow_by_limit_kind_id",
        ]
    )
    completeness: SnapshotCompleteness = SnapshotCompleteness.UNAVAILABLE
    read_only: bool = True

    @field_validator("snapshot_id", "contract_version", "observer_version")
    @classmethod
    def _snapshot_required_text_not_blank(cls, value: str) -> str:
        return _clean_identifier(value, "snapshot field")

    @field_validator("omitted_paths")
    @classmethod
    def _omitted_paths_are_relative(cls, value: list[str]) -> list[str]:
        return [_validate_relative_path(item) for item in value]

    @model_validator(mode="after")
    def _completeness_matches_overflow(self) -> "RepositorySnapshot":
        has_partial_overflow = any(item.snapshot_partial for item in self.overflow)
        has_truncation = any(item.truncated for item in self.overflow)
        if self.completeness is SnapshotCompleteness.COMPLETE and (
            has_partial_overflow or has_truncation
        ):
            raise ValueError("complete snapshots cannot contain truncation metadata")
        if has_partial_overflow and self.completeness is not SnapshotCompleteness.PARTIAL:
            raise ValueError("partial overflow requires partial snapshot completeness")
        return self
