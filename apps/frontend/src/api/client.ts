import type {
  ContextPacket,
  ContextPacketRequest,
  IntelligenceReport,
  KnowledgeGraphResponse,
  ObsidianImportRequest,
  ObsidianImportSummary,
  RepositoryObservationSnapshotRequest,
  RepositoryDriftAnalysis,
  RepositoryDriftAnalysisRequest,
  RepositorySnapshot,
  SourceRegistryListResponse,
} from "../types/api";

// `import.meta.env` is populated by Vite at build time. Guard the access with
// `?.` so this module can also be imported by the plain-Node request self-tests
// (where `import.meta.env` is undefined) without throwing at module load.
const API_BASE_URL =
  import.meta.env?.VITE_API_BASE_URL ?? "http://localhost:8787/api";

// Bounded default timeout for Repository Observer transport. A hung or
// unreachable backend must fail as a distinct, recoverable timeout rather than
// leaving the request pending forever; the observer service is itself bounded
// (Phase 37J subprocess timeout is 5s), so a generous client ceiling above that
// still surfaces a stuck transport deterministically.
export const REPOSITORY_OBSERVER_REQUEST_TIMEOUT_MS = 15_000;

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

export class ApiClientError extends Error {
  readonly status: number | null;
  /**
   * True when the request was aborted by the client-side bounded timeout
   * rather than answered by the backend. Lets the UI present a distinct,
   * recoverable "request timed out" state instead of a generic failure.
   */
  readonly timedOut: boolean;

  // Explicit field declarations (rather than TypeScript parameter properties)
  // keep this module importable by the plain-Node request self-tests, whose
  // strip-only TypeScript loader does not support parameter properties.
  constructor(message: string, status: number | null, timedOut = false) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.timedOut = timedOut;
  }
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new ApiClientError(
      `API request failed with status ${response.status}`,
      response.status,
    );
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
    throw new ApiClientError(await errorMessage(response), response.status);
  }

  return response.json() as Promise<T>;
}

/**
 * POST with a bounded client-side timeout. On timeout the in-flight request is
 * aborted and a `timedOut` {@link ApiClientError} is thrown so the caller can
 * present a distinct, recoverable state. A genuine network failure (backend
 * down) still surfaces as a non-timeout error, keeping the two transport
 * failure modes distinguishable.
 */
async function postWithTimeout<T>(
  path: string,
  body: unknown,
  timeoutMs: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error: unknown) {
    if (controller.signal.aborted) {
      throw new ApiClientError(
        "Request timed out before the backend responded.",
        null,
        true,
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    throw new ApiClientError(await errorMessage(response), response.status);
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
  buildContextPacket: (request: ContextPacketRequest) =>
    post<ContextPacket>("/active-memory/context-packet", request),
  observeRepositorySnapshot: (request: RepositoryObservationSnapshotRequest) =>
    postWithTimeout<RepositorySnapshot>(
      "/repository-observer/snapshot",
      request,
      REPOSITORY_OBSERVER_REQUEST_TIMEOUT_MS,
    ),
  analyzeRepositoryDrift: (request: RepositoryDriftAnalysisRequest) =>
    postWithTimeout<RepositoryDriftAnalysis>(
      "/repository-observer/drift",
      request,
      REPOSITORY_OBSERVER_REQUEST_TIMEOUT_MS,
    ),
  importObsidianVault: (request: ObsidianImportRequest) =>
    post<ObsidianImportSummary>("/obsidian/import", request),
};

