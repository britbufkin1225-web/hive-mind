import type {
  RepositoryDriftAnalysisRequest,
  RepositoryObservationSnapshotRequest,
} from "../types/api";

export const REPOSITORY_OBSERVER_MAX_FILE_COUNT = 1024;
export const REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES = 262_144;
export const REPOSITORY_OBSERVER_MAX_PATH_LENGTH = 2048;

export interface RepositoryObserverRequestInput {
  repositoryRoot: string;
  observedAt: string;
  maxFileCount: number;
  maxSnapshotBytes: number;
}

export interface RepositoryObserverRequestResult {
  request: RepositoryObservationSnapshotRequest | null;
  error: string | null;
}

export interface RepositoryDriftRequestResult {
  request: RepositoryDriftAnalysisRequest | null;
  error: string | null;
}

interface ValidatedRepositoryObserverRequest {
  repository_root: string;
  observed_at: string;
  max_file_count: number;
  max_snapshot_bytes: number;
}

function isAbsoluteLocalPath(value: string): boolean {
  return (
    /^[A-Za-z]:[\\/]/.test(value) ||
    value.startsWith("\\\\") ||
    value.startsWith("/")
  );
}

function containsParentTraversal(value: string): boolean {
  return value
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)
    .includes("..");
}

function validIsoTimestamp(value: string): boolean {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed);
}

function integerWithin(value: number, min: number, max: number): boolean {
  return Number.isInteger(value) && value >= min && value <= max;
}

function validateRepositoryObserverRequest(
  input: RepositoryObserverRequestInput,
): { request: ValidatedRepositoryObserverRequest | null; error: string | null } {
  const repositoryRoot = input.repositoryRoot.trim();
  if (repositoryRoot === "") {
    return { request: null, error: "Enter an absolute repository path." };
  }
  if (repositoryRoot.length > REPOSITORY_OBSERVER_MAX_PATH_LENGTH) {
    return { request: null, error: "Repository path is too long." };
  }
  if (repositoryRoot.includes("\0")) {
    return { request: null, error: "Repository path is malformed." };
  }
  if (!isAbsoluteLocalPath(repositoryRoot)) {
    return {
      request: null,
      error: "Repository path must be absolute.",
    };
  }
  if (containsParentTraversal(repositoryRoot)) {
    return {
      request: null,
      error: "Repository path must not include parent traversal.",
    };
  }

  const observedAt = input.observedAt.trim();
  if (!validIsoTimestamp(observedAt)) {
    return {
      request: null,
      error: "Observation timestamp must be a valid ISO timestamp.",
    };
  }

  if (!integerWithin(input.maxFileCount, 0, REPOSITORY_OBSERVER_MAX_FILE_COUNT)) {
    return {
      request: null,
      error: `File limit must be an integer from 0 to ${REPOSITORY_OBSERVER_MAX_FILE_COUNT}.`,
    };
  }
  if (
    !integerWithin(
      input.maxSnapshotBytes,
      0,
      REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES,
    )
  ) {
    return {
      request: null,
      error: `Snapshot byte limit must be an integer from 0 to ${REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES}.`,
    };
  }

  return {
    error: null,
    request: {
      repository_root: repositoryRoot,
      observed_at: observedAt,
      max_file_count: input.maxFileCount,
      max_snapshot_bytes: input.maxSnapshotBytes,
    },
  };
}

export function buildRepositoryObserverSnapshotRequest(
  input: RepositoryObserverRequestInput,
): RepositoryObserverRequestResult {
  return validateRepositoryObserverRequest(input);
}

export function buildRepositoryDriftAnalysisRequest(
  input: RepositoryObserverRequestInput,
): RepositoryDriftRequestResult {
  const result = validateRepositoryObserverRequest(input);
  if (!result.request) {
    return { request: null, error: result.error };
  }
  return {
    error: null,
    request: { ...result.request, baseline_reference: "HEAD" },
  };
}
