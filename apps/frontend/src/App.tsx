import { useEffect, useState } from "react";
import {
  apiClient,
  type HealthResponse,
  type VaultSummaryResponse,
} from "./api/client";
import ConsolePanel from "./components/ConsolePanel";
import SourceRegistryPanel from "./components/SourceRegistryPanel";
import KnowledgeGraphPanel from "./components/KnowledgeGraphPanel";
import IntelligenceReportPanel from "./components/IntelligenceReportPanel";

/* Phase 22B — single-page section navigation. Each entry maps a nav label to a
   stable `id` anchor on an existing top-level surface (see Phase 22A §4.3). The
   labels mirror what the reviewer reads as section headings, so the nav reads as
   a table of contents for the one connected dashboard page — no routes, no new
   pages, no new data. */
const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "status", label: "Status" },
  { id: "vault", label: "Vault" },
  { id: "sources", label: "Sources" },
  { id: "knowledge-graph", label: "Graph" },
  { id: "intelligence-report", label: "Intelligence" },
  { id: "console", label: "Console" },
] as const;

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [vault, setVault] = useState<VaultSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>(SECTIONS[0].id);

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

  // Scrollspy: a single IntersectionObserver toggles the active nav item as each
  // section crosses a band near the top of the viewport. Presentation only — it
  // observes scroll position and sets local state; it changes no data or panel
  // behavior (Phase 22A §4.4).
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (a, b) => a.boundingClientRect.top - b.boundingClientRect.top,
          );
        if (visible.length > 0) {
          setActiveSection(visible[0].target.id);
        }
      },
      { rootMargin: "-40% 0px -55% 0px", threshold: 0 },
    );

    const observed = SECTIONS.map(({ id }) =>
      document.getElementById(id),
    ).filter((element): element is HTMLElement => element !== null);
    observed.forEach((element) => observer.observe(element));

    return () => observer.disconnect();
  }, []);

  return (
    <>
      <a className="skip-link" href="#overview">
        Skip to main content
      </a>

      <nav className="section-nav" aria-label="Dashboard sections">
        <ul className="section-nav-list">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                className={
                  activeSection === section.id
                    ? "section-nav-link section-nav-link-active"
                    : "section-nav-link"
                }
                href={`#${section.id}`}
                aria-current={activeSection === section.id ? "true" : undefined}
              >
                {section.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <main>
      <header id="overview" className="app-header" tabIndex={-1}>
        <p className="parent-label">devdevbuilds</p>
        <h1>Hive|Mind</h1>
        <p className="app-tagline">
          Local-first knowledge graph over your sources
          <span className="app-mode-badge">read-only demo build</span>
        </p>
      </header>

      <div id="status" className="status-row">
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
              <div><dt>Service</dt><dd>{health.service}</dd></div>
              <div><dt>Version</dt><dd>{health.version}</dd></div>
              <div><dt>Healthy</dt><dd>{health.ok ? "Yes" : "No"}</dd></div>
            </dl>
          ) : (
            <p className="console-hint">No health response yet.</p>
          )}
        </section>
      </div>

      <section id="vault" className="panel-vault">
        <h2>Vault summary</h2>
        {vault ? (
          <>
            <dl className="metric-grid metric-grid-vault">
              <div><dt>Files</dt><dd>{vault.totalFiles}</dd></div>
              <div><dt>Sources</dt><dd>{vault.totalSources}</dd></div>
              <div><dt>Models</dt><dd>{vault.totalModels}</dd></div>
              <div><dt>Nodes</dt><dd>{vault.totalNodes}</dd></div>
              <div><dt>Graph mode</dt><dd>{vault.graphMode}</dd></div>
            </dl>
            <p className="vault-message">{vault.message}</p>
          </>
        ) : (
          <p className="console-hint">Vault summary unavailable.</p>
        )}
      </section>

      <SourceRegistryPanel id="sources" />

      <KnowledgeGraphPanel id="knowledge-graph" />

      <IntelligenceReportPanel id="intelligence-report" />

      <ConsolePanel id="console" />
      </main>
    </>
  );
}

export default App;

