import type { CSSProperties, KeyboardEvent, ReactNode, RefObject } from "react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../api/client";
import type { HiveMetadata, KnowledgeGraphResponse } from "../types/api";
import { ZERO_MOTION, type MotionCommand } from "../handLandmarkMotion";
import {
  ambientSwayPose,
  applyDragDelta,
  composeSpatialCameraPose,
  easePointerPose,
  integrateOrbitalCamera,
  mapMotionCommandToOrbitalGraphControlCommand,
  ORBITAL_GRAPH_CAMERA_NEUTRAL,
  pointerParallaxTarget,
  SPATIAL_DRAG_CLICK_THRESHOLD_PX,
  SPATIAL_POINTER_NEUTRAL,
  type OrbitalGraphCameraTransform,
  type SpatialPointerPose,
} from "../orbitalGraphControl";
import {
  buildSpatialHiveNodes,
  compareProjectedDepth,
  computeSpatialDepthUnit,
  hashUnit,
  projectSpatialPoint,
  spatialEdgeFog,
  spatialEdgeWidthFactor,
  spatialNodeBlur,
  spatialNodeFog,
} from "../spatialHiveProjection";
import {
  buildSpatialHiveParticleField,
  drawSpatialHiveParticles,
  type SpatialParticleEnergy,
} from "../spatialHiveParticles";
import {
  buildGraphViewModel,
  edgeTypeColor,
  nodeTypeColor,
  nodeTypeLabel,
  relatedToNode,
  type GraphTypeSummary,
  type GraphViewEdge,
  type GraphViewNode,
} from "../lib/graphViewModel";
import { computeGraphLayout } from "../lib/graphLayout";
import type { GraphLayoutEdge, GraphLayoutNode } from "../lib/graphLayout";

/**
 * Roving keyboard navigation within a node/edge list: Up/Down move focus
 * between rows, Home/End jump to the ends. Mouse/Tab behavior is untouched, so
 * this is purely additive for keyboard users.
 */
function handleListArrowKeys(event: KeyboardEvent<HTMLUListElement>): void {
  const keys = ["ArrowDown", "ArrowUp", "Home", "End"];
  if (!keys.includes(event.key)) {
    return;
  }
  const list = event.currentTarget;
  const buttons = Array.from(
    list.querySelectorAll<HTMLButtonElement>(":scope > li > button"),
  );
  if (buttons.length === 0) {
    return;
  }
  const currentIndex = buttons.findIndex(
    (button) => button === document.activeElement,
  );
  let nextIndex: number;
  switch (event.key) {
    case "ArrowDown":
      nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % buttons.length;
      break;
    case "ArrowUp":
      nextIndex =
        currentIndex <= 0 ? buttons.length - 1 : currentIndex - 1;
      break;
    case "Home":
      nextIndex = 0;
      break;
    default:
      nextIndex = buttons.length - 1;
  }
  event.preventDefault();
  buttons[nextIndex]?.focus();
}

type PanelState = "loading" | "success" | "error";

/**
 * Phase 32G — compact snapshot the graph camera loop hands back to the panel for
 * its small status readout. Purely informational: it reflects what the read-only
 * camera is doing (opt-in state, live motion trust, and the current pose) and
 * drives no data or selection flow.
 */
type GraphControlStatus = {
  enabled: boolean;
  active: boolean;
  confidence: number;
  reducedMotion: boolean;
  camera: OrbitalGraphCameraTransform;
};

const GRAPH_CONTROL_STATUS_OFF: GraphControlStatus = {
  enabled: false,
  active: false,
  confidence: 0,
  reducedMotion: false,
  camera: ORBITAL_GRAPH_CAMERA_NEUTRAL,
};

/**
 * The panel holds a single selection that is either a node or an edge (or
 * nothing). Keeping it as one discriminated value means selecting a node
 * naturally deselects any edge and vice versa, so the inspector always shows
 * exactly one record.
 */
type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

/**
 * Phase 35B — Spatial Hive interaction state (Level 1).
 *
 * A single, small, *transient* presentation mode summarising how the graph
 * surface is currently being engaged. It is derived fresh every render from
 * state that already exists (selection, canvas-local hover, orbital-control
 * availability) and is display-only: it drives CSS via `data-*` attributes and
 * readout copy. It deliberately does NOT persist (no storage / URL / backend),
 * never mutates graph data, and never changes selection — so a reload always
 * resets it to `idle` because there is nothing to restore.
 */
type SpatialHiveInteractionMode =
  | "idle"
  | "hover"
  | "focus"
  | "inspect"
  | "motion";

/**
 * Resolve the single winning interaction mode from the currently-active
 * signals. The priority order is deliberate and load-bearing:
 *
 *   focus / inspect (a committed selection)  ← strongest, always wins
 *   → hover (a transient pointer / keyboard cue)
 *   → motion (orbital camera control is available)
 *   → idle (resting fallback)
 *
 * A committed selection outranks hover so exploring with the pointer never
 * fights or dislodges the inspected record — selected-node clarity is never
 * overridden. A node selection reads as `focus`; an edge selection reads as
 * `inspect` (examining a relationship). `motion` sits just above `idle`, so it
 * marks "camera control is armed" as a distinct resting state without ever
 * competing with an active selection. The function is pure (same inputs → same
 * mode), so the mode carries no memory of its own.
 */
function resolveInteractionMode({
  selectionKind,
  hasHover,
  motionAvailable,
}: {
  selectionKind: "node" | "edge" | null;
  hasHover: boolean;
  motionAvailable: boolean;
}): SpatialHiveInteractionMode {
  if (selectionKind === "node") {
    return "focus";
  }
  if (selectionKind === "edge") {
    return "inspect";
  }
  if (hasHover) {
    return "hover";
  }
  if (motionAvailable) {
    return "motion";
  }
  return "idle";
}

/** Render a metadata value as a readable string (mirrors the Sources panel). */
function formatMetaValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function SummaryMetrics({
  nodeCount,
  edgeCount,
  connectedNodeCount,
  isolatedNodeCount,
  compact = false,
}: {
  nodeCount: number;
  edgeCount: number;
  connectedNodeCount: number;
  isolatedNodeCount: number;
  compact?: boolean;
}) {
  // The compact variant (used as a top-bar readout in the full-viewfinder
  // shell) shows only Nodes/Edges — Connected/Isolated already surface in the
  // legend's Status group, so repeating all four here would just crowd the
  // bar without adding information.
  const metrics: Array<[string, number]> = compact
    ? [
        ["Nodes", nodeCount],
        ["Edges", edgeCount],
      ]
    : [
        ["Nodes", nodeCount],
        ["Edges", edgeCount],
        ["Connected", connectedNodeCount],
        ["Isolated", isolatedNodeCount],
      ];
  return (
    <dl
      className={compact ? "graph-summary graph-summary-compact" : "graph-summary"}
      aria-label="Graph summary"
    >
      {metrics.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Legend mapping the panel's visual vocabulary — node-type swatches,
 * relationship-type labels, and connectivity status — so colors and badges are
 * self-explaining. Only types actually present in the graph are listed.
 */
function GraphLegend({
  nodeTypes,
  relationshipTypes,
  connectedNodeCount,
  isolatedNodeCount,
}: {
  nodeTypes: GraphTypeSummary[];
  relationshipTypes: GraphTypeSummary[];
  connectedNodeCount: number;
  isolatedNodeCount: number;
}) {
  return (
    <div className="graph-legend" aria-label="Graph legend">
      {nodeTypes.length > 0 && (
        <div className="graph-legend-group">
          <span className="graph-legend-title">Node types</span>
          <ul className="graph-legend-items">
            {nodeTypes.map((entry) => (
              <li key={entry.type} className="graph-legend-item">
                <span
                  className="graph-legend-swatch"
                  style={{ background: nodeTypeColor(entry.type) }}
                  aria-hidden="true"
                />
                <span className="graph-legend-label">{entry.label}</span>
                <span className="graph-legend-count">{entry.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {relationshipTypes.length > 0 && (
        <div className="graph-legend-group">
          <span className="graph-legend-title">Relationships</span>
          <ul className="graph-legend-items">
            {relationshipTypes.map((entry) => (
              <li key={entry.type} className="graph-legend-item">
                <span
                  className="graph-legend-edge"
                  style={{ borderTopColor: edgeTypeColor(entry.type) }}
                  aria-hidden="true"
                />
                <span className="graph-legend-label">{entry.label}</span>
                <span className="graph-legend-count">{entry.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="graph-legend-group">
        <span className="graph-legend-title">Status</span>
        <ul className="graph-legend-items">
          <li className="graph-legend-item">
            <span
              className="graph-legend-badge graph-badge-connected"
              aria-hidden="true"
            />
            <span className="graph-legend-label">Connected</span>
            <span className="graph-legend-count">{connectedNodeCount}</span>
          </li>
          <li className="graph-legend-item">
            <span
              className="graph-legend-badge graph-badge-isolated"
              aria-hidden="true"
            />
            <span className="graph-legend-label">Isolated</span>
            <span className="graph-legend-count">{isolatedNodeCount}</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

function NodeRow({
  node,
  selected,
  related,
  dimmed,
  onSelect,
}: {
  node: GraphViewNode;
  selected: boolean;
  related?: boolean;
  dimmed?: boolean;
  onSelect: () => void;
}) {
  const className = [
    "graph-node-row",
    selected && "graph-row-selected",
    related && "graph-row-related",
    dimmed && "graph-row-dimmed",
  ]
    .filter(Boolean)
    .join(" ");
  const isolated = node.degree === 0;
  return (
    <li>
      <button
        type="button"
        className={className}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <span className="graph-node-row-head">
          <span className="graph-node-name" title={node.label}>
            <span
              className="graph-node-swatch"
              style={{ background: nodeTypeColor(node.type) }}
              aria-hidden="true"
            />
            {node.label}
          </span>
          <span className="graph-node-type">{nodeTypeLabel(node.type)}</span>
        </span>
        <span className="graph-node-row-sub">
          <span className="graph-node-degree" title="incoming / outgoing">
            {node.incomingCount} in · {node.outgoingCount} out
          </span>
          {isolated && (
            <span className="graph-node-flag" title="No relationships">
              {" "}
              · isolated
            </span>
          )}
          {node.sourceName ? ` · ${node.sourceName}` : ""}
        </span>
        {node.previewText && (
          <span className="graph-node-preview">{node.previewText}</span>
        )}
      </button>
    </li>
  );
}

function EdgeRow({
  edge,
  labelFor,
  selected,
  related,
  dimmed,
  onSelect,
}: {
  edge: GraphViewEdge;
  labelFor: (nodeId: string) => string;
  selected: boolean;
  related?: boolean;
  dimmed?: boolean;
  onSelect: () => void;
}) {
  const className = [
    "graph-edge-row",
    selected && "graph-row-selected",
    related && "graph-row-related",
    dimmed && "graph-row-dimmed",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <li>
      <button
        type="button"
        className={className}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <span className="graph-edge-endpoints">
          <span className="graph-edge-node">{labelFor(edge.source)}</span>
          <span className="graph-edge-arrow" aria-hidden="true">
            →
          </span>
          <span className="graph-edge-node">{labelFor(edge.target)}</span>
        </span>
        {edge.label && (
          <span className="graph-edge-relationship">{edge.label}</span>
        )}
      </button>
    </li>
  );
}

/** Key/value detail list shared by the node and edge inspector views. */
function DetailList({ rows }: { rows: Array<[string, ReactNode]> }) {
  return (
    <dl className="source-meta">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Generic metadata block, omitted entirely when there is nothing to show. */
function MetadataBlock({ metadata }: { metadata: HiveMetadata }) {
  const entries = Object.entries(metadata ?? {});
  return (
    <div className="graph-inspector-metadata">
      <span className="result-key">Metadata</span>
      {entries.length === 0 ? (
        <span className="console-hint"> (none)</span>
      ) : (
        <dl className="source-meta">
          {entries.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{formatMetaValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function NodeInspector({ node }: { node: GraphViewNode }) {
  const rows: Array<[string, ReactNode]> = [
    ["ID", <code key="id">{node.id}</code>],
    ["Type", nodeTypeLabel(node.type)],
    ["Group", node.displayGroup],
    [
      "Connections",
      `${node.incomingCount} in · ${node.outgoingCount} out (${node.degree} total)`,
    ],
  ];
  if (node.sourceName) {
    rows.push(["Source", node.sourceName]);
  }

  return (
    <div
      className="graph-inspector"
      style={{ borderLeftWidth: "3px", borderLeftColor: nodeTypeColor(node.type) }}
    >
      <div className="graph-inspector-head">
        <h3>{node.label}</h3>
        <span className="graph-node-type">{nodeTypeLabel(node.type)}</span>
      </div>
      {node.previewText && (
        <p className="source-description">{node.previewText}</p>
      )}
      <DetailList rows={rows} />
      <MetadataBlock metadata={node.metadata} />
    </div>
  );
}

function EdgeInspector({
  edge,
  labelFor,
}: {
  edge: GraphViewEdge;
  labelFor: (nodeId: string) => string;
}) {
  const rows: Array<[string, ReactNode]> = [
    ["ID", <code key="id">{edge.id}</code>],
    ["Relationship", edge.label ?? "—"],
    ["From", labelFor(edge.source)],
    ["To", labelFor(edge.target)],
  ];

  return (
    <div className="graph-inspector">
      <div className="graph-inspector-head">
        <h3 className="graph-inspector-edge-title">
          <span className="graph-edge-node">{labelFor(edge.source)}</span>
          <span className="graph-edge-arrow" aria-hidden="true">
            →
          </span>
          <span className="graph-edge-node">{labelFor(edge.target)}</span>
        </h3>
        {edge.label && (
          <span className="graph-edge-relationship">{edge.label}</span>
        )}
      </div>
      <DetailList rows={rows} />
      <MetadataBlock metadata={edge.metadata} />
    </div>
  );
}

function GraphInspector({
  node,
  edge,
  labelFor,
}: {
  node: GraphViewNode | null;
  edge: GraphViewEdge | null;
  labelFor: (nodeId: string) => string;
}) {
  if (node) {
    return <NodeInspector node={node} />;
  }
  if (edge) {
    return <EdgeInspector edge={edge} labelFor={labelFor} />;
  }
  return (
    <div className="graph-inspector graph-inspector-empty">
      <p className="console-hint graph-inspector-empty-hint">
        Select a node or edge to inspect its details.
      </p>
    </div>
  );
}

/** Trim a node label so it stays legible beside its circle on the canvas. */
function truncateLabel(label: string, max = 22): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

/**
 * Phase 33C — 2.5D spatial depth model.
 *
 * Each node resolves to one discrete depth tier (near / mid / far) plus a
 * cluster phase, derived purely from *stable* graph data — never randomness and
 * never a mutation of the model — so the same graph renders the same layered
 * structure on every reload (visual contract §6, determinism).
 *
 * Depth is a display-only illusion layered on top of the existing read-only
 * ring layout: it drives node scale, opacity, aura intensity, and edge subtlety,
 * and it rides the existing orbital-camera transform. It never touches node
 * positions, selection, or data.
 */
type DepthTier = "near" | "mid" | "far";

/**
 * Discrete scale per tier. The ramp is monotonic and tightly bounded
 * (near > mid > far) so it reads as believable depth rather than a cartoonish
 * zoom (visual contract §3).
 *
 * Phase 34B: the far end of the ramp is widened a touch (0.9 → 0.87) and near
 * lifted a hair (1.12 → 1.14) so the resting Hive-State reads as clearer layered
 * depth at a glance. Still tightly bounded and monotonic — near stays below the
 * selected lift (1.2) and related (1.04) set in CSS, so the selection hierarchy's
 * spatial order (selected > related > ambient) is preserved, not flattened.
 */
const DEPTH_TIER_SCALE: Record<DepthTier, number> = {
  near: 1.14,
  mid: 1,
  far: 0.87,
};

interface NodeDepth {
  tier: DepthTier;
  /** Cluster breathing phase in [0, 1); shared by nodes of the same type. */
  phase: number;
}

interface DepthModel {
  nodes: Map<string, NodeDepth>;
  /** Resting depth tier per edge, inherited from its nearer endpoint. */
  edges: Map<string, DepthTier>;
}

/** Bucket a continuous depth value [0, 1] into one of the three discrete tiers. */
function tierFromZ(z: number): DepthTier {
  if (z >= 0.62) {
    return "near";
  }
  if (z >= 0.32) {
    return "mid";
  }
  return "far";
}

/**
 * Build the deterministic resting depth model for the current layout. Structural
 * depth brings the busy hubs forward (degree-ranked, so foreground carries the
 * most-connected nodes — depth that improves readability, not decoration) while a
 * stable id hash spreads equal-degree nodes across tiers so the field reads as
 * layered space rather than flat bands. Edges inherit the nearer endpoint's tier
 * so a link to a foreground hub stays legible and purely background links recede.
 */
function buildDepthModel(
  nodes: GraphLayoutNode[],
  edges: GraphLayoutEdge[],
): DepthModel {
  const maxDegree = nodes.reduce((max, node) => Math.max(max, node.degree), 0);
  const nodeMap = new Map<string, NodeDepth>();
  const zById = new Map<string, number>();

  for (const node of nodes) {
    // Phase 36F: the depth unit is now computed by the shared spatial helper
    // (same formula as before), so the discrete tiers and the continuous
    // point-cloud projection can never disagree about a node's depth.
    const z = computeSpatialDepthUnit(node.id, node.degree, maxDegree);
    zById.set(node.id, z);
    nodeMap.set(node.id, {
      tier: tierFromZ(z),
      // Cluster phase keyed on node type so a whole type-cluster breathes as one
      // organism at a reproducible offset (visual contract §4, phase-organized).
      phase: hashUnit(`cluster:${node.type}`),
    });
  }

  const edgeMap = new Map<string, DepthTier>();
  for (const edge of edges) {
    const zs = zById.get(edge.source) ?? 0;
    const zt = zById.get(edge.target) ?? 0;
    edgeMap.set(edge.id, tierFromZ(Math.max(zs, zt)));
  }

  return { nodes: nodeMap, edges: edgeMap };
}

/**
 * Read-only SVG visualization of the graph. Renders nodes and relationships in
 * the deterministic ring layout and reports node/edge clicks back up so the
 * existing inspector stays the single source of selection truth. Purely
 * presentational: it draws from the prepared view model and mutates nothing.
 */
const GraphCanvas = memo(function GraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  selectedEdgeId,
  relatedNodeIds,
  hasSelection,
  onSelectNode,
  onSelectEdge,
  onClearSelection,
  graphControlEnabled,
  motionCommandRef,
  onCameraStatus,
  recenterSignal,
}: {
  nodes: GraphViewNode[];
  edges: GraphViewEdge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  relatedNodeIds: Set<string>;
  hasSelection: boolean;
  onSelectNode: (id: string) => void;
  onSelectEdge: (id: string) => void;
  onClearSelection: () => void;
  graphControlEnabled: boolean;
  motionCommandRef: RefObject<MotionCommand>;
  onCameraStatus: (status: GraphControlStatus) => void;
  recenterSignal: number;
}) {
  const layout = useMemo(
    () => computeGraphLayout(nodes, edges),
    [nodes, edges],
  );

  // Phase 33C — deterministic 2.5D depth model, derived once per layout. It is a
  // display-only projection of stable graph data (never mutated, never random),
  // so it recomputes only when the layout itself changes, not per motion frame.
  const depth = useMemo(
    () => buildDepthModel(layout.nodes, layout.edges),
    [layout.nodes, layout.edges],
  );

  // Phase 36F — spatial Hive point-cloud model. The deterministic pseudo-3D
  // lift of the ring layout: stable (x, y, z) per node plus a hash-seeded
  // particle shell per cluster. Display geometry only — derived once per
  // layout, never mutated, never random, and the flat layout stays the
  // authoritative structure underneath.
  const spatialNodes = useMemo(
    () => buildSpatialHiveNodes(layout.nodes, layout.width, layout.height),
    [layout.nodes, layout.width, layout.height],
  );
  const particleField = useMemo(
    () => buildSpatialHiveParticleField(Array.from(spatialNodes.values())),
    [spatialNodes],
  );

  // Neutral-pose projection for the initial React render: nodes and edges are
  // born already occupying depth (perspective scale + fog at yaw 0 / pitch 0 /
  // zoom 1), and the per-frame driver below only ever *re-projects* the same
  // stable spatial model through the live camera pose. Constant per layout, so
  // React reconciliation never fights the imperative per-frame writes.
  const initialNodeProjection = useMemo(() => {
    const m = new Map<string, { transform: string; fog: number }>();
    for (const [id, spatialNode] of spatialNodes) {
      const p = projectSpatialPoint(
        spatialNode.x,
        spatialNode.y,
        spatialNode.z,
        ORBITAL_GRAPH_CAMERA_NEUTRAL,
        layout.width,
        layout.height,
      );
      m.set(id, {
        transform: `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)}) scale(${p.scale.toFixed(4)})`,
        fog: spatialNodeFog(p.depth),
      });
    }
    return m;
  }, [spatialNodes, layout.width, layout.height]);

  // Painter's-algorithm render order at rest: far nodes/edges first in the
  // DOM so near ones paint over them. The per-frame driver re-sorts from the
  // live *projected* depth whenever the camera pose changes the order, so
  // occlusion stays correct mid-orbit — render order is part of the depth
  // model, not a fixed document order. (Tab order follows the depth order;
  // the explorer lists remain the stable, model-ordered keyboard surface.)
  const nodesRenderOrder = useMemo(() => {
    return [...layout.nodes].sort(
      (a, b) => (spatialNodes.get(a.id)?.z ?? 0) - (spatialNodes.get(b.id)?.z ?? 0),
    );
  }, [layout.nodes, spatialNodes]);
  const edgesRenderOrder = useMemo(() => {
    const meanZ = (edge: GraphLayoutEdge) =>
      ((spatialNodes.get(edge.source)?.z ?? 0) +
        (spatialNodes.get(edge.target)?.z ?? 0)) /
      2;
    return [...layout.edges].sort((a, b) => meanZ(a) - meanZ(b));
  }, [layout.edges, spatialNodes]);

  const initialEdgeProjection = useMemo(() => {
    const m = new Map<
      string,
      { x1: number; y1: number; x2: number; y2: number; fog: number; width: number }
    >();
    for (const edge of layout.edges) {
      const s = spatialNodes.get(edge.source);
      const t = spatialNodes.get(edge.target);
      if (!s || !t) continue;
      const ps = projectSpatialPoint(
        s.x, s.y, s.z, ORBITAL_GRAPH_CAMERA_NEUTRAL, layout.width, layout.height,
      );
      const pt = projectSpatialPoint(
        t.x, t.y, t.z, ORBITAL_GRAPH_CAMERA_NEUTRAL, layout.width, layout.height,
      );
      const meanDepth = (ps.depth + pt.depth) / 2;
      m.set(edge.id, {
        x1: ps.x,
        y1: ps.y,
        x2: pt.x,
        y2: pt.y,
        fog: spatialEdgeFog(meanDepth),
        width: spatialEdgeWidthFactor(meanDepth),
      });
    }
    return m;
  }, [spatialNodes, layout.edges, layout.width, layout.height]);

  const edgeTypeById = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of edges) {
      if (e.type) m.set(e.id, String(e.type));
    }
    return m;
  }, [edges]);

  // Phase 31C: adjacency map (node id -> direct neighbor ids) so hovering a
  // node can briefly illuminate the nodes at the far end of its edges, not
  // just the edges themselves. Kept as a derived lookup here so the hover
  // handlers stay O(1); it drives a purely presentational lift and never
  // touches selection/data flow (Phase 29A hover contract preserved).
  const neighborsByNode = useMemo(() => {
    const m = new Map<string, Set<string>>();
    const link = (a: string, b: string) => {
      let set = m.get(a);
      if (!set) {
        set = new Set<string>();
        m.set(a, set);
      }
      set.add(b);
    };
    for (const e of edges) {
      link(e.source, e.target);
      link(e.target, e.source);
    }
    return m;
  }, [edges]);

  // Phase 29B hover affordance state, kept local to the canvas: hover is a
  // transient presentation cue (it lifts the hovered element and its direct
  // neighbors) and must never drive overlays, dimming, or data flow — so it
  // deliberately never leaves this component (Phase 29A hover contract).
  // Focus mirrors hover so keyboard traversal gets the same affordance.
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);
  const [hoverEdge, setHoverEdge] = useState<{
    id: string;
    source: string;
    target: string;
  } | null>(null);

  // Phase 36F — spatial projection driver refs. The opt-in orbital camera
  // (Phase 32G) and the new cursor parallax both feed one composed pose; a
  // ref-driven rAF loop re-projects every node, edge, and particle through it.
  // This replaces the old whole-wrapper CSS transform: the camera now moves a
  // *pseudo-3D structure* (near/far objects move differently — parallax), not
  // a tilted flat poster. Still a visual, read-only camera: it never touches
  // nodes, edges, source data, layout, or selection, and driving it through
  // refs keeps every per-frame write off React's render path.
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const particleCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraPoseRef = useRef<OrbitalGraphCameraTransform>(
    ORBITAL_GRAPH_CAMERA_NEUTRAL,
  );
  const pointerPoseRef = useRef<SpatialPointerPose>(SPATIAL_POINTER_NEUTRAL);
  const pointerTargetRef = useRef<SpatialPointerPose>(SPATIAL_POINTER_NEUTRAL);
  // Persistent drag-to-orbit pose: survives effect re-runs so a vantage the
  // user grabbed stays put until Recenter / double-click clears it.
  const dragPoseRef = useRef<SpatialPointerPose>(SPATIAL_POINTER_NEUTRAL);
  const appliedPoseRef = useRef<OrbitalGraphCameraTransform>(
    ORBITAL_GRAPH_CAMERA_NEUTRAL,
  );
  // Latest apply function, exposed to the recenter/energy/sync effects so they
  // can re-project outside the driver effect's closure without re-running it.
  const applyPoseRef = useRef<((pose: OrbitalGraphCameraTransform) => void) | null>(
    null,
  );
  // Per-node particle styling (type color + selection/hover energy), read by
  // the draw path each frame. Held in a ref so pose frames never re-render.
  const particleEnergyRef = useRef<Map<string, SpatialParticleEnergy>>(new Map());

  // Phase 36C hardening — track the OS reduced-motion preference *live*, not
  // just at toggle time. Previously the preference was read once inside the
  // camera effect, so flipping it on mid-session left the rAF loop running
  // (visually masked by the CSS `transform: none` guard, but the readout kept
  // claiming Live/Idle and the pose kept accumulating in the ref) — and
  // flipping it back off made CSS re-apply that stale accumulated pose as a
  // jump. Holding the preference in state re-runs the camera effect on change:
  // enabling reduced motion now halts the loop, resets the pose to neutral,
  // and reports "Reduced motion" honestly; disabling it restarts cleanly from
  // neutral. Rationale: the reduced-motion contract must hold across a live
  // preference change, not only across control toggles.
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // Phase 36F — the spatial projection driver. One effect owns: (1) collecting
  // the projected elements, (2) the applyPose writer that re-projects nodes /
  // edges / particles through a camera pose, (3) the rAF loop that integrates
  // the opt-in motion camera and eases cursor parallax, and (4) the pointer
  // listeners that feed parallax targets. The loop is wake-on-input: it runs
  // continuously only while motion control is enabled (it must keep reading
  // commands and reporting status); cursor parallax wakes it and it goes back
  // to sleep once the pose settles, so the resting graph costs zero rAF work.
  useEffect(() => {
    const svg = svgRef.current;
    const wrap = wrapRef.current;
    if (!svg || !wrap) {
      applyPoseRef.current = null;
      return;
    }

    // --- Projected-element maps (stable per layout; React only ever changes
    // classes/styles inside these wrappers, never the wrappers themselves).
    const nodeTargets: Array<{
      el: SVGGElement;
      /** The inner Hive group (`.graph-canvas-node`), read per frame so the
          depth-of-field blur can yield to selected / related / hover-primary
          clarity without the driver ever *writing* those classes. */
      inner: SVGGElement | null;
      x: number;
      y: number;
      z: number;
    }> = [];
    svg.querySelectorAll<SVGGElement>("g[data-spatial-node]").forEach((el) => {
      const spatialNode = spatialNodes.get(
        el.getAttribute("data-spatial-node") ?? "",
      );
      if (spatialNode) {
        nodeTargets.push({
          el,
          inner: el.querySelector<SVGGElement>(".graph-canvas-node"),
          x: spatialNode.x,
          y: spatialNode.y,
          z: spatialNode.z,
        });
      }
    });
    const edgeTargets: Array<{
      el: SVGGElement;
      lines: SVGLineElement[];
      source: { x: number; y: number; z: number };
      target: { x: number; y: number; z: number };
    }> = [];
    svg.querySelectorAll<SVGGElement>("g[data-spatial-edge]").forEach((el) => {
      const s = spatialNodes.get(el.getAttribute("data-spatial-source") ?? "");
      const t = spatialNodes.get(el.getAttribute("data-spatial-target") ?? "");
      if (s && t) {
        edgeTargets.push({
          el,
          lines: Array.from(el.querySelectorAll<SVGLineElement>("line")),
          source: { x: s.x, y: s.y, z: s.z },
          target: { x: t.x, y: t.y, z: t.z },
        });
      }
    });

    const width = layout.width;
    const height = layout.height;

    // --- Particle canvas frame: fit the viewBox into the canvas box exactly
    // like the SVG's preserveAspectRatio="xMidYMid meet", at device pixels.
    const drawParticles = (
      pose: OrbitalGraphCameraTransform,
      timeSec: number,
      animate: boolean,
    ) => {
      const canvas = particleCanvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;
      const box = canvas.getBoundingClientRect();
      if (box.width < 1 || box.height < 1) return;
      const dpr = window.devicePixelRatio || 1;
      const pxWidth = Math.round(box.width * dpr);
      const pxHeight = Math.round(box.height * dpr);
      if (canvas.width !== pxWidth || canvas.height !== pxHeight) {
        canvas.width = pxWidth;
        canvas.height = pxHeight;
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, pxWidth, pxHeight);
      const fit = Math.min(box.width / width, box.height / height);
      const offsetX = (box.width - width * fit) / 2;
      const offsetY = (box.height - height * fit) / 2;
      ctx.setTransform(dpr * fit, 0, 0, dpr * fit, dpr * offsetX, dpr * offsetY);
      drawSpatialHiveParticles(
        ctx,
        particleField,
        pose,
        width,
        height,
        particleEnergyRef.current,
        timeSec,
        animate,
      );
    };

    // --- The single pose writer. Re-projects the stable spatial model through
    // `pose` and writes screen geometry only: node wrapper transform + fog
    // opacity, edge endpoints + fog + depth width factor, particle canvas.
    // Every Hive class (tiers, auras, selection, hover) lives on elements
    // *inside* these wrappers, so the polish composes on top untouched.
    // Last applied paint orders, so re-sorting (an appendChild pass) happens
    // only on frames where the projected occlusion order actually changed.
    let lastNodeOrder: SVGGElement[] = [];
    let lastEdgeOrder: SVGGElement[] = [];
    const reorderIfChanged = (
      sorted: Array<{ el: SVGGElement; depth: number }>,
      last: SVGGElement[],
    ): SVGGElement[] => {
      const next = sorted.map((entry) => entry.el);
      const changed =
        next.length !== last.length || next.some((el, i) => el !== last[i]);
      if (changed && next.length > 0) {
        const parent = next[0].parentNode;
        if (parent) {
          for (const el of next) parent.appendChild(el);
        }
      }
      return next;
    };

    const applyPose = (
      pose: OrbitalGraphCameraTransform,
      timeSec: number,
      animate: boolean,
    ) => {
      const nodePaint: Array<{ el: SVGGElement; depth: number }> = [];
      for (const target of nodeTargets) {
        const p = projectSpatialPoint(target.x, target.y, target.z, pose, width, height);
        target.el.setAttribute(
          "transform",
          `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)}) scale(${p.scale.toFixed(4)})`,
        );
        target.el.style.opacity = spatialNodeFog(p.depth).toFixed(3);
        // Camera-relative depth of field: back-of-field nodes soften, and a
        // far node swinging near under yaw resolves sharp. Emphasised nodes
        // (selected / related / hover-primary / keyboard focus) always render
        // clear — depth may recede them, it never smudges the active focus.
        const inner = target.inner;
        const emphasised =
          inner !== null &&
          (inner.classList.contains("graph-canvas-node-selected") ||
            inner.classList.contains("graph-canvas-node-related") ||
            inner.classList.contains("graph-canvas-node-hover-primary") ||
            inner === document.activeElement);
        const blur = emphasised ? 0 : spatialNodeBlur(p.depth);
        target.el.style.filter = blur > 0.04 ? `blur(${blur.toFixed(2)}px)` : "";
        nodePaint.push({ el: target.el, depth: p.depth });
      }
      const edgePaint: Array<{ el: SVGGElement; depth: number }> = [];
      for (const target of edgeTargets) {
        const ps = projectSpatialPoint(
          target.source.x, target.source.y, target.source.z, pose, width, height,
        );
        const pt = projectSpatialPoint(
          target.target.x, target.target.y, target.target.z, pose, width, height,
        );
        for (const line of target.lines) {
          line.setAttribute("x1", ps.x.toFixed(2));
          line.setAttribute("y1", ps.y.toFixed(2));
          line.setAttribute("x2", pt.x.toFixed(2));
          line.setAttribute("y2", pt.y.toFixed(2));
        }
        const meanDepth = (ps.depth + pt.depth) / 2;
        target.el.style.opacity = spatialEdgeFog(meanDepth).toFixed(3);
        target.el.style.setProperty(
          "--spatial-edge-w",
          spatialEdgeWidthFactor(meanDepth).toFixed(3),
        );
        edgePaint.push({ el: target.el, depth: meanDepth });
      }
      // Painter's algorithm on the live pose: far paints first, near last, so
      // orbiting visibly changes occlusion — the render-order half of depth.
      nodePaint.sort(compareProjectedDepth);
      edgePaint.sort(compareProjectedDepth);
      lastNodeOrder = reorderIfChanged(nodePaint, lastNodeOrder);
      lastEdgeOrder = reorderIfChanged(edgePaint, lastEdgeOrder);
      drawParticles(pose, timeSec, animate);
      appliedPoseRef.current = pose;
    };
    applyPoseRef.current = (pose) =>
      applyPose(pose, performance.now() / 1000, false);

    // Respect the OS reduced-motion preference: no loop, no parallax, no
    // shimmer — but the *static* pseudo-3D structure stays (visual contract:
    // keep static depth cues, drop movement). A live preference flip re-runs
    // this effect, so the pose is honestly neutral the moment it changes.
    if (prefersReducedMotion) {
      cameraPoseRef.current = ORBITAL_GRAPH_CAMERA_NEUTRAL;
      pointerPoseRef.current = SPATIAL_POINTER_NEUTRAL;
      pointerTargetRef.current = SPATIAL_POINTER_NEUTRAL;
      dragPoseRef.current = SPATIAL_POINTER_NEUTRAL;
      applyPose(ORBITAL_GRAPH_CAMERA_NEUTRAL, 0, false);
      onCameraStatus(
        graphControlEnabled
          ? {
              enabled: true,
              active: false,
              confidence: 0,
              reducedMotion: true,
              camera: ORBITAL_GRAPH_CAMERA_NEUTRAL,
            }
          : GRAPH_CONTROL_STATUS_OFF,
      );
      return () => {
        applyPoseRef.current = null;
      };
    }

    if (!graphControlEnabled) {
      // Camera held neutral and readout off; cursor parallax stays available.
      cameraPoseRef.current = ORBITAL_GRAPH_CAMERA_NEUTRAL;
      onCameraStatus(GRAPH_CONTROL_STATUS_OFF);
    }

    let frame = 0;
    let lastStatus = 0;

    // Drag-to-orbit gesture bookkeeping (closure-scoped; the accumulated pose
    // itself lives in dragPoseRef so it survives effect re-runs and Recenter
    // can clear it from outside).
    let pointerHeld = false;
    let dragPointerId = -1;
    let dragTravel = 0;
    let lastDragX = 0;
    let lastDragY = 0;
    let suppressNextClick = false;

    const tick = (now: number) => {
      // 1. Motion camera: integrate the gated command stream (only while the
      //    opt-in control is enabled — otherwise the motion pose holds
      //    neutral and the cursor owns the steering).
      if (graphControlEnabled) {
        const command = mapMotionCommandToOrbitalGraphControlCommand(
          motionCommandRef.current,
        );
        // Pass `now` so the integrator can drop a stale active command (e.g.
        // the sandbox loop stalled mid-motion) instead of drifting on it.
        const pose = integrateOrbitalCamera(cameraPoseRef.current, command, now);
        cameraPoseRef.current = pose;
        // Projection updates every frame; the React-facing readout stays
        // throttled to ~10Hz so the status text is legible and cheap.
        if (now - lastStatus >= 100) {
          lastStatus = now;
          onCameraStatus({
            enabled: true,
            active: command.active,
            confidence: command.confidence,
            reducedMotion: false,
            camera: pose,
          });
        }
      }

      // 2. Compose every steering input: motion pose + eased cursor parallax
      //    + persistent drag orbit + the slow ambient sway that keeps a
      //    whisper of parallax alive at rest (the floating-object tell).
      pointerPoseRef.current = easePointerPose(
        pointerPoseRef.current,
        pointerTargetRef.current,
      );
      const composed = composeSpatialCameraPose(
        cameraPoseRef.current,
        pointerPoseRef.current,
        dragPoseRef.current,
        ambientSwayPose(now / 1000),
      );
      applyPose(composed, now / 1000, true);

      // 3. The sway keeps the pose perpetually breathing, so the driver runs
      //    for the life of the (non-reduced-motion) surface — no sleep state.
      frame = requestAnimationFrame(tick);
    };

    // --- Direct manipulation: press-drag orbits the structure ---------------
    // Reads only cursor movement; never selection, never data. A press only
    // becomes a drag past the click threshold, so plain clicks keep their
    // normal target and the read-only select/deselect behavior is untouched.
    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      pointerHeld = true;
      dragPointerId = event.pointerId;
      dragTravel = 0;
      lastDragX = event.clientX;
      lastDragY = event.clientY;
    };

    const onPointerMove = (event: PointerEvent) => {
      const box = wrap.getBoundingClientRect();
      if (box.width < 1 || box.height < 1) return;
      if (pointerHeld && event.pointerId === dragPointerId) {
        const dx = event.clientX - lastDragX;
        const dy = event.clientY - lastDragY;
        lastDragX = event.clientX;
        lastDragY = event.clientY;
        dragTravel += Math.abs(dx) + Math.abs(dy);
        if (dragTravel > SPATIAL_DRAG_CLICK_THRESHOLD_PX) {
          // Real drag: capture the pointer so the orbit keeps following even
          // outside the surface, flag the trailing click for suppression so
          // orbiting never selects, and steer the persistent drag pose.
          // Capture is taken only after the threshold, so an ordinary click's
          // pointerup still lands on the node/edge it pressed.
          try {
            if (!wrap.hasPointerCapture(event.pointerId)) {
              wrap.setPointerCapture(event.pointerId);
            }
          } catch {
            // Capture is a smoothness nicety; dragging works without it.
          }
          suppressNextClick = true;
          wrap.classList.add("graph-orbiting");
          dragPoseRef.current = applyDragDelta(
            dragPoseRef.current,
            dx / box.width,
            dy / box.height,
          );
        }
        return; // while dragging, the cursor steers the orbit, not parallax
      }
      // Cursor parallax target: normalized offset from the surface centre,
      // mapped through the bounded parallax helper.
      const nx = ((event.clientX - box.left) / box.width) * 2 - 1;
      const ny = ((event.clientY - box.top) / box.height) * 2 - 1;
      pointerTargetRef.current = pointerParallaxTarget(nx, ny);
    };

    const endDrag = (event: PointerEvent) => {
      if (event.pointerId !== dragPointerId) return;
      pointerHeld = false;
      dragPointerId = -1;
      wrap.classList.remove("graph-orbiting");
      try {
        if (wrap.hasPointerCapture(event.pointerId)) {
          wrap.releasePointerCapture(event.pointerId);
        }
      } catch {
        // Nothing to release.
      }
      // The click a drag suppresses fires synchronously right after this
      // pointerup; if the gesture produced no click at all (released off-
      // surface / cancelled), disarm on the next task so the flag can never
      // linger and swallow a later, legitimate selection click.
      window.setTimeout(() => {
        suppressNextClick = false;
      }, 0);
    };

    const onPointerLeave = () => {
      pointerTargetRef.current = SPATIAL_POINTER_NEUTRAL;
    };

    // A gesture that travelled past the click threshold must not commit the
    // click it releases on (capture phase, so it is consumed before the
    // node/edge/empty-space handlers ever see it).
    const onClickCapture = (event: MouseEvent) => {
      if (suppressNextClick) {
        suppressNextClick = false;
        event.stopPropagation();
        event.preventDefault();
      }
    };

    // Double-click on empty space shakes off the accumulated drag + parallax
    // orbit — a no-chrome view reset (selection and data untouched). Node and
    // edge double-clicks are ignored so rapid selection clicks never recenter.
    const onDoubleClick = (event: MouseEvent) => {
      const target = event.target as Element | null;
      if (target?.closest("[data-spatial-node], [data-spatial-edge]")) return;
      dragPoseRef.current = SPATIAL_POINTER_NEUTRAL;
      pointerPoseRef.current = SPATIAL_POINTER_NEUTRAL;
      pointerTargetRef.current = SPATIAL_POINTER_NEUTRAL;
    };

    wrap.addEventListener("pointerdown", onPointerDown);
    wrap.addEventListener("pointermove", onPointerMove);
    wrap.addEventListener("pointerup", endDrag);
    wrap.addEventListener("pointercancel", endDrag);
    wrap.addEventListener("pointerleave", onPointerLeave);
    wrap.addEventListener("click", onClickCapture, true);
    wrap.addEventListener("dblclick", onDoubleClick);

    // Re-fit the particle canvas when the surface resizes (static redraw at
    // the current pose; the SVG scales itself via its viewBox).
    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => {
            applyPose(appliedPoseRef.current, performance.now() / 1000, false);
          })
        : null;
    resizeObserver?.observe(wrap);

    // Initial projection at the current composed pose (neutral on first
    // mount; drag/motion poses are preserved across toggles and layout
    // refreshes so nothing jumps), then the continuous driver loop.
    applyPose(
      composeSpatialCameraPose(
        cameraPoseRef.current,
        pointerPoseRef.current,
        dragPoseRef.current,
        ambientSwayPose(performance.now() / 1000),
      ),
      performance.now() / 1000,
      false,
    );
    frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame);
      wrap.removeEventListener("pointerdown", onPointerDown);
      wrap.removeEventListener("pointermove", onPointerMove);
      wrap.removeEventListener("pointerup", endDrag);
      wrap.removeEventListener("pointercancel", endDrag);
      wrap.removeEventListener("pointerleave", onPointerLeave);
      wrap.removeEventListener("click", onClickCapture, true);
      wrap.removeEventListener("dblclick", onDoubleClick);
      wrap.classList.remove("graph-orbiting");
      resizeObserver?.disconnect();
      applyPoseRef.current = null;
    };
  }, [
    graphControlEnabled,
    motionCommandRef,
    onCameraStatus,
    prefersReducedMotion,
    spatialNodes,
    particleField,
    layout.width,
    layout.height,
  ]);

  // Phase 32H — explicit recenter. Bumping `recenterSignal` from the panel snaps
  // the accumulated camera pose straight back to neutral, so the user never has
  // to wait out the idle decay to get a face-on view again. It resets ONLY the
  // visual transform — never nodes, edges, source data, or selection — and is
  // safe whether or not the rAF loop is running: when control is live the next
  // frame simply re-integrates from neutral; when it is disabled or reduced-
  // motion (no loop) this is the only writer and the reset sticks. The `=== 0`
  // guard skips the initial mount so we never fight the first render.
  useEffect(() => {
    if (recenterSignal === 0) return;
    cameraPoseRef.current = ORBITAL_GRAPH_CAMERA_NEUTRAL;
    // Phase 36F: recenter clears the cursor parallax and the persistent drag
    // orbit too, and re-projects the whole spatial structure at the neutral
    // pose immediately — face-on, level, unscaled — whether or not the driver
    // loop happens to be running.
    pointerPoseRef.current = SPATIAL_POINTER_NEUTRAL;
    pointerTargetRef.current = SPATIAL_POINTER_NEUTRAL;
    dragPoseRef.current = SPATIAL_POINTER_NEUTRAL;
    applyPoseRef.current?.(ORBITAL_GRAPH_CAMERA_NEUTRAL);
  }, [recenterSignal]);

  // Phase 36F — particle cluster energy. Each node's dust inherits its type
  // accent and the live Hive emphasis: the selected cluster burns brightest,
  // related clusters stay lit, unrelated clusters calm down while a selection
  // is active, and the hovered node's cloud lifts at rest. Derived (never
  // stored), pushed into a ref for the per-frame draw path, and redrawn once
  // per change so emphasis updates even while the driver loop is asleep.
  const particleEnergy = useMemo(() => {
    const m = new Map<string, SpatialParticleEnergy>();
    for (const node of nodes) {
      let energy = 1;
      if (node.id === selectedNodeId) {
        energy = 1.65;
      } else if (relatedNodeIds.has(node.id)) {
        energy = 1.3;
      } else if (hasSelection) {
        energy = 0.5;
      } else if (node.id === hoverNodeId) {
        energy = 1.35;
      }
      m.set(node.id, { color: nodeTypeColor(node.type), energy });
    }
    return m;
  }, [nodes, selectedNodeId, relatedNodeIds, hasSelection, hoverNodeId]);

  useEffect(() => {
    particleEnergyRef.current = particleEnergy;
    applyPoseRef.current?.(appliedPoseRef.current);
  }, [particleEnergy]);

  if (layout.nodes.length === 0) {
    return null;
  }

  // Phase 35B — transient interaction mode for the graph surface. Derived (not
  // stored) from the selection passed down, the canvas-local hover cue, and
  // whether orbital control is available. It only feeds the surface `data-*`
  // attributes and the readout copy below — it never persists, never mutates
  // data, and never changes selection. Hover stays canvas-local (Phase 29A
  // hover contract): it is surfaced here purely as a presentational attribute,
  // not lifted into panel/app state.
  const hasHover = hoverNodeId !== null || hoverEdge !== null;
  const interactionMode = resolveInteractionMode({
    selectionKind:
      selectedEdgeId !== null
        ? "edge"
        : selectedNodeId !== null
          ? "node"
          : null,
    hasHover,
    motionAvailable: graphControlEnabled,
  });
  // Label of the node currently under pointer / keyboard focus, for the
  // transient hover readout. Selection copy still wins in the hint below, so
  // this only ever surfaces while nothing is selected.
  const hoverNodeLabel =
    hoverNodeId !== null
      ? (nodes.find((node) => node.id === hoverNodeId)?.label ?? null)
      : null;

  return (
    <div
      className="viewfinder-canvas-wrap"
      // Phase 36F: the wrap anchors the cursor-parallax listeners and the
      // particle-canvas resize observer (both attached imperatively in the
      // spatial driver effect — read-only view steering, never data).
      ref={wrapRef}
      // Phase 35B: expose the resolved interaction mode + its raw inputs so CSS
      // can style idle / hover / focus / inspect / motion surface states without
      // any of it leaving the render path into persistence.
      data-interaction-mode={interactionMode}
      data-has-selection={hasSelection ? "true" : "false"}
      data-has-hover={hasHover ? "true" : "false"}
    >
      {/* Phase 32G camera stage, re-founded by Phase 36F: the camera pose is no
          longer written to this wrapper as a whole-layer CSS tilt (that read as
          a rotated flat poster). The stage now just hosts the point-cloud
          particle canvas and the SVG; the pose is applied *per element* by the
          spatial projection driver, so near and far objects move differently
          (true parallax) while node hit-testing and selection stay untouched —
          the camera still moves the view, never the data. */}
      <div
        className="graph-camera"
        data-graph-control={graphControlEnabled ? "on" : "off"}
      >
      {/* Phase 36F point-cloud layer: deterministic per-cluster dust drawn
          behind the SVG. Presentation only — pointer-events off, aria-hidden,
          and fed exclusively from the projected spatial model. */}
      <canvas
        className="graph-particle-canvas"
        ref={particleCanvasRef}
        aria-hidden="true"
      />
      <svg
        ref={svgRef}
        className="graph-canvas"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="group"
        aria-label="Knowledge graph visualization"
        preserveAspectRatio="xMidYMid meet"
        // Clicking empty canvas deselects; with nothing selected it does
        // nothing (Phase 29A "clicking empty graph space"). Node/edge clicks
        // land on painted child elements, so target === currentTarget is
        // true only for genuinely empty space.
        onClick={(event) => {
          if (event.target === event.currentTarget && hasSelection) {
            onClearSelection();
          }
        }}
      >
          <defs>
            <marker
              id="graph-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 z" className="graph-canvas-arrow" />
            </marker>
          </defs>

          <g className="graph-canvas-edges">
            {edgesRenderOrder.map((edge) => {
              const selected = edge.id === selectedEdgeId;
              const incident =
                selectedNodeId !== null &&
                (edge.source === selectedNodeId ||
                  edge.target === selectedNodeId);
              // Phase 29B three-tier emphasis: with a selection active, edges
              // that are neither selected nor incident recede so the active
              // context reads first. Hover lifts are purely additive.
              const dimmed = hasSelection && !selected && !incident;
              const hovered = hoverEdge?.id === edge.id;
              const hoverLift =
                hoverNodeId !== null &&
                (edge.source === hoverNodeId || edge.target === hoverNodeId);
              const className = [
                "graph-canvas-edge",
                selected ? "graph-canvas-edge-selected" : "",
                incident ? "graph-canvas-edge-incident" : "",
                dimmed ? "graph-canvas-edge-dimmed" : "",
                hovered ? "graph-canvas-edge-hovered" : "",
                hoverLift ? "graph-canvas-edge-hover-lift" : "",
              ]
                .filter(Boolean)
                .join(" ");
              const setHover = () =>
                setHoverEdge({
                  id: edge.id,
                  source: edge.source,
                  target: edge.target,
                });
              const clearHover = () =>
                setHoverEdge((current) =>
                  current?.id === edge.id ? null : current,
                );
              // Phase 33C: resting depth tier for the edge, inherited from its
              // nearer endpoint. Drives a subtle background/foreground fade so
              // deep links recede — but only while nothing is selected, so the
              // selection's own incident/dimmed hierarchy stays untouched.
              const edgeDepthTier = depth.edges.get(edge.id) ?? "mid";
              // Phase 36F: spatial synapse geometry. The outer wrapper carries
              // the camera-projected endpoints (updated per frame by the
              // driver), depth fog as element opacity (multiplies with the
              // tier/selection opacities on the inner group — never overrides
              // them), and the depth width factor consumed by the CSS ladder.
              const spatialEdge = initialEdgeProjection.get(edge.id);
              return (
                <g
                  key={edge.id}
                  className="graph-spatial-edge"
                  data-spatial-edge={edge.id}
                  data-spatial-source={edge.source}
                  data-spatial-target={edge.target}
                  style={
                    {
                      opacity: spatialEdge?.fog ?? 1,
                      "--spatial-edge-w": spatialEdge?.width ?? 1,
                    } as CSSProperties
                  }
                >
                <g
                  data-edge-type={edgeTypeById.get(edge.id) ?? ""}
                  className={`graph-depth-edge graph-depth-edge-${edgeDepthTier}`}
                >
                  <line
                    className={className}
                    x1={spatialEdge?.x1 ?? edge.x1}
                    y1={spatialEdge?.y1 ?? edge.y1}
                    x2={spatialEdge?.x2 ?? edge.x2}
                    y2={spatialEdge?.y2 ?? edge.y2}
                    markerEnd="url(#graph-arrow)"
                  />
                  {/* Wider transparent line so thin edges are easy to click. */}
                  <line
                    className="graph-canvas-edge-hit"
                    data-edge-id={edge.id}
                    x1={spatialEdge?.x1 ?? edge.x1}
                    y1={spatialEdge?.y1 ?? edge.y1}
                    x2={spatialEdge?.x2 ?? edge.x2}
                    y2={spatialEdge?.y2 ?? edge.y2}
                    role="button"
                    tabIndex={0}
                    aria-label={`Relationship ${edge.label ?? "edge"}`}
                    aria-pressed={selected}
                    onClick={() => onSelectEdge(edge.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSelectEdge(edge.id);
                      }
                    }}
                    onMouseEnter={setHover}
                    onMouseLeave={clearHover}
                    onFocus={setHover}
                    onBlur={clearHover}
                  />
                </g>
                </g>
              );
            })}
          </g>

          <g className="graph-canvas-nodes">
            {nodesRenderOrder.map((node) => {
              const selected = node.id === selectedNodeId;
              // Related nodes (direct neighbors of the selection, or the two
              // endpoints of a selected edge) form the middle emphasis tier:
              // brighter than dimmed ambient nodes, quieter than the
              // selection itself (Phase 29A "exactly three tiers").
              const isRelated = !selected && relatedNodeIds.has(node.id);
              const dimmed = hasSelection && !selected && !isRelated;
              const endpointLift =
                hoverEdge !== null &&
                (hoverEdge.source === node.id || hoverEdge.target === node.id);
              // Phase 31C: a direct neighbor of the hovered node. Guarded off
              // selected/related so this quiet "reveal local structure" lift is
              // purely additive on ambient nodes and never competes with — or
              // overrides — the selection hierarchy's own emphasis (hover must
              // not overpower selected state).
              const hoverNeighbor =
                !selected &&
                !isRelated &&
                hoverNodeId !== null &&
                hoverNodeId !== node.id &&
                (neighborsByNode.get(hoverNodeId)?.has(node.id) ?? false);
              // Phase 31F: the node actually under the pointer/focus, when it
              // is neither selected nor related. Lets the hovered node light up
              // its *own* faint aura (not just its neighbours'), so hover reads
              // as energy emanating from the node itself. Guarded off
              // selected/related so this quiet cue never competes with — or
              // overrides — the selection hierarchy's brighter aura tiers.
              const hoverPrimary =
                !selected && !isRelated && hoverNodeId === node.id;
              // Phase 33C: effective depth tier. When a selection is active it is
              // relationship-driven (selected anchors to near, its cluster lifts
              // to mid, everything else recedes to far) so Focus-State reads as a
              // spatial lift; at rest it falls back to the deterministic
              // structural tier so the idle Hive-State already reads as layered
              // space (visual contract §3/§5). Depth never hides the selection —
              // the selected node always resolves to near.
              const structuralDepth = depth.nodes.get(node.id);
              const depthTier: DepthTier = hasSelection
                ? selected
                  ? "near"
                  : isRelated
                    ? "mid"
                    : "far"
                : (structuralDepth?.tier ?? "mid");
              const depthScale = DEPTH_TIER_SCALE[depthTier];
              const className = [
                "graph-canvas-node",
                `graph-depth-tier-${depthTier}`,
                selected ? "graph-canvas-node-selected" : "",
                isRelated ? "graph-canvas-node-related" : "",
                dimmed ? "graph-canvas-node-dimmed" : "",
                endpointLift ? "graph-canvas-node-hover-endpoint" : "",
                hoverNeighbor ? "graph-canvas-node-hover-neighbor" : "",
                hoverPrimary ? "graph-canvas-node-hover-primary" : "",
              ]
                .filter(Boolean)
                .join(" ");
              // Phase 36F: spatial anchor for this node. The wrapper owns the
              // camera-projected translate + perspective scale (updated per
              // frame by the driver) and depth fog as element opacity; every
              // Hive class — tiers, aura, breathing, selection, hover — stays
              // on the inner group, so the living polish rides the projected
              // position untouched. Labels only ever translate/scale (never
              // rotate), so they remain readable billboard labels.
              const spatialProj = initialNodeProjection.get(node.id);
              return (
                <g
                  key={node.id}
                  className="graph-spatial-node"
                  data-spatial-node={node.id}
                  transform={spatialProj?.transform ?? `translate(${node.x} ${node.y})`}
                  style={{ opacity: spatialProj?.fog ?? 1 } as CSSProperties}
                >
                <g
                  className={className}
                  data-node-type={node.type}
                  data-node-id={node.id}
                  // Cluster breathing phase inherits to the circle so a type
                  // cluster breathes together at a reproducible offset.
                  style={
                    {
                      "--hive-phase": structuralDepth?.phase ?? 0,
                    } as CSSProperties
                  }
                  role="button"
                  tabIndex={0}
                  aria-label={`${node.label}, ${nodeTypeLabel(node.type)}, ${
                    node.degree
                  } connections`}
                  aria-pressed={selected}
                  onClick={() => onSelectNode(node.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectNode(node.id);
                    }
                  }}
                  onMouseEnter={() => setHoverNodeId(node.id)}
                  onMouseLeave={() =>
                    setHoverNodeId((current) =>
                      current === node.id ? null : current,
                    )
                  }
                  onFocus={() => setHoverNodeId(node.id)}
                  onBlur={() =>
                    setHoverNodeId((current) =>
                      current === node.id ? null : current,
                    )
                  }
                >
                  {/* Phase 33C depth stage: a display-only inner group that
                      scales the node's whole visual mass by its depth tier so
                      near nodes read forward and far nodes recede. Because the
                      parent group already carries the translate, this inner
                      group's origin (0,0) is the node centre, so the scale is
                      centred and never shifts the node's position, hit-testing,
                      or selection. The scale is eased in CSS for a calm
                      Hive↔Focus transition. */}
                  <g
                    className="graph-node-depth"
                    style={
                      { "--depth-scale": depthScale } as CSSProperties
                    }
                  >
                    {/* Phase 31B presentational aura ring: a concentric halo that
                        sits behind the node circle. Invisible at rest, it fades in
                        faintly for related neighbors and pulses for the selected
                        node — a distinct "energy" cue outside the node's own glow
                        that strengthens the selected/related hierarchy. pointer-
                        events are disabled in CSS so it never intercepts clicks or
                        changes selection/deselection behavior. */}
                    <circle
                      className="graph-canvas-node-aura"
                      r={node.radius + 7}
                      aria-hidden="true"
                    />
                    <circle className="graph-canvas-node-circle" r={node.radius} />
                    <text
                      className="graph-canvas-node-label"
                      y={node.radius + 14}
                      textAnchor="middle"
                    >
                      {truncateLabel(node.label)}
                    </text>
                  </g>
                </g>
                </g>
              );
            })}
          </g>
      </svg>
      </div>
      {/* Phase 31D: the surface hint is contextual rather than static. With
          nothing selected it explains the primary affordance; once a node or
          edge is active it switches to "how to clear" guidance and surfaces the
          Esc keyboard shortcut as a small chip, so the graph teaches its own
          interaction model without a tutorial panel. Purely presentational —
          it reads existing selection state and drives no data/selection flow. */}
      <p
        className={
          hasSelection
            ? "console-hint graph-canvas-hint viewfinder-canvas-hint graph-canvas-hint-active"
            : "console-hint graph-canvas-hint viewfinder-canvas-hint"
        }
      >
        {hasSelection ? (
          <>
            {selectedEdgeId !== null ? "Relationship selected" : "Node selected"}
            {" · "}
            <kbd className="graph-hint-key">Esc</kbd> or click empty space to
            clear
          </>
        ) : hoverNodeLabel !== null ? (
          // Phase 35B: transient hover context. It only appears with nothing
          // selected (selection copy above wins), so hover informs exploration
          // without ever replacing the selected-node inspection line.
          <>
            Hovering{" "}
            <span className="graph-hint-focus">
              {truncateLabel(hoverNodeLabel, 28)}
            </span>
            {" · select to inspect"}
          </>
        ) : hoverEdge !== null ? (
          <>Hovering a relationship · select to inspect</>
        ) : (
          "Read-only map · drag to orbit · select a node or relationship to inspect it."
        )}
      </p>
    </div>
  );
});

function KnowledgeGraphPanel({
  id,
  graphControlEnabled = false,
  motionCommandRef,
}: {
  id?: string;
  graphControlEnabled?: boolean;
  motionCommandRef?: RefObject<MotionCommand>;
}) {
  const [state, setState] = useState<PanelState>("loading");
  const [graph, setGraph] = useState<KnowledgeGraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  // Phase 28B: the legend/groups/lists explorer is a summoned overlay, closed
  // by default, rather than an always-visible side column — the graph alone
  // is the at-rest state (Phase 28A §1).
  const [explorerOpen, setExplorerOpen] = useState(false);

  // Phase 32G: live snapshot of the opt-in orbital camera, fed (throttled) from
  // the camera loop inside GraphCanvas so the panel can show a small readout.
  // Purely presentational — it drives no data or selection flow.
  const [controlStatus, setControlStatus] = useState<GraphControlStatus>(
    GRAPH_CONTROL_STATUS_OFF,
  );
  const handleCameraStatus = useCallback((status: GraphControlStatus) => {
    setControlStatus(status);
  }, []);

  // Phase 32H: a monotonic "recenter" signal. Bumping it tells GraphCanvas to
  // snap the orbital camera pose back to neutral. It carries no data of its own —
  // it only resets the visual transform, never selection or graph data — so the
  // user always has an obvious, instant way back to a face-on view after motion.
  const [recenterSignal, setRecenterSignal] = useState(0);
  const recenterCamera = useCallback(() => {
    setRecenterSignal((n) => n + 1);
  }, []);

  // The motion bridge is owned by App; keep a local idle fallback so the panel
  // (and its GraphCanvas) still type-check and run standalone when no bridge is
  // wired in. With no motion source, the fallback stays idle → camera neutral.
  const localMotionRef = useRef<MotionCommand>(ZERO_MOTION);
  const activeMotionRef = motionCommandRef ?? localMotionRef;

  // Phase 29B focus management (Phase 29A "opening an overlay should move
  // focus into it; dismissing it should return focus to the element that
  // summoned it"): the explorer pane takes focus when summoned and hands it
  // back to its toggle on dismissal; the inspector's close affordance hands
  // focus back to the selected element on the canvas.
  const panelRef = useRef<HTMLElement | null>(null);
  const explorerRef = useRef<HTMLElement | null>(null);
  const explorerToggleRef = useRef<HTMLButtonElement | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getKnowledgeGraph();
      setGraph(response);
      // A fresh payload may not contain the previously selected record, so
      // reset the inspector rather than leave a dangling selection.
      setSelection(null);
      setState("success");
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Network request failed. Is the backend running?",
      );
      setState("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // The view model is the single prepared, deterministic projection the panel
  // renders from — and the shape a future visual renderer will consume.
  const model = useMemo(() => buildGraphViewModel(graph), [graph]);

  // node id -> readable label, so edges can show endpoint names. Falls back to
  // the raw id when an edge references a node absent from the list.
  const labelFor = useCallback(
    (nodeId: string) =>
      model.nodes.find((node) => node.id === nodeId)?.label ?? nodeId,
    [model.nodes],
  );

  const selectedNode = useMemo(
    () =>
      selection?.kind === "node"
        ? (model.nodes.find((node) => node.id === selection.id) ?? null)
        : null,
    [selection, model.nodes],
  );

  const selectedEdge = useMemo(
    () =>
      selection?.kind === "edge"
        ? (model.edges.find((edge) => edge.id === selection.id) ?? null)
        : null,
    [selection, model.edges],
  );

  const selectNode = useCallback(
    (id: string) => setSelection({ kind: "node", id }),
    [],
  );
  const selectEdge = useCallback(
    (id: string) => setSelection({ kind: "edge", id }),
    [],
  );
  const clearSelection = useCallback(() => setSelection(null), []);

  /**
   * Close the inspector from its explicit close affordance: clear the
   * selection and return focus to the canvas element that anchored it, so
   * keyboard users land back on the graph rather than on <body>. The canvas
   * element stays mounted through the state change, so focusing it
   * synchronously here is safe.
   */
  const closeInspector = useCallback(() => {
    const host = panelRef.current;
    const target =
      host && selection
        ? host.querySelector<SVGElement>(
            selection.kind === "node"
              ? `[data-node-id="${CSS.escape(selection.id)}"]`
              : `[data-edge-id="${CSS.escape(selection.id)}"]`,
          )
        : null;
    setSelection(null);
    target?.focus();
  }, [selection]);

  /** Close the explorer and hand focus back to the toggle that summoned it. */
  const closeExplorer = useCallback(() => {
    setExplorerOpen(false);
    explorerToggleRef.current?.focus();
  }, []);

  // Move focus into the explorer pane when it opens (it is a summoned
  // surface, so focus follows the summons); closing paths return focus via
  // closeExplorer above.
  useEffect(() => {
    if (explorerOpen) {
      explorerRef.current?.focus();
    }
  }, [explorerOpen]);

  // Related elements drive the "focus + dim" hierarchy: with a selection
  // active, the selected record and anything connected to it stay prominent
  // while everything else is dimmed. Empty sets mean "nothing is related".
  const related = useMemo(() => {
    if (selectedNode) {
      return relatedToNode(model, selectedNode.id);
    }
    if (selectedEdge) {
      return {
        nodeIds: new Set([selectedEdge.source, selectedEdge.target]),
        edgeIds: new Set<string>(),
      };
    }
    return { nodeIds: new Set<string>(), edgeIds: new Set<string>() };
  }, [model, selectedNode, selectedEdge]);

  const hasSelection = selectedNode !== null || selectedEdge !== null;

  // Escape dismisses exactly one summoned surface per press, walking the
  // Phase 29A stack order (tertiary dock → explorer → selection/inspector;
  // the dock layer is handled in App.tsx before this handler can run). The
  // explorer closes before the selection so repeated presses step down to a
  // bare graph predictably. Scoped to the panel via onKeyDown.
  const handlePanelKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      if (event.key !== "Escape") {
        return;
      }
      if (explorerOpen) {
        closeExplorer();
      } else if (hasSelection) {
        clearSelection();
      }
    },
    [explorerOpen, closeExplorer, hasSelection, clearSelection],
  );

  const hasNodes = model.nodes.length > 0;
  const hasEdges = model.edges.length > 0;
  const isEmptyGraph = state === "success" && !hasNodes && !hasEdges;

  /** Class helpers: a row is "related" when connected to the selection, and
   * "dimmed" when a selection exists but this row is neither selected nor
   * related — giving inactive elements clearly lower visual weight. */
  const nodeStateFor = (id: string) => {
    const selected = selectedNode?.id === id;
    const isRelated = related.nodeIds.has(id);
    return { selected, related: isRelated, dimmed: hasSelection && !selected && !isRelated };
  };
  const edgeStateFor = (id: string) => {
    const selected = selectedEdge?.id === id;
    const isRelated = related.edgeIds.has(id);
    return { selected, related: isRelated, dimmed: hasSelection && !selected && !isRelated };
  };

  return (
    <section
      ref={panelRef}
      className="knowledge-graph-panel graph-viewfinder"
      id={id}
      // Phase 30B: the panel owns the explorer/selection Escape scope
      // (handlePanelKeyDown). Making it programmatically focusable (but not
      // tab-reachable) lets the shell return focus here after a dock closes,
      // so the next Escape lands inside this scope and keeps peeling surfaces
      // instead of dying on a rail button outside it. It never joins the tab
      // order, so keyboard traversal of the inner controls is unchanged.
      tabIndex={-1}
      onKeyDown={handlePanelKeyDown}
      data-has-selection={hasSelection ? "true" : "false"}
    >
      {/* Base layer: the graph canvas (or its loading/error/empty state) fills
          the entire viewfinder and reads as the app's living background. */}
      <div
        className="viewfinder-field"
        aria-live="polite"
        aria-busy={state === "loading"}
      >
        {state === "loading" && (
          <div className="graph-state-loading viewfinder-state" role="status">
            Loading knowledge graph…
          </div>
        )}

        {state === "error" && (
          <div className="graph-state-error viewfinder-state" role="alert">
            <p>Could not load the knowledge graph — {error}</p>
          </div>
        )}

        {state === "success" && isEmptyGraph && (
          <div className="graph-state-empty viewfinder-state">
            <p>
              The graph is empty. Import or register a source to populate
              nodes and relationships.
            </p>
          </div>
        )}

        {state === "success" && !isEmptyGraph && (
          <GraphCanvas
            nodes={model.nodes}
            edges={model.edges}
            selectedNodeId={selectedNode?.id ?? null}
            selectedEdgeId={selectedEdge?.id ?? null}
            relatedNodeIds={related.nodeIds}
            hasSelection={hasSelection}
            onSelectNode={selectNode}
            onSelectEdge={selectEdge}
            onClearSelection={clearSelection}
            graphControlEnabled={graphControlEnabled}
            motionCommandRef={activeMotionRef}
            onCameraStatus={handleCameraStatus}
            recenterSignal={recenterSignal}
          />
        )}
      </div>

      {/* Overlay layer: title, actions, legend, lists, and inspector float
          over the graph as glass chrome instead of stacking beneath it. */}
      <div className="viewfinder-chrome">
        <header className="viewfinder-topbar">
          <div className="viewfinder-title">
            <h2>Knowledge Graph</h2>
            <p className="console-hint graph-subtitle">
              A read-only, visualization-ready view of the graph derived from
              your sources.
            </p>
          </div>

          {state === "success" && (
            <SummaryMetrics
              nodeCount={model.nodeCount}
              edgeCount={model.edgeCount}
              connectedNodeCount={model.connectedNodeCount}
              isolatedNodeCount={model.isolatedNodeCount}
              compact
            />
          )}

          <div className="graph-head-actions">
            {state === "success" && !isEmptyGraph && (
              <button
                type="button"
                ref={explorerToggleRef}
                className={
                  explorerOpen
                    ? "source-refresh graph-explorer-toggle graph-explorer-toggle-active"
                    : "source-refresh graph-explorer-toggle"
                }
                aria-pressed={explorerOpen}
                aria-controls="graph-explorer-pane"
                title={
                  explorerOpen
                    ? "Hide legend & lists (Esc)"
                    : "Show the legend, groups, and node/edge lists"
                }
                onClick={() => setExplorerOpen((open) => !open)}
              >
                {explorerOpen ? "Hide legend" : "Legend & lists"}
              </button>
            )}
            <button
              type="button"
              className="source-refresh graph-reset"
              onClick={clearSelection}
              disabled={!hasSelection}
              title="Clear the current selection and dimming (Esc)"
            >
              Reset view
            </button>
            <button
              type="button"
              className="source-refresh"
              onClick={() => void load()}
              disabled={state === "loading"}
            >
              {state === "loading" ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </header>

        {/* Phase 32G — opt-in orbital camera readout. Rendered only while the
            user has motion control enabled (from the Motion Sandbox). Compact
            and informational: it never redesigns the dashboard and never mutates
            graph data — it just reports what the read-only camera is doing. */}
        {graphControlEnabled && (
          <div
            className="graph-control-readout"
            aria-live="polite"
            aria-label="Orbital motion control status"
          >
            <div className="graph-control-readout-head">
              <span className="graph-control-readout-title">Motion camera</span>
              <span
                className={
                  controlStatus.reducedMotion
                    ? "graph-control-state is-reduced"
                    : controlStatus.active
                      ? "graph-control-state is-live"
                      : "graph-control-state is-idle"
                }
              >
                {controlStatus.reducedMotion
                  ? "Reduced motion"
                  : controlStatus.active
                    ? "Live"
                    : "Idle"}
              </span>
            </div>
            {controlStatus.reducedMotion ? (
              <p className="graph-control-readout-note">
                Camera held neutral — your system prefers reduced motion.
              </p>
            ) : (
              <>
                <dl className="graph-control-metrics">
                  <div>
                    <dt>yaw</dt>
                    <dd>{controlStatus.camera.yaw.toFixed(1)}°</dd>
                  </div>
                  <div>
                    <dt>pitch</dt>
                    <dd>{controlStatus.camera.pitch.toFixed(1)}°</dd>
                  </div>
                  <div>
                    <dt>zoom</dt>
                    <dd>{controlStatus.camera.zoom.toFixed(2)}×</dd>
                  </div>
                </dl>
                <div
                  className="graph-control-confidence"
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={1}
                  aria-valuenow={Number(controlStatus.confidence.toFixed(2))}
                  aria-label="Motion control intensity"
                >
                  <span
                    className="graph-control-confidence-fill"
                    style={{
                      width: `${Math.max(0, Math.min(1, controlStatus.confidence)) * 100}%`,
                    }}
                  />
                </div>
                <p className="graph-control-readout-note">
                  Visual-only camera — it moves the view, never your graph data.
                  Still hands let it recentre on its own.
                </p>
              </>
            )}
            {/* Phase 32H — explicit recenter. Always available while control is on
                (even under reduced motion), needs no webcam, and only snaps the
                visual camera back to face-on — selection and data are untouched. */}
            <div className="graph-control-readout-actions">
              <button
                type="button"
                className="graph-control-recenter"
                onClick={recenterCamera}
                title="Snap the graph camera back to a face-on, level view"
              >
                Recenter camera
              </button>
            </div>
          </div>
        )}

        {/* Explorer tray: summoned from the topbar toggle rather than a
            permanently mounted side column (Phase 28A §1/§2 — a graph-loaded
            state must not imply a persistent split-column layout). */}
        {state === "success" && !isEmptyGraph && explorerOpen && (
          <aside
            id="graph-explorer-pane"
            ref={explorerRef}
            // Focusable as a container so summoning it can move focus into
            // the pane without adding it to the tab order.
            tabIndex={-1}
            className="viewfinder-pane viewfinder-pane-explorer"
            aria-label="Graph legend, groups, and lists"
          >
            <div className="viewfinder-pane-head">
              <h3>Legend &amp; lists</h3>
              <button
                type="button"
                className="viewfinder-pane-close"
                aria-label="Close legend and lists (Escape)"
                title="Close (Esc)"
                onClick={closeExplorer}
              >
                Close
              </button>
            </div>

            <GraphLegend
              nodeTypes={model.nodeTypes}
              relationshipTypes={model.relationshipTypes}
              connectedNodeCount={model.connectedNodeCount}
              isolatedNodeCount={model.isolatedNodeCount}
            />

            <div className="graph-section">
              <h3 className="graph-section-title">Groups</h3>
              {model.groups.length === 0 ? (
                <p className="console-hint">No nodes to group yet.</p>
              ) : (
                <ul className="graph-group-list">
                  {model.groups.map((group) => (
                    <li key={group.name} className="graph-group-chip">
                      <span className="graph-group-name">{group.name}</span>
                      <span className="graph-group-count">
                        {group.count}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {model.topConnectedNodes.length > 0 && (
              <div className="graph-section">
                <h3 className="graph-section-title">Top connected nodes</h3>
                <ul className="graph-node-list" onKeyDown={handleListArrowKeys}>
                  {model.topConnectedNodes.map((node) => (
                    <NodeRow
                      key={node.id}
                      node={node}
                      {...nodeStateFor(node.id)}
                      onSelect={() => selectNode(node.id)}
                    />
                  ))}
                </ul>
              </div>
            )}

            <div className="graph-section">
              <h3 className="graph-section-title">Nodes</h3>
              {hasNodes ? (
                <ul className="graph-node-list" onKeyDown={handleListArrowKeys}>
                  {model.nodes.map((node) => (
                    <NodeRow
                      key={node.id}
                      node={node}
                      {...nodeStateFor(node.id)}
                      onSelect={() => selectNode(node.id)}
                    />
                  ))}
                </ul>
              ) : (
                <p className="console-hint">
                  No nodes yet. Import or register a source to populate the
                  graph.
                </p>
              )}
            </div>

            <div className="graph-section">
              <h3 className="graph-section-title">Relationships</h3>
              {hasEdges ? (
                <ul className="graph-edge-list" onKeyDown={handleListArrowKeys}>
                  {model.edges.map((edge) => (
                    <EdgeRow
                      key={edge.id}
                      edge={edge}
                      labelFor={labelFor}
                      {...edgeStateFor(edge.id)}
                      onSelect={() => selectEdge(edge.id)}
                    />
                  ))}
                </ul>
              ) : (
                <p className="console-hint">
                  No relationships yet. Edges appear once nodes are linked.
                </p>
              )}
            </div>
          </aside>
        )}

        {/* Node inspector: mounts only once something is selected. Phase 28B
            correction — this used to render an always-visible pane with a
            "select a node…" placeholder any time the graph had data, which
            reads as a permanent detail column; the bottom-left canvas hint
            already communicates the selection affordance, so the quiet,
            graph-first empty state is simply "no pane at all" (Phase 28A
            §3/§6, "Empty state should be quiet and graph-first"). */}
        {hasSelection && (
          <aside
            className="viewfinder-pane viewfinder-pane-inspector"
            aria-label="Inspector"
          >
            <div className="viewfinder-pane-head">
              <h3>Inspector</h3>
              <button
                type="button"
                className="viewfinder-pane-close"
                aria-label="Close inspector and return focus to the graph (Escape)"
                title="Close (Esc)"
                onClick={closeInspector}
              >
                Close
              </button>
            </div>

            <GraphInspector
              node={selectedNode}
              edge={selectedEdge}
              labelFor={labelFor}
            />
          </aside>
        )}
      </div>
    </section>
  );
}

export default KnowledgeGraphPanel;
