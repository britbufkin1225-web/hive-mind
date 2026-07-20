"""Phase 39B - persistent repository workspace configuration contract.

These are the versioned, local-only shapes that let Hive|Mind remember which
Git repositories an operator uses between sessions. The document is deliberately
minimal: it stores identity and operator intent only, never observation results,
timestamps, credentials, or Active Memory records.

This module defines contract types and bounded validation. It performs no file
I/O, no Git execution, no network access, and no repository mutation. Persistence
and availability probing live in
``app.services.repository_workspace_config``; reusable path/remote normalization
lives in ``app.services.workspace_paths``.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.workspace_paths import (
    remote_has_credentials,
    repository_root_comparison_key,
)

# The persisted document format version. A future incompatible layout increments
# this string; loaders reject any other value rather than guessing.
REPOSITORY_WORKSPACE_SCHEMA_VERSION = "repository-workspaces.v1"

# Bounded identity-bearing field limits. Values that exceed a limit are rejected
# rather than truncated so a workspace identity is never silently corrupted.
MAX_WORKSPACE_ID_LENGTH = 128
MAX_WORKSPACE_DISPLAY_NAME_LENGTH = 256
MAX_REPOSITORY_ROOT_LENGTH = 4096
MAX_EXPECTED_REMOTE_LENGTH = 2048

# Bounded collection / document limits guard against unexpectedly large files.
MAX_WORKSPACE_RECORDS = 256
MAX_WORKSPACE_CONFIG_BYTES = 262_144

# Workspace identifiers are stable, filesystem-safe, and comparison-friendly.
WORKSPACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RepositoryWorkspace(BaseModel):
    """A single registered local repository workspace.

    ``repository_root`` preserves the operator-readable path exactly as supplied
    (NFC-normalized and stripped). Duplicate detection and identity comparison use
    the derived comparison key rather than the display string.
    """

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(min_length=1, max_length=MAX_WORKSPACE_ID_LENGTH)
    display_name: str = Field(min_length=1, max_length=MAX_WORKSPACE_DISPLAY_NAME_LENGTH)
    repository_root: str = Field(min_length=1, max_length=MAX_REPOSITORY_ROOT_LENGTH)
    expected_remote: str | None = Field(
        default=None, max_length=MAX_EXPECTED_REMOTE_LENGTH
    )
    enabled: bool = True

    @field_validator("workspace_id")
    @classmethod
    def _validate_workspace_id(cls, value: str) -> str:
        text = value.strip()
        if not WORKSPACE_ID_PATTERN.fullmatch(text):
            raise ValueError(
                "workspace_id must start alphanumeric and contain only "
                "letters, digits, '.', '_', or '-'"
            )
        return text

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("display_name must not be blank")
        return text

    @field_validator("repository_root")
    @classmethod
    def _validate_repository_root(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("repository_root must not be blank")
        return text

    @field_validator("expected_remote")
    @classmethod
    def _validate_expected_remote(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if remote_has_credentials(text):
            # Credentials/tokens must never be persisted. Reject rather than
            # redact so the operator learns their input was unsafe.
            raise ValueError(
                "expected_remote must not embed credentials or access tokens"
            )
        return text

    @property
    def comparison_key(self) -> str:
        """Canonical key used for duplicate-root detection and identity."""

        return repository_root_comparison_key(self.repository_root)


class RepositoryWorkspaceConfig(BaseModel):
    """The full versioned workspace configuration document."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=REPOSITORY_WORKSPACE_SCHEMA_VERSION)
    active_workspace_id: str | None = None
    workspaces: list[RepositoryWorkspace] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        if value != REPOSITORY_WORKSPACE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version {value!r}; "
                f"expected {REPOSITORY_WORKSPACE_SCHEMA_VERSION!r}"
            )
        return value

    @model_validator(mode="after")
    def _validate_document(self) -> "RepositoryWorkspaceConfig":
        if len(self.workspaces) > MAX_WORKSPACE_RECORDS:
            raise ValueError(
                f"workspace count {len(self.workspaces)} exceeds the "
                f"{MAX_WORKSPACE_RECORDS} record limit"
            )
        seen_ids: set[str] = set()
        seen_roots: dict[str, str] = {}
        for workspace in self.workspaces:
            if workspace.workspace_id in seen_ids:
                raise ValueError(
                    f"duplicate workspace_id {workspace.workspace_id!r}"
                )
            seen_ids.add(workspace.workspace_id)
            key = workspace.comparison_key
            if key in seen_roots:
                raise ValueError(
                    "duplicate repository_root shared by workspaces "
                    f"{seen_roots[key]!r} and {workspace.workspace_id!r}"
                )
            seen_roots[key] = workspace.workspace_id
        if (
            self.active_workspace_id is not None
            and self.active_workspace_id not in seen_ids
        ):
            raise ValueError(
                f"active_workspace_id {self.active_workspace_id!r} does not "
                "match any workspace"
            )
        return self

    def get(self, workspace_id: str) -> RepositoryWorkspace | None:
        for workspace in self.workspaces:
            if workspace.workspace_id == workspace_id:
                return workspace
        return None

    def normalized(self) -> "RepositoryWorkspaceConfig":
        """Return a copy with workspaces ordered deterministically by id."""

        ordered = sorted(self.workspaces, key=lambda item: item.workspace_id)
        return RepositoryWorkspaceConfig(
            schema_version=self.schema_version,
            active_workspace_id=self.active_workspace_id,
            workspaces=ordered,
        )


def empty_config() -> RepositoryWorkspaceConfig:
    """Return a fresh, valid, empty configuration document."""

    return RepositoryWorkspaceConfig(
        schema_version=REPOSITORY_WORKSPACE_SCHEMA_VERSION,
        active_workspace_id=None,
        workspaces=[],
    )
