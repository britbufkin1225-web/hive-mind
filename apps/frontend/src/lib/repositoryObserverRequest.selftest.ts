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

const cases: Array<[string, ReturnType<typeof buildRepositoryObserverSnapshotRequest>]> = [
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
