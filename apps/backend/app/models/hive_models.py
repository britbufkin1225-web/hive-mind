from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.validation import (
    MAX_REQUEST_NESTING_DEPTH,
    assert_within_nesting_depth,
)

# --------------------------------------------------------------------------- #
# Phase 18B — defensive upper bounds for client-supplied free-text fields.
#
# These guard the write/POST surface against pathologically large inputs without
# constraining any realistic value. Oversized input is rejected with a
# deterministic 422 at the contract boundary, before any downstream processing
# (shlex parsing, filesystem path resolution, persistence) runs. The bounds are
# additive: every existing valid request stays valid. No minimum length is added
# so existing empty/blank handling (graceful console errors, 400 on empty vault
# path) is preserved.
# --------------------------------------------------------------------------- #
MAX_CONSOLE_COMMAND_LENGTH = 4096
MAX_VAULT_PATH_LENGTH = 4096
MAX_SOURCE_NAME_LENGTH = 512
MAX_ROOT_PATH_LENGTH = 4096


# --------------------------------------------------------------------------- #
# Phase 18E — bounded request-body nesting-depth guard.
#
# Phase 18B bounded individual free-text fields; it could not see request
# *shape*. A deeply nested object (``{"a": {"a": {"a": ...}}}``) is a structural
# edge that lands in a free-form ``metadata`` dict (or in the nested lists of a
# snapshot import) and would otherwise be traversed before any field guard runs.
# This mixin rejects an over-depth body at the contract edge with a clean 422,
# before downstream processing, using the shared iterative guard in
# ``app.services.validation`` (see ``MAX_REQUEST_NESTING_DEPTH`` for the bound and
# rationale). It is applied only to the POST/PATCH request models that accept a
# free-form nested structure; read-only response models and flat request models
# (e.g. ``ConsoleExecuteRequest``, ``ObsidianImportRequest``) have no nestable
# field and are left untouched. The guard is additive: every realistic body
# stays well under the bound, and the 422 it raises matches the existing
# Phase 18B validation-error shape.
# --------------------------------------------------------------------------- #
class _NestingDepthGuardedModel(BaseModel):
    """Mixin: reject request bodies nested deeper than ``MAX_REQUEST_NESTING_DEPTH``."""

    @model_validator(mode="before")
    @classmethod
    def _enforce_nesting_depth(cls, data: Any) -> Any:
        assert_within_nesting_depth(data, MAX_REQUEST_NESTING_DEPTH)
        return data


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


class HiveImportRequest(_NestingDepthGuardedModel):
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
    command: str = Field(max_length=MAX_CONSOLE_COMMAND_LENGTH)


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


class SourceRecordCreate(_NestingDepthGuardedModel):
    name: str = Field(max_length=MAX_SOURCE_NAME_LENGTH)
    type: RegistrySourceType
    root_path: str | None = Field(default=None, max_length=MAX_ROOT_PATH_LENGTH)
    status: RegistrySourceStatus = RegistrySourceStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()


class SourceRecordUpdate(_NestingDepthGuardedModel):
    name: str | None = Field(default=None, max_length=MAX_SOURCE_NAME_LENGTH)
    type: RegistrySourceType | None = None
    root_path: str | None = Field(default=None, max_length=MAX_ROOT_PATH_LENGTH)
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

    vault_path: str = Field(max_length=MAX_VAULT_PATH_LENGTH)
    source_name: str | None = Field(default=None, max_length=MAX_SOURCE_NAME_LENGTH)


class ImportedSourceRef(BaseModel):
    """Stable linkage from an import run back to its Source Registry record.

    A compact, frontend-friendly slice of the registered ``SourceRecord`` so a
    caller can show the imported source without a second registry lookup. The
    ``status`` mirrors the registry record's status after the run completes.
    """

    id: str
    name: str
    type: RegistrySourceType = RegistrySourceType.OBSIDIAN
    status: RegistrySourceStatus
    root_path: str | None = None
    last_imported_at: datetime | None = None


class ObsidianImportSummary(BaseModel):
    """Deterministic summary of a single Obsidian import run.

    Counts are mutually exclusive per note: a scanned ``.md`` file lands in
    exactly one of ``imported_count`` (new node), ``updated_count`` (existing
    node refreshed), ``skipped_count`` (e.g. empty content), ``duplicate_count``
    (a second file resolving to an already-seen node id within this run), or
    ``error_count`` (read/parse failure). ``imported_node_ids`` lists every node
    written to the store (new + updated) so re-imports stay deterministic.

    ``source`` is the Source Registry linkage for this run (the registered
    Obsidian source), or ``None`` if registry wiring was unavailable.
    ``link_count`` is the total number of wiki/markdown references captured
    across imported notes (not yet materialized as edges in this phase).
    """

    source_id: str | None = None
    source_name: str | None = None
    source: ImportedSourceRef | None = None
    vault_path: str
    imported_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    link_count: int = 0
    imported_node_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase 8A — Knowledge Graph API foundation
#
# Graph-shaped contracts derived deterministically from the existing stored /
# imported knowledge records. These are read/projection shapes built by the
# graph builder (``app/services/knowledge_graph.py``) and served from
# ``GET /api/knowledge-graph``. They reuse the established ``HiveGraphNode`` /
# ``HiveGraphEdge`` record shapes and add a lightweight summary block. No AI /
# "dreaming" connections are produced in this phase.
# --------------------------------------------------------------------------- #
class KnowledgeGraphSummary(BaseModel):
    """Deterministic counts for a built knowledge graph."""

    node_count: int = 0
    edge_count: int = 0


class KnowledgeGraphResponse(BaseModel):
    """Stable graph-shaped response: nodes, edges, and summary counts.

    The shape is stable even when there is no graph data — ``nodes`` and
    ``edges`` default to empty lists and ``summary`` to zeroed counts so a
    future frontend graph view can consume it unconditionally.
    """

    nodes: list[HiveGraphNode] = Field(default_factory=list)
    edges: list[HiveGraphEdge] = Field(default_factory=list)
    summary: KnowledgeGraphSummary = Field(default_factory=KnowledgeGraphSummary)


# --------------------------------------------------------------------------- #
# Phase 10B — Intelligence Contract Types / Read-Only Schemas
#
# Contract-only shapes for the first Tier-1 intelligence surfaces planned in
# docs/intelligence-surface-plan.md (Phase 10A): Dreaming suggestions, temporal
# decay status, provenance chains, and query trails. These define the agreed
# wire shapes ONLY — exactly as Phase 2 defined the API contract before any
# logic. This phase adds:
#   * NO endpoints or router wiring
#   * NO scoring/heuristics, decay calculation, or provenance engine
#   * NO persistence or store changes
#
# Per the intelligence-layer principles, every shape here is read-only and
# additive: it describes *derived, advisory* output that is shown for review and
# never mutates graph/source/import data. Derived output carries an explicit
# ``origin`` marker, mirroring how the graph builder tags derived edges.
# --------------------------------------------------------------------------- #
class DreamingSuggestionType(StrEnum):
    """Canonical Dreaming suggestion types.

    Members follow the project convention: an ``UPPER_SNAKE`` member name whose
    serialized value is the ``snake_case`` string. Because this is a ``StrEnum``,
    the serialized API value is the string literal below — that is the value the
    frontend ``DreamingSuggestionType`` union and the panel label map key on, so
    the literals here are the stable wire contract.

    Notes:

    * The source-related type is ``source_conflict`` ("notes from different
      sources that disagree"). There is intentionally no ``source_coverage_gap``
      value — no derivation exists for one and adding it would duplicate the same
      concept space without a producer.
    * ``unresolved_query`` is reserved but **blocked/planned**: it depends on
      persisted query history, which does not exist yet. No derivation or fixture
      produces it, and no ``unresolved_query_pattern`` variant is added until that
      persistence lands.
    """

    RELATED_NODES = "related_nodes"
    DUPLICATE = "duplicate"
    STALE = "stale"
    MISSING_BACKLINK = "missing_backlink"
    UNRESOLVED_QUERY = "unresolved_query"  # planned/blocked: needs query history
    ORPHAN = "orphan"
    SOURCE_CONFLICT = "source_conflict"


class DreamingSuggestionStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


class DreamingSuggestion(BaseModel):
    """A single read-only Dreaming suggestion (advisory, never applied).

    Derived per-request from current store/graph state and shown for review. It
    references existing nodes/edges by id but never mutates them. ``status``
    captures the review-only lifecycle (``open`` -> ``acknowledged``/
    ``dismissed``); an "apply" action that would create real graph data is
    explicitly out of scope for this phase. ``confidence_hint`` is a lightweight
    human-readable label only — a numeric confidence model is deferred (Tier 2),
    so the field name stays ``confidence_hint`` (never ``confidence``).

    Supporting evidence (referenced records, matched snippets, scores) attaches
    under ``metadata.evidence`` rather than a dedicated top-level field, keeping
    the contract additive — ``metadata`` is the free-form, forward-compatible bag
    used across the API.
    """

    id: str
    type: DreamingSuggestionType
    status: DreamingSuggestionStatus = DreamingSuggestionStatus.OPEN
    rationale: str
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    confidence_hint: str | None = None
    origin: str = "dreaming"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DecayStatusBucket(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class DecayStatus(BaseModel):
    """Read-only freshness view derived over an existing node's timestamps.

    Phase 10B defines the representation only; no decay calculation runs here.
    ``status`` defaults to ``unknown`` (e.g. when timestamps are missing) and
    ``review_needed`` is a derived boolean that feeds the dashboard rollup.
    ``source_reliability_hint`` is a lightweight label derived from source
    type/status, not a trust engine. This adds no new authoritative state.
    """

    node_id: str
    status: DecayStatusBucket = DecayStatusBucket.UNKNOWN
    last_imported_at: datetime | None = None
    last_referenced_at: datetime | None = None
    last_updated_at: datetime | None = None
    source_reliability_hint: str | None = None
    review_needed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceLinkKind(StrEnum):
    SOURCE = "source"
    IMPORT = "import"
    NODE = "node"
    EDGE = "edge"


class ProvenanceChainStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ProvenanceLink(BaseModel):
    """One step in a provenance chain (registry source -> import run -> node).

    ``origin`` mirrors the existing ``metadata.origin`` marker so a consumer can
    tell derived links (e.g. graph-builder ``references`` edges) from stored
    ones. Contract only: this references existing records by id; it does not
    resolve or verify them.
    """

    kind: ProvenanceLinkKind
    ref_id: str
    label: str | None = None
    origin: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceChain(BaseModel):
    """Read-only "where did this come from?" view for a selected node/edge.

    Presents already-captured fields together: the source chain, origin path,
    immediate neighbors, derived vs. stored edges, and update history. Phase 10B
    makes no provenance-engine changes and adds no new authoritative state.
    Relationship confidence is reserved for Tier 2 and intentionally omitted.
    """

    node_id: str
    id: str | None = None
    title: str | None = None
    summary: str | None = None
    status: ProvenanceChainStatus = ProvenanceChainStatus.UNKNOWN
    read_only: bool = True
    source_id: str | None = None
    source_name: str | None = None
    source_type: RegistrySourceType | None = None
    origin_path: str | None = None
    links: list[ProvenanceLink] = Field(default_factory=list)
    linked_node_ids: list[str] = Field(default_factory=list)
    derived_edge_ids: list[str] = Field(default_factory=list)
    stored_edge_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_imported_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryTrailKind(StrEnum):
    CONSOLE = "console"
    SEARCH = "search"


class QueryTrailStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class QueryTrailCategory(StrEnum):
    """Trail-type / category axis for a Query Trail entry.

    Phase 16B contract-alignment axis describing *what kind of query-memory
    pattern* an entry represents, separate from ``kind`` (the originating
    surface: console vs. search). Members follow the project convention: an
    ``UPPER_SNAKE`` member name whose serialized ``StrEnum`` value is the
    ``snake_case`` literal below — those literals are the stable wire contract
    the frontend ``QueryTrailCategory`` union keys on.

    These categories are **contract-only placeholders** for a later
    derivation/persistence phase. No backend logic derives them yet; only
    deterministic demo fixtures may set them. They intentionally mirror the
    future concepts named in the Phase 16A plan and must not be read as evidence
    that query history is persisted. ``unresolved_question`` is the query-trail
    analogue of the still-blocked Dreaming ``unresolved_query`` type and likewise
    does not imply persisted history.
    """

    REPEATED_QUERY = "repeated_query"
    UNRESOLVED_QUESTION = "unresolved_question"
    RELATED_QUERY_CLUSTER = "related_query_cluster"
    SOURCE_FOLLOWUP = "source_followup"
    KNOWLEDGE_GAP = "knowledge_gap"


class QueryTrailEntry(BaseModel):
    """A single read-only entry in the query memory / knowledge trail.

    Describes a past console/search interaction and where it led. No query
    persistence runs (deferred to a dedicated phase); this is the target shape
    only. ``status`` marks whether the query surfaced anything (``unresolved``
    feeds Dreaming's "unresolved query patterns"), ``occurrence_count`` supports
    repeated-question detection, and ``pinned`` marks a user-saved useful query.

    Phase 16B aligns this contract toward future persisted query history without
    requiring it yet. The added fields are additive and default-safe so existing
    fixtures and any future persisted record validate unchanged:

    * ``category`` — the trail-type axis (:class:`QueryTrailCategory`), separate
      from ``kind`` (the originating surface). ``None`` until a record is
      explicitly classified; no derivation assigns it in this phase.
    * ``result_source_ids`` / ``provenance_chain_ids`` — id-only references that
      let a trail link out to the Source Registry and derived provenance chains
      (mirroring the Phase 16A relationship plan). References only; this contract
      never resolves, mutates, or copies the linked records.
    * ``confidence_hint`` — a lightweight human-readable label only, matching
      :class:`DreamingSuggestion`. A numeric ``confidence`` model is deferred
      (Tier 2), so the field name stays ``confidence_hint`` (never
      ``confidence``).
    * ``origin`` — derived/surface origin marker (mirrors
      ``DreamingSuggestion.origin``) advertising read-only query-trail output.

    Supporting evidence/reason metadata continues to attach under
    ``metadata`` (e.g. ``metadata.evidence``), keeping the contract additive.
    """

    id: str
    query: str
    kind: QueryTrailKind = QueryTrailKind.SEARCH
    category: QueryTrailCategory | None = None
    status: QueryTrailStatus = QueryTrailStatus.RESOLVED
    result_node_ids: list[str] = Field(default_factory=list)
    result_source_ids: list[str] = Field(default_factory=list)
    provenance_chain_ids: list[str] = Field(default_factory=list)
    result_count: int = 0
    occurrence_count: int = 1
    pinned: bool = False
    confidence_hint: str | None = None
    origin: str = "query_trail"
    last_executed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Phase 10C — Intelligence Report API foundation
#
# A read-only report shape that surfaces the Phase 10B intelligence contracts
# (Dreaming suggestions, decay statuses, provenance chains, query trails)
# through a single stable endpoint (``GET /api/intelligence/report``). This is
# the contract/foundation only — exactly like Phase 8A wrapped the existing
# record shapes in ``KnowledgeGraphResponse`` before any algorithm ran. This
# phase adds NO scoring/heuristics, decay calculation, provenance engine, query
# persistence, or AI ("dreaming") logic; the report is deterministic and, in the
# absence of any derived intelligence data, returns a valid empty state (empty
# lists + zeroed counts) so a future frontend can consume it unconditionally.
# --------------------------------------------------------------------------- #
class IntelligenceReportSummary(BaseModel):
    """Deterministic per-section counts for an intelligence report."""

    dreaming_suggestion_count: int = 0
    decay_status_count: int = 0
    provenance_chain_count: int = 0
    query_trail_entry_count: int = 0


class IntelligenceReport(BaseModel):
    """Stable, read-only roll-up of the Phase 10B intelligence contracts.

    The shape is stable even when there is no derived intelligence data — every
    section defaults to an empty list and ``summary`` to zeroed counts. No real
    Dreaming / Temporal Decay / provenance heuristics run in this phase, so the
    report content is deterministic; only ``generated_at`` reflects request time
    (mirroring ``HiveSystemStatus.last_updated`` / ``HiveExportSnapshot``).
    ``read_only`` advertises that this endpoint never mutates store state.
    """

    generated_at: datetime
    report_version: str = "0.1.0"
    read_only: bool = True
    dreaming_suggestions: list[DreamingSuggestion] = Field(default_factory=list)
    decay_statuses: list[DecayStatus] = Field(default_factory=list)
    provenance_chains: list[ProvenanceChain] = Field(default_factory=list)
    query_trail_entries: list[QueryTrailEntry] = Field(default_factory=list)
    summary: IntelligenceReportSummary = Field(default_factory=IntelligenceReportSummary)
