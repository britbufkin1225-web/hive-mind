import type {
  IntelligenceReport,
  KnowledgeGraphResponse,
  ObsidianImportRequest,
  ObsidianImportSummary,
  SourceRegistryListResponse,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8787/api";

export interface HealthResponse {
  ok: boolean;
  service: string;
  version: string;
}

export interface StatusResponse {
  app: string;
  parent: string;
  environment: string;
  backend: string;
  frontend: string;
}

export interface VaultSummaryResponse {
  totalFiles: number;
  totalSources: number;
  totalModels: number;
  totalNodes: number;
  graphMode: string;
  message: string;
}

export interface ConsoleExecuteResponse {
  ok: boolean;
  command: string;
  result: Record<string, unknown> | null;
  error: string | null;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Pull a human-readable message out of a failed JSON response. FastAPI puts the
 * useful text in `detail` (a string for HTTPException, or a list for 422 schema
 * errors); fall back to the status when nothing usable is present.
 */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    const detail = body?.detail;
    if (typeof detail === "string" && detail.trim() !== "") {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === "string" && first.msg.trim() !== "") {
        return first.msg;
      }
    }
  } catch {
    // Non-JSON or empty body — fall through to the status-based message.
  }
  return `API request failed with status ${response.status}`;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => get<HealthResponse>("/health"),
  getStatus: () => get<StatusResponse>("/status"),
  getVaultSummary: () => get<VaultSummaryResponse>("/vault/summary"),
  executeConsole: (command: string) =>
    post<ConsoleExecuteResponse>("/console/execute", { command }),
  getRegistrySources: () =>
    get<SourceRegistryListResponse>("/registry/sources"),
  getKnowledgeGraph: () =>
    get<KnowledgeGraphResponse>("/knowledge-graph"),
  getIntelligenceReport: () =>
    get<IntelligenceReport>("/intelligence/report"),
  importObsidianVault: (request: ObsidianImportRequest) =>
    post<ObsidianImportSummary>("/obsidian/import", request),
  
};

