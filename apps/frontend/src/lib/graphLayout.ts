/**
 * Phase 9A — Knowledge Graph read-only visualization layout.
 *
 * Pure, deterministic positioning for the SVG graph canvas. Given the prepared
 * {@link GraphViewModel} node/edge lists, it assigns each node a stable (x, y)
 * on a fixed-size canvas so the same input always renders identically.
 *
 * Design constraints (mirroring the view model):
 *   - No physics / force simulation — positions are a closed-form function of
 *     each node's index in the already-deterministic model ordering.
 *   - Stable between renders: layout depends only on node ids/order and counts,
 *     never on timing, randomness, or previous frames.
 *   - Render-safe: tolerates an empty graph and edges whose endpoints are
 *     missing from the node list (such edges are simply dropped from layout).
 *   - No mutation of the input model.
 */

import type { GraphViewEdge, GraphViewNode } from "./graphViewModel";

export interface GraphLayoutNode {
  id: string;
  label: string;
  type: string;
  degree: number;
  /** Center coordinates within the layout viewBox. */
  x: number;
  y: number;
  /** Circle radius, scaled by connectedness for a readable visual hierarchy. */
  radius: number;
}

export interface GraphLayoutEdge {
  id: string;
  source: string;
  target: string;
  label: string | null;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface GraphLayout {
  width: number;
  height: number;
  nodes: GraphLayoutNode[];
  edges: GraphLayoutEdge[];
  /** Quick lookup for incident-edge highlighting and label resolution. */
  nodeById: Map<string, GraphLayoutNode>;
}

/** Fixed viewBox the canvas draws into; the SVG scales responsively in CSS. */
const WIDTH = 760;
const HEIGHT = 560;
/** Keep nodes and their labels clear of the canvas edge. */
const PADDING = 96;
const MIN_RADIUS = 12;
const MAX_RADIUS = 26;

/** Clamp a value into an inclusive range. */
function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Scale a node's circle radius from its degree. Uses a square-root curve so a
 * very high-degree hub stays bounded rather than dwarfing the rest.
 */
function radiusForDegree(degree: number, maxDegree: number): number {
  if (maxDegree <= 0) {
    return MIN_RADIUS;
  }
  const ratio = Math.sqrt(degree) / Math.sqrt(maxDegree);
  return MIN_RADIUS + ratio * (MAX_RADIUS - MIN_RADIUS);
}

/**
 * Compute a deterministic ring layout for the given nodes and edges. Nodes are
 * placed evenly around a circle in model order (most-connected first), which
 * keeps the busy hub region of the graph visually contiguous. A single node is
 * centered; an empty graph yields empty layout arrays.
 */
export function computeGraphLayout(
  nodes: GraphViewNode[],
  edges: GraphViewEdge[],
): GraphLayout {
  const centerX = WIDTH / 2;
  const centerY = HEIGHT / 2;
  const ringRadius = Math.min(centerX, centerY) - PADDING;
  const maxDegree = nodes.reduce((max, node) => Math.max(max, node.degree), 0);
  const count = nodes.length;

  const layoutNodes: GraphLayoutNode[] = nodes.map((node, index) => {
    let x = centerX;
    let y = centerY;
    if (count > 1) {
      // Start at the top (-90°) and step clockwise so order reads naturally.
      const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
      x = centerX + ringRadius * Math.cos(angle);
      y = centerY + ringRadius * Math.sin(angle);
    }
    return {
      id: node.id,
      label: node.label,
      type: node.type,
      degree: node.degree,
      x,
      y,
      radius: radiusForDegree(node.degree, maxDegree),
    };
  });

  const nodeById = new Map(layoutNodes.map((node) => [node.id, node]));

  // Only edges whose both endpoints resolved to a placed node can be drawn.
  const layoutEdges: GraphLayoutEdge[] = [];
  for (const edge of edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) {
      continue;
    }
    layoutEdges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    });
  }

  return {
    width: WIDTH,
    height: HEIGHT,
    nodes: layoutNodes,
    edges: layoutEdges,
    nodeById,
  };
}
