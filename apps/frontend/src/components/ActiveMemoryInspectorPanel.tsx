import { useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type {
  ContextPacket,
  ContextPacketRequest,
  ContradictionRecord,
  EvidenceReference,
  MemoryRecord,
  MemoryScope,
  MemoryScopeType,
  PacketWarning,
  RepositoryBaseline,
  VerificationSummary,
} from "../types/api";

const MEMORY_SCOPE_TYPES: MemoryScopeType[] = [
  "project",
  "repository",
  "branch",
  "phase",
  "feature",
  "component",
  "session",
];

type SubmitState = "idle" | "loading" | "success" | "error";

function isoNow(): string {
  return new Date().toISOString();
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Unavailable";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function display(value: string | null | undefined): string {
  return value && value.trim() !== "" ? value : "Unavailable";
}

function joinIds(ids: string[]): string {
  return ids.length > 0 ? ids.join(", ") : "None";
}

function scopeLabel(scope: MemoryScope | null): string {
  return scope ? `${scope.scope_type}: ${scope.scope_id}` : "Project-wide";
}

function workingTreeStatus(baseline: RepositoryBaseline): string {
  if (baseline.working_tree_clean === true) {
    return "Clean";
  }
  if (baseline.working_tree_clean === false) {
    return "Dirty";
  }
  return "Unknown";
}

function hasMetadata(metadata: Record<string, unknown>): boolean {
  return Object.keys(metadata).length > 0;
}

function MetadataDetails({
  label,
  metadata,
}: {
  label: string;
  metadata: Record<string, unknown>;
}) {
  if (!hasMetadata(metadata)) {
    return null;
  }
  return (
    <details className="memory-details">
      <summary>{label}</summary>
      <pre>{JSON.stringify(metadata, null, 2)}</pre>
    </details>
  );
}

function KeyValueGrid({
  items,
}: {
  items: Array<[string, string | number | boolean]>;
}) {
  return (
    <dl className="memory-kv-grid">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function VerificationSummaryView({
  summary,
}: {
  summary: VerificationSummary;
}) {
  return (
    <section className="memory-section">
      <h3>Verification Summary</h3>
      <KeyValueGrid
        items={[
          ["Verified", summary.verified_count],
          ["Human confirmed", summary.human_confirmed_count],
          ["Partially verified", summary.partially_verified_count],
          ["Unverified", summary.unverified_count],
          ["Contradicted", summary.contradicted_count],
          ["Unresolvable", summary.unresolvable_count],
        ]}
      />
    </section>
  );
}

function RepositoryBaselineView({
  baseline,
}: {
  baseline: RepositoryBaseline | null;
}) {
  return (
    <section className="memory-section">
      <h3>Repository Baseline</h3>
      {baseline ? (
        <>
          <KeyValueGrid
            items={[
              ["Branch", display(baseline.branch)],
              ["Head commit", display(baseline.head_commit)],
              ["Working tree", workingTreeStatus(baseline)],
              ["Observed", formatTimestamp(baseline.observed_at)],
              ["Evidence IDs", joinIds(baseline.evidence_ids)],
            ]}
          />
          <MetadataDetails label="Backend metadata" metadata={baseline.metadata} />
        </>
      ) : (
        <p className="memory-empty">
          No repository baseline was derived from the records supplied in this
          request.
        </p>
      )}
    </section>
  );
}

function MemoryRecordCard({ record }: { record: MemoryRecord }) {
  return (
    <li className="memory-record-card">
      <div className="memory-record-head">
        <span className="memory-record-id">
          <code>{record.record_id}</code>
        </span>
        <span className="memory-chip">{record.kind}</span>
      </div>
      <KeyValueGrid
        items={[
          ["Claim subject", record.claim.subject],
          ["Claim predicate", record.claim.predicate],
          ["Claim value", record.claim.value],
          ["Value kind", record.claim.value_kind],
          ["Verification", record.verification_state],
          ["Lifecycle", record.lifecycle_state],
          ["Confidence", record.confidence ?? "Unavailable"],
          ["Scope", scopeLabel(record.scope)],
          ["Source type", record.source.source_type],
          ["Source ID", record.source.source_id],
          ["Created", formatTimestamp(record.created_at)],
          ["Observed", formatTimestamp(record.observed_at)],
          ["Evidence IDs", joinIds(record.evidence_ids)],
        ]}
      />
      {record.claim.summary && (
        <p className="memory-record-summary">{record.claim.summary}</p>
      )}
      <details className="memory-details">
        <summary>Secondary metadata</summary>
        <KeyValueGrid
          items={[
            ["Project ID", record.project_id],
            ["Source label", display(record.source.display_label)],
            ["Source session", display(record.source.session_id)],
            [
              "Verification checked",
              formatTimestamp(record.verification?.checked_at ?? null),
            ],
            [
              "Verification evidence IDs",
              joinIds(record.verification?.evidence_ids ?? []),
            ],
            ["Verification note", display(record.verification?.note)],
          ]}
        />
        {record.verification?.checker && (
          <KeyValueGrid
            items={[
              ["Checker type", record.verification.checker.source_type],
              ["Checker ID", record.verification.checker.source_id],
            ]}
          />
        )}
        {record.supersession_refs.length > 0 ? (
          <ul className="memory-nested-list">
            {record.supersession_refs.map((ref) => (
              <li key={`${ref.kind}-${ref.target_record_id}-${ref.created_at}`}>
                <code>{ref.kind}</code> <code>{ref.target_record_id}</code>
                {ref.reason ? ` - ${ref.reason}` : ""} |{" "}
                {formatTimestamp(ref.created_at)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="memory-empty">No supersession or retraction references.</p>
        )}
        <MetadataDetails label="Record metadata" metadata={record.metadata} />
      </details>
    </li>
  );
}

function RecordCollection({
  title,
  records,
}: {
  title: string;
  records: MemoryRecord[];
}) {
  return (
    <section className="memory-section">
      <h3>
        {title} <span className="memory-count">{records.length}</span>
      </h3>
      {records.length === 0 ? (
        <p className="memory-empty">
          No records entered this active collection for this request.
        </p>
      ) : (
        <ul className="memory-record-list">
          {records.map((record) => (
            <MemoryRecordCard key={record.record_id} record={record} />
          ))}
        </ul>
      )}
    </section>
  );
}

function ContradictionCard({
  contradiction,
}: {
  contradiction: ContradictionRecord;
}) {
  return (
    <li className="memory-contradiction-card">
      <div className="memory-record-head">
        <span className="memory-record-id">
          <code>{contradiction.contradiction_id}</code>
        </span>
        <span className="memory-chip memory-chip-strong">
          {contradiction.contradiction_class}
        </span>
      </div>
      <p className="memory-contradiction-summary">{contradiction.summary}</p>
      <KeyValueGrid
        items={[
          ["Severity", contradiction.severity ?? "Unavailable"],
          ["Resolution state", contradiction.resolution_state],
          ["Involved records", joinIds(contradiction.involved_record_ids)],
          ["Evidence IDs", joinIds(contradiction.evidence_ids)],
          ["Detected", formatTimestamp(contradiction.detected_at)],
          ["Detection source type", contradiction.detection_source.source_type],
          ["Detection source ID", contradiction.detection_source.source_id],
          ["Resolution record", display(contradiction.resolution_record_id)],
          [
            "Resolution source",
            contradiction.resolution_source
              ? `${contradiction.resolution_source.source_type}: ${contradiction.resolution_source.source_id}`
              : "Unavailable",
          ],
        ]}
      />
      <MetadataDetails
        label="Relevant backend metadata"
        metadata={contradiction.metadata}
      />
    </li>
  );
}

function ContradictionsView({
  contradictions,
}: {
  contradictions: ContradictionRecord[];
}) {
  return (
    <section className="memory-section memory-section-contradictions">
      <h3>
        Unresolved Contradictions{" "}
        <span className="memory-count">{contradictions.length}</span>
      </h3>
      {contradictions.length === 0 ? (
        <p className="memory-empty">
          No unresolved contradictions were returned. The frontend has not chosen
          or resolved any record.
        </p>
      ) : (
        <ul className="memory-record-list">
          {contradictions.map((contradiction) => (
            <ContradictionCard
              key={contradiction.contradiction_id}
              contradiction={contradiction}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function WarningsView({ warnings }: { warnings: PacketWarning[] }) {
  return (
    <section className="memory-section">
      <h3>
        Packet Warnings <span className="memory-count">{warnings.length}</span>
      </h3>
      {warnings.length === 0 ? (
        <p className="memory-empty">No packet warnings were returned.</p>
      ) : (
        <ul className="memory-warning-list">
          {warnings.map((warning) => (
            <li key={`${warning.record_id}-${warning.lifecycle_state}`}>
              <code>{warning.record_id}</code>
              <span>{warning.lifecycle_state}</span>
              <p>{warning.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EvidenceReferencesView({
  references,
}: {
  references: EvidenceReference[];
}) {
  return (
    <section className="memory-section">
      <h3>
        Evidence References{" "}
        <span className="memory-count">{references.length}</span>
      </h3>
      {references.length === 0 ? (
        <p className="memory-empty">
          No packet-level evidence references were returned. This MVP does not
          yet have a connected evidence resolver; record-level evidence IDs still
          render on their records.
        </p>
      ) : (
        <ul className="memory-evidence-list">
          {references.map((reference) => (
            <li key={`${reference.reference_kind}-${reference.value}`}>
              <span className="memory-chip">{reference.reference_kind}</span>
              <code>{reference.value}</code>
              {reference.detail && <span>{reference.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ProhibitedAssumptionsView({ items }: { items: string[] }) {
  return (
    <section className="memory-section">
      <h3>
        Prohibited Assumptions <span className="memory-count">{items.length}</span>
      </h3>
      {items.length === 0 ? (
        <p className="memory-empty">
          No prohibited-assumption strings were returned.
        </p>
      ) : (
        <ul className="memory-prohibited-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PacketInspector({ packet }: { packet: ContextPacket }) {
  return (
    <div className="memory-result">
      <section className="memory-section">
        <h3>Packet Identity</h3>
        <KeyValueGrid
          items={[
            ["Packet version", packet.packet_version],
            ["Project ID", packet.project_id],
            ["Generated", formatTimestamp(packet.generated_at)],
            ["Read-only", packet.read_only ? "Yes" : "No"],
            ["Active track", display(packet.active_track)],
            ["Active phase", display(packet.active_phase)],
          ]}
        />
      </section>
      <RepositoryBaselineView baseline={packet.repository_baseline} />
      <VerificationSummaryView summary={packet.verification_summary} />
      <RecordCollection title="Active Facts" records={packet.active_facts} />
      <RecordCollection title="Active Decisions" records={packet.active_decisions} />
      <RecordCollection
        title="Active Constraints"
        records={packet.active_constraints}
      />
      <RecordCollection
        title="Known Capabilities"
        records={packet.known_capabilities}
      />
      <ContradictionsView contradictions={packet.unresolved_contradictions} />
      <WarningsView warnings={packet.warnings} />
      <ProhibitedAssumptionsView items={packet.prohibited_assumptions} />
      <EvidenceReferencesView references={packet.evidence_references} />
    </div>
  );
}

function buildRequest(
  projectId: string,
  generatedAt: string,
  scopeType: string,
  scopeId: string,
  recordsText: string,
): { request: ContextPacketRequest | null; error: string | null } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(recordsText);
  } catch {
    return {
      request: null,
      error: "Records must be valid JSON. Use a top-level array of MemoryRecord objects.",
    };
  }

  if (!Array.isArray(parsed)) {
    return {
      request: null,
      error: "Records JSON must be a top-level array.",
    };
  }

  const trimmedScopeType = scopeType.trim();
  const trimmedScopeId = scopeId.trim();
  if (
    (trimmedScopeType !== "" && trimmedScopeId === "") ||
    (trimmedScopeType === "" && trimmedScopeId !== "")
  ) {
    return {
      request: null,
      error: "Scope is optional, but scope type and scope ID must be supplied together.",
    };
  }

  const scope =
    trimmedScopeType === ""
      ? null
      : {
          scope_type: trimmedScopeType as MemoryScopeType,
          scope_id: trimmedScopeId,
        };

  return {
    error: null,
    request: {
      project_id: projectId,
      generated_at: generatedAt,
      scope,
      records: parsed as MemoryRecord[],
    },
  };
}

function ActiveMemoryInspectorPanel({ id }: { id?: string }) {
  const [projectId, setProjectId] = useState("hive-mind");
  const [generatedAt, setGeneratedAt] = useState(isoNow);
  const [scopeType, setScopeType] = useState("");
  const [scopeId, setScopeId] = useState("");
  const [recordsText, setRecordsText] = useState("[]");
  const [state, setState] = useState<SubmitState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [packet, setPacket] = useState<ContextPacket | null>(null);

  const recordCount = useMemo(() => {
    try {
      const parsed = JSON.parse(recordsText);
      return Array.isArray(parsed) ? parsed.length : null;
    } catch {
      return null;
    }
  }, [recordsText]);

  const submit = async (): Promise<void> => {
    const { request, error: validationError } = buildRequest(
      projectId,
      generatedAt,
      scopeType,
      scopeId,
      recordsText,
    );
    if (validationError || request === null) {
      setError(validationError);
      setState("error");
      return;
    }

    setState("loading");
    setError(null);
    try {
      const response = await apiClient.buildContextPacket(request);
      setPacket(response);
      setState("success");
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Network request failed. Is the backend running?",
      );
      setState("error");
    }
  };

  return (
    <section className="active-memory-panel" id={id}>
      <div className="source-registry-head">
        <div>
          <h2 className="intel-title">Active Memory Inspector</h2>
          <p className="console-hint graph-subtitle">
            Read-only frontend over the stateless context-packet endpoint.
            Records are supplied explicitly here; Hive|Mind does not persist,
            ingest, observe, interpret, authorize, or mutate Active Memory from
            this panel.
          </p>
        </div>
      </div>

      <div className="memory-panel-grid">
        <form
          className="memory-editor"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <div className="memory-editor-head">
            <h3>Request Editor</h3>
            <span className="memory-chip">
              {recordCount === null ? "Invalid JSON" : `${recordCount} records`}
            </span>
          </div>

          <label className="memory-field">
            <span>Project ID</span>
            <input
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
              autoComplete="off"
            />
          </label>

          <label className="memory-field">
            <span>Generated timestamp</span>
            <input
              value={generatedAt}
              onChange={(event) => setGeneratedAt(event.target.value)}
              autoComplete="off"
            />
          </label>

          <div className="memory-scope-row">
            <label className="memory-field">
              <span>Optional exact scope type</span>
              <select
                value={scopeType}
                onChange={(event) => setScopeType(event.target.value)}
              >
                <option value="">No scope</option>
                {MEMORY_SCOPE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>

            <label className="memory-field">
              <span>Optional exact scope ID</span>
              <input
                value={scopeId}
                onChange={(event) => setScopeId(event.target.value)}
                autoComplete="off"
              />
            </label>
          </div>

          <label className="memory-field">
            <span>MemoryRecord JSON array</span>
            <textarea
              className="memory-records-input"
              value={recordsText}
              onChange={(event) => setRecordsText(event.target.value)}
              spellCheck={false}
              rows={16}
            />
          </label>

          <div className="memory-actions">
            <button type="submit" disabled={state === "loading"}>
              {state === "loading" ? "Generating..." : "Generate context packet"}
            </button>
            <button
              type="button"
              onClick={() => setGeneratedAt(isoNow())}
              disabled={state === "loading"}
            >
              Refresh timestamp
            </button>
          </div>

          {state === "loading" && (
            <p className="console-hint" aria-live="polite">
              Building a read-only packet from the records in this request...
            </p>
          )}

          {state === "error" && error && (
            <div className="memory-error" role="alert">
              <strong>Context packet was not generated.</strong>
              <p>{error}</p>
              {packet && (
                <p className="console-hint">
                  The last successful packet remains visible below.
                </p>
              )}
            </div>
          )}
        </form>

        <div className="memory-inspector" aria-busy={state === "loading"}>
          <div className="memory-editor-head">
            <h3>Response Inspector</h3>
            <span className="memory-chip">ContextPacket</span>
          </div>

          {packet ? (
            <PacketInspector packet={packet} />
          ) : (
            <p className="memory-empty memory-empty-large">
              No packet has been generated yet. Submit a valid request to inspect
              the backend's deterministic ContextPacket response.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default ActiveMemoryInspectorPanel;
