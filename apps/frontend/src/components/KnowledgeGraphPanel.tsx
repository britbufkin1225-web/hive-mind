import type { KeyboardEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { HiveMetadata, KnowledgeGraphResponse } from "../types/api";
import {
  buildGraphViewModel,
  nodeTypeColor,
  nodeTypeLabel,
  relatedToNode,
  type GraphTypeSummary,
  type GraphViewEdge,
  type GraphViewNode,
} from "../lib/graphViewModel";
import { computeGraphLayout } from "../lib/graphLayout";

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
 * The panel holds a single selection that is either a node or an edge (or
 * nothing). Keeping it as one discriminated value means selecting a node
 * naturally deselects any edge and vice versa, so the inspector always shows
 * exactly one record.
 */
type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string }
  | null;

/** Render a metadata value as a readable string (mirrors the Sources panel). */
function formatMetaValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function SummaryMetrics({
  nodeCount,
  edgeCount,
  connectedNodeCount,
  isolatedNodeCount,
}: {
  nodeCount: number;
  edgeCount: number;
  connectedNodeCount: number;
  isolatedNodeCount: number;
}) {
  const metrics: Array<[string, number]> = [
    ["Nodes", nodeCount],
    ["Edges", edgeCount],
    ["Connected", connectedNodeCount],
    ["Isolated", isolatedNodeCount],
  ];
  return (
    <dl className="graph-summary" aria-label="Graph summary">
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
                <span className="graph-legend-edge" aria-hidden="true" />
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
    <div className="graph-inspector">
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
      <p className="console-hint">
        Select a node or edge to inspect graph details.
      </p>
    </div>
  );
}

/** Trim a node label so it stays legible beside its circle on the canvas. */
function truncateLabel(label: string, max = 22): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

/**
 * Read-only SVG visualization of the graph. Renders nodes and relationships in
 * the deterministic ring layout and reports node/edge clicks back up so the
 * existing inspector stays the single source of selection truth. Purely
 * presentational: it draws from the prepared view model and mutates nothing.
 */
function GraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
}: {
  nodes: GraphViewNode[];
  edges: GraphViewEdge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  onSelectNode: (id: string) => void;
  onSelectEdge: (id: string) => void;
}) {
  const layout = useMemo(
    () => computeGraphLayout(nodes, edges),
    [nodes, edges],
  );

  if (layout.nodes.length === 0) {
    return null;
  }

  return (
    <div className="graph-section">
      <h3 className="graph-section-title">Graph map</h3>
      <div className="graph-canvas-wrap">
        <svg
          className="graph-canvas"
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="group"
          aria-label="Knowledge graph visualization"
          preserveAspectRatio="xMidYMid meet"
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
            {layout.edges.map((edge) => {
              const selected = edge.id === selectedEdgeId;
              const incident =
                selectedNodeId !== null &&
                (edge.source === selectedNodeId ||
                  edge.target === selectedNodeId);
              const className = [
                "graph-canvas-edge",
                selected ? "graph-canvas-edge-selected" : "",
                incident ? "graph-canvas-edge-incident" : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <g key={edge.id}>
                  <line
                    className={className}
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    markerEnd="url(#graph-arrow)"
                  />
                  {/* Wider transparent line so thin edges are easy to click. */}
                  <line
                    className="graph-canvas-edge-hit"
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
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
                  />
                </g>
              );
            })}
          </g>

          <g className="graph-canvas-nodes">
            {layout.nodes.map((node) => {
              const selected = node.id === selectedNodeId;
              return (
                <g
                  key={node.id}
                  className={`graph-canvas-node${
                    selected ? " graph-canvas-node-selected" : ""
                  }`}
                  transform={`translate(${node.x}, ${node.y})`}
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
                >
                  <circle className="graph-canvas-node-circle" r={node.radius} />
                  <text
                    className="graph-canvas-node-label"
                    y={node.radius + 14}
                    textAnchor="middle"
                  >
                    {truncateLabel(node.label)}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
        <p className="console-hint graph-canvas-hint">
          Read-only map · select a node or relationship to inspect it.
        </p>
      </div>
    </div>
  );
}

function KnowledgeGraphPanel({ id }: { id?: string }) {
  const [state, setState] = useState<PanelState>("loading");
  const [graph, setGraph] = useState<KnowledgeGraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>(null);

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

  // Escape clears the selection, so keyboard users can reset focus state
  // without reaching for the mouse. Scoped to the panel via onKeyDown.
  const handlePanelKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      if (event.key === "Escape" && hasSelection) {
        clearSelection();
      }
    },
    [hasSelection, clearSelection],
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
    <section className="knowledge-graph-panel" id={id} onKeyDown={handlePanelKeyDown}>
      <div className="source-registry-head">
        <div>
          <h2>Knowledge Graph</h2>
          <p className="console-hint graph-subtitle">
            A read-only, visualization-ready view of the graph derived from your
            sources.
          </p>
        </div>
        <div className="graph-head-actions">
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
      </div>

      <div aria-live="polite" aria-busy={state === "loading"}>
        {state === "loading" && (
          <p className="console-hint">Loading knowledge graph…</p>
        )}

        {state === "error" && (
          <p className="error" role="alert">
            Error: could not load the knowledge graph — {error}
          </p>
        )}

        {state === "success" && (
          <>
            <SummaryMetrics
              nodeCount={model.nodeCount}
              edgeCount={model.edgeCount}
              connectedNodeCount={model.connectedNodeCount}
              isolatedNodeCount={model.isolatedNodeCount}
            />

            {!isEmptyGraph && (
              <GraphLegend
                nodeTypes={model.nodeTypes}
                relationshipTypes={model.relationshipTypes}
                connectedNodeCount={model.connectedNodeCount}
                isolatedNodeCount={model.isolatedNodeCount}
              />
            )}

            {isEmptyGraph ? (
              <p className="console-hint">
                The graph is empty. Import or register a source to populate
                nodes and relationships.
              </p>
            ) : (
              <>
                <GraphCanvas
                  nodes={model.nodes}
                  edges={model.edges}
                  selectedNodeId={selectedNode?.id ?? null}
                  selectedEdgeId={selectedEdge?.id ?? null}
                  onSelectNode={selectNode}
                  onSelectEdge={selectEdge}
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

                <div className="graph-explorer-layout">
                  <div className="graph-lists">
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
                          No nodes yet. Import or register a source to populate
                          the graph.
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
                          No relationships yet. Edges appear once nodes are
                          linked.
                        </p>
                      )}
                    </div>
                  </div>

                  <aside className="graph-inspector-aside" aria-label="Inspector">
                    <GraphInspector
                      node={selectedNode}
                      edge={selectedEdge}
                      labelFor={labelFor}
                    />
                  </aside>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </section>
  );
}

export default KnowledgeGraphPanel;
