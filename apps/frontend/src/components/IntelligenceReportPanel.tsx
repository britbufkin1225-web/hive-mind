import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type {
  DecayStatus,
  DecayStatusBucket,
  DreamingSuggestion,
  DreamingSuggestionStatus,
  DreamingSuggestionType,
  IntelligenceReport,
  ProvenanceChain,
  QueryTrailEntry,
  QueryTrailStatus,
} from "../types/api";

type PanelState = "loading" | "success" | "error";

const SUGGESTION_TYPE_LABELS: Record<DreamingSuggestionType, string> = {
  related_nodes: "Related nodes",
  duplicate: "Duplicate",
  stale: "Stale",
  missing_backlink: "Missing backlink",
  unresolved_query: "Unresolved query",
  orphan: "Orphan",
  source_conflict: "Source conflict",
};

const DECAY_BUCKET_LABELS: Record<DecayStatusBucket, string> = {
  fresh: "Fresh",
  aging: "Aging",
  stale: "Stale",
  unknown: "Unknown",
};

/** Format an ISO timestamp for display, falling back to the raw value. */
function formatDate(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

function suggestionTypeLabel(type: DreamingSuggestionType): string {
  return SUGGESTION_TYPE_LABELS[type] ?? type;
}

function decayBucketLabel(bucket: DecayStatusBucket): string {
  return DECAY_BUCKET_LABELS[bucket] ?? bucket;
}

/** Per-section count strip mirroring the graph panel's summary metrics. */
function SummaryMetrics({ report }: { report: IntelligenceReport }) {
  const metrics: Array<[string, number]> = [
    ["Suggestions", report.summary.dreaming_suggestion_count],
    ["Decay", report.summary.decay_status_count],
    ["Provenance", report.summary.provenance_chain_count],
    ["Query trails", report.summary.query_trail_entry_count],
  ];
  return (
    <dl className="graph-summary" aria-label="Intelligence report summary">
      {metrics.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Section wrapper: a titled block with a count and a graceful empty state. */
function ReportSection({
  title,
  count,
  emptyText,
  children,
}: {
  title: string;
  count: number;
  emptyText: string;
  children: ReactNode;
}) {
  return (
    <div className="graph-section intel-section">
      <h3 className="graph-section-title">
        {title}
        <span className="intel-section-count">{count}</span>
      </h3>
      {count === 0 ? <p className="console-hint">{emptyText}</p> : children}
    </div>
  );
}

function SuggestionRow({ suggestion }: { suggestion: DreamingSuggestion }) {
  const statusClass: Record<DreamingSuggestionStatus, string> = {
    open: "intel-status-open",
    acknowledged: "intel-status-ack",
    dismissed: "intel-status-dismissed",
  };
  return (
    <li className="intel-row">
      <div className="intel-row-head">
        <span className="intel-tag">{suggestionTypeLabel(suggestion.type)}</span>
        <span className={`intel-status ${statusClass[suggestion.status] ?? ""}`}>
          {suggestion.status}
        </span>
      </div>
      <p className="intel-row-body">{suggestion.rationale}</p>
      <p className="intel-row-sub">
        {suggestion.node_ids.length} node(s) · {suggestion.edge_ids.length} edge(s)
        {suggestion.confidence_hint
          ? ` · confidence: ${suggestion.confidence_hint}`
          : ""}
        {` · origin: ${suggestion.origin}`}
      </p>
    </li>
  );
}

function DecayRow({ decay }: { decay: DecayStatus }) {
  return (
    <li className="intel-row">
      <div className="intel-row-head">
        <span className="intel-row-id">
          <code>{decay.node_id}</code>
        </span>
        <span className={`intel-status intel-decay-${decay.status}`}>
          {decayBucketLabel(decay.status)}
        </span>
      </div>
      <p className="intel-row-sub">
        Last referenced: {formatDate(decay.last_referenced_at)} · Last updated:{" "}
        {formatDate(decay.last_updated_at)}
        {decay.review_needed ? " · review needed" : ""}
        {decay.source_reliability_hint
          ? ` · reliability: ${decay.source_reliability_hint}`
          : ""}
      </p>
    </li>
  );
}

function ProvenanceRow({ chain }: { chain: ProvenanceChain }) {
  return (
    <li className="intel-row">
      <div className="intel-row-head">
        <span className="intel-row-id">
          <code>{chain.node_id}</code>
        </span>
        {chain.source_type && (
          <span className="intel-tag">{chain.source_type}</span>
        )}
      </div>
      <p className="intel-row-sub">
        {chain.links.length} link(s) · {chain.linked_node_ids.length} linked node(s)
        {chain.origin_path ? ` · origin: ${chain.origin_path}` : ""}
      </p>
      <p className="intel-row-sub">
        Last imported: {formatDate(chain.last_imported_at)}
      </p>
    </li>
  );
}

function QueryTrailRow({ entry }: { entry: QueryTrailEntry }) {
  const statusClass: Record<QueryTrailStatus, string> = {
    resolved: "intel-trail-resolved",
    unresolved: "intel-trail-unresolved",
  };
  return (
    <li className="intel-row">
      <div className="intel-row-head">
        <span className="intel-row-id">{entry.query}</span>
        <span className={`intel-status ${statusClass[entry.status] ?? ""}`}>
          {entry.status}
        </span>
      </div>
      <p className="intel-row-sub">
        {entry.kind} · {entry.result_count} result(s) · seen{" "}
        {entry.occurrence_count}× · last run {formatDate(entry.last_executed_at)}
        {entry.pinned ? " · pinned" : ""}
      </p>
    </li>
  );
}

function IntelligenceReportPanel() {
  const [state, setState] = useState<PanelState>("loading");
  const [report, setReport] = useState<IntelligenceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setState("loading");
    setError(null);
    try {
      const response = await apiClient.getIntelligenceReport();
      setReport(response);
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

  const isEmpty =
    state === "success" &&
    report !== null &&
    report.summary.dreaming_suggestion_count === 0 &&
    report.summary.decay_status_count === 0 &&
    report.summary.provenance_chain_count === 0 &&
    report.summary.query_trail_entry_count === 0;

  return (
    <section className="intelligence-report-panel">
      <div className="source-registry-head">
        <div>
          <h2>Intelligence Report</h2>
          <p className="console-hint graph-subtitle">
            A read-only roll-up of the intelligence layer — Dreaming, decay,
            provenance, and query trails. Advisory only; nothing is mutated.
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
          <p className="console-hint">Loading intelligence report…</p>
        )}

        {state === "error" && (
          <p className="error" role="alert">
            Error: could not load the intelligence report — {error}
          </p>
        )}

        {state === "success" && report && (
          <>
            <div className="intel-overview">
              <SummaryMetrics report={report} />
              <dl className="source-meta intel-meta">
                <div>
                  <dt>Generated</dt>
                  <dd>{formatDate(report.generated_at)}</dd>
                </div>
                <div>
                  <dt>Report version</dt>
                  <dd>{report.report_version}</dd>
                </div>
                <div>
                  <dt>Mode</dt>
                  <dd>{report.read_only ? "Read-only" : "Mutable"}</dd>
                </div>
              </dl>
            </div>

            {isEmpty ? (
              <p className="console-hint">
                No intelligence data yet. Suggestions, decay statuses,
                provenance chains, and query trails will appear here as the
                intelligence layer is populated.
              </p>
            ) : (
              <>
                <ReportSection
                  title="Dreaming Suggestions"
                  count={report.summary.dreaming_suggestion_count}
                  emptyText="No suggestions yet."
                >
                  <ul className="intel-list">
                    {report.dreaming_suggestions.map((suggestion) => (
                      <SuggestionRow
                        key={suggestion.id}
                        suggestion={suggestion}
                      />
                    ))}
                  </ul>
                </ReportSection>

                <ReportSection
                  title="Temporal Decay"
                  count={report.summary.decay_status_count}
                  emptyText="No decay statuses yet."
                >
                  <ul className="intel-list">
                    {report.decay_statuses.map((decay) => (
                      <DecayRow key={decay.node_id} decay={decay} />
                    ))}
                  </ul>
                </ReportSection>

                <ReportSection
                  title="Provenance Chains"
                  count={report.summary.provenance_chain_count}
                  emptyText="No provenance chains yet."
                >
                  <ul className="intel-list">
                    {report.provenance_chains.map((chain) => (
                      <ProvenanceRow key={chain.node_id} chain={chain} />
                    ))}
                  </ul>
                </ReportSection>

                <ReportSection
                  title="Query Trails"
                  count={report.summary.query_trail_entry_count}
                  emptyText="No query trails yet."
                >
                  <ul className="intel-list">
                    {report.query_trail_entries.map((entry) => (
                      <QueryTrailRow key={entry.id} entry={entry} />
                    ))}
                  </ul>
                </ReportSection>
              </>
            )}
          </>
        )}
      </div>
    </section>
  );
}

export default IntelligenceReportPanel;
