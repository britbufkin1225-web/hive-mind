/**
 * Phase 8C — Knowledge Graph visualization-prep view model.
 *
 * Pure, read-only transform from the backend knowledge-graph API response into
 * a normalized model that a future visual graph renderer can consume directly.
 *
 * Design constraints:
 *   - Never mutates the input response (nodes/edges/metadata are copied or
 *     re-projected, never edited in place).
 *   - Deterministic: identical input always yields identical ordering and ids.
 *   - Render-safe: tolerates empty responses, missing optional fields, and
 *     edges that reference nodes which are absent from the node list. Nothing
 *     here throws on sparse/partial data.
 *   - No graph layout, physics, or rendering — this is data prep only.
 */

import type {
  HiveGraphEdge,
  HiveGraphNode,
  HiveGraphRelationship,
  HiveMetadata,
  KnowledgeGraphResponse,
} from "../types/api";

export interface GraphViewNode {
  id: string;
  label: string;
  type: string;
  sourceId: string | null;
  sourceName: string | null;
  degree: number;
  incomingCount: number;
  outgoingCount: number;
  displayGroup: string;
  previewText: string | null;
  metadata: HiveMetadata;
}

export interface GraphViewEdge {
  id: string;
  source: string;
  target: string;
  label: string | null;
  type: HiveGraphRelationship | string | null;
  metadata: HiveMetadata;
}

export interface GraphViewGroup {
  name: string;
  count: number;
}

/** A node/relationship type paired with its label and how often it occurs. */
export interface GraphTypeSummary {
  type: string;
  label: string;
  count: number;
}

export interface GraphViewModel {
  nodes: GraphViewNode[];
  edges: GraphViewEdge[];
  nodeCount: number;
  edgeCount: number;
  isolatedNodeCount: number;
  connectedNodeCount: number;
  groups: GraphViewGroup[];
  topConnectedNodes: GraphViewNode[];
  /** Distinct node types present, most common first — powers the legend. */
  nodeTypes: GraphTypeSummary[];
  /** Distinct relationship types present, most common first. */
  relationshipTypes: GraphTypeSummary[];
}

/** Elements related to a current selection, for the "focus + dim" hierarchy. */
export interface GraphRelated {
  nodeIds: Set<string>;
  edgeIds: Set<string>;
}

const RELATIONSHIP_LABELS: Record<string, string> = {
  contains: "Contains",
  references: "References",
  related: "Related",
  generated_from: "Generated from",
  linked_to: "Linked to",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  root: "Root",
  folder: "Folder",
  file: "File",
  concept: "Concept",
  note: "Note",
  model: "Model",
  source: "Source",
};

/**
 * Stable accent colors per node type, used by the legend and as the swatch on
 * node chips so the same type reads consistently across the panel. Deterministic
 * and purely presentational — no layout or rendering happens here.
 */
const NODE_TYPE_COLORS: Record<string, string> = {
  root: "#6b4fbb",
  folder: "#3b7dd8",
  file: "#2f9e6f",
  concept: "#c2792f",
  note: "#c44f8f",
  model: "#7a7a2f",
  source: "#4f8fbb",
};

const NODE_TYPE_FALLBACK_COLOR = "#6b6b6b";

/** How many top-degree nodes to surface for a future "most connected" view. */
const TOP_CONNECTED_LIMIT = 5;

export function relationshipLabel(relationship: string): string {
  return RELATIONSHIP_LABELS[relationship] ?? relationship;
}

export function nodeTypeLabel(type: string): string {
  return NODE_TYPE_LABELS[type] ?? type;
}

/** Accent color for a node type; falls back to a neutral gray for unknowns. */
export function nodeTypeColor(type: string): string {
  return NODE_TYPE_COLORS[type] ?? NODE_TYPE_FALLBACK_COLOR;
}

/**
 * Collect the edges touching a node and the nodes on the other end of them.
 * Read-only; the selected node id itself is excluded from the related node set
 * so callers can style "self", "related", and "inactive" distinctly.
 */
export function relatedToNode(
  model: GraphViewModel,
  nodeId: string,
): GraphRelated {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  for (const edge of model.edges) {
    if (edge.source === nodeId || edge.target === nodeId) {
      edgeIds.add(edge.id);
      nodeIds.add(edge.source);
      nodeIds.add(edge.target);
    }
  }
  nodeIds.delete(nodeId);
  return { nodeIds, edgeIds };
}

/** Build a {@link GraphTypeSummary} list ordered by count desc, then label. */
function summarizeTypes(
  counts: Map<string, number>,
  labelFor: (type: string) => string,
): GraphTypeSummary[] {
  return [...counts.entries()]
    .map(([type, count]) => ({ type, label: labelFor(type), count }))
    .sort((a, b) => {
      if (b.count !== a.count) {
        return b.count - a.count;
      }
      return a.label.localeCompare(b.label);
    });
}

/** Read a metadata value as a non-empty trimmed string, else null. */
function metaString(metadata: HiveMetadata | undefined, key: string): string | null {
  const value = metadata?.[key];
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

/**
 * Pick a short, human-readable preview string for a node, if one is available
 * in metadata. Tries a few conventional keys; returns null when none apply so
 * the UI can omit the line rather than render an empty/"undefined" value.
 */
function previewFor(node: HiveGraphNode): string | null {
  const meta = node.metadata ?? {};
  const candidate =
    metaString(meta, "preview") ??
    metaString(meta, "summary") ??
    metaString(meta, "description") ??
    metaString(meta, "excerpt");
  if (candidate === null) {
    return null;
  }
  // Keep previews compact; a future renderer can show the full text on demand.
  return candidate.length > 160 ? `${candidate.slice(0, 157)}…` : candidate;
}

/** Resolve a readable source name from metadata when the backend supplies one. */
function sourceNameFor(node: HiveGraphNode): string | null {
  return metaString(node.metadata ?? {}, "source_name");
}

/**
 * Choose the display group for a node. Prefers an explicit source name (so
 * nodes cluster by where they came from), then node type, then a stable
 * fallback — always a readable, non-empty label.
 */
function displayGroupFor(node: HiveGraphNode, sourceName: string | null): string {
  if (sourceName) {
    return sourceName;
  }
  if (node.type) {
    return nodeTypeLabel(node.type);
  }
  return "Ungrouped";
}

/** Stable, deterministic id for an edge the API did not assign one to. */
function deriveEdgeId(edge: HiveGraphEdge, index: number): string {
  const rel = edge.relationship ?? "edge";
  return `kg-view-edge-${edge.source_node_id}->${edge.target_node_id}:${rel}#${index}`;
}

/**
 * Build a deterministic, read-only {@link GraphViewModel} from the knowledge
 * graph API response. Safe to call with `null`/`undefined` or a sparse payload.
 */
export function buildGraphViewModel(
  response: KnowledgeGraphResponse | null | undefined,
): GraphViewModel {
  const rawNodes = response?.nodes ?? [];
  const rawEdges = response?.edges ?? [];

  // Degree accounting keyed by node id. Edges are tallied even when an endpoint
  // is missing from the node list, but only counts for ids we actually know
  // about surface on a node (so an unknown endpoint can't inflate a real node).
  const incoming = new Map<string, number>();
  const outgoing = new Map<string, number>();

  const edges: GraphViewEdge[] = rawEdges.map((edge, index) => {
    const source = edge.source_node_id;
    const target = edge.target_node_id;
    outgoing.set(source, (outgoing.get(source) ?? 0) + 1);
    incoming.set(target, (incoming.get(target) ?? 0) + 1);

    const id =
      typeof edge.id === "string" && edge.id.trim() !== ""
        ? edge.id
        : deriveEdgeId(edge, index);

    return {
      id,
      source,
      target,
      label: edge.relationship ? relationshipLabel(edge.relationship) : null,
      type: edge.relationship ?? null,
      metadata: edge.metadata ?? {},
    };
  });

  const nodes: GraphViewNode[] = rawNodes.map((node) => {
    const incomingCount = incoming.get(node.id) ?? 0;
    const outgoingCount = outgoing.get(node.id) ?? 0;
    const sourceName = sourceNameFor(node);
    const label =
      typeof node.label === "string" && node.label.trim() !== ""
        ? node.label
        : node.id;

    return {
      id: node.id,
      label,
      type: node.type,
      sourceId: node.source_id ?? null,
      sourceName,
      degree: incomingCount + outgoingCount,
      incomingCount,
      outgoingCount,
      displayGroup: displayGroupFor(node, sourceName),
      previewText: previewFor(node),
      metadata: node.metadata ?? {},
    };
  });

  // Deterministic node ordering: most connected first, then alphabetical label,
  // then id as a final stable tie-breaker.
  const orderedNodes = [...nodes].sort((a, b) => {
    if (b.degree !== a.degree) {
      return b.degree - a.degree;
    }
    const labelCmp = a.label.localeCompare(b.label);
    if (labelCmp !== 0) {
      return labelCmp;
    }
    return a.id.localeCompare(b.id);
  });

  // Deterministic edge ordering by endpoints then relationship then id.
  const orderedEdges = [...edges].sort((a, b) => {
    const sourceCmp = a.source.localeCompare(b.source);
    if (sourceCmp !== 0) {
      return sourceCmp;
    }
    const targetCmp = a.target.localeCompare(b.target);
    if (targetCmp !== 0) {
      return targetCmp;
    }
    return a.id.localeCompare(b.id);
  });

  const connectedNodeCount = nodes.filter((node) => node.degree > 0).length;
  const isolatedNodeCount = nodes.length - connectedNodeCount;

  // Group counts, ordered by descending count then group name for stability.
  const groupCounts = new Map<string, number>();
  for (const node of nodes) {
    groupCounts.set(node.displayGroup, (groupCounts.get(node.displayGroup) ?? 0) + 1);
  }
  const groups: GraphViewGroup[] = [...groupCounts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => {
      if (b.count !== a.count) {
        return b.count - a.count;
      }
      return a.name.localeCompare(b.name);
    });

  const topConnectedNodes = orderedNodes
    .filter((node) => node.degree > 0)
    .slice(0, TOP_CONNECTED_LIMIT);

  // Distinct node/relationship types present, for the legend. Tallying from the
  // projected nodes/edges keeps the legend honest: it only lists what's drawn.
  const nodeTypeCounts = new Map<string, number>();
  for (const node of nodes) {
    if (node.type) {
      nodeTypeCounts.set(node.type, (nodeTypeCounts.get(node.type) ?? 0) + 1);
    }
  }
  const relationshipTypeCounts = new Map<string, number>();
  for (const edge of edges) {
    const type = typeof edge.type === "string" ? edge.type : null;
    if (type) {
      relationshipTypeCounts.set(
        type,
        (relationshipTypeCounts.get(type) ?? 0) + 1,
      );
    }
  }

  return {
    nodes: orderedNodes,
    edges: orderedEdges,
    nodeCount: response?.summary?.node_count ?? nodes.length,
    edgeCount: response?.summary?.edge_count ?? edges.length,
    isolatedNodeCount,
    connectedNodeCount,
    groups,
    topConnectedNodes,
    nodeTypes: summarizeTypes(nodeTypeCounts, nodeTypeLabel),
    relationshipTypes: summarizeTypes(relationshipTypeCounts, relationshipLabel),
  };
}
