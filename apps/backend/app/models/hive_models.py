from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


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


class HiveSource(BaseModel):
    id: str
    name: str
    type: SourceType
    path: str | None = None
    status: SourceStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


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
