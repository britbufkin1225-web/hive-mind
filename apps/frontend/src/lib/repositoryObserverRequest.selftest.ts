import {
  buildRepositoryObserverSnapshotRequest,
  REPOSITORY_OBSERVER_MAX_FILE_COUNT,
  REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES,
} from "./repositoryObserverRequest.ts";

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

const valid = buildRepositoryObserverSnapshotRequest({
  repositoryRoot: " C:\\Users\\britb\\Documents\\hive-mind ",
  observedAt: "2026-07-18T12:00:00.000Z",
  maxFileCount: 25,
  maxSnapshotBytes: 4096,
});

assert(valid.request !== null, "valid request should serialize");
assertEqual(valid.error, null, "valid request should not return an error");
assertEqual(
  valid.request?.repository_root,
  "C:\\Users\\britb\\Documents\\hive-mind",
  "repository_root should be trimmed and preserved",
);
assertEqual(valid.request?.max_file_count, 25, "max_file_count should serialize");
assertEqual(
  valid.request?.max_snapshot_bytes,
  4096,
  "max_snapshot_bytes should serialize",
);
assert(
  !Object.prototype.hasOwnProperty.call(valid.request, "scope"),
  "scope should not be sent when the MVP does not expose it",
);

// Boundary minimums (0/0) and maximums must be accepted, not rejected — the
// backend bounds are inclusive (ge=0, le=MAX), so the frontend must not tighten
// them by an off-by-one.
const boundaryMin = buildRepositoryObserverSnapshotRequest({
  repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
  observedAt: "2026-07-18T12:00:00.000Z",
  maxFileCount: 0,
  maxSnapshotBytes: 0,
});
assert(boundaryMin.request !== null, "0/0 limits should be accepted");
assertEqual(boundaryMin.request?.max_file_count, 0, "max_file_count 0 should serialize");
assertEqual(boundaryMin.request?.max_snapshot_bytes, 0, "max_snapshot_bytes 0 should serialize");

const boundaryMax = buildRepositoryObserverSnapshotRequest({
  repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
  observedAt: "2026-07-18T12:00:00.000Z",
  maxFileCount: REPOSITORY_OBSERVER_MAX_FILE_COUNT,
  maxSnapshotBytes: REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES,
});
assert(boundaryMax.request !== null, "maximum limits should be accepted");

// UNC-style absolute roots must survive unchanged (backend accepts absolute
// Windows paths; the frontend must not corrupt the leading double backslash).
const uncRoot = buildRepositoryObserverSnapshotRequest({
  repositoryRoot: "\\\\server\\share\\repo",
  observedAt: "2026-07-18T12:00:00.000Z",
  maxFileCount: 10,
  maxSnapshotBytes: 4096,
});
assert(uncRoot.request !== null, "UNC-style absolute root should be accepted");
assertEqual(
  uncRoot.request?.repository_root,
  "\\\\server\\share\\repo",
  "UNC root should be preserved verbatim",
);

// A valid explicit-offset timestamp (not just UTC "Z") must be accepted.
const offsetTimestamp = buildRepositoryObserverSnapshotRequest({
  repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
  observedAt: "2026-07-18T12:00:00-04:00",
  maxFileCount: 10,
  maxSnapshotBytes: 4096,
});
assert(offsetTimestamp.request !== null, "explicit-offset timestamp should be accepted");
assertEqual(
  offsetTimestamp.request?.observed_at,
  "2026-07-18T12:00:00-04:00",
  "explicit-offset timestamp should be preserved verbatim",
);

const cases: Array<[string, ReturnType<typeof buildRepositoryObserverSnapshotRequest>]> = [
  [
    "empty root",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "whitespace-only root",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "    ",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "decimal file count",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1.5,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "NaN byte limit",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: Number.NaN,
    }),
  ],
  [
    "negative file count",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: -1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "relative path",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "parent traversal",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\..\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "bad timestamp",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "not-a-date",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "missing timestamp",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "   ",
      maxFileCount: 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "file count overflow",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: REPOSITORY_OBSERVER_MAX_FILE_COUNT + 1,
      maxSnapshotBytes: 1,
    }),
  ],
  [
    "snapshot byte overflow",
    buildRepositoryObserverSnapshotRequest({
      repositoryRoot: "C:\\Users\\britb\\Documents\\hive-mind",
      observedAt: "2026-07-18T12:00:00.000Z",
      maxFileCount: 1,
      maxSnapshotBytes: REPOSITORY_OBSERVER_MAX_SNAPSHOT_BYTES + 1,
    }),
  ],
];

for (const [label, result] of cases) {
  assert(result.request === null, `${label} should fail validation`);
  assert(result.error !== null, `${label} should return a readable error`);
}

console.log("repositoryObserverRequest selftest: all assertions passed.");
