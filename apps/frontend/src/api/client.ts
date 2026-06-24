import type { SourceRegistryListResponse } from "../types/api";

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

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
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
};

