export type HiveSourceType =
  | "markdown"
  | "text"
  | "json"
  | "folder"
  | "unknown";

export type HiveSourceStatus = "active" | "pending" | "error" | "disabled";

export type HiveGraphNodeType =
  | "root"
  | "folder"
  | "file"
  | "concept"
  | "note"
  | "model"
  | "source";

export type HiveGraphRelationship =
  | "contains"
  | "references"
  | "related"
  | "generated_from"
  | "linked_to";

export type HiveActivityEventType =
  | "system"
  | "source"
  | "graph"
  | "import"
  | "error";

export type HiveActivitySeverity = "info" | "warning" | "error" | "success";

export type HiveSystemStatusValue = "ok" | "degraded" | "error";

export type HiveMetadata = Record<string, unknown>;

export interface HiveGraphPosition {
  x: number;
  y: number;
}

export interface HiveSource {
  id: string;
  name: string;
  type: HiveSourceType;
  path: string | null;
  status: HiveSourceStatus;
  created_at: string;
  updated_at: string;
  metadata: HiveMetadata;
}

export interface HiveGraphNode {
  id: string;
  label: string;
  type: HiveGraphNodeType;
  source_id: string | null;
  parent_id: string | null;
  tags: string[];
  weight: number;
  position: HiveGraphPosition | null;
  metadata: HiveMetadata;
  created_at: string;
  updated_at: string;
}

export interface HiveGraphEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relationship: HiveGraphRelationship;
  weight: number;
  metadata: HiveMetadata;
  created_at: string;
}

export interface HiveActivityEvent {
  id: string;
  timestamp: string;
  event_type: HiveActivityEventType;
  severity: HiveActivitySeverity;
  message: string;
  source_id: string | null;
  node_id: string | null;
  metadata: HiveMetadata;
}

export interface HiveSystemStatus {
  service: string;
  status: HiveSystemStatusValue;
  uptime_seconds: number;
  version: string;
  environment: string;
  sources_count: number;
  nodes_count: number;
  edges_count: number;
  last_updated: string;
}

export interface HiveGraphResponse {
  nodes: HiveGraphNode[];
  edges: HiveGraphEdge[];
  metadata: HiveMetadata;
}

// Phase 5A/5B — Source Registry (future import connectors). Separate from the
// graph's HiveSource resource; mirrors the backend SourceRecord wire shape.
export type RegistrySourceType =
  | "obsidian"
  | "local_files"
  | "github"
  | "pdf"
  | "web"
  | "api";

export type RegistrySourceStatus =
  | "active"
  | "inactive"
  | "error"
  | "pending";

export interface SourceRecord {
  id: string;
  name: string;
  type: RegistrySourceType;
  root_path: string | null;
  status: RegistrySourceStatus;
  last_imported_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: HiveMetadata;
}

export interface SourceRegistryListResponse {
  sources: SourceRecord[];
}

// Phase 6B/7A — Obsidian import. Mirrors the backend ObsidianImportRequest and
// ObsidianImportSummary wire shapes (POST /api/obsidian/import).
export interface ObsidianImportRequest {
  vault_path: string;
  source_name?: string | null;
}

/** Compact linkage from an import run back to its Source Registry record. */
export interface ImportedSourceRef {
  id: string;
  name: string;
  type: RegistrySourceType;
  status: RegistrySourceStatus;
  root_path: string | null;
  last_imported_at: string | null;
}

export interface ObsidianImportSummary {
  source_id: string | null;
  source_name: string | null;
  source: ImportedSourceRef | null;
  vault_path: string;
  imported_count: number;
  updated_count: number;
  skipped_count: number;
  duplicate_count: number;
  error_count: number;
  link_count: number;
  imported_node_ids: string[];
  warnings: string[];
  notes: string[];
}
