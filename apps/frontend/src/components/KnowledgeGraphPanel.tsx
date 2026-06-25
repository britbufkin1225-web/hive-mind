import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { HiveMetadata, KnowledgeGraphResponse } from "../types/api";
import {
  buildGraphViewModel,
  nodeTypeLabel,
  type GraphViewEdge,
  type GraphViewNode,
} from "../lib/graphViewModel";
import { computeGraphLayout } from "../lib/graphLayout";

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

function NodeRow({
  node,
  selected,
  onSelect,
}: {
  node: GraphViewNode;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={`graph-node-row${selected ? " graph-row-selected" : ""}`}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <span className="graph-node-row-head">
          <span className="graph-node-name">{node.label}</span>
          <span className="graph-node-type">{nodeTypeLabel(node.type)}</span>
        </span>
        <span className="graph-node-row-sub">
          <span className="graph-node-degree" title="incoming / outgoing">
            {node.incomingCount} in · {node.outgoingCount} out
          </span>
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
  onSelect,
}: {
  edge: GraphViewEdge;
  labelFor: (nodeId: string) => string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={`graph-edge-row${selected ? " graph-row-selected" : ""}`}
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

function KnowledgeGraphPanel() {
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

  const hasNodes = model.nodes.length > 0;
  const hasEdges = model.edges.length > 0;
  const isEmptyGraph = state === "success" && !hasNodes && !hasEdges;

  return (
    <section className="knowledge-graph-panel">
      <div className="source-registry-head">
        <div>
          <h2>Knowledge Graph</h2>
          <p className="console-hint graph-subtitle">
            A read-only, visualization-ready view of the graph derived from your
            sources.
          </p>
        </div>
        <button
          type="button"
          className="source-refresh"
          onClick={() => void load()}
          disabled={state === "loading"}
        >
          {state === "loading" ? "Refreshing…" : "Refresh"}
        </button>
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
                    <ul className="graph-node-list">
                      {model.topConnectedNodes.map((node) => (
                        <NodeRow
                          key={node.id}
                          node={node}
                          selected={selectedNode?.id === node.id}
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
                        <ul className="graph-node-list">
                          {model.nodes.map((node) => (
                            <NodeRow
                              key={node.id}
                              node={node}
                              selected={selectedNode?.id === node.id}
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
                        <ul className="graph-edge-list">
                          {model.edges.map((edge) => (
                            <EdgeRow
                              key={edge.id}
                              edge={edge}
                              labelFor={labelFor}
                              selected={selectedEdge?.id === edge.id}
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
