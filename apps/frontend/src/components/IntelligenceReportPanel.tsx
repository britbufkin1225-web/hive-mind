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

/** True when a record carries the seed/demo fixture marker stamped by the
 *  backend fixtures (`metadata.fixture === true`). Used only to label the
 *  surface honestly as demo data — it changes no behavior. */
function isFixtureRecord(record: { metadata?: Record<string, unknown> }): boolean {
  return record.metadata?.fixture === true;
}

/** Whether the report is built entirely from seed/demo fixtures, so the panel
 *  can say so plainly for demos and screenshots. */
function isDemoReport(report: IntelligenceReport): boolean {
  return [
    ...report.dreaming_suggestions,
    ...report.decay_statuses,
    ...report.provenance_chains,
    ...report.query_trail_entries,
  ].some(isFixtureRecord);
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

/** Section wrapper: a titled block with a one-line summary of what the section
 *  surfaces, a count badge, and a graceful, intentional-feeling empty state. */
function ReportSection({
  title,
  description,
  count,
  emptyText,
  children,
}: {
  title: string;
  description: string;
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
      <p className="intel-section-desc">{description}</p>
      {count === 0 ? (
        <p className="intel-empty">{emptyText}</p>
      ) : (
        children
      )}
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

  const isDemo = report !== null && isDemoReport(report);

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
          <h2 className="intel-title">
            Intelligence Report
            {state === "success" && isDemo && (
              <span className="intel-demo-badge">Demo data</span>
            )}
          </h2>
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
          <div className="intel-error" role="alert">
            <p className="error">
              Could not load the intelligence report.
            </p>
            <p className="console-hint">
              The backend may be unavailable. Check that the API is running,
              then use Refresh to try again.
            </p>
            <p className="intel-error-detail">{error}</p>
          </div>
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

            {isDemo && (
              <p className="intel-demo-note">
                These sections are populated with deterministic seed/demo
                fixtures so the surface shows meaningful content. No Dreaming,
                decay, provenance, or query-trail logic runs yet — real
                intelligence arrives in a later phase.
              </p>
            )}

            {isEmpty && (
              <p className="intel-empty intel-empty-global">
                The intelligence layer is wired up and reporting cleanly — it
                just has nothing to surface yet. Suggestions, decay statuses,
                provenance chains, and query trails will populate the sections
                below as the graph grows.
              </p>
            )}

            <ReportSection
              title="Dreaming Suggestions"
              description="Advisory ideas the system would propose during idle “dreaming” — likely related nodes, duplicates, stale notes, and missing backlinks. Suggestions only; nothing is applied automatically."
              count={report.summary.dreaming_suggestion_count}
              emptyText="No suggestions yet — these appear once the graph has enough connected notes to reason about."
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
              title="Temporal Knowledge Decay"
              description="How fresh each node is, based on when it was last referenced or updated. Flags aging and stale knowledge that may be worth reviewing — purely informational."
              count={report.summary.decay_status_count}
              emptyText="No decay statuses yet — these appear once nodes accumulate reference and update history."
            >
              <ul className="intel-list">
                {report.decay_statuses.map((decay) => (
                  <DecayRow key={decay.node_id} decay={decay} />
                ))}
              </ul>
            </ReportSection>

            <ReportSection
              title="Provenance Chains"
              description="Where each node came from — its originating source, import run, and linked nodes. A read-only audit trail tracing knowledge back to its origin."
              count={report.summary.provenance_chain_count}
              emptyText="No provenance chains yet — these appear once sources are imported into the graph."
            >
              <ul className="intel-list">
                {report.provenance_chains.map((chain) => (
                  <ProvenanceRow key={chain.node_id} chain={chain} />
                ))}
              </ul>
            </ReportSection>

            <ReportSection
              title="Query Trails"
              description="A history of console and search queries, showing which resolved to results and which went unanswered. Highlights recurring and unresolved questions over time."
              count={report.summary.query_trail_entry_count}
              emptyText="No query trails yet — these appear as queries are run against the graph."
            >
              <ul className="intel-list">
                {report.query_trail_entries.map((entry) => (
                  <QueryTrailRow key={entry.id} entry={entry} />
                ))}
              </ul>
            </ReportSection>
          </>
        )}
      </div>
    </section>
  );
}

export default IntelligenceReportPanel;
