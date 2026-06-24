import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type {
  HiveGraphEdge,
  HiveGraphNode,
  HiveGraphNodeType,
  HiveGraphRelationship,
  HiveMetadata,
  KnowledgeGraphResponse,
} from "../types/api";

type PanelState = "loading" | "success" | "error";

const NODE_TYPE_LABELS: Record<HiveGraphNodeType, string> = {
  root: "Root",
  folder: "Folder",
  file: "File",
  concept: "Concept",
  note: "Note",
  model: "Model",
  source: "Source",
};

const RELATIONSHIP_LABELS: Record<HiveGraphRelationship, string> = {
  contains: "Contains",
  references: "References",
  related: "Related",
  generated_from: "Generated from",
  linked_to: "Linked to",
};

function nodeTypeLabel(type: HiveGraphNodeType): string {
  return NODE_TYPE_LABELS[type] ?? type;
}

function relationshipLabel(relationship: HiveGraphRelationship): string {
  return RELATIONSHIP_LABELS[relationship] ?? relationship;
}

/** Format an ISO timestamp for display, falling back to the raw value. */
function formatDate(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

/** Render a metadata value as a readable string. */
function formatMetaValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

/**
 * Read a numeric confidence-style value out of edge metadata, if present.
 * The backend may attach a ``confidence``/``weight`` style hint; anything that
 * is not a finite number is treated as absent so nothing renders as "NaN".
 */
function metaNumber(metadata: HiveMetadata, key: string): number | null {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function NodeCard({
  node,
  selected,
  onSelect,
}: {
  node: HiveGraphNode;
  selected: boolean;
  onSelect: () => void;
}) {
  const sourceId = node.source_id;
  return (
    <li>
      <button
        type="button"
        className={`graph-node-card${selected ? " graph-node-card-selected" : ""}`}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <span className="graph-node-card-head">
          <span className="graph-node-name">{node.label}</span>
          <span className="graph-node-type">{nodeTypeLabel(node.type)}</span>
        </span>
        <span className="graph-node-card-sub">
          {sourceId ? `Source: ${sourceId}` : "No source"}
          {node.tags.length > 0 ? ` · ${node.tags.join(", ")}` : ""}
        </span>
      </button>
    </li>
  );
}

function NodeInspector({ node }: { node: HiveGraphNode | null }) {
  if (node === null) {
    return (
      <div className="graph-inspector graph-inspector-empty">
        <p className="console-hint">Select a node to view its details.</p>
      </div>
    );
  }

  const metadataEntries = Object.entries(node.metadata ?? {});

  return (
    <div className="graph-inspector">
      <div className="graph-inspector-head">
        <h3>{node.label}</h3>
        <span className="graph-node-type">{nodeTypeLabel(node.type)}</span>
      </div>

      <dl className="source-meta">
        <div>
          <dt>ID</dt>
          <dd>
            <code>{node.id}</code>
          </dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{nodeTypeLabel(node.type)}</dd>
        </div>
        <div>
          <dt>Source ID</dt>
          <dd>{node.source_id ?? "—"}</dd>
        </div>
        <div>
          <dt>Parent ID</dt>
          <dd>{node.parent_id ?? "—"}</dd>
        </div>
        <div>
          <dt>Tags</dt>
          <dd>{node.tags.length > 0 ? node.tags.join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Weight</dt>
          <dd>{node.weight}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDate(node.created_at)}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{formatDate(node.updated_at)}</dd>
        </div>
      </dl>

      <div className="graph-inspector-metadata">
        <span className="result-key">Metadata</span>
        {metadataEntries.length === 0 ? (
          <span className="console-hint"> (none)</span>
        ) : (
          <dl className="source-meta">
            {metadataEntries.map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{formatMetaValue(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

function EdgeRow({
  edge,
  labelFor,
}: {
  edge: HiveGraphEdge;
  labelFor: (nodeId: string) => string;
}) {
  const confidence =
    metaNumber(edge.metadata ?? {}, "confidence") ??
    metaNumber(edge.metadata ?? {}, "weight");

  return (
    <li className="graph-edge-row">
      <span className="graph-edge-endpoints">
        <span className="graph-edge-node">{labelFor(edge.source_node_id)}</span>
        <span className="graph-edge-arrow" aria-hidden="true">
          →
        </span>
        <span className="graph-edge-node">{labelFor(edge.target_node_id)}</span>
      </span>
      <span className="graph-edge-meta">
        <span className="graph-edge-relationship">
          {relationshipLabel(edge.relationship)}
        </span>
        {confidence !== null && (
          <span className="graph-edge-confidence">
            confidence {confidence}
          </span>
        )}
      </span>
    </li>
  );
}

function KnowledgeGraphPanel() {
  const [state, setState] = useState<PanelState>("loading");
  const [graph, setGraph] = useState<KnowledgeGraphResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getKnowledgeGraph();
      setGraph(response);
      // Keep the current selection if the node still exists; otherwise clear.
      setSelectedId((current) =>
        current && response.nodes.some((n) => n.id === current) ? current : null,
      );
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

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  // node id -> label, so edges can render readable endpoint names. Falls back
  // to the raw id when an edge references a node that isn't in the list.
  const nodeLabels = useMemo(() => {
    const map = new Map<string, string>();
    for (const node of nodes) {
      map.set(node.id, node.label);
    }
    return map;
  }, [nodes]);

  const labelFor = useCallback(
    (nodeId: string) => nodeLabels.get(nodeId) ?? nodeId,
    [nodeLabels],
  );

  // Sources are not in the summary, but a distinct-source count is a useful,
  // read-only figure we can derive from the nodes themselves.
  const sourceCount = useMemo(() => {
    const ids = new Set<string>();
    for (const node of nodes) {
      if (node.source_id) {
        ids.add(node.source_id);
      }
    }
    return ids.size;
  }, [nodes]);

  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedId) ?? null,
    [nodes, selectedId],
  );

  const nodeCount = graph?.summary.node_count ?? nodes.length;
  const edgeCount = graph?.summary.edge_count ?? edges.length;

  return (
    <section className="knowledge-graph-panel">
      <div className="source-registry-head">
        <div>
          <h2>Knowledge Graph</h2>
          <p className="console-hint graph-subtitle">
            A read-only view of the graph data derived from your sources.
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
            <dl className="graph-summary" aria-label="Graph summary">
              <div>
                <dt>Nodes</dt>
                <dd>{nodeCount}</dd>
              </div>
              <div>
                <dt>Edges</dt>
                <dd>{edgeCount}</dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>{sourceCount}</dd>
              </div>
            </dl>

            <div className="graph-section">
              <h3 className="graph-section-title">Nodes</h3>
              {nodes.length === 0 ? (
                <p className="console-hint">
                  No nodes yet. Import or register a source to populate the
                  graph.
                </p>
              ) : (
                <div className="source-registry-layout">
                  <ul className="graph-node-list">
                    {nodes.map((node) => (
                      <NodeCard
                        key={node.id}
                        node={node}
                        selected={node.id === selectedId}
                        onSelect={() => setSelectedId(node.id)}
                      />
                    ))}
                  </ul>
                  <NodeInspector node={selectedNode} />
                </div>
              )}
            </div>

            <div className="graph-section">
              <h3 className="graph-section-title">Relationships</h3>
              {edges.length === 0 ? (
                <p className="console-hint">
                  No relationships yet. Edges appear once nodes are linked.
                </p>
              ) : (
                <ul className="graph-edge-list">
                  {edges.map((edge) => (
                    <EdgeRow key={edge.id} edge={edge} labelFor={labelFor} />
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

export default KnowledgeGraphPanel;
