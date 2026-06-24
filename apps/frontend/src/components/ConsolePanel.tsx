import { useState, type FormEvent } from "react";
import {
  apiClient,
  type ConsoleExecuteResponse,
} from "../api/client";

type PanelState = "idle" | "loading" | "success" | "error";

function ConsolePanel() {
  const [command, setCommand] = useState("");
  const [state, setState] = useState<PanelState>("idle");
  const [response, setResponse] = useState<ConsoleExecuteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = command.trim();
    if (!trimmed || state === "loading") {
      return;
    }

    setState("loading");
    setError(null);
    setResponse(null);

    try {
      const result = await apiClient.executeConsole(trimmed);
      setResponse(result);
      setState("success");
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Console request failed.",
      );
      setState("error");
    }
  }

  function handleClear() {
    setCommand("");
    setState("idle");
    setResponse(null);
    setError(null);
  }

  return (
    <section className="console-panel">
      <h2>Hive Console</h2>

      <form className="console-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="console-input"
          placeholder='Try: help, status, list nodes, find note, add note "hello"'
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          aria-label="Console command"
        />
        <div className="console-actions">
          <button type="submit" disabled={state === "loading" || !command.trim()}>
            {state === "loading" ? "Running…" : "Run"}
          </button>
          <button
            type="button"
            className="console-clear"
            onClick={handleClear}
            disabled={state === "loading"}
          >
            Clear
          </button>
        </div>
      </form>

      <div className="console-output">
        {state === "idle" && (
          <p className="console-hint">
            Enter a command to query the backend console. Nothing has run yet.
          </p>
        )}

        {state === "loading" && <p>Running command…</p>}

        {state === "error" && (
          <p className="error">Request failed: {error}</p>
        )}

        {state === "success" && response && (
          <>
            <p className={response.ok ? "success" : "error"}>
              {response.ok
                ? `OK — ${response.command}`
                : `Error — ${response.error ?? "command failed"}`}
            </p>
            <pre className="console-result">
              {JSON.stringify(response.result ?? response, null, 2)}
            </pre>
          </>
        )}
      </div>
    </section>
  );
}

export default ConsolePanel;
