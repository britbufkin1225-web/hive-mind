import { ApiClientError } from "../api/client.ts";
import {
  clientSafeErrorMessage,
  errorKindFrom,
  errorTitle,
  type ErrorKind,
} from "./repositoryObserverErrors.ts";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

// --- errorKindFrom: HTTP status -> stable ErrorKind ---------------------------
const statusCases: Array<[number, ErrorKind]> = [
  [400, "invalid_root"],
  [404, "not_found"],
  [422, "validation"],
  [502, "backend_unavailable"],
  [503, "backend_unavailable"],
  [500, "server"],
  [418, "unexpected"],
];
for (const [status, kind] of statusCases) {
  assertEqual(
    errorKindFrom(new ApiClientError(`status ${status}`, status)),
    kind,
    `status ${status} should classify as ${kind}`,
  );
}

// A client-side timeout takes precedence over the (null) status and is distinct
// from a plain network failure.
assertEqual(
  errorKindFrom(new ApiClientError("timed out", null, true)),
  "timeout",
  "timedOut ApiClientError should classify as timeout",
);

// A non-ApiClientError means fetch itself rejected (backend unreachable).
assertEqual(
  errorKindFrom(new TypeError("Failed to fetch")),
  "backend_unavailable",
  "raw fetch rejection should classify as backend_unavailable",
);

// --- errorTitle: every kind has a non-empty, distinct headline ----------------
const allKinds: ErrorKind[] = [
  "validation",
  "invalid_root",
  "not_found",
  "timeout",
  "backend_unavailable",
  "server",
  "unexpected",
];
const titles = new Set<string>();
for (const kind of allKinds) {
  const title = errorTitle(kind);
  assert(title.trim().length > 0, `errorTitle(${kind}) must be non-empty`);
  titles.add(title);
}
assertEqual(titles.size, allKinds.length, "each ErrorKind should have a distinct title");

// --- clientSafeErrorMessage: never leaks raw server internals -----------------
// A generic 500 is collapsed to a fixed, non-leaking string even if the error
// carries a raw exception message.
const serverError = new ApiClientError(
  "RuntimeError: credential=ghp_SUPERSECRET at /private/id_rsa",
  500,
);
const serverMessage = clientSafeErrorMessage(serverError, "server");
assertEqual(serverMessage, "Internal server error", "500 must collapse to a fixed string");
assert(!serverMessage.includes("ghp_SUPERSECRET"), "500 message must not leak secrets");
assert(!serverMessage.includes("id_rsa"), "500 message must not leak paths");

// A timeout produces an actionable recovery hint, not the raw message.
const timeoutMessage = clientSafeErrorMessage(
  new ApiClientError("Request timed out before the backend responded.", null, true),
  "timeout",
);
assert(timeoutMessage.toLowerCase().includes("try again"), "timeout message should be actionable");

// A network failure (non-ApiClientError) gets the backend-running hint.
const networkMessage = clientSafeErrorMessage(new TypeError("Failed to fetch"), "backend_unavailable");
assert(
  networkMessage.toLowerCase().includes("backend"),
  "network failure message should mention the backend",
);

// A client-safe backend detail (e.g. 400/404) is passed through unchanged.
const detailMessage = clientSafeErrorMessage(
  new ApiClientError("Repository root not found", 404),
  "not_found",
);
assertEqual(detailMessage, "Repository root not found", "safe backend detail should pass through");

console.log("repositoryObserverErrors selftest: all assertions passed.");
