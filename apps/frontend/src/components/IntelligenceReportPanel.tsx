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

/** True when a record carries the backend-derived marker (`metadata.derived
 *  === true`). Phase 13A stamps every Temporal Decay row with this so the
 *  surface can honestly distinguish computed data from demo fixtures. */
function isDerivedRecord(record: { metadata?: Record<string, unknown> }): boolean {
  return record.metadata?.derived === true;
}

/** Read a string field out of a record's `metadata`, or `null` when absent or
 *  the wrong type. Used to surface the backend's human-readable `reason`. */
function metaString(
  record: { metadata?: Record<string, unknown> },
  key: string,
): string | null {
  const value = record.metadata?.[key];
  return typeof value === "string" ? value : null;
}

/** Read a numeric field out of a record's `metadata`, or `null` when absent or
 *  the wrong type. Used to surface the backend's computed `age_days`. */
function metaNumber(
  record: { metadata?: Record<string, unknown> },
  key: string,
): number | null {
  const value = record.metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
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
  badge,
  note,
  children,
}: {
  title: string;
  description: string;
  count: number;
  emptyText: string;
  badge?: ReactNode;
  note?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="graph-section intel-section">
      <h3 className="graph-section-title">
        {title}
        <span className="intel-section-count">{count}</span>
        {badge}
      </h3>
      <p className="intel-section-desc">{description}</p>
      {count === 0 ? (
        <p className="intel-empty">{emptyText}</p>
      ) : (
        <>
          {note}
          {children}
        </>
      )}
    </div>
  );
}

/** Honest provenance pill shown on a section heading: "Backend-derived" for
 *  real computed data, "Demo data" for fixture-backed sections. */
function SectionBadge({ kind }: { kind: "derived" | "demo" }) {
  return kind === "derived" ? (
    <span className="intel-section-badge intel-section-badge-derived">
      Backend-derived
    </span>
  ) : (
    <span className="intel-section-badge intel-section-badge-demo">
      Demo data
    </span>
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
  const reason = metaString(decay, "reason");
  const ageDays = metaNumber(decay, "age_days");
  return (
    <li className="intel-row intel-decay-row">
      <div className="intel-row-head">
        <span className="intel-row-id">
          <code>{decay.node_id}</code>
        </span>
        <span className={`intel-status intel-decay-${decay.status}`}>
          {decayBucketLabel(decay.status)}
        </span>
      </div>
      {reason && <p className="intel-row-body intel-decay-reason">{reason}</p>}
      <div className="intel-chip-row">
        {ageDays !== null && (
          <span className="intel-chip">
            Age: {ageDays} day{ageDays === 1 ? "" : "s"}
          </span>
        )}
        {decay.review_needed && (
          <span className="intel-chip intel-chip-review">Review needed</span>
        )}
        {decay.source_reliability_hint && (
          <span className="intel-chip">
            Reliability: {decay.source_reliability_hint}
          </span>
        )}
      </div>
      <p className="intel-row-sub">
        Last updated: {formatDate(decay.last_updated_at)}
        {decay.last_imported_at
          ? ` · last imported: ${formatDate(decay.last_imported_at)}`
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
                <strong>Temporal Knowledge Decay is now backend-derived</strong>{" "}
                — its rows are computed read-only from real store timestamps and
                labelled “Backend-derived” below. Dreaming, provenance, and
                query-trail sections remain deterministic demo fixtures (labelled
                “Demo data”) until their real logic ships in a later phase.
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
              badge={
                report.dreaming_suggestions.some(isFixtureRecord) ? (
                  <SectionBadge kind="demo" />
                ) : undefined
              }
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
              description="How fresh each node is, computed from its most recent activity timestamp. Buckets every node as fresh, aging, stale, or unknown and flags rows worth reviewing — purely informational."
              count={report.summary.decay_status_count}
              emptyText="No decay statuses yet — these appear once nodes accumulate update and import history."
              badge={
                report.decay_statuses.some(isDerivedRecord) ? (
                  <SectionBadge kind="derived" />
                ) : undefined
              }
              note={
                <p className="intel-derived-note">
                  Read-only and deterministic: each row is derived on the backend
                  from real store timestamps using fixed thresholds
                  (fresh&nbsp;≤&nbsp;30 days, aging&nbsp;≤&nbsp;90 days). No
                  scoring model and no AI — the “reason” explains exactly how each
                  status was assigned.
                </p>
              }
            >
              <div className="intel-decay-legend" aria-hidden="true">
                <span className="intel-status intel-decay-fresh">Fresh</span>
                <span className="intel-status intel-decay-aging">Aging</span>
                <span className="intel-status intel-decay-stale">Stale</span>
                <span className="intel-status intel-decay-unknown">Unknown</span>
              </div>
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
              badge={
                report.provenance_chains.some(isFixtureRecord) ? (
                  <SectionBadge kind="demo" />
                ) : undefined
              }
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
              badge={
                report.query_trail_entries.some(isFixtureRecord) ? (
                  <SectionBadge kind="demo" />
                ) : undefined
              }
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
