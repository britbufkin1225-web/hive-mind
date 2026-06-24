from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SourceType(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    FOLDER = "folder"
    UNKNOWN = "unknown"


class SourceStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    ERROR = "error"
    DISABLED = "disabled"


class GraphNodeType(StrEnum):
    ROOT = "root"
    FOLDER = "folder"
    FILE = "file"
    CONCEPT = "concept"
    NOTE = "note"
    MODEL = "model"
    SOURCE = "source"


class GraphRelationship(StrEnum):
    CONTAINS = "contains"
    REFERENCES = "references"
    RELATED = "related"
    GENERATED_FROM = "generated_from"
    LINKED_TO = "linked_to"


class ActivityEventType(StrEnum):
    SYSTEM = "system"
    SOURCE = "source"
    GRAPH = "graph"
    IMPORT = "import"
    ERROR = "error"


class ActivitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class SystemStatusValue(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class GraphPosition(BaseModel):
    x: float
    y: float


class VaultFileMeta(BaseModel):
    """Placeholder for future Obsidian vault mapping.

    Phase 3A defines these fields for forward compatibility only. Nothing in
    this phase scans a filesystem, parses markdown/frontmatter, watches files,
    or runs a vault import. All fields are optional and default to empty so
    existing in-memory/seed data remains valid. A future Obsidian phase can
    populate these without changing the wire shape.
    """

    file_path: str | None = None  # absolute or source-relative path on disk
    vault_path: str | None = None  # path relative to the Obsidian vault root
    file_name: str | None = None
    extension: str | None = None  # e.g. ".md"
    frontmatter: dict[str, Any] = Field(default_factory=dict)  # parsed YAML placeholder
    tags: list[str] = Field(default_factory=list)
    backlinks: list[str] = Field(default_factory=list)  # incoming [[wikilinks]] placeholder
    outlinks: list[str] = Field(default_factory=list)  # outgoing [[wikilinks]] placeholder
    last_modified: datetime | None = None
    content_hash: str | None = None  # e.g. sha256 of file contents placeholder
    origin: str | None = None  # source provider, e.g. "obsidian", "upload", "manual"


class HiveSource(BaseModel):
    id: str
    name: str
    type: SourceType
    path: str | None = None
    status: SourceStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Obsidian forward-compatibility (placeholders, not populated in Phase 3A)
    origin: str | None = None  # provider this source came from, e.g. "obsidian"
    vault_path: str | None = None  # vault root or relative path for vault-backed sources


class HiveGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    source_id: str | None = None
    parent_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    weight: float = 1.0
    position: GraphPosition | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    # Obsidian forward-compatibility (placeholder, not populated in Phase 3A)
    file_meta: VaultFileMeta | None = None


class HiveGraphEdge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relationship: GraphRelationship
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class HiveActivityEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: ActivityEventType
    severity: ActivitySeverity
    message: str
    source_id: str | None = None
    node_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Obsidian forward-compatibility (placeholder, not populated in Phase 3A)
    origin: str | None = None  # provider that emitted the event, e.g. "obsidian"


class HiveSystemStatus(BaseModel):
    service: str
    status: SystemStatusValue
    uptime_seconds: int
    version: str
    environment: str
    sources_count: int
    nodes_count: int
    edges_count: int
    last_updated: datetime


class HiveGraphResponse(BaseModel):
    nodes: list[HiveGraphNode]
    edges: list[HiveGraphEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelStatus(StrEnum):
    AVAILABLE = "available"
    LOADING = "loading"
    UNAVAILABLE = "unavailable"


class HiveModel(BaseModel):
    id: str
    name: str
    provider: str = "local"
    status: ModelStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class HiveVault(BaseModel):
    total_files: int
    total_sources: int
    total_models: int
    total_nodes: int
    graph_mode: str
    status: str
    # Obsidian forward-compatibility (placeholders, not populated in Phase 3A)
    vault_path: str | None = None  # filesystem root of a future linked Obsidian vault
    last_indexed: datetime | None = None  # timestamp of last vault index run


class HiveExportSnapshot(BaseModel):
    version: str
    exported_at: datetime
    sources: list[HiveSource]
    nodes: list[HiveGraphNode]
    edges: list[HiveGraphEdge]
    activity: list[HiveActivityEvent]
    models: list[HiveModel]


class HiveImportRequest(BaseModel):
    sources: list[HiveSource] = Field(default_factory=list)
    nodes: list[HiveGraphNode] = Field(default_factory=list)
    edges: list[HiveGraphEdge] = Field(default_factory=list)
    activity: list[HiveActivityEvent] = Field(default_factory=list)
    models: list[HiveModel] = Field(default_factory=list)


class SourcesResponse(BaseModel):
    sources: list[HiveSource]


class GraphNodesResponse(BaseModel):
    nodes: list[HiveGraphNode]


class GraphEdgesResponse(BaseModel):
    edges: list[HiveGraphEdge]


class ActivityResponse(BaseModel):
    events: list[HiveActivityEvent]


class ModelsResponse(BaseModel):
    models: list[HiveModel]


class ImportResponse(BaseModel):
    imported: bool
    sources: int
    nodes: int
    edges: int
    activity: int
    models: int


class ConsoleExecuteRequest(BaseModel):
    command: str


class ConsoleExecuteResponse(BaseModel):
    ok: bool
    command: str
    result: dict[str, Any] | None = None
    error: str | None = None


# --------------------------------------------------------------------------- #
# Phase 5A — Source Registry
#
# A registry of future *import connectors* (Obsidian, local files, GitHub, PDF,
# web, API). This is intentionally separate from the graph's `HiveSource`/
# `/api/sources` resource and does NOT implement any import/scanning logic.
# --------------------------------------------------------------------------- #
class RegistrySourceType(StrEnum):
    OBSIDIAN = "obsidian"
    LOCAL_FILES = "local_files"
    GITHUB = "github"
    PDF = "pdf"
    WEB = "web"
    API = "api"


class RegistrySourceStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class SourceRecord(BaseModel):
    id: str
    name: str
    type: RegistrySourceType
    root_path: str | None = None
    status: RegistrySourceStatus = RegistrySourceStatus.PENDING
    last_imported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRecordCreate(BaseModel):
    name: str
    type: RegistrySourceType
    root_path: str | None = None
    status: RegistrySourceStatus = RegistrySourceStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()


class SourceRecordUpdate(BaseModel):
    name: str | None = None
    type: RegistrySourceType | None = None
    root_path: str | None = None
    status: RegistrySourceStatus | None = None
    last_imported_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be empty")
        return value.strip() if value is not None else None


class SourceRegistryListResponse(BaseModel):
    sources: list[SourceRecord]


# --------------------------------------------------------------------------- #
# Phase 6A — Obsidian Adapter Contract
#
# Contract/planning shapes for a *future* Obsidian vault adapter. Nothing in
# this phase reads a vault, scans the filesystem, parses markdown, or watches
# files. These models define the wire/contract shapes only so a later import
# phase can be built without destabilizing the backend.
# --------------------------------------------------------------------------- #
class ObsidianLinkStrategy(StrEnum):
    WIKILINK = "wikilink"
    MARKDOWN = "markdown"
    BOTH = "both"


class ObsidianVaultConfig(BaseModel):
    """Configuration shape for a future Obsidian vault adapter.

    Contract only: `root_path` is a declared value, not a verified location on
    disk. No code in this phase opens, scans, or watches the path.
    """

    vault_id: str
    name: str
    root_path: str
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    tag_prefix: str | None = None
    link_strategy: ObsidianLinkStrategy = ObsidianLinkStrategy.BOTH
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObsidianDocumentCandidate(BaseModel):
    """Normalized document an Obsidian adapter *would* emit in a future phase.

    Defined now for forward-compatibility. No code in Phase 6A produces these.
    """

    source_id: str
    source_path: str
    title: str
    content_preview: str | None = None
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Phase 6B — Obsidian Import MVP
#
# Request/response shapes for a one-shot, backend-only import of markdown files
# from an explicitly provided Obsidian vault path into the graph store. The
# import never mutates the user's vault files; it only reads them.
# --------------------------------------------------------------------------- #
class ObsidianImportRequest(BaseModel):
    """Request to import an explicit local Obsidian vault path (one-shot)."""

    vault_path: str
    source_name: str | None = None


class ObsidianImportSummary(BaseModel):
    """Deterministic summary of a single Obsidian import run."""

    source_id: str | None = None
    vault_path: str
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    imported_node_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
