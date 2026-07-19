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

// ------------------------------------------------------------------------- //
// Phase 37B — Active Agent Memory + Verification Layer contract types.
//
// Mirrors the backend Phase 37B shapes in
// `apps/backend/app/models/active_memory.py` exactly (same snake_case wire
// values, same property names, datetimes as ISO-8601 strings, `dict` as
// HiveMetadata, Optional as `| null`). Contract-only: no endpoint, store,
// persistence, ingestion, contradiction/active-state/packet logic, or UI exists
// yet. Every enum value below is the stable wire contract and must stay
// byte-for-byte identical to the backend StrEnum values. Rationale for each
// design decision lives in docs/active-agent-memory-verification-layer.md.
// ------------------------------------------------------------------------- //

/** Stable wire version for the whole active-memory contract family. */
export const ACTIVE_MEMORY_CONTRACT_VERSION = "active-memory.v1";

// Closed record categories (backend MemoryRecordKind).
export type MemoryRecordKind =
  | "project_fact"
  | "project_decision"
  | "project_constraint"
  | "phase_status"
  | "repository_state"
  | "capability";

// Belief axis — kept separate from LifecycleState (backend VerificationState).
export type VerificationState =
  | "unverified"
  | "partially_verified"
  | "verified"
  | "human_confirmed"
  | "contradicted"
  | "unresolvable";

// In-force axis — kept separate from VerificationState (backend LifecycleState).
export type LifecycleState =
  | "active"
  | "inactive"
  | "superseded"
  | "retracted"
  | "stale"
  | "archived";

// Qualitative confidence band, separate from verification (backend ConfidenceBand).
export type ConfidenceBand = "low" | "medium" | "high";

// How to interpret a claim's bounded scalar value (backend ClaimValueKind).
export type ClaimValueKind =
  | "string"
  | "boolean"
  | "integer"
  | "float"
  | "timestamp"
  | "identifier"
  | "enum";

// Closed scope axis (backend MemoryScopeType).
export type MemoryScopeType =
  | "project"
  | "repository"
  | "branch"
  | "phase"
  | "feature"
  | "component"
  | "session";

// Source identity category — carries NO trust signal (backend MemorySourceType).
export type MemorySourceType =
  | "human"
  | "claude_code"
  | "codex"
  | "chatgpt"
  | "cli_report"
  | "repository_observer"
  | "ci_system"
  | "imported_document"
  | "unknown";

// Closed evidence categories, not equal in strength (backend EvidenceType).
export type EvidenceType =
  | "human_confirmation"
  | "repository_command_output"
  | "commit"
  | "branch"
  | "pull_request"
  | "test_output"
  | "ci_output"
  | "runtime_api_response"
  | "source_code"
  | "source_controlled_doc"
  | "structured_cli_report"
  | "structured_agent_report"
  | "screenshot"
  | "video"
  | "conversational_summary"
  | "inferred_context";

// Bounded, inspectable evidence-reference pointer kinds (backend
// EvidenceReferenceKind). No raw-command / arbitrary-path kind by design.
export type EvidenceReferenceKind =
  | "commit_hash"
  | "branch_name"
  | "pull_request_number"
  | "file_path"
  | "symbol_reference"
  | "command_id"
  | "test_run_id"
  | "source_record_id"
  | "artifact_id"
  | "external_source_id";

// Supersession/retraction link kinds. Only `supersedes`/`retracts` are stored;
// `superseded_by`/`retracted_by` are derived inverses (backend SupersessionKind).
export type SupersessionKind =
  | "supersedes"
  | "superseded_by"
  | "retracts"
  | "retracted_by";

// The five Phase 37D MVP contradiction classes (backend ContradictionClass).
export type ContradictionClass =
  | "duplicate_phase_status"
  | "pending_vs_merged"
  | "frontend_only_vs_backend_modification"
  | "current_vs_superseded_decision"
  | "clean_vs_dirty_working_tree";

// Contradiction resolution lifecycle (backend ContradictionResolutionState).
export type ContradictionResolutionState = "open" | "resolved" | "archived";

// Optional contradiction impact band (backend ContradictionSeverity).
export type ContradictionSeverity = "info" | "warning" | "critical";

// Per-slot active-state result — never a boolean (backend ActiveStateResult).
export type ActiveStateResult =
  | "active"
  | "inactive"
  | "unresolved"
  | "no_eligible_record";

export interface MemoryScope {
  scope_type: MemoryScopeType;
  scope_id: string;
}

export interface MemorySource {
  source_type: MemorySourceType;
  source_id: string;
  display_label: string | null;
  session_id: string | null;
}

export interface MemoryClaim {
  subject: string;
  predicate: string;
  value: string;
  value_kind: ClaimValueKind;
  summary: string | null;
}

export interface EvidenceReference {
  reference_kind: EvidenceReferenceKind;
  value: string;
  detail: string | null;
}

export interface SupersessionReference {
  kind: SupersessionKind;
  target_record_id: string;
  reason: string | null;
  created_at: string;
}

export interface VerificationMetadata {
  state: VerificationState;
  checked_at: string | null;
  checker: MemorySource | null;
  evidence_ids: string[];
  note: string | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  evidence_type: EvidenceType;
  reference: EvidenceReference;
  scope: MemoryScope | null;
  source: MemorySource | null;
  captured_at: string;
  valid_until: string | null;
  summary: string | null;
  metadata: HiveMetadata;
}

export interface MemoryRecord {
  record_id: string;
  kind: MemoryRecordKind;
  claim: MemoryClaim;
  project_id: string;
  scope: MemoryScope | null;
  source: MemorySource;
  verification_state: VerificationState;
  lifecycle_state: LifecycleState;
  confidence: ConfidenceBand | null;
  evidence_ids: string[];
  verification: VerificationMetadata | null;
  supersession_refs: SupersessionReference[];
  observed_at: string | null;
  created_at: string;
  metadata: HiveMetadata;
}

export interface ContradictionRecord {
  contradiction_id: string;
  contradiction_class: ContradictionClass;
  involved_record_ids: string[];
  summary: string;
  detection_source: MemorySource;
  detected_at: string;
  resolution_state: ContradictionResolutionState;
  resolution_record_id: string | null;
  resolution_source: MemorySource | null;
  evidence_ids: string[];
  severity: ContradictionSeverity | null;
  metadata: HiveMetadata;
}

export interface VerificationSummary {
  verified_count: number;
  human_confirmed_count: number;
  partially_verified_count: number;
  unverified_count: number;
  contradicted_count: number;
  unresolvable_count: number;
}

export interface RepositoryBaseline {
  project_id: string;
  branch: string | null;
  head_commit: string | null;
  // `null` means unknown — never collapsed to `false`.
  working_tree_clean: boolean | null;
  observed_at: string | null;
  evidence_ids: string[];
  metadata: HiveMetadata;
}

export interface PacketWarning {
  record_id: string;
  lifecycle_state: LifecycleState;
  reason: string;
}

export interface ContextPacket {
  packet_version: string;
  generated_at: string;
  project_id: string;
  repository_baseline: RepositoryBaseline | null;
  active_track: string | null;
  active_phase: string | null;
  active_facts: MemoryRecord[];
  active_decisions: MemoryRecord[];
  active_constraints: MemoryRecord[];
  known_capabilities: MemoryRecord[];
  unresolved_contradictions: ContradictionRecord[];
  warnings: PacketWarning[];
  evidence_references: EvidenceReference[];
  verification_summary: VerificationSummary;
  prohibited_assumptions: string[];
  read_only: boolean;
}

export interface ContextPacketRequest {
  project_id: string;
  generated_at: string;
  scope: MemoryScope | null;
  records: MemoryRecord[];
}

// ------------------------------------------------------------------------- //
// Phase 37I/37L/37M — Repository Observer contract types.
//
// Mirrors the backend repository_observer.py and repository_observer_api.py
// wire shapes. The frontend inspector is read-only and snapshot-based; these
// types deliberately preserve backend evidence, warning, limitation, overflow,
// completeness, truncation, and identity fields without reinterpreting them.
// ------------------------------------------------------------------------- //

export const REPOSITORY_OBSERVER_CONTRACT_VERSION = "repo-observer.v1";

export type RepositoryIdentityStatus =
  | "verified"
  | "unverified"
  | "mismatched_root"
  | "mismatched_remote"
  | "missing_git_metadata"
  | "unsafe_location";

export type RepositoryOperationState =
  | "normal"
  | "merging"
  | "rebasing"
  | "cherry_picking"
  | "bisecting"
  | "detached"
  | "bare"
  | "unavailable"
  | "unknown";

export type WorkingTreeState =
  | "clean"
  | "modified"
  | "staged"
  | "untracked"
  | "conflicted"
  | "unavailable"
  | "unknown";

export type FileChangeKind =
  | "added"
  | "modified"
  | "deleted"
  | "renamed"
  | "copied"
  | "untracked"
  | "conflicted"
  | "unchanged"
  | "unknown";

export type FileObservationCategory =
  | "git_status"
  | "file_metadata"
  | "bounded_text_excerpt"
  | "repository_configuration"
  | "exclusion_record"
  | "unsupported_data"
  | "unknown";

export type FileContentKind =
  | "text"
  | "binary"
  | "symlink"
  | "directory"
  | "submodule"
  | "unknown"
  | "unavailable";

export type RepositoryEvidenceCategory =
  | "git_metadata"
  | "working_tree_metadata"
  | "file_metadata"
  | "bounded_text_excerpt"
  | "repository_configuration"
  | "validation_result"
  | "exclusion_record"
  | "externally_supplied_claim"
  | "unsupported_data";

export type RepositoryEvidenceAuthority =
  | "direct_git_output"
  | "direct_filesystem_metadata"
  | "parsed_repository_document"
  | "validated_execution_source"
  | "user_supplied_statement"
  | "agent_generated_summary"
  | "unsupported_assumption"
  | "unavailable_information";

export type RepositoryTruncationState =
  | "not_truncated"
  | "truncated"
  | "omitted"
  | "unknown";

export type ObserverWarningCategory =
  | "repository_identity_mismatch"
  | "unsafe_repository_path"
  | "inaccessible_path"
  | "unsupported_file_type"
  | "binary_content_omitted"
  | "ignored_content_omitted"
  | "excluded_path"
  | "evidence_truncated"
  | "file_limit_reached"
  | "byte_limit_reached"
  | "evidence_limit_reached"
  | "git_metadata_unavailable"
  | "partial_snapshot"
  | "observer_capability_unavailable"
  | "timestamp_ambiguity"
  | "unknown_observer_error";

export type ObserverLimitationCategory =
  | "metadata_only"
  | "file_contents_not_allowed"
  | "ignored_files_not_included"
  | "untracked_files_not_included"
  | "binary_files_not_included"
  | "excluded_paths_applied"
  | "bounded_collection"
  | "unsupported_data"
  | "unavailable_information";

export type OverflowLimitKind =
  | "file_count"
  | "evidence_count"
  | "text_bytes"
  | "snapshot_bytes"
  | "warning_count"
  | "limitation_count"
  | "unknown";

export type SnapshotCompleteness =
  | "complete"
  | "partial"
  | "unavailable"
  | "invalid"
  | "rejected";

export interface RepositoryRemote {
  name: string;
  url: string;
  normalized_url: string | null;
}

export interface RepositoryIdentity {
  repository_id: string;
  canonical_root: string;
  normalized_root: string;
  repository_name: string;
  remotes: RepositoryRemote[];
  primary_remote_url: string | null;
  current_branch: string | null;
  current_commit: string | null;
  upstream_reference: string | null;
  default_branch: string | null;
  operation_state: RepositoryOperationState;
  status: RepositoryIdentityStatus;
  warning_ids: string[];
}

export interface RepositoryObserverScope {
  repository_root: string;
  included_paths: string[];
  excluded_paths: string[];
  max_file_count: number;
  max_evidence_entries: number;
  max_text_bytes: number;
  max_snapshot_bytes: number;
  include_untracked_files: boolean;
  include_ignored_files: boolean;
  include_binary_files: boolean;
  allow_file_contents: boolean;
  metadata_only: boolean;
}

export interface RepositoryObservationSnapshotRequest {
  repository_root: string;
  observed_at: string;
  max_file_count: number;
  max_snapshot_bytes: number;
  scope?: RepositoryObserverScope | null;
}

export interface RepositoryDriftAnalysisRequest {
  repository_root: string;
  observed_at: string;
  baseline_reference: "HEAD";
  max_file_count: number;
  max_snapshot_bytes: number;
}

export type RepositoryDriftStatus =
  | "clean"
  | "drifted"
  | "partial"
  | "unsupported"
  | "unavailable";

export interface WorkingTreeStatus {
  states: WorkingTreeState[];
  staged_count: number;
  unstaged_count: number;
  untracked_count: number;
  conflicted_count: number;
}

export interface PathRelationship {
  change_kind: FileChangeKind;
  prior_path: string;
  current_path: string;
}

export interface FileObservationSummary {
  file_id: string;
  repository_relative_path: string;
  normalized_path: string;
  change_kind: FileChangeKind;
  observation_category: FileObservationCategory;
  size_bytes: number | null;
  content_kind: FileContentKind;
  tracked: boolean | null;
  ignored: boolean | null;
  staged: boolean | null;
  content_digest: string | null;
  path_relationship: PathRelationship | null;
  evidence_ids: string[];
  omission_reason: string | null;
  warning_ids: string[];
}

export interface RepositoryEvidence {
  evidence_id: string;
  category: RepositoryEvidenceCategory;
  authority: RepositoryEvidenceAuthority;
  source: string;
  repository_relative_path: string | null;
  summary: string;
  bounded_excerpt: string | null;
  excerpt_limit: number | null;
  digest: string | null;
  captured_at: string | null;
  truncation_state: RepositoryTruncationState;
  omission_reason: string | null;
  related_file_ids: string[];
}

export interface ObserverWarning {
  warning_id: string;
  category: ObserverWarningCategory;
  summary: string;
  path: string | null;
  evidence_ids: string[];
}

export interface ObserverLimitation {
  limitation_id: string;
  category: ObserverLimitationCategory;
  summary: string;
  path: string | null;
}

export interface OverflowMetadata {
  overflow_id: string;
  limit_kind: OverflowLimitKind;
  truncated: boolean;
  configured_limit: number;
  observed_count: number | null;
  observed_size_bytes: number | null;
  retained_count: number;
  omitted_count: number | null;
  deterministic_cutoff: string;
  snapshot_partial: boolean;
}

export interface RepositorySnapshot {
  snapshot_id: string;
  contract_version: string;
  repository_identity: RepositoryIdentity;
  observed_at: string;
  observer_version: string;
  branch: string | null;
  commit: string | null;
  working_tree: WorkingTreeStatus;
  changed_files: FileObservationSummary[];
  evidence: RepositoryEvidence[];
  warnings: ObserverWarning[];
  limitations: ObserverLimitation[];
  omitted_paths: string[];
  overflow: OverflowMetadata[];
  deterministic_ordering: string[];
  completeness: SnapshotCompleteness;
  read_only: boolean;
}

export interface RepositoryDriftSummary {
  total_changed_files: number;
  retained_file_count: number;
  staged_count: number;
  unstaged_count: number;
  untracked_count: number;
  conflicted_count: number;
  added_count: number;
  modified_count: number;
  deleted_count: number;
  renamed_count: number;
  copied_count: number;
  type_changed_count: number;
  unknown_count: number;
}

export interface RepositoryDriftFile {
  file_id: string;
  change_kind: FileChangeKind;
  current_path: string;
  normalized_path: string;
  old_path: string | null;
  staged: boolean;
  unstaged: boolean;
  untracked: boolean;
  tracked: boolean | null;
  evidence_ids: string[];
  warning_ids: string[];
}

export interface RepositoryDriftAnalysis {
  drift_id: string;
  contract_version: string;
  repository_identity: RepositoryIdentity;
  observed_at: string;
  observer_version: string;
  baseline_reference: string;
  baseline_commit_hash: string | null;
  drift_status: RepositoryDriftStatus;
  summary: RepositoryDriftSummary;
  files: RepositoryDriftFile[];
  evidence: RepositoryEvidence[];
  warnings: ObserverWarning[];
  limitations: ObserverLimitation[];
  omitted_paths: string[];
  overflow: OverflowMetadata[];
  deterministic_ordering: string[];
  completeness: SnapshotCompleteness;
  read_only: boolean;
}

