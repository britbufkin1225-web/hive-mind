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

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [vault, setVault] = useState<VaultSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main>
      <header>
        <p className="parent-label">devdevbuilds</p>
        <h1>Hive|Mind</h1>
        <p>Local-first knowledge graph over your sources · read-only demo build</p>
      </header>

      <section>
        <h2>Backend connection test</h2>
        {error ? (
          <p className="error">Disconnected: {error}</p>
        ) : health ? (
          <p className="success">Connected</p>
        ) : (
          <p>Checking connection…</p>
        )}
      </section>

      <section>
        <h2>API health</h2>
        {health ? (
          <dl>
            <div><dt>Service</dt><dd>{health.service}</dd></div>
            <div><dt>Version</dt><dd>{health.version}</dd></div>
            <div><dt>Healthy</dt><dd>{health.ok ? "Yes" : "No"}</dd></div>
          </dl>
        ) : (
          <p>No health response yet.</p>
        )}
      </section>

      <section>
        <h2>Vault summary placeholder</h2>
        {vault ? (
          <>
            <dl>
              <div><dt>Files</dt><dd>{vault.totalFiles}</dd></div>
              <div><dt>Sources</dt><dd>{vault.totalSources}</dd></div>
              <div><dt>Models</dt><dd>{vault.totalModels}</dd></div>
              <div><dt>Nodes</dt><dd>{vault.totalNodes}</dd></div>
              <div><dt>Graph mode</dt><dd>{vault.graphMode}</dd></div>
            </dl>
            <p>{vault.message}</p>
          </>
        ) : (
          <p>Vault summary unavailable.</p>
        )}
      </section>

      <SourceRegistryPanel />

      <KnowledgeGraphPanel />

      <IntelligenceReportPanel />

      <ConsolePanel />
    </main>
  );
}

export default App;

