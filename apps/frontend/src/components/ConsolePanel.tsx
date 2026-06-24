import { useState, type FormEvent } from "react";
import { apiClient, type ConsoleExecuteResponse } from "../api/client";

type PanelState = "idle" | "loading" | "success" | "error";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Pick a human-friendly one-line summary for a record-like object. */
function summarize(item: Record<string, unknown>): string {
  for (const key of ["label", "name", "message", "id"]) {
    const value = item[key];
    if (typeof value === "string" && value.trim() !== "") {
      return value;
    }
  }
  return JSON.stringify(item);
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="console-result">{JSON.stringify(value, null, 2)}</pre>;
}

/** Render a single named field of a console result in a readable way. */
function ResultField({ name, value }: { name: string; value: unknown }) {
  // Arrays -> readable groups.
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <div className="result-field">
          <span className="result-key">{name}</span>{" "}
          <span className="console-hint">(none)</span>
        </div>
      );
    }
    const allStrings = value.every((entry) => typeof entry === "string");
    return (
      <div className="result-field">
        <span className="result-key">{name}</span>{" "}
        <span className="result-count">({value.length})</span>
        <ul className="result-list">
          {value.map((entry, index) => (
            <li key={index}>
              {allStrings ? (
                (entry as string)
              ) : isPlainObject(entry) ? (
                <>
                  <span className="result-summary">{summarize(entry)}</span>
                  <JsonBlock value={entry} />
                </>
              ) : (
                String(entry)
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Objects whose values are all arrays -> nested groups (e.g. find matches).
  if (isPlainObject(value)) {
    const values = Object.values(value);
    const isGroupedArrays =
      values.length > 0 && values.every((entry) => Array.isArray(entry));
    if (isGroupedArrays) {
      return (
        <div className="result-field">
          <span className="result-key">{name}</span>
          {Object.entries(value).map(([key, entry]) => (
            <ResultField key={key} name={key} value={entry} />
          ))}
        </div>
      );
    }
    // Other objects -> structured JSON block (no better display available).
    return (
      <div className="result-field">
        <span className="result-key">{name}</span>
        <JsonBlock value={value} />
      </div>
    );
  }

  // Primitives -> key: value line.
  return (
    <div className="result-field">
      <span className="result-key">{name}</span>{" "}
      <span className="result-value">{String(value)}</span>
    </div>
  );
}

function ConsoleResult({ result }: { result: Record<string, unknown> }) {
  const entries = Object.entries(result);
  if (entries.length === 0) {
    return <p className="console-hint">No result data returned.</p>;
  }
  return (
    <div className="result-fields">
      {entries.map(([key, value]) => (
        <ResultField key={key} name={key} value={value} />
      ))}
    </div>
  );
}

function ConsolePanel() {
  const [command, setCommand] = useState("");
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const [state, setState] = useState<PanelState>("idle");
  const [response, setResponse] = useState<ConsoleExecuteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const trimmed = command.trim();
  const isLoading = state === "loading";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!trimmed || isLoading) {
      return; // prevent blank/duplicate submissions
    }

    setState("loading");
    setError(null);
    setResponse(null);
    setLastCommand(trimmed);

    try {
      const result = await apiClient.executeConsole(trimmed);
      setResponse(result);
      setState("success");
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Network request failed. Is the backend running?",
      );
      setState("error");
    }
  }

  function handleClear() {
    setCommand("");
    setLastCommand(null);
    setState("idle");
    setResponse(null);
    setError(null);
  }

  // Detect an empty (zero-result) success, e.g. find/list with count 0.
  const resultCount =
    response && response.result && typeof response.result.count === "number"
      ? (response.result.count as number)
      : undefined;
  const isEmptyResult =
    state === "success" && response?.ok === true && resultCount === 0;

  return (
    <section className="console-panel">
      <h2>Hive Console</h2>

      <form className="console-form" onSubmit={handleSubmit}>
        <label className="console-label" htmlFor="console-command">
          Command
        </label>
        <input
          id="console-command"
          type="text"
          className="console-input"
          placeholder='Try: help, status, list nodes, find note, add note "hello"'
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          disabled={isLoading}
          autoComplete="off"
        />
        <div className="console-actions">
          <button type="submit" disabled={isLoading || !trimmed}>
            {isLoading ? "Running…" : "Run"}
          </button>
          <button
            type="button"
            className="console-clear"
            onClick={handleClear}
            disabled={isLoading || (state === "idle" && command === "")}
          >
            Clear
          </button>
        </div>
      </form>

      <div className="console-output" aria-live="polite" aria-busy={isLoading}>
        {state === "idle" && (
          <p className="console-hint">
            Enter a command to query the backend console. Nothing has run yet.
          </p>
        )}

        {state === "loading" && (
          <p className="console-status">Running “{trimmed}”…</p>
        )}

        {state === "error" && (
          <p className="error" role="alert">
            Error: request failed — {error}
          </p>
        )}

        {state === "success" && response && (
          <>
            {lastCommand && (
              <p className="console-echo">
                <span className="result-key">Command</span>{" "}
                <code>{lastCommand}</code>
              </p>
            )}

            {response.ok ? (
              <p className="success">
                Success: {response.command}
                {response.result && typeof response.result.type === "string"
                  ? ` · type ${response.result.type}`
                  : ""}
                {resultCount !== undefined ? ` · ${resultCount} result(s)` : ""}
              </p>
            ) : (
              <p className="error" role="alert">
                Error: {response.error ?? "command failed"}
              </p>
            )}

            {response.ok &&
              (isEmptyResult ? (
                <p className="console-hint">
                  No results{lastCommand ? ` for “${lastCommand}”` : ""}.
                </p>
              ) : response.result ? (
                <ConsoleResult result={response.result} />
              ) : (
                <p className="console-hint">Command completed with no data.</p>
              ))}
          </>
        )}
      </div>
    </section>
  );
}

export default ConsolePanel;
