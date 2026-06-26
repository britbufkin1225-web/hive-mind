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
  duplicate: "Duplicate signal",
  stale: "Stale knowledge link",
  missing_backlink: "Missing backlink",
  unresolved_query: "Unresolved query",
  orphan: "Orphaned node",
  source_conflict: "Source conflict",
};

/** Per-type accent class for the three Phase 14C backend-derived suggestion
 *  types, so duplicate / orphan / stale rows are scannable at a glance. Other
 *  (contract-only, not-yet-derived) types fall back to the neutral styling. */
const SUGGESTION_TYPE_CLASS: Partial<Record<DreamingSuggestionType, string>> = {
  duplicate: "intel-suggest-duplicate",
  orphan: "intel-suggest-orphan",
  stale: "intel-suggest-stale",
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

/** Read a nested object field out of a record's `metadata`, or `null` when
 *  absent or not a plain object. Used to surface `metadata.evidence`, the
 *  backend's stable Dreaming evidence trail. */
function metaObject(
  record: { metadata?: Record<string, unknown> },
  key: string,
): Record<string, unknown> | null {
  const value = record.metadata?.[key];
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Coerce an arbitrary value to a non-empty string, or `null`. */
function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** Coerce an arbitrary value to a list of strings (drops non-string members). */
function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((member): member is string => typeof member === "string")
    : [];
}

/** Map the backend's `confidence_hint` string to a pill accent class. */
function confidenceClass(hint: string | null): string {
  switch ((hint ?? "").toLowerCase()) {
    case "high":
      return "intel-confidence-high";
    case "medium":
      return "intel-confidence-medium";
    case "low":
      return "intel-confidence-low";
    default:
      return "";
  }
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
  footer,
  children,
}: {
  title: string;
  description: string;
  count: number;
  emptyText: string;
  badge?: ReactNode;
  note?: ReactNode;
  footer?: ReactNode;
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
      {footer}
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
  const typeClass = SUGGESTION_TYPE_CLASS[suggestion.type] ?? "";

  // Phase 14C stamps a stable `metadata.evidence` trail on every derived
  // suggestion. Surface it read-only: the concise `reason` reads as the title,
  // `rationale` as the summary, and the rest as a collapsible evidence trail.
  const evidence = metaObject(suggestion, "evidence");
  const reason = evidence ? asString(evidence.reason) : null;
  const derivation = evidence ? asString(evidence.derivation) : null;
  const fieldsUsed = evidence ? asStringArray(evidence.fields_used) : [];
  const evidenceNodeIds = evidence ? asStringArray(evidence.node_ids) : [];
  const evidenceEdgeIds = evidence ? asStringArray(evidence.edge_ids) : [];
  const evidenceSourceIds = evidence ? asStringArray(evidence.source_ids) : [];
  const hasEvidence =
    derivation !== null ||
    fieldsUsed.length > 0 ||
    evidenceNodeIds.length > 0 ||
    evidenceEdgeIds.length > 0 ||
    evidenceSourceIds.length > 0;

  return (
    <li className={`intel-row intel-suggest-row ${typeClass}`.trim()}>
      <div className="intel-row-head">
        <span className={`intel-tag intel-suggest-tag ${typeClass}`.trim()}>
          {suggestionTypeLabel(suggestion.type)}
        </span>
        <span className="intel-suggest-head-meta">
          {suggestion.confidence_hint && (
            <span
              className={`intel-chip intel-confidence ${confidenceClass(
                suggestion.confidence_hint,
              )}`.trim()}
            >
              {suggestion.confidence_hint} confidence
            </span>
          )}
          <span className={`intel-status ${statusClass[suggestion.status] ?? ""}`}>
            {suggestion.status}
          </span>
        </span>
      </div>
      {reason && <p className="intel-suggest-title">{reason}</p>}
      <p className="intel-row-body">{suggestion.rationale}</p>
      <div className="intel-chip-row">
        <span className="intel-chip">
          {suggestion.node_ids.length} node{suggestion.node_ids.length === 1 ? "" : "s"}
        </span>
        {suggestion.edge_ids.length > 0 && (
          <span className="intel-chip">
            {suggestion.edge_ids.length} edge
            {suggestion.edge_ids.length === 1 ? "" : "s"}
          </span>
        )}
        {fieldsUsed.length > 0 && (
          <span className="intel-chip">Fields: {fieldsUsed.join(", ")}</span>
        )}
      </div>
      {hasEvidence && (
        <details className="intel-evidence">
          <summary>Evidence trail</summary>
          <dl>
            {derivation && (
              <>
                <dt>Derivation</dt>
                <dd>{derivation}</dd>
              </>
            )}
            {evidenceNodeIds.length > 0 && (
              <>
                <dt>Nodes</dt>
                <dd>
                  <code>{evidenceNodeIds.join(", ")}</code>
                </dd>
              </>
            )}
            {evidenceEdgeIds.length > 0 && (
              <>
                <dt>Edges</dt>
                <dd>
                  <code>{evidenceEdgeIds.join(", ")}</code>
                </dd>
              </>
            )}
            {evidenceSourceIds.length > 0 && (
              <>
                <dt>Sources</dt>
                <dd>
                  <code>{evidenceSourceIds.join(", ")}</code>
                </dd>
              </>
            )}
          </dl>
        </details>
      )}
      <p className="intel-row-sub">
        Origin: {suggestion.origin} · derived read-only on the backend · never
        applied automatically
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
                <strong>
                  Temporal Knowledge Decay and Dreaming Suggestions are now
                  backend-derived
                </strong>{" "}
                — both are computed read-only from real store data and labelled
                “Backend-derived” below. Provenance and query-trail sections
                remain deterministic demo fixtures (labelled “Demo data”) until
                their real logic ships in a later phase.
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
              description="Read-only maintenance hints the backend derives during “dreaming” — duplicate signals, orphaned nodes, and stale knowledge links. Advisory only; nothing is ever applied automatically."
              count={report.summary.dreaming_suggestion_count}
              emptyText="No suggestions found — Dreaming ran but found no maintenance opportunities in the current graph (no duplicate labels, orphaned nodes, or stale links)."
              badge={
                report.dreaming_suggestions.some(isDerivedRecord) ? (
                  <SectionBadge kind="derived" />
                ) : undefined
              }
              note={
                <p className="intel-derived-note">
                  <strong>Backend-derived · Read-only · Non-mutating.</strong>{" "}
                  This MVP suggestion surface is computed per request from real
                  store nodes and edges — duplicate labels, orphaned nodes, and
                  stale links. No scoring model and no AI; each row carries an
                  evidence trail explaining exactly why it was raised. Dreaming
                  never merges, repairs, deletes, or changes knowledge — these are
                  review-only hints.
                </p>
              }
              footer={
                <p className="intel-deferred-note">
                  <strong>Not yet surfaced.</strong> Two suggestion types are
                  intentionally held back from this MVP:{" "}
                  <code>source_coverage_gap</code> is <em>deferred</em> (no
                  derivation is defined for it yet), and{" "}
                  <code>unresolved_query_pattern</code> is{" "}
                  <em>blocked until query history exists</em>. Neither is
                  fabricated here.
                </p>
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
