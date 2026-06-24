import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type {
  RegistrySourceStatus,
  RegistrySourceType,
  SourceRecord,
} from "../types/api";

type PanelState = "loading" | "success" | "error";

const TYPE_LABELS: Record<RegistrySourceType, string> = {
  obsidian: "Obsidian",
  local_files: "Local Files",
  github: "GitHub",
  pdf: "PDF",
  web: "Web",
  api: "API",
};

const STATUS_LABELS: Record<RegistrySourceStatus, string> = {
  active: "Active",
  inactive: "Inactive",
  error: "Error",
  pending: "Pending",
};

function typeLabel(type: RegistrySourceType): string {
  return TYPE_LABELS[type] ?? type;
}

function statusLabel(status: RegistrySourceStatus): string {
  return STATUS_LABELS[status] ?? status;
}

/** Format an ISO timestamp for display, falling back to the raw value. */
function formatDate(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

function SourceCard({ source }: { source: SourceRecord }) {
  const metadataEntries = Object.entries(source.metadata ?? {});

  return (
    <li className="source-card">
      <div className="source-card-head">
        <span className="source-name">{source.name}</span>
        <span className={`source-status source-status-${source.status}`}>
          {statusLabel(source.status)}
        </span>
      </div>
      <dl className="source-meta">
        <div>
          <dt>Type</dt>
          <dd>{typeLabel(source.type)}</dd>
        </div>
        <div>
          <dt>Path</dt>
          <dd>{source.root_path ?? "—"}</dd>
        </div>
        <div>
          <dt>Last import</dt>
          <dd>{formatDate(source.last_imported_at)}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDate(source.created_at)}</dd>
        </div>
        {metadataEntries.length > 0 &&
          metadataEntries.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>
                {typeof value === "string" ? value : JSON.stringify(value)}
              </dd>
            </div>
          ))}
      </dl>
    </li>
  );
}

function SourceRegistryPanel() {
  const [state, setState] = useState<PanelState>("loading");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getRegistrySources();
      setSources(response.sources);
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

  return (
    <section className="source-registry-panel">
      <div className="source-registry-head">
        <h2>Sources</h2>
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
          <p className="console-hint">Loading registered sources…</p>
        )}

        {state === "error" && (
          <p className="error" role="alert">
            Error: could not load sources — {error}
          </p>
        )}

        {state === "success" &&
          (sources.length === 0 ? (
            <p className="console-hint">
              No sources registered yet. Connectors will appear here once
              registered.
            </p>
          ) : (
            <ul className="source-list">
              {sources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </ul>
          ))}
      </div>
    </section>
  );
}

export default SourceRegistryPanel;
