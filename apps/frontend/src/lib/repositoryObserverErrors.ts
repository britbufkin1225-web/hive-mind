import { ApiClientError } from "../api/client.ts";

/**
 * Deterministic, operator-facing classification of Repository Observer request
 * failures. Each kind maps a transport/backend outcome to a single recovery
 * story; the mapping is exhaustive so the panel never renders an unclassified
 * failure. Extracted from the panel so it can be exercised by the request
 * self-tests without a DOM harness.
 */
export type ErrorKind =
  | "validation"
  | "invalid_root"
  | "not_found"
  | "timeout"
  | "backend_unavailable"
  | "server"
  | "unexpected";

/**
 * Classify a caught request error into a stable {@link ErrorKind}.
 *
 * A non-{@link ApiClientError} means `fetch` itself rejected (the backend was
 * unreachable), which is presented as "backend unavailable". A client-side
 * bounded timeout is reported by {@link ApiClientError.timedOut} and takes
 * precedence over the (null) status so it reads as a distinct, recoverable
 * timeout rather than a generic outage.
 */
export function errorKindFrom(error: unknown): ErrorKind {
  if (!(error instanceof ApiClientError)) {
    return "backend_unavailable";
  }
  if (error.timedOut) {
    return "timeout";
  }
  if (error.status === 400) {
    return "invalid_root";
  }
  if (error.status === 404) {
    return "not_found";
  }
  if (error.status === 422) {
    return "validation";
  }
  if (error.status === 502 || error.status === 503) {
    return "backend_unavailable";
  }
  if (error.status === 500) {
    return "server";
  }
  return "unexpected";
}

/** Short, safe headline for each failure class. */
export function errorTitle(kind: ErrorKind): string {
  switch (kind) {
    case "validation":
      return "Request did not match the contract.";
    case "invalid_root":
      return "Repository root could not be observed.";
    case "not_found":
      return "Repository root was not found.";
    case "timeout":
      return "Repository Observer request timed out.";
    case "backend_unavailable":
      return "Repository Observer is unavailable.";
    case "server":
      return "Repository Observer returned an unexpected server error.";
    case "unexpected":
      return "Repository snapshot failed.";
  }
}

/**
 * Produce a client-safe message body for a failed request. Never surfaces a raw
 * server exception: a generic 500 is collapsed to a fixed string, a timeout and
 * a network failure get actionable recovery hints, and any backend-provided
 * detail (already client-safe from the router) is passed through otherwise.
 */
export function clientSafeErrorMessage(error: unknown, kind: ErrorKind): string {
  if (kind === "timeout") {
    return "The backend did not respond in time. Confirm the runtime is healthy and try again.";
  }
  if (!(error instanceof ApiClientError)) {
    return "Network request failed. Is the backend running?";
  }
  if (kind === "server") {
    return "Internal server error";
  }
  return error.message;
}
