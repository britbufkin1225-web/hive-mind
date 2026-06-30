import { useCallback, useEffect, useRef, useState } from "react";
import {
  apiClient,
  type HealthResponse,
  type VaultSummaryResponse,
} from "./api/client";
import ConsolePanel from "./components/ConsolePanel";
import SourceRegistryPanel from "./components/SourceRegistryPanel";
import KnowledgeGraphPanel from "./components/KnowledgeGraphPanel";
import IntelligenceReportPanel from "./components/IntelligenceReportPanel";

/* Phase 27B — graph-first app shell. The Knowledge Graph is the persistent
   primary viewport; every other surface (vault/status, Source Registry,
   Intelligence Report, Console) becomes a contextual dock pane opened from a
   compact control rail instead of a stacked dashboard section. All panes stay
   mounted (just hidden) so toggling between them never re-triggers their data
   fetch — only the active pane is visible/focusable at a time. */
type PanelKey = "vault" | "sources" | "intelligence" | "console";

const RAIL_ITEMS: Array<{ key: PanelKey; label: string }> = [
  { key: "vault", label: "Vault" },
  { key: "sources", label: "Sources" },
  { key: "intelligence", label: "Intelligence" },
  { key: "console", label: "Console" },
];

const PANEL_LABELS: Record<PanelKey, string> = {
  vault: "Vault & Status",
  sources: "Source Registry",
  intelligence: "Intelligence Report",
  console: "Console",
};

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [vault, setVault] = useState<VaultSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<PanelKey | null>(null);

  const dockRef = useRef<HTMLElement | null>(null);
  const railButtonRefs = useRef<Partial<Record<PanelKey, HTMLButtonElement | null>>>(
    {},
  );

  useEffect(() => {
    Promise.all([apiClient.getHealth(), apiClient.getVaultSummary()])
      .then(([healthResponse, vaultResponse]) => {
        setHealth(healthResponse);
        setVault(vaultResponse);
      })
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to reach the backend.",
        );
      });
  }, []);

  const closePanel = useCallback(() => {
    setActivePanel((current) => {
      if (current) {
        railButtonRefs.current[current]?.focus();
      }
      return null;
    });
  }, []);

  const togglePanel = useCallback((key: PanelKey) => {
    setActivePanel((current) => (current === key ? null : key));
  }, []);

  // Move focus into the dock when it opens, and let Escape close it from
  // anywhere — the dock is a contextual surface, not a modal, so the graph
  // underneath stays interactive while it's open.
  useEffect(() => {
    if (activePanel === null) {
      return;
    }
    dockRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closePanel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activePanel, closePanel]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#graph-viewport">
        Skip to knowledge graph
      </a>

      <header className="shell-topbar">
        <div className="shell-topbar-brand">
          <p className="parent-label">devdevbuilds</p>
          <h1>Hive|Mind</h1>
        </div>
        <p className="shell-topbar-tagline">
          Local-first knowledge graph over your sources
          <span className="app-mode-badge">read-only demo build</span>
        </p>
        <div className="shell-topbar-status">
          {error ? (
            <p className="status-pill status-pill-error">
              <span className="status-dot" aria-hidden="true" />
              Disconnected
            </p>
          ) : health ? (
            <p className="status-pill status-pill-success">
              <span className="status-dot" aria-hidden="true" />
              Connected
            </p>
          ) : (
            <p className="status-pill status-pill-pending">
              <span className="status-dot" aria-hidden="true" />
              Checking…
            </p>
          )}
        </div>
      </header>

      <div className="shell-body">
        <nav className="shell-rail" aria-label="Workspace panels">
          <ul className="shell-rail-list">
            {RAIL_ITEMS.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  ref={(element) => {
                    railButtonRefs.current[item.key] = element;
                  }}
                  className={
                    activePanel === item.key
                      ? "shell-rail-button shell-rail-button-active"
                      : "shell-rail-button"
                  }
                  aria-pressed={activePanel === item.key}
                  aria-controls="contextual-dock"
                  onClick={() => togglePanel(item.key)}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <main id="graph-viewport" className="shell-graph-viewport">
          <KnowledgeGraphPanel id="knowledge-graph" />
        </main>

        <aside
          id="contextual-dock"
          ref={dockRef}
          className={
            activePanel ? "shell-dock shell-dock-open" : "shell-dock"
          }
          aria-hidden={activePanel === null}
          aria-label={
            activePanel ? PANEL_LABELS[activePanel] : "Contextual panel"
          }
          // `inert` is a standard HTML attribute (React 19 supports it); it
          // keeps the closed dock's contents out of tab order and pointer
          // reach without unmounting them, so reopening never re-fetches data.
          inert={activePanel === null ? true : undefined}
          tabIndex={-1}
        >
          <div className="shell-dock-header">
            <h2>{activePanel ? PANEL_LABELS[activePanel] : "Panel"}</h2>
            <button
              type="button"
              className="shell-dock-close"
              onClick={closePanel}
            >
              Close
            </button>
          </div>

          <div className="shell-dock-body">
            <div className="shell-dock-pane" hidden={activePanel !== "vault"}>
              <div className="status-row">
                <section className="panel-connection">
                  <h2>Backend connection</h2>
                  {error ? (
                    <p className="status-pill status-pill-error">
                      <span className="status-dot" aria-hidden="true" />
                      Disconnected: {error}
                    </p>
                  ) : health ? (
                    <p className="status-pill status-pill-success">
                      <span className="status-dot" aria-hidden="true" />
                      Connected
                    </p>
                  ) : (
                    <p className="status-pill status-pill-pending">
                      <span className="status-dot" aria-hidden="true" />
                      Checking connection…
                    </p>
                  )}
                </section>

                <section className="panel-health">
                  <h2>API health</h2>
                  {health ? (
                    <dl className="metric-grid">
                      <div>
                        <dt>Service</dt>
                        <dd>{health.service}</dd>
                      </div>
                      <div>
                        <dt>Version</dt>
                        <dd>{health.version}</dd>
                      </div>
                      <div>
                        <dt>Healthy</dt>
                        <dd>{health.ok ? "Yes" : "No"}</dd>
                      </div>
                    </dl>
                  ) : (
                    <p className="console-hint">No health response yet.</p>
                  )}
                </section>
              </div>

              <section className="panel-vault">
                <h2>Vault summary</h2>
                {vault ? (
                  <>
                    <dl className="metric-grid metric-grid-vault">
                      <div>
                        <dt>Files</dt>
                        <dd>{vault.totalFiles}</dd>
                      </div>
                      <div>
                        <dt>Sources</dt>
                        <dd>{vault.totalSources}</dd>
                      </div>
                      <div>
                        <dt>Models</dt>
                        <dd>{vault.totalModels}</dd>
                      </div>
                      <div>
                        <dt>Nodes</dt>
                        <dd>{vault.totalNodes}</dd>
                      </div>
                      <div>
                        <dt>Graph mode</dt>
                        <dd>{vault.graphMode}</dd>
                      </div>
                    </dl>
                    <p className="vault-message">{vault.message}</p>
                  </>
                ) : (
                  <p className="console-hint">Vault summary unavailable.</p>
                )}
              </section>
            </div>

            <div
              className="shell-dock-pane"
              hidden={activePanel !== "sources"}
            >
              <SourceRegistryPanel id="sources" />
            </div>

            <div
              className="shell-dock-pane"
              hidden={activePanel !== "intelligence"}
            >
              <IntelligenceReportPanel id="intelligence-report" />
            </div>

            <div
              className="shell-dock-pane"
              hidden={activePanel !== "console"}
            >
              <ConsolePanel id="console" />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
