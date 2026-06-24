import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type {
  HiveMetadata,
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

/** Pull a human-readable description out of metadata if one is present. */
function description(metadata: HiveMetadata): string | null {
  const value = metadata?.description;
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

/** Render a metadata value as a readable string. */
function formatMetaValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function SourceCard({
  source,
  selected,
  onSelect,
}: {
  source: SourceRecord;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={`source-card${selected ? " source-card-selected" : ""}`}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <span className="source-card-head">
          <span className="source-name">{source.name}</span>
          <span className={`source-status source-status-${source.status}`}>
            {statusLabel(source.status)}
          </span>
        </span>
        <span className="source-card-sub">
          {typeLabel(source.type)}
          {source.root_path ? ` · ${source.root_path}` : ""}
        </span>
      </button>
    </li>
  );
}

function SourceInspector({ source }: { source: SourceRecord | null }) {
  if (source === null) {
    return (
      <div className="source-inspector source-inspector-empty">
        <p className="console-hint">
          Select a source to view its details.
        </p>
      </div>
    );
  }

  const desc = description(source.metadata ?? {});
  // Show every metadata key except the description we already surface above.
  const metadataEntries = Object.entries(source.metadata ?? {}).filter(
    ([key]) => !(key === "description" && desc !== null),
  );

  return (
    <div className="source-inspector">
      <div className="source-inspector-head">
        <h3>{source.name}</h3>
        <span className={`source-status source-status-${source.status}`}>
          {statusLabel(source.status)}
        </span>
      </div>

      {desc && <p className="source-description">{desc}</p>}

      <dl className="source-meta">
        <div>
          <dt>ID</dt>
          <dd>
            <code>{source.id}</code>
          </dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{typeLabel(source.type)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{statusLabel(source.status)}</dd>
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
        <div>
          <dt>Updated</dt>
          <dd>{formatDate(source.updated_at)}</dd>
        </div>
      </dl>

      <div className="source-inspector-metadata">
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

function SourceRegistryPanel() {
  const [state, setState] = useState<PanelState>("loading");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getRegistrySources();
      setSources(response.sources);
      // Keep the current selection if it still exists; otherwise clear it.
      setSelectedId((current) =>
        current && response.sources.some((s) => s.id === current)
          ? current
          : null,
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

  const selectedSource = useMemo(
    () => sources.find((source) => source.id === selectedId) ?? null,
    [sources, selectedId],
  );

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
            <div className="source-registry-layout">
              <ul className="source-list">
                {sources.map((source) => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    selected={source.id === selectedId}
                    onSelect={() => setSelectedId(source.id)}
                  />
                ))}
              </ul>
              <SourceInspector source={selectedSource} />
            </div>
          ))}
      </div>
    </section>
  );
}

export default SourceRegistryPanel;
