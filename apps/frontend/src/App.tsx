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
import MotionSandboxPanel from "./components/MotionSandboxPanel";
import { ZERO_MOTION, type MotionCommand } from "./handLandmarkMotion";

/* Phase 27B — graph-first app shell; corrected by Phase 28B (see
   docs/phase-28a-true-graph-primary-overlay-contract.md). The Knowledge Graph
   is the full-viewport application surface; every other surface (vault/status,
   Source Registry, Intelligence Report, Console) becomes a contextual overlay
   opened from a floating, translucent icon rail instead of a permanent
   sidebar column. All panes stay mounted (just hidden) so toggling between
   them never re-triggers their data fetch — only the active pane is
   visible/focusable at a time. */
type PanelKey = "vault" | "sources" | "intelligence" | "console" | "motion";

const RAIL_ITEMS: Array<{ key: PanelKey; label: string; glyph: string }> = [
  { key: "vault", label: "Vault", glyph: "V" },
  { key: "sources", label: "Sources", glyph: "S" },
  { key: "intelligence", label: "Intelligence", glyph: "I" },
  { key: "console", label: "Console", glyph: "C" },
  // Phase 32B — Motion Sandbox: an isolated webcam-motion probe opened from the
  // same contextual rail as every other overlay. It never touches the graph.
  { key: "motion", label: "Motion", glyph: "M" },
];

const PANEL_LABELS: Record<PanelKey, string> = {
  vault: "Vault & Status",
  sources: "Source Registry",
  intelligence: "Intelligence Report",
  console: "Console",
  motion: "Motion Sandbox",
};

// The graph panel's section id, shared between the mount below and the
// dock-close focus-return so the two stay in lockstep.
const GRAPH_PANEL_ID = "knowledge-graph";

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [vault, setVault] = useState<VaultSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<PanelKey | null>(null);

  // Phase 32G — first opt-in Motion Sandbox → Knowledge Graph wiring.
  //
  // The bridge is a single ref, not React state: the Motion Sandbox writes the
  // freshest MotionCommand into it every frame, and the graph's own animation
  // loop reads it — so per-frame motion never triggers an app-wide re-render.
  // Graph control is disabled by default and only takes effect once the user
  // explicitly enables it below (opt-in); until then the graph ignores the ref
  // entirely, and the Motion Sandbox behaves exactly as before.
  const motionCommandRef = useRef<MotionCommand>(ZERO_MOTION);
  const [graphControlEnabled, setGraphControlEnabled] = useState(false);

  const handleMotionCommand = useCallback((command: MotionCommand) => {
    motionCommandRef.current = command;
  }, []);

  const dockRef = useRef<HTMLElement | null>(null);

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
    setActivePanel(null);
    // Phase 30B: return focus to the graph panel — which owns the
    // explorer/selection Escape scope — rather than to the rail button that
    // summoned the dock. The rail button sits outside that scope, so leaving
    // focus there made the next Escape a dead key until the user re-entered
    // the panel; landing focus inside the panel keeps the dismissal stack
    // (dock → explorer → selection) working press-for-press. The panel stays
    // mounted through the close, so focusing it synchronously here is safe and
    // needs no timeout; it never traps focus since Tab still moves freely.
    document.getElementById(GRAPH_PANEL_ID)?.focus();
  }, []);

  const togglePanel = useCallback((key: PanelKey) => {
    setActivePanel((current) => (current === key ? null : key));
  }, []);

  // Move focus into the dock when it opens, and let Escape close it from
  // anywhere — the dock is a contextual surface, not a modal, so the graph
  // underneath stays interactive while it's open.
  //
  // Phase 29B: Escape dismisses exactly one surface per press, topmost first
  // (Phase 29A order: tertiary dock → explorer → selection/inspector). While
  // the dock is open it is the topmost tier, so this listener runs in the
  // capture phase and stops propagation — otherwise the same press would
  // also reach the graph panel's Escape handling and close two surfaces at
  // once (e.g. the dock and the selection).
  useEffect(() => {
    if (activePanel === null) {
      return;
    }
    dockRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        closePanel();
      }
    };
    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
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
        <main id="graph-viewport" className="shell-graph-viewport">
          <KnowledgeGraphPanel
            id={GRAPH_PANEL_ID}
            graphControlEnabled={graphControlEnabled}
            motionCommandRef={motionCommandRef}
          />
        </main>

        {/* Floating utility rail: a translucent icon dock that sits over the
            graph rather than beside it — recedes to icon-only at rest, and
            reveals labels on hover/focus so it never reads as a permanent
            sidebar column (Phase 28A §6.3). */}
        <nav className="shell-rail" aria-label="Workspace panels">
          <ul className="shell-rail-list">
            {RAIL_ITEMS.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  className={
                    activePanel === item.key
                      ? "shell-rail-button shell-rail-button-active"
                      : "shell-rail-button"
                  }
                  aria-pressed={activePanel === item.key}
                  aria-controls="contextual-dock"
                  onClick={() => togglePanel(item.key)}
                >
                  <span className="shell-rail-glyph" aria-hidden="true">
                    {item.glyph}
                  </span>
                  <span className="shell-rail-label">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

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
            {/* Phase 28B correction pass 2: the Vault pane previously rendered
                three stacked `<section>` cards (each carrying the global
                opaque `--surface` background) — inside the glass dock that
                read as a monitoring dashboard restored behind the rail
                button. It's now flat rows of content sharing the dock's own
                single translucent glass panel, so there is exactly one HUD
                surface, not one outer glass card wrapping three opaque ones. */}
            <div className="shell-dock-pane" hidden={activePanel !== "vault"}>
              <div className="vault-hud">
                <div className="vault-hud-row">
                  <span className="vault-hud-label">Connection</span>
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
                </div>

                <div className="vault-hud-row">
                  <span className="vault-hud-label">API health</span>
                  {health ? (
                    <span className="vault-hud-value">
                      {health.service} · v{health.version} ·{" "}
                      {health.ok ? "Healthy" : "Unhealthy"}
                    </span>
                  ) : (
                    <span className="console-hint">No health response yet.</span>
                  )}
                </div>

                <div className="vault-hud-divider" aria-hidden="true" />

                <span className="vault-hud-label">Vault summary</span>
                {vault ? (
                  <>
                    <dl className="vault-hud-metrics">
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
                    <p className="vault-hud-message">{vault.message}</p>
                  </>
                ) : (
                  <p className="console-hint">Vault summary unavailable.</p>
                )}
              </div>
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

            {/* Phase 32B — isolated webcam Motion Sandbox. Stays mounted (just
                hidden) like the other panes, but it requests no camera and
                starts no stream until the user explicitly presses Start inside
                it, so a closed/hidden pane keeps the device untouched. */}
            <div
              className="shell-dock-pane"
              hidden={activePanel !== "motion"}
            >
              <MotionSandboxPanel
                id="motion-sandbox"
                onMotionCommand={handleMotionCommand}
                graphControlEnabled={graphControlEnabled}
                onToggleGraphControl={setGraphControlEnabled}
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
