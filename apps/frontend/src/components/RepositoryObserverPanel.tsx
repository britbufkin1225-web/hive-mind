import { useMemo, useRef, useState } from "react";
import { ApiClientError, apiClient } from "../api/client";
import {
  buildRepositoryObserverSnapshotRequest,
  REPOSITORY_OBSERVER_MAX_FILE_COUNT,
  REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES,
} from "../lib/repositoryObserverRequest";
import type {
  FileObservationSummary,
  ObserverLimitation,
  ObserverWarning,
  OverflowMetadata,
  RepositoryEvidence,
  RepositorySnapshot,
} from "../types/api";

type SnapshotState = "idle" | "loading" | "success" | "error";
type ErrorKind =
  | "validation"
  | "invalid_root"
  | "not_found"
  | "backend_unavailable"
  | "server"
  | "unexpected";

function isoNow(): string {
  return new Date().toISOString();
}

function display(value: string | null | undefined): string {
  return value && value.trim() !== "" ? value : "Unavailable";
}

function yesNo(value: boolean | null | undefined): string {
  if (value === true) {
    return "Yes";
  }
  if (value === false) {
    return "No";
  }
  return "Unknown";
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Unavailable";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return `${value.toLocaleString()} bytes`;
}

function joinList(values: string[]): string {
  return values.length > 0 ? values.join(", ") : "None";
}

function isCleanSnapshot(snapshot: RepositorySnapshot): boolean {
  return (
    snapshot.working_tree.states.length === 1 &&
    snapshot.working_tree.states[0] === "clean" &&
    snapshot.changed_files.length === 0
  );
}

function hasPartialOrTruncatedSnapshot(snapshot: RepositorySnapshot): boolean {
  return (
    snapshot.completeness !== "complete" ||
    snapshot.overflow.some(
      (overflow) => overflow.truncated || overflow.snapshot_partial,
    ) ||
    snapshot.evidence.some(
      (evidence) => evidence.truncation_state !== "not_truncated",
    )
  );
}

function errorKindFrom(error: unknown): ErrorKind {
  if (!(error instanceof ApiClientError)) {
    return "backend_unavailable";
  }
  if (error.status === 400) {
    return "invalid_root";
  }
  if (error.status === 404) {
    return "not_found";
  }
  if (error.status === 422) {
    return "validation";
  }
  if (error.status === 502 || error.status === 503) {
    return "backend_unavailable";
  }
  if (error.status === 500) {
    return "server";
  }
  return "unexpected";
}

function errorTitle(kind: ErrorKind): string {
  switch (kind) {
    case "validation":
      return "Request did not match the contract.";
    case "invalid_root":
      return "Repository root could not be observed.";
    case "not_found":
      return "Repository root was not found.";
    case "backend_unavailable":
      return "Repository Observer is unavailable.";
    case "server":
      return "Repository Observer returned an unexpected server error.";
    case "unexpected":
      return "Repository snapshot failed.";
  }
}

function clientSafeErrorMessage(error: unknown, kind: ErrorKind): string {
  if (!(error instanceof ApiClientError)) {
    return "Network request failed. Is the backend running?";
  }
  if (kind === "server") {
    return "Internal server error";
  }
  return error.message;
}

function KeyValueGrid({
  items,
}: {
  items: Array<[string, string | number | boolean]>;
}) {
  return (
    <dl className="repo-kv-grid">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function SnapshotBadges({ snapshot }: { snapshot: RepositorySnapshot }) {
  const clean = isCleanSnapshot(snapshot);
  const partial = hasPartialOrTruncatedSnapshot(snapshot);
  const uncertain = snapshot.repository_identity.status !== "verified";
  return (
    <div className="repo-badge-row" aria-label="Snapshot status">
      <span className={clean ? "repo-chip repo-chip-success" : "repo-chip repo-chip-warn"}>
        {clean ? "Clean repository" : "Dirty or changed repository"}
      </span>
      <span className={partial ? "repo-chip repo-chip-warn" : "repo-chip"}>
        {partial ? "Partial or truncated" : "Complete snapshot"}
      </span>
      <span className={uncertain ? "repo-chip repo-chip-warn" : "repo-chip"}>
        Identity {snapshot.repository_identity.status}
      </span>
      <span className="repo-chip">
        {snapshot.read_only ? "Read-only" : "Read-only flag unavailable"}
      </span>
    </div>
  );
}

function FileObservationCard({ file }: { file: FileObservationSummary }) {
  return (
    <li className="repo-file-card">
      <div className="repo-card-head">
        <code>{file.repository_relative_path}</code>
        <span className="repo-chip">{file.change_kind}</span>
      </div>
      <KeyValueGrid
        items={[
          ["Normalized path", file.normalized_path],
          ["Observation", file.observation_category],
          ["Content", file.content_kind],
          ["Size", formatBytes(file.size_bytes)],
          ["Tracked", yesNo(file.tracked)],
          ["Staged", yesNo(file.staged)],
          ["Ignored", yesNo(file.ignored)],
          ["Evidence IDs", joinList(file.evidence_ids)],
          ["Warning IDs", joinList(file.warning_ids)],
        ]}
      />
      {file.path_relationship && (
        <p className="repo-card-note">
          {file.path_relationship.change_kind} from{" "}
          <code>{file.path_relationship.prior_path}</code> to{" "}
          <code>{file.path_relationship.current_path}</code>
        </p>
      )}
      {file.omission_reason && (
        <p className="repo-card-note">Omission: {file.omission_reason}</p>
      )}
    </li>
  );
}

function EvidenceCard({ evidence }: { evidence: RepositoryEvidence }) {
  return (
    <li className="repo-evidence-card">
      <div className="repo-card-head">
        <code>{evidence.evidence_id}</code>
        <span className="repo-chip">{evidence.authority}</span>
      </div>
      <KeyValueGrid
        items={[
          ["Category", evidence.category],
          ["Source", evidence.source],
          ["Path", display(evidence.repository_relative_path)],
          ["Captured", formatTimestamp(evidence.captured_at)],
          ["Truncation", evidence.truncation_state],
          ["Digest", display(evidence.digest)],
          ["Related files", joinList(evidence.related_file_ids)],
        ]}
      />
      <p className="repo-card-note">{evidence.summary}</p>
      {evidence.bounded_excerpt && (
        <details className="repo-details">
          <summary>Bounded excerpt</summary>
          <pre>{evidence.bounded_excerpt}</pre>
        </details>
      )}
      {evidence.omission_reason && (
        <p className="repo-card-note">Omission: {evidence.omission_reason}</p>
      )}
    </li>
  );
}

function WarningCard({ warning }: { warning: ObserverWarning }) {
  return (
    <li className="repo-warning-card">
      <div className="repo-card-head">
        <code>{warning.warning_id}</code>
        <span className="repo-chip repo-chip-warn">{warning.category}</span>
      </div>
      <p>{warning.summary}</p>
      <KeyValueGrid
        items={[
          ["Path", display(warning.path)],
          ["Evidence IDs", joinList(warning.evidence_ids)],
        ]}
      />
    </li>
  );
}

function LimitationCard({ limitation }: { limitation: ObserverLimitation }) {
  return (
    <li className="repo-limitation-card">
      <div className="repo-card-head">
        <code>{limitation.limitation_id}</code>
        <span className="repo-chip">{limitation.category}</span>
      </div>
      <p>{limitation.summary}</p>
      <KeyValueGrid items={[["Path", display(limitation.path)]]} />
    </li>
  );
}

function OverflowCard({ overflow }: { overflow: OverflowMetadata }) {
  return (
    <li className="repo-overflow-card">
      <div className="repo-card-head">
        <code>{overflow.overflow_id}</code>
        <span className="repo-chip repo-chip-warn">{overflow.limit_kind}</span>
      </div>
      <KeyValueGrid
        items={[
          ["Truncated", yesNo(overflow.truncated)],
          ["Snapshot partial", yesNo(overflow.snapshot_partial)],
          ["Configured limit", overflow.configured_limit],
          ["Observed count", display(String(overflow.observed_count ?? ""))],
          ["Observed size", formatBytes(overflow.observed_size_bytes)],
          ["Retained count", overflow.retained_count],
          ["Omitted count", display(String(overflow.omitted_count ?? ""))],
          ["Deterministic cutoff", overflow.deterministic_cutoff],
        ]}
      />
    </li>
  );
}

function SnapshotInspector({
  snapshot,
  submittedRoot,
}: {
  snapshot: RepositorySnapshot;
  submittedRoot: string;
}) {
  return (
    <div className="repo-result">
      <section className="repo-section">
        <h3>Snapshot Status</h3>
        <SnapshotBadges snapshot={snapshot} />
        <KeyValueGrid
          items={[
            ["Snapshot ID", snapshot.snapshot_id],
            ["Contract", snapshot.contract_version],
            ["Observer version", snapshot.observer_version],
            ["Observed", formatTimestamp(snapshot.observed_at)],
            ["Completeness", snapshot.completeness],
            ["Read-only", snapshot.read_only ? "Yes" : "No"],
            ["Submitted target", submittedRoot],
          ]}
        />
      </section>

      <section className="repo-section">
        <h3>Repository Identity</h3>
        <KeyValueGrid
          items={[
            ["Repository", snapshot.repository_identity.repository_name],
            ["Repository ID", snapshot.repository_identity.repository_id],
            ["Canonical root", snapshot.repository_identity.canonical_root],
            ["Normalized root", snapshot.repository_identity.normalized_root],
            ["Identity status", snapshot.repository_identity.status],
            ["Primary remote", display(snapshot.repository_identity.primary_remote_url)],
            ["Default branch", display(snapshot.repository_identity.default_branch)],
            ["Upstream", display(snapshot.repository_identity.upstream_reference)],
            ["Operation", snapshot.repository_identity.operation_state],
            ["Identity warnings", joinList(snapshot.repository_identity.warning_ids)],
          ]}
        />
        {snapshot.repository_identity.remotes.length > 0 && (
          <ul className="repo-compact-list">
            {snapshot.repository_identity.remotes.map((remote) => (
              <li key={`${remote.name}-${remote.url}`}>
                <strong>{remote.name}</strong>
                <span>{remote.url}</span>
                {remote.normalized_url && <code>{remote.normalized_url}</code>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="repo-section">
        <h3>HEAD and Working Tree</h3>
        <KeyValueGrid
          items={[
            ["Branch", display(snapshot.branch ?? snapshot.repository_identity.current_branch)],
            ["HEAD commit", display(snapshot.commit ?? snapshot.repository_identity.current_commit)],
            ["States", joinList(snapshot.working_tree.states)],
            ["Staged", snapshot.working_tree.staged_count],
            ["Unstaged", snapshot.working_tree.unstaged_count],
            ["Untracked", snapshot.working_tree.untracked_count],
            ["Conflicted", snapshot.working_tree.conflicted_count],
          ]}
        />
      </section>

      <section className="repo-section">
        <h3>
          Observed File Changes{" "}
          <span className="repo-count">{snapshot.changed_files.length}</span>
        </h3>
        {snapshot.changed_files.length === 0 ? (
          <p className="repo-empty">
            No file observations were returned for this bounded snapshot.
          </p>
        ) : (
          <ul className="repo-card-list">
            {snapshot.changed_files.map((file) => (
              <FileObservationCard key={file.file_id} file={file} />
            ))}
          </ul>
        )}
      </section>

      <section className="repo-section">
        <h3>
          Repository Evidence{" "}
          <span className="repo-count">{snapshot.evidence.length}</span>
        </h3>
        {snapshot.evidence.length === 0 ? (
          <p className="repo-empty">No evidence records were returned.</p>
        ) : (
          <ul className="repo-card-list">
            {snapshot.evidence.map((evidence) => (
              <EvidenceCard key={evidence.evidence_id} evidence={evidence} />
            ))}
          </ul>
        )}
      </section>

      <section className="repo-section">
        <h3>
          Warnings <span className="repo-count">{snapshot.warnings.length}</span>
        </h3>
        {snapshot.warnings.length === 0 ? (
          <p className="repo-empty">No backend warnings were returned.</p>
        ) : (
          <ul className="repo-card-list">
            {snapshot.warnings.map((warning) => (
              <WarningCard key={warning.warning_id} warning={warning} />
            ))}
          </ul>
        )}
      </section>

      <section className="repo-section">
        <h3>
          Limitations{" "}
          <span className="repo-count">{snapshot.limitations.length}</span>
        </h3>
        {snapshot.limitations.length === 0 ? (
          <p className="repo-empty">No backend limitations were returned.</p>
        ) : (
          <ul className="repo-card-list">
            {snapshot.limitations.map((limitation) => (
              <LimitationCard
                key={limitation.limitation_id}
                limitation={limitation}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="repo-section">
        <h3>
          Overflow and Ordering{" "}
          <span className="repo-count">{snapshot.overflow.length}</span>
        </h3>
        {snapshot.overflow.length === 0 ? (
          <p className="repo-empty">No overflow metadata was returned.</p>
        ) : (
          <ul className="repo-card-list">
            {snapshot.overflow.map((overflow) => (
              <OverflowCard key={overflow.overflow_id} overflow={overflow} />
            ))}
          </ul>
        )}
        <KeyValueGrid
          items={[
            ["Omitted paths", joinList(snapshot.omitted_paths)],
            ["Deterministic ordering", joinList(snapshot.deterministic_ordering)],
          ]}
        />
      </section>
    </div>
  );
}

function RepositoryObserverPanel({ id }: { id?: string }) {
  const [repositoryRoot, setRepositoryRoot] = useState("");
  const [observedAt, setObservedAt] = useState(isoNow);
  const [maxFileCount, setMaxFileCount] = useState(200);
  const [maxSnapshotBytes, setMaxSnapshotBytes] = useState(262_144);
  const [state, setState] = useState<SnapshotState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ErrorKind>("unexpected");
  const [snapshot, setSnapshot] = useState<RepositorySnapshot | null>(null);
  const [submittedRoot, setSubmittedRoot] = useState<string | null>(null);
  const requestSequenceRef = useRef(0);

  const dirtySummary = useMemo(() => {
    if (!snapshot) {
      return null;
    }
    return isCleanSnapshot(snapshot)
      ? "Clean: no changed files in the returned snapshot."
      : `Dirty/changed: ${snapshot.changed_files.length} file observations returned.`;
  }, [snapshot]);

  const submit = async (): Promise<void> => {
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    const { request, error: validationError } =
      buildRepositoryObserverSnapshotRequest({
        repositoryRoot,
        observedAt,
        maxFileCount,
        maxSnapshotBytes,
      });
    if (!request || validationError) {
      setError(validationError);
      setErrorKind("validation");
      setState("error");
      return;
    }

    setState("loading");
    setError(null);
    setSubmittedRoot(request.repository_root);
    try {
      const response = await apiClient.observeRepositorySnapshot(request);
      if (requestSequence !== requestSequenceRef.current) {
        return;
      }
      setSnapshot(response);
      setState("success");
    } catch (requestError: unknown) {
      if (requestSequence !== requestSequenceRef.current) {
        return;
      }
      const kind = errorKindFrom(requestError);
      setErrorKind(kind);
      setError(clientSafeErrorMessage(requestError, kind));
      setState("error");
    }
  };

  return (
    <section className="repository-observer-panel" id={id}>
      <div className="source-registry-head">
        <div>
          <h2 className="intel-title">Repository Observer</h2>
          <p className="console-hint graph-subtitle">
            Read-only, backend-derived, deterministic repository snapshot. This
            surface observes once per request and never watches, stages,
            commits, switches branches, repairs, reviews, pushes, pulls, or
            mutates repository state.
          </p>
        </div>
      </div>

      <div className="repo-panel-grid">
        <form
          className="repo-editor"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <div className="repo-editor-head">
            <h3>Snapshot Request</h3>
            <span className="repo-chip">POST /api/repository-observer/snapshot</span>
          </div>

          <label className="repo-field">
            <span>Repository root</span>
            <input
              value={repositoryRoot}
              onChange={(event) => setRepositoryRoot(event.target.value)}
              placeholder="C:\\Users\\name\\Documents\\hive-mind"
              autoComplete="off"
              aria-invalid={state === "error" && errorKind === "validation"}
            />
          </label>

          <label className="repo-field">
            <span>Observation timestamp</span>
            <input
              value={observedAt}
              onChange={(event) => setObservedAt(event.target.value)}
              autoComplete="off"
            />
          </label>

          <div className="repo-limit-row">
            <label className="repo-field">
              <span>File limit</span>
              <input
                type="number"
                min={0}
                max={REPOSITORY_OBSERVER_MAX_FILE_COUNT}
                step={1}
                // Clearing a number input yields valueAsNumber === NaN; keep the
                // NaN in state so validation still rejects an empty limit, but
                // never feed NaN back into the controlled value prop (React logs
                // a "Received NaN" warning for that).
                value={Number.isNaN(maxFileCount) ? "" : maxFileCount}
                onChange={(event) => setMaxFileCount(event.target.valueAsNumber)}
              />
            </label>

            <label className="repo-field">
              <span>Snapshot byte limit</span>
              <input
                type="number"
                min={0}
                max={REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES}
                step={1024}
                value={Number.isNaN(maxSnapshotBytes) ? "" : maxSnapshotBytes}
                onChange={(event) =>
                  setMaxSnapshotBytes(event.target.valueAsNumber)
                }
              />
            </label>
          </div>

          <div className="repo-actions">
            <button type="submit" disabled={state === "loading"}>
              {state === "loading" ? "Observing..." : "Observe snapshot"}
            </button>
            <button
              type="button"
              disabled={state === "loading"}
              onClick={() => setObservedAt(isoNow())}
            >
              Refresh timestamp
            </button>
          </div>

          <div aria-live="polite" aria-busy={state === "loading"}>
            {state === "idle" && (
              <p className="repo-empty repo-empty-large">
                No snapshot has been requested. Enter an absolute repository path
                and submit one bounded observation.
              </p>
            )}

            {state === "loading" && (
              <p className="console-hint">
                Requesting one bounded read-only snapshot from the backend...
              </p>
            )}

            {state === "error" && error && (
              <div className="repo-error" role="alert">
                <strong>{errorTitle(errorKind)}</strong>
                <p>{error}</p>
                {snapshot && (
                  <p className="console-hint">
                    The previous successful snapshot remains visible.
                  </p>
                )}
              </div>
            )}
          </div>
        </form>

        <div className="repo-inspector" aria-busy={state === "loading"}>
          <div className="repo-editor-head">
            <h3>Snapshot Inspector</h3>
            <span className="repo-chip">RepositorySnapshot</span>
          </div>

          {snapshot ? (
            <>
              {dirtySummary && <p className="repo-summary">{dirtySummary}</p>}
              <SnapshotInspector
                snapshot={snapshot}
                submittedRoot={submittedRoot ?? repositoryRoot}
              />
            </>
          ) : (
            <p className="repo-empty repo-empty-large">
              The inspector will show repository identity, branch, HEAD, working
              tree state, file observations, evidence, warnings, limitations,
              overflow, and completeness after a successful backend response.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default RepositoryObserverPanel;
