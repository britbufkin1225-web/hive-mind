import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { KnowledgeGraphResponse } from "../types/api";
import {
  buildGraphViewModel,
  nodeTypeLabel,
  type GraphViewEdge,
  type GraphViewNode,
} from "../lib/graphViewModel";

type PanelState = "loading" | "success" | "error";

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

function NodeRow({ node }: { node: GraphViewNode }) {
  return (
    <li className="graph-node-row">
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
    </li>
  );
}

function EdgeRow({
  edge,
  labelFor,
}: {
  edge: GraphViewEdge;
  labelFor: (nodeId: string) => string;
}) {
  return (
    <li className="graph-edge-row">
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
    </li>
  );
}

function KnowledgeGraphPanel() {
  const [state, setState] = useState<PanelState>("loading");
  const [graph, setGraph] = useState<KnowledgeGraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getKnowledgeGraph();
      setGraph(response);
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

  const hasNodes = model.nodes.length > 0;
  const hasEdges = model.edges.length > 0;

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

            <div className="graph-section">
              <h3 className="graph-section-title">Groups</h3>
              {model.groups.length === 0 ? (
                <p className="console-hint">No nodes to group yet.</p>
              ) : (
                <ul className="graph-group-list">
                  {model.groups.map((group) => (
                    <li key={group.name} className="graph-group-chip">
                      <span className="graph-group-name">{group.name}</span>
                      <span className="graph-group-count">{group.count}</span>
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
                    <NodeRow key={node.id} node={node} />
                  ))}
                </ul>
              </div>
            )}

            <div className="graph-section">
              <h3 className="graph-section-title">Nodes</h3>
              {hasNodes ? (
                <ul className="graph-node-list">
                  {model.nodes.map((node) => (
                    <NodeRow key={node.id} node={node} />
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
                <ul className="graph-edge-list">
                  {model.edges.map((edge) => (
                    <EdgeRow key={edge.id} edge={edge} labelFor={labelFor} />
                  ))}
                </ul>
              ) : (
                <p className="console-hint">
                  No relationships yet. Edges appear once nodes are linked.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

export default KnowledgeGraphPanel;
