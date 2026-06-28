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

// Phase 8A/8B/8C "” knowledge graph projection. Mirrors the backend
// KnowledgeGraphResponse wire shape (GET /api/knowledge-graph): the existing
// node/edge record shapes plus a lightweight, deterministic summary block.
export interface KnowledgeGraphSummary {
  node_count: number;
  edge_count: number;
}

export interface KnowledgeGraphResponse {
  nodes: HiveGraphNode[];
  edges: HiveGraphEdge[];
  summary: KnowledgeGraphSummary;
}

// Phase 5A/5B "” Source Registry (future import connectors). Separate from the
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

// Phase 6B/7A "” Obsidian import. Mirrors the backend ObsidianImportRequest and
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

// Phase 10B "” Intelligence contract types / read-only schemas. Mirrors the
// backend Phase 10B shapes in hive_models.py (DreamingSuggestion, DecayStatus,
// ProvenanceChain, QueryTrailEntry). Contract-only: no endpoint, logic, or
// persistence exists yet. Every shape is read-only/advisory and additive.
export type DreamingSuggestionType =
  | "related_nodes"
  | "duplicate"
  | "stale"
  | "missing_backlink"
  | "unresolved_query"
  | "orphan"
  | "source_conflict";

export type DreamingSuggestionStatus =
  | "open"
  | "acknowledged"
  | "dismissed";

export interface DreamingSuggestion {
  id: string;
  type: DreamingSuggestionType;
  status: DreamingSuggestionStatus;
  rationale: string;
  node_ids: string[];
  edge_ids: string[];
  confidence_hint: string | null;
  origin: string;
  metadata: HiveMetadata;
  created_at: string;
}

export type DecayStatusBucket = "fresh" | "aging" | "stale" | "unknown";

export interface DecayStatus {
  node_id: string;
  status: DecayStatusBucket;
  last_imported_at: string | null;
  last_referenced_at: string | null;
  last_updated_at: string | null;
  source_reliability_hint: string | null;
  review_needed: boolean;
  metadata: HiveMetadata;
}

export type ProvenanceLinkKind = "source" | "import" | "node" | "edge";

export type ProvenanceChainStatus = "complete" | "partial" | "unknown";

export interface ProvenanceLink {
  kind: ProvenanceLinkKind;
  ref_id: string;
  label: string | null;
  origin: string | null;
  metadata: HiveMetadata;
}

export interface ProvenanceChain {
  node_id: string;
  id: string | null;
  title: string | null;
  summary: string | null;
  status: ProvenanceChainStatus;
  read_only: boolean;
  source_id: string | null;
  source_name: string | null;
  source_type: RegistrySourceType | null;
  origin_path: string | null;
  links: ProvenanceLink[];
  linked_node_ids: string[];
  derived_edge_ids: string[];
  stored_edge_ids: string[];
  created_at: string | null;
  updated_at: string | null;
  last_imported_at: string | null;
  metadata: HiveMetadata;
}

export type QueryTrailKind = "console" | "search";

export type QueryTrailStatus = "resolved" | "unresolved";

// Phase 16B trail-type / category axis (separate from `kind`, the originating
// surface). Contract-only placeholders for a future derivation/persistence
// phase: no backend logic derives them yet — only demo fixtures may set them.
export type QueryTrailCategory =
  | "repeated_query"
  | "unresolved_question"
  | "related_query_cluster"
  | "source_followup"
  | "knowledge_gap";

export interface QueryTrailEntry {
  id: string;
  query: string;
  kind: QueryTrailKind;
  category: QueryTrailCategory | null;
  status: QueryTrailStatus;
  result_node_ids: string[];
  result_source_ids: string[];
  provenance_chain_ids: string[];
  result_count: number;
  occurrence_count: number;
  pinned: boolean;
  confidence_hint: string | null;
  origin: string;
  last_executed_at: string;
  metadata: HiveMetadata;
}

// Phase 10C/10D "” intelligence report roll-up. Mirrors the backend
// IntelligenceReport / IntelligenceReportSummary wire shapes
// (GET /api/intelligence/report): a stable, read-only projection of the Phase
// 10B contracts above. Deterministic and advisory "” no heuristics run yet.
export interface IntelligenceReportSummary {
  dreaming_suggestion_count: number;
  decay_status_count: number;
  provenance_chain_count: number;
  query_trail_entry_count: number;
}

export interface IntelligenceReport {
  generated_at: string;
  report_version: string;
  read_only: boolean;
  dreaming_suggestions: DreamingSuggestion[];
  decay_statuses: DecayStatus[];
  provenance_chains: ProvenanceChain[];
  query_trail_entries: QueryTrailEntry[];
  summary: IntelligenceReportSummary;
}

