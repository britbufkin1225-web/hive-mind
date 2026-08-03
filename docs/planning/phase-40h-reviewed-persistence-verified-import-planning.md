# Phase 40H — Reviewed Persistence + Verified Import (Planning)

**Status:** Planning-only. No runtime implementation exists. This document defines
the foundation; nothing here is built. Earlier commits resolved the six high-severity
blockers and three medium-severity gaps of the four-commit Codex audit (kind↔claim policy
§C.2; project/scope authorization context §C.3; ledger + snapshot envelope integrity
§H.7/§H.8; complete `MemoryRecord` equality §F.3; stable authoritative provenance §F.3;
removal of impossible historical-generation restoration §I; shared canonicalization +
collision policy §H.0; `review_decision_id` derivation §H.9; explicit holder
read/write-guard boundaries §A.6.1). **This commit additionally closes the material
defects of the independent five-commit Codex audit** — the review/authorization identity
cycle (now an acyclic dependency graph, §H.0a/§H.9/§H.10, Codex-1); pre-durability
live-store visibility (a private candidate store built off-guard, persisted and verified
durably, then published **last** via an O(1) holder swap, §A.6/§E/§I, Codex-2); the
callback-based raw-store escape (replaced by holder-owned read/query/`publish` operations
with **no caller callbacks**, §A.6, Codex-3); scope authorization by **exact set
membership** with no invented hierarchy plus `project_level_authorized` (§C.3, Codex-4);
**complete** authorization-digest coverage of `issued_at` (§H.10, Codex-5); an explicit
reviewer-authored **`observed_at`** kept distinct from `created_at` (§C.1/§F.3, Codex-6);
one deterministic **timestamp-only-vs-renewal** rule with a `renewal_revision`
discriminator (§H.9/§D.7, Codex-7); and **non-overlapping malformed-claim diagnostic
precedence** (§C.1/§C.2/§J, Codex-8). It remains **proposed and pending a further
independent six-commit audit** (another Codex re-audit); the five-commit audit has **not**
passed and no wording claims it did. Implementation stays locked until this planning
branch passes that further audit and is merged. No public Phase 40H API exists.
**Track:** Grounded Synthesis + Memory Migration (Phase 40D.5–40L sequence).
**Baseline:** `origin/main` at merge commit
`d1b2c3eea662ccb8876de9761650e31c0e44f4b9`.
**Branch:** `phase-40h-reviewed-persistence-verified-import-planning`.
**Depends on (merged / locally implemented, unchanged):**
[Phase 40E](phase-40e-memory-migration-contract-intake-safety-foundation.md) (intake,
merged), [Phase 40F](phase-40f-export-parser-candidate-projection.md) (parser +
projector), [Phase 40G](phase-40g-migration-candidate-assessment-dry-run.md)
(candidate-set dry-run assessment), and the existing Phase 37B/37C **Active Memory
contract + store** ([`app/models/active_memory.py`](../../apps/backend/app/models/active_memory.py),
[`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py)),
which Phase 40H integrates with and does **not** redefine.

Phase 40H is the first phase in the memory-migration track permitted to **create an
Active Memory record from a migration candidate** — and only for a candidate a human
has explicitly reviewed and approved, and only **through the existing Active Memory
ownership boundary**. Everything before it is read-only: Phase 40E judges
declarations, Phase 40F reads bytes and projects inactive candidates, Phase 40G
assesses the candidate set. None of them writes anything durable. Phase 40H adds the
durable, human-gated bridge from an assessed candidate to an Active Memory record,
and it does so without ever inferring approval from parsing success, assessment
cleanliness, or an approval boolean standing alone.

This is a **planning document**. It defines the ownership model, the durable
migration-workflow record types, the review-provenance requirements, the mandatory
reviewer-approved **import specification** that supplies the record kind, the
structured claim, and the validated project id the Phase 40F candidate does **not**
carry, the **closed, versioned kind↔claim compatibility policy** its named validator
owns (§C.2), the mandatory typed **project/scope authorization context** owned by the
human authorization boundary (§C.3), the persistence lifecycle, the verified-import
contract, the authorized Active-Memory-insertion seam, the mandatory **authoritative
live-store holder** and its explicit read/write-guard synchronization protocol and
atomic store replacement, the mandatory durable **Active Memory snapshot store**, the
**complete integrity digests sealing both durable envelopes** (ledger and snapshot,
§H.7/§H.8), the shared persisted **commit generation** that binds the two durable
artifacts, the single **import coordinator** and its one concrete exclusive lock-file
protocol, the ordered intent/effect/receipt protocol, the explicit **N/N+1
uncertain-commit recovery exception** evaluated before ordinary generation equality
(and only after both envelopes pass integrity validation), the **post-insert rollback
and quarantine** rules, the idempotency/replay contract with a monotonic attempt
sequence, the **candidate-to-`MemoryRecord` provenance mapping** with a **complete
canonical `MemoryRecord` equality** gate, the **canonical identity derivation** for
every derived id under one **shared canonicalization + collision policy** (§H.0), the
full-content **receipt integrity digest**, uncertain-commit recovery with **no
impossible historical-generation restoration**, the typed diagnostics, the test
matrix, the integration map, the API decision, and the deferred work. It implements
none of them.

---

## 0. The one thing this phase exists to prevent

> An approval boolean by itself is not valid provenance.

A field reading `approved = true` records that *someone set a flag*. It does not
record **who** decided, **when**, **against which exact candidate bytes**, against
**which assessment**, on **what evidence**, or **why**. Phase 40H treats a bare
approval flag as meaningless. Mutation authority flows only from a complete,
immutable **review-decision record** bound to a specific candidate digest and a
specific assessment identity/version, re-validated at import time. If any part of
that binding is missing, stale, or contradictory, import **fails closed** and
Active Memory is not touched.

Three things are kept structurally distinct and are never conflated:

1. **Verified candidate bytes** — the bytes are the bytes the user declared
   (Phase 40F already proves this via recomputed digest; Phase 40H re-proves it at
   import time). This says nothing about whether the content is true.
2. **Reviewed claims and assessment** — a human looked at the assessed candidate
   set and its dry-run report and recorded an explicit, attributable decision.
   This is a statement about a *decision*, not about truth.
3. **Verified import into Active Memory** — a candidate a human approved was
   durably imported into the existing Active Memory store exactly once, under a
   deterministic receipt that links the candidate, its digest, its assessment, the
   review decision, the import attempt, the shared commit generation, and the exact
   resulting `MemoryRecord.record_id`.

"Verified import" proves the pipeline was honored end-to-end and byte-consistent.
It does **not** prove the imported statement is factually true — the resulting
Active Memory record is imported evidence, never adjudicated truth (see §E.1).

---

## A. State-ownership contract

Phase 40H spans **two durable stores plus one authoritative in-memory store reached
only through a mandatory live-store holder**, with distinct owners, and the plan is
explicit about which owns what. Conflating them is the specific failure this section
exists to prevent. Four distinct owners exist: the **`ActiveMemorySnapshotStore`**
owns durable snapshots (§A.4); the **`AuthoritativeActiveMemoryStoreHolder`** owns
the current live authoritative in-memory store reference and its atomic replacement
(§A.6); the **`MigrationImportStore`** owns durable migration-workflow records
(§A.3); and the **import coordinator** owns the reviewed-import transaction (§A.2).
These four responsibilities never merge.

### A.1 The Active Memory store remains authoritative for Active Memory records

The existing Phase 37C store — the `MemoryStore` protocol and its
`InMemoryActiveMemoryStore` implementation in
[`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py)
— **remains the sole authority for `MemoryRecord` state.** Phase 40H does **not**
introduce a competing Active Memory store, and it does **not** copy, wrap, shadow, or
re-home authoritative `MemoryRecord` data inside the migration ledger. The Active
Memory store keeps its own identity rule (caller-supplied `record_id`), its own
immutability guarantee, its own lifecycle transition table, and its own
serialize/restore boundary. Phase 40H reads and writes Active Memory **only** through
that store's existing public seam (§F.2). The **published live** store instance is served
**only** through the mandatory `AuthoritativeActiveMemoryStoreHolder`'s holder-owned
operations (§A.6) — no caller ever obtains, retains, or injects the published mutable
store reference (Codex-3). Preparation of an import runs on a **private candidate store**
the coordinator reconstructs from the durable snapshot and publishes only after durable
verification (§A.6, §E, Codex-2). The **durable Active Memory snapshot** (§A.4) is the
authoritative durable representation of that store's records; the migration ledger never
holds record content.

### A.2 The import coordinator is an orchestration boundary

A single new backend service, the **Reviewed Migration Import Service** (working
name `MemoryMigrationImportService`), is the **one import coordinator**. It is
**not** an Active Memory store. It is an **orchestration boundary** that owns the
exclusive writer lock (§I.4) and coordinates three stores — the durable migration
ledger, the durable Active Memory snapshot, and the authoritative in-memory Active
Memory store — to perform one reviewed import:

- it records review decisions, import attempts, and receipts in the durable
  migration ledger (§A.3);
- it constructs the authorized `MemoryRecord` and inserts it into a **private candidate
  Active Memory store** it builds from the last validated durable snapshot (§A.4, §A.6) —
  never into the published live store — then persists that candidate as the durable
  snapshot at the next generation, and only after durable verification **publishes** the
  validated candidate through the holder's `publish` swap (§A.6, §E);
- it answers idempotent replay lookups and drives uncertain-commit recovery (§I.7).

It owns the *workflow and the orchestration*, never the Active Memory records
themselves. No router, parser, projector, assessor, or frontend may write
migration-import workflow state; they call this coordinator or they read nothing.

### A.3 MigrationImportStore owns durable migration-workflow records only

Durable migration-workflow state lives behind a **persistence adapter** (working
name `MigrationImportStore`) that is the only component performing filesystem I/O for
the *ledger*. **It owns exactly four kinds of durable record and nothing else:**

1. **review decisions** (who approved/rejected/deferred which exact reviewed input);
2. **import attempts** (each retry a distinct attempt, §G);
3. **import receipts** (the deterministic link set, referencing — never copying —
   the resulting `MemoryRecord.record_id`);
4. **idempotency and recovery metadata** (the stable idempotency key → outcome map,
   the persisted ledger revision, the shared `commit_generation`, and per-attempt
   intent/commit markers used by recovery, §I).

It stores **references** to Active Memory records (a `record_id` plus the version
semantics described in §B), never a duplicate of the record's content. The
coordinator depends on the adapter's typed interface, never on `open`, `json`, or
`os.replace` directly. This mirrors the Phase 40F parser/projector split (all I/O
behind one seam) and the Phase 37 store/service split.

**The established local persistence architecture is reused, not replaced.** The
authoritative pattern is the Phase 39B
[`RepositoryWorkspaceConfigService`](../../apps/backend/app/services/repository_workspace_config.py):

- a **versioned JSON contract** (`schema_version`, `extra="forbid"` models);
- an **OS-appropriate path outside the repository** (Windows `%LOCALAPPDATA%`,
  otherwise XDG), with a `HIVEMIND_MIGRATION_IMPORT_PATH` environment override of
  highest precedence, resolved without side effects (Phase 39B's
  `resolve_workspace_config_path`);
- **atomic, corruption-resistant writes** (temp sibling + `fsync` + `os.replace`),
  so a failed write never destroys the prior valid file;
- **bounded loads** with typed failure states for not-found, malformed,
  unsupported-version, too-large, and inaccessible;
- **fail-closed reads** — a malformed or unreadable ledger raises a typed error and
  never silently discards or overwrites.

Phase 40H's ledger is an **append-oriented import ledger** rather than a mutable
registry (see §D.6), so the store adds three capabilities the Phase 39B config service
does not need, all additive reuses of the established pattern rather than a new
persistence technology: a **persisted monotonic ledger revision with compare-and-swap**
(§I.5), the shared **commit generation** (§I.3), and a **`ledger_integrity_digest`**
sealing the complete ledger envelope (§H.7) — recomputed and matched at every load,
recovery classification, and reload before any ledger value is trusted (§I.9), with a
mismatch mapped to `corrupt_ledger`, fail closed. The ledger envelope carries an
explicit **type/domain tag** and `schema_version`. Atomic file replacement alone is
explicitly **insufficient** for this feature's concurrency and cross-store
guarantees (§I.4–§I.6) and is not relied on as if it were.

> **No speculative PostgreSQL rewrite.** A relational database is explicitly *not*
> proposed. Hive|Mind is local-first and single-user (roadmap "Current
> Limitations"); the Active Memory store itself is still
> in-memory-with-serialize/restore. Introducing a server database here would be a
> large, unaudited dependency far beyond the smallest reviewed-import foundation. The
> local versioned-JSON ledger plus the versioned-JSON Active Memory snapshot are
> sufficient for a single operator's own migration history; if future evidence ever
> shows them insufficient, that is a separate, justified decision — not part of this
> phase.

### A.4 ActiveMemorySnapshotStore owns the durable Active Memory snapshot (mandatory)

The Active Memory store is in-memory; its durability is caller-owned via
`serialize()`/`restore()` (Phase 37C), and **no durable snapshot owner exists
today**. Phase 40H makes a concrete **`ActiveMemorySnapshotStore`** a **mandatory**
component of this phase — not a conditional "if none exists" fallback. It is the
authoritative durable representation of `MemoryRecord` state and the second durable
artifact the commit generation binds (§I.3).

- **Proposed module:** `apps/backend/app/services/active_memory_snapshot_store.py`
  (§L).
- **Responsibility:** durable **serialization, loading, validation, and atomic
  replacement** of the authoritative Active Memory snapshot. It wraps the existing
  `InMemoryActiveMemoryStore.serialize()` / `restore()` boundary; it does **not**
  rewrite the store and does **not** re-home records into the ledger.
- **Interface (typed, minimal):**
  - `load() -> LoadedActiveMemorySnapshot` — returns the restored
    `InMemoryActiveMemoryStore` plus the snapshot's recorded `commit_generation`, or
    a typed failure;
  - `persist(store, commit_generation) -> None` — serialize the store, stamp the
    snapshot document with `commit_generation`, write atomically (temp sibling +
    `fsync` + `os.replace`);
  - `exists() -> bool`, `path() -> Path` (side-effect-free resolution).
- **Snapshot document:** the existing 37C snapshot payload
  (`contract_version = "active-memory.v1"`, `records: [...]`) wrapped with an outer
  envelope adding an explicit envelope **type/domain tag**,
  `schema_version = "active-memory-snapshot.v1"`, the shared `commit_generation`, and a
  **`snapshot_integrity_digest`** sealing the complete envelope (§H.8). Record content is
  exactly the store's own `serialize()` output — never reshaped, never augmented
  per-record by the ledger.
- **Configuration path:** OS-appropriate path outside the repository (Windows
  `%LOCALAPPDATA%`, otherwise XDG), resolved side-effect-free by the shared resolver,
  with a `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` **environment override of highest
  precedence** (parallel to `HIVEMIND_MIGRATION_IMPORT_PATH`).
- **Startup behavior:** at startup, **under the coordinator lock** (§I.4), the
  coordinator loads *both* the ledger and the snapshot and validates the shared
  generation (§I.3). A cold start with neither artifact present initializes both at
  `commit_generation = 0`.
- **Integrity checks:** the outer envelope's `snapshot_integrity_digest` is **recomputed
  and matched first** (§H.8) — a mismatch is `corrupt_active_memory_snapshot`, fail
  closed, before any generation value is trusted; then structural validation and full
  contract re-validation of every record via the store's existing `restore()`
  (all-or-nothing); the outer envelope's type tag, `schema_version`, and
  `commit_generation` must be present and typed; and the snapshot's recorded generation
  must equal the ledger's (§I.3). No untrusted generation authorizes recovery (§I.9).
- **Typed failures:** `snapshot_missing`, `corrupt_active_memory_snapshot`,
  `generation_mismatch`, `persistence_failure`, `partial_write_detected` (§J).

Ownership boundary restated: **the Active Memory snapshot remains authoritative for
`MemoryRecord` data; the migration ledger remains authoritative for review decisions,
attempts, intents, receipts, idempotency, and recovery metadata.** Neither duplicates
the other.

### A.5 Router thinness and non-mutating layers

- **Routers stay thin.** Phase 40H proposes **no** router by default (see §M). If a
  future, separately-approved phase adds one, it does only transport: validate a
  request contract, call the coordinator, map typed results to safe responses. It
  holds no persistence, digest, or lifecycle logic.
- **Only the import coordinator creates an Active Memory record from a migration
  candidate**, and it does so exclusively through the Active Memory store's own
  insertion seam (§F.2). That is the single migration→Active-Memory mutation
  boundary (§F).
- **Parsing (40F), projection (40F), assessment (40G), dry-run, and inspection stay
  non-mutating.** They are pure/read-only today and Phase 40H changes none of them.
  Phase 40H depends on their outputs and never edits their modules.

### A.6 AuthoritativeActiveMemoryStoreHolder owns the live authoritative reference (mandatory)

The Active Memory store is in-memory. Before Phase 40H **no component holds an
app-lifespan authoritative live store**: the existing request-scoped path
([`app/routers/active_memory.py`](../../apps/backend/app/routers/active_memory.py))
constructs a throwaway `InMemoryActiveMemoryStore.from_records(...)` per request for a
stateless read computation and never persists it. Phase 40H introduces a durable
reviewed-import path, so it must also introduce the **first** owner of the live
authoritative store reference: a mandatory **`AuthoritativeActiveMemoryStoreHolder`**
(equivalently an `ActiveMemoryStoreGateway`). It is a **committed component of this
phase, not a conditional fallback.**

- **Proposed module:** `apps/backend/app/services/active_memory_store_holder.py` (§L).
- **What it owns:** the *single* current **published** authoritative
  `InMemoryActiveMemoryStore` reference served to runtime readers. It **does not** modify
  the store class and **does not** re-home records into the ledger; it wraps the existing
  store instance and governs how that reference is **read and replaced**. It never mutates
  the published store in place.
- **No raw store ever escapes — holder-owned operations, no caller callbacks (Codex-3).**
  The former `read(fn)`/`mutate(fn)` callback surface is **removed**: a callback can retain
  whatever reference it is handed, so no callback contract can *guarantee* non-escape. The
  holder instead exposes a **fixed set of holder-owned operations** whose return values are
  only records, copies, collections, or scalars — **never a store**:
  - **read/query (read guard):** `find_record(record_id) -> MemoryRecord | None`,
    `get_record(record_id) -> MemoryRecord`, `list_records(**filters) -> list[MemoryRecord]`,
    and `snapshot_payload() -> dict` (the `serialize()` document for the snapshot store).
    Each returns the store's **defensive deep copies** (§37C) or a fresh dict — no returned
    object aliases internal state, and none is the store.
  - **generation/quarantine (read guard):** `current_generation() -> int`,
    `quarantine_state() -> QuarantineState` (a closed reason code, never a path/exception).
  - **publication (write guard):** `publish(replacement: InMemoryActiveMemoryStore,
    expected_generation: int, new_generation: int) -> None` — the **only** way the
    authoritative reference ever changes. It accepts a **fully constructed and validated
    replacement store** (built off-guard by the coordinator from the durable snapshot,
    below) and performs an **O(1) reference swap** under the write guard; it returns nothing
    and hands nothing back. There is **no** operation that returns, lends, or mutates the
    live store.
  - **any internal callback is private.** If the implementation uses a helper closure to
    perform the swap, it is a private method of the holder; it is **never** a parameter a
    caller can supply. Callers cannot inject behavior that touches the raw store.
  - The coordinator **never obtains the live store** for preparation. It builds its private
    candidate replacement store by loading the durable snapshot
    (`ActiveMemorySnapshotStore.load`, §A.4) — a store the holder does not own and no reader
    can reach — inserts into *that*, and then calls `publish`. The live published store is
    thus **never handed out and never mutated in place**; it is only ever *replaced*.

**A.6.1 Explicit read/write-guard synchronization protocol (Ruling 9).**

- **Two guards.** The holder owns an in-process **read/write guard**: a **shared read
  guard** (many concurrent readers) and an **exclusive write guard** (one writer,
  excluding all readers). The read/query/generation/quarantine-read operations acquire the
  **read guard**; `publish` (the O(1) swap) and every quarantine-state change acquire the
  **write guard**. There is **no** `mutate` operation and **no** in-place write to the
  published store.
- **Preparation never touches the published store (Codex-2).** The whole reviewed import
  is prepared against a **private candidate store** the coordinator builds off-guard from
  the last validated durable snapshot (`ActiveMemorySnapshotStore.load`, §A.4) — a store
  **no runtime reader can reach**. The new record is inserted into that *private* candidate
  store, not the live one. The published live store is **not mutated during preparation**;
  it keeps serving readers at generation `N` throughout.
- **Publication is last, O(1), and only after durable verification.** Only after the
  durable intent, the candidate snapshot at `N+1`, the receipt, and the ledger advance to
  `N+1` are all persisted **and reloaded/integrity-verified** (§E, §I.2) does the
  coordinator call `publish` to swap the holder's reference to the validated candidate
  store under the **shortest** write-guard boundary. A reader therefore observes **either**
  the complete old validated store (`N`) **or** the complete new validated store (`N+1`),
  **never a partially committed mutation**.
- **Acquisition order (fixed, global, deadlock-free):** the coordinator acquires the
  **filesystem `O_EXCL` coordinator lock first (outermost, §I.4)**, then — only for the
  `publish` swap (and quarantine changes) — the holder's **in-process write guard
  (innermost)**. This single global order is never inverted, so the two lock layers can
  never deadlock. **Release is strict reverse order** — inner write guard released before
  the outer filesystem lock — and both releases are in `finally` (exception-safe), covering
  success, handled-failure, and exception paths.
- **No lock upgrades.** There is **no read→write upgrade** path (the classic upgrade
  deadlock): the swap takes the write guard from the start. The **expensive
  reconstruct-and-validate of the candidate store happens WITHOUT holding the write
  guard**; only the **O(1) pointer swap** is performed under the write guard.
- **Reader visibility:** the swap replaces the holder's single reference under the write
  guard. **Reads already in progress** complete against the reference they began on (they
  hold the read guard / a deep-copied result); **new reads after the swap** see the
  replacement.
- **Writes/publications during import/quarantine:** serialized by the write guard; a new
  reviewed import cannot publish while a swap holds the write guard, and while quarantined
  new reviewed imports are rejected outright (below).
- **Failed candidate construction vs failed publish are distinct.** If **candidate
  construction/validation fails** (before durable persistence and before any `publish`),
  the published reference stays at `N` untouched, nothing durable was written past the
  intent, and the coordinator fails closed (safe retry). If the **`publish` swap itself**
  cannot complete safely, the holder raises `live_store_replacement_failure` and the
  coordinator maps it to `import_service_quarantined` (§I.6). Because `publish` runs
  **after** durable commit at `N+1`, a failed swap means the **durable truth is already
  `N+1`** while the in-memory published store is stale at `N`: the operation **does not
  report success** (Codex-2 — "an unsuccessful final swap cannot report import success"),
  it quarantines; **startup/recovery** then reconstructs and publishes the live store from
  the committed `N+1` snapshot (§I.6, §I.7), and a later idempotent replay of the same
  reviewed input returns the already-committed receipt (`duplicate_replay`). No data is
  lost and no false success is reported. A swap never leaves a half-installed store.
- **Quarantine is read/changed under the guards.** Quarantine state + its **closed reason
  code** (never a path or raw exception) is read under the read guard and changed under
  the write guard. While quarantined the holder **rejects new reviewed imports**
  (`import_service_quarantined`, §J) but **permits unrelated read-only access against the
  last validated authoritative store**. Quarantine is **cleared only after** locked
  startup/recovery validation succeeds (§I.6, §I.7).
- **Typed failure:** a replacement that cannot complete safely produces a typed
  **`live_store_replacement_failure`** which the coordinator maps unambiguously to
  **`import_service_quarantined`** with safe diagnostic context (§J).
- **All runtime readers and writers use holder-controlled operations.** Every runtime read
  goes through the holder's read/query operations (which return copies, never the store);
  the **only** write path is `publish`. Phase 40H does **not** claim any existing
  dependency-injection or router keeps a raw store: today the only Active Memory path is the
  stateless request-scoped router (§L) that builds a throwaway store and retains nothing, so
  there is no raw retained store to migrate. Any **future** app-lifespan/injected Active
  Memory store MUST be served through the holder's operations — a named, separate future
  change (§L), never a raw reference handed to callers.
- **Tests (§K):** **no raw store escapes** — every public holder operation returns a
  record/copy/collection/scalar or `None`, never an `InMemoryActiveMemoryStore`, and a test
  asserts a caller cannot obtain or retain the live store or mutate authoritative state
  outside `publish`; same-process multithreading (concurrent readers + one publisher
  serialized by the guard and the `O_EXCL` lock); concurrent import; reader-visibility
  (prior-or-replacement, never partial); write rejection during quarantine; and lock
  **acquisition and release failure** at both layers.

Ownership boundary restated: the **`ActiveMemorySnapshotStore` owns durable
snapshots** (§A.4); the **holder owns the live published reference and its atomic
`publish` replacement** (this section); the **import coordinator owns the reviewed-import
transaction** (§A.2), preparing on a private candidate store and publishing only after
durable verification. These stay separate — the holder never persists, the snapshot
store never mutates the live reference, and the coordinator never obtains, retains, or
mutates the live store directly (it only builds a private candidate and calls `publish`).

---

## B. Durable record types and relationships

All migration-workflow records are versioned (`memory-migration-import.v1`),
`extra="forbid"`, and use the repository's canonical-JSON + SHA-256 identity
convention (§H). Identifiers are pure functions of typed content; nothing reads a
clock, randomness, or process state to form an identity. Caller-supplied timestamps
follow the Phase 37E/40F convention (the service records time it is given; it does
not read the wall clock to fabricate provenance).

**Ownership note (critical):** the first three rows describe *references into stores
Phase 40H does not own* (Phase 40F candidate, Phase 40G report, Phase 37C Active
Memory store). The migration ledger stores only their **identities**, never copies.
The **resulting Active Memory record is owned entirely by the Active Memory store**
(durably, by the §A.4 snapshot); the ledger holds only its `record_id` and
version-linkage metadata.

| Record | Identity | Key fields | Mutability / ownership |
| --- | --- | --- | --- |
| **Migration candidate reference** | `candidate_id` (Phase 40F, reused unchanged) | `candidate_id`, `content_digest`, `provenance` (bundle/artifact fingerprints, observed digest), assessed-set membership | Immutable; a *reference*, not a copy of candidate bytes; owned by Phase 40F output |
| **Candidate byte digest** | value of `content_digest` | the Phase 40F SHA-256 over candidate content; the observed artifact digest from `MigrationCandidateProvenance` | Immutable reference value |
| **Assessment reference** | `report_id` (Phase 40G) + `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION` | `report_id`, ruleset version, `review_readiness` verdict | Immutable; owned by Phase 40G output |
| **Review decision** | `review_decision_id` = canonical id over its own fields (§H.9; **excludes `decision_timestamp` and any authorization id**) | reviewer id, decision timestamp, status, reason, notes, candidate id + digest, assessment id + version, evidence references, optional `supersedes_decision_id`, `renewal_revision` | Immutable once recorded (append-only; a superseding decision is a new record, §C/§D.6/§D.7); **owned by the migration ledger** |
| **Review evidence reference** | reference tuple `(kind, ref_id)` | typed pointer to the assessment report, the dry-run finding(s), and/or the candidate provenance the reviewer relied on | Immutable; owned by the migration ledger |
| **Project/scope authorization context** | `authorization_context_id` = canonical id over its own fields (§C.3, §H.10) | `authorization_context_version`, `authorization_policy_version`, `authorized_project_id`, `authorized_scopes` (explicit allowed-scope set), `authorizing_principal_id`, `review_decision_id`, candidate id + digest, assessment id + version, `expires_at?`, `revoked?`, `authorization_context_digest` | Immutable once issued; **constructed and authorized by the human review/authorization boundary**, recorded in the migration ledger; the coordinator validates and executes it and never invents authorization (§C.3) |
| **Reviewed-import specification** | `specification_digest` = canonical id over its own fields (§C.1, §H.5) | contract name/version, candidate id + digest, assessment id + version, `review_decision_id`, reviewer-approved `target_kind`, complete structured `MemoryClaim`, `kind_claim_policy_version` (§C.2), validated `project_id`, optional `scope`, `authorization_context_id` + `authorization_context_digest` (§C.3), evidence references, `source_type = IMPORTED_DOCUMENT`, canonical source/provenance, applicable `supersession_refs` | Immutable once authorized; **supplied and authorized by the human review boundary**, recorded in the migration ledger; carries the record kind/claim/project the candidate does **not** (§C.1) and the authorization-context binding (§C.3) |
| **Import attempt** | `import_attempt_id` = canonical id over `(idempotency_key, attempt_sequence)` (§H) | `idempotency_key`, `attempt_sequence` (deterministic monotonic int, retries only, §G.2), referenced `review_decision_id`, candidate id + digest, assessment id + version, `intent_state` (`intended`/`committed`/`failed`/`uncertain`), planned `target_record_id`, `commit_generation` observed at intent, attempt timestamp | Append-only; each retry is a **distinct** attempt id (§G); owned by the migration ledger |
| **Verified import receipt** | `receipt_id` = canonical id over the linked identities + `commit_generation` (§H) | see §B.3 (full receipt contract) | Immutable; created only at verified commit; **owned by the migration ledger** |
| **Resulting Active Memory record** | `record_id` (caller-supplied to the Active Memory store; here the canonical id over the **complete authoritative record content** — kind/claim/project/scope, source, standing, `supersession_refs`, the content-identity provenance block, and the deterministic `created_at`/`observed_at`, §H.3) so `record_id` equality ≡ complete canonical equality | the `MemoryRecord` itself — lifecycle/verification standing, claim, source, provenance, supersession refs, timestamps; **carries no attempt/decision/authorization audit** (§F.3, Rulings 4/5) | **Owned exclusively by the Active Memory store** (durable in the §A.4 snapshot). The ledger stores only its `record_id`; it is never copied, wrapped, or shadowed in the ledger (§A.1) |
| **Ledger revision** | monotonic integer `ledger_revision` | the persisted CAS token guarding every *ledger* write (§I.5) | Monotone, advanced only under the exclusive writer lock |
| **Commit generation** | monotonic integer `commit_generation` | the shared cross-store epoch recorded in **both** the ledger and the Active Memory snapshot (§I.3) | Monotone, advanced exactly once per verified import, only under the exclusive writer lock |
| **Ledger integrity digest** | `ledger_integrity_digest` = canonical SHA-256 over the complete immutable ledger envelope except its own field (§H.7) | seals the whole ledger envelope: type/domain tag, schema/version, `ledger_revision`, `commit_generation`, and every decision/attempt/intent/receipt/provenance member | Recomputed and verified at every load, recovery classification, and reload (§I.9); mismatch → `corrupt_ledger`, fail closed |
| **Snapshot integrity digest** | `snapshot_integrity_digest` = canonical SHA-256 over the complete immutable snapshot envelope except its own field (§H.8) | seals the whole snapshot envelope: type/domain tag, schema/version, `commit_generation`, and the exact 37C `serialize()` records payload | Recomputed and verified at every load, recovery classification, and reload (§I.9); mismatch → `corrupt_active_memory_snapshot`, fail closed |

### B.1 Ownership and cardinality

- One **candidate** may be referenced by many **review decisions** over time (a
  deferred decision later superseded by an approval), but at most **one
  non-superseded approved decision** is valid for a given `(candidate_id,
  content_digest, assessment_id, assessment_version)` tuple at any time (§D.6, §D.7).
- One valid **approved review decision** authorizes at most **one verified import**
  for its exact reviewed input (its idempotency key, §G.1), producing exactly **one
  receipt** and referencing exactly **one resulting `record_id`**.
- One **import attempt** references exactly one **review decision** and yields zero
  or one **receipt** (zero on failure, one on verified commit). Multiple attempts may
  share one idempotency key (retries), but each has a distinct `import_attempt_id`.
- One **receipt** references exactly one resulting `record_id`. That `record_id` must
  resolve to an existing record in the **Active Memory snapshot**. A receipt whose
  `record_id` does not resolve is a detected corruption (`missing_linked_memory_record`,
  §J), never a valid state. This cross-store linkage is the invariant §I protects.
- **Distinct decisions over identical authored content:** `record_id` derives over the
  **complete authoritative record content** (§H.3), and the authoritative record carries
  **no** decision-, attempt-, or authorization-specific audit — that all lives in the
  ledger (§F.3, Rulings 4/5). Consequences: a **retry of the same reviewed input**
  reproduces the identical record and `record_id` (idempotent reuse, one record, its
  receipt returned unchanged, §G.3). **Two genuinely distinct decisions** differ in at
  least one **identity-bearing decision field** (⇒ different `review_decision_id`, §H.9,
  Codex-7) — not merely in `decision_timestamp`, which alone makes them the *same*
  decision. When such distinct decisions also author different record content, or carry
  different recorded `decision_timestamp`s (⇒ different `created_at`), they deterministically
  produce **distinct `record_id`s** — two distinct records, each with its own receipt,
  never a silent merge and never a forced collision. In the boundary case where two
  distinct decisions author a **byte-identical** record (identical content *and* the same
  recorded `created_at = decision_timestamp`), they share one `record_id`; the second
  import finds complete canonical equality, reuses the existing record, and writes its own
  receipt (one record, two audited receipts). A same-`record_id`/different-content state is
  only ever tampering or a hash collision → `record_identity_collision`, fail closed
  (§F.3).

### B.2 Uniqueness, foreign keys, timestamps, version semantics

- **Uniqueness constraints (enforced by the ledger, adapter-level):**
  `review_decision_id`, `import_attempt_id`, and `receipt_id` are each unique. The
  **idempotency key** (§G) maps to at most **one** committed receipt — a duplicate
  valid request resolves to the existing receipt, never a new record.
- **Foreign-key equivalents:** every import attempt names an existing
  `review_decision_id`; every receipt names an existing `import_attempt_id`,
  `review_decision_id`, and a `record_id` that exists in the Active Memory snapshot;
  every review decision names an existing `candidate_id` + `content_digest` and
  `report_id` + version, and (when renewing review) an existing
  `supersedes_decision_id`. A dangling *intra-ledger* reference fails closed as
  `missing_linked_attempt` / `incomplete_review_provenance`; a dangling *cross-store*
  reference (receipt → absent `record_id`) fails closed as
  `missing_linked_memory_record` (§J).
- **Timestamps:** `decision_timestamp`, `attempt_timestamp`, and
  `verification_timestamp` are caller-supplied and immutable once recorded. There is
  no server-clock read; determinism and auditability come from the caller stating
  time, exactly as Phase 37E/40F do. Temporal fields are **excluded** from every
  derived identity (§H).
- **Version semantics (reuse, not reinvention):** Active Memory records have no
  numeric version field. The Active Memory store's existing model *is* the version
  semantics — a stable `record_id` is one immutable version, and a *changed* import
  (new digest or new assessment) produces a **new** `record_id` that **supersedes**
  the prior one via the store's existing `supersession_refs`, never an in-place edit
  (§D.7, §F.2). The receipt records `record_id` and, when the import supersedes a
  prior import of the same logical candidate line, the prior `record_id` in
  `record_supersedes`. Phase 40H introduces **no** competing version scheme for
  Active Memory.
- **Immutable vs mutable:** every ledger record above is immutable once written. The
  *ledger* grows by appending new records and advancing `ledger_revision`; a lifecycle
  "transition" is a new controlled record referencing the prior one (§D.6), never an
  in-place edit. The only field that could be described as "changing" is a decision's
  or attempt's *effective* status, and that is expressed by a newer superseding
  record or an appended attempt state, not by mutation.

### B.3 The verified-import receipt contract

The receipt is created **only** at verified commit and carries exactly these fields:

| Field | Purpose |
| --- | --- |
| `receipt_id` | Deterministic **identity** over the non-temporal linked identities + `commit_generation` (§H.4). **Excludes** all timestamps. |
| `receipt_version` | The `memory-migration-import.v1` contract tag (immutable content). |
| `candidate_id` | The exact Phase 40F candidate imported. |
| `content_digest` | The exact candidate byte digest imported. |
| `assessment_report_id` | The exact Phase 40G report reviewed. |
| `assessment_version` | The Phase 40G ruleset contract/version reviewed. |
| `review_decision_id` | The approving decision. |
| `specification_digest` | The exact reviewed-import specification authorized (§C.1). |
| `authorization_context_id` | The project/scope authorization context that authorized this import (§C.3). |
| `authorization_context_digest` | The sealed digest of that authorization context (§H.10), re-validated at recovery. |
| `idempotency_key` | The stable reviewed-input key (§G.1). |
| `import_attempt_id` | The committing attempt. |
| `record_id` | The authoritative resulting `MemoryRecord.record_id`. |
| `record_supersedes` | 0..1 prior `record_id` this import supersedes (same logical candidate line). |
| `supersession_refs` | The applicable forward supersession references written on the new record (mirror of what §F.2 authored), for audit. |
| `commit_generation` | The shared generation this receipt (and its snapshot) represent (§I.3). |
| `verification_status` | Closed enum: `verified` (the only status a committed receipt carries). Uncertain/failed outcomes never produce a receipt. |
| `attempt_timestamp` | Caller-supplied time the attempt was made. Immutable content; **not** in `receipt_id`, **but covered by `receipt_integrity_digest`**. |
| `verification_timestamp` | Caller-supplied time linkage was verified. Immutable content; **not** in `receipt_id`, **but covered by `receipt_integrity_digest`**. |
| `receipt_integrity_digest` | Canonical SHA-256 over the **complete immutable receipt content** — every field above **including both timestamps** — excluding only `receipt_integrity_digest` itself (§H.6). Any alteration of any content field, including either timestamp, causes `receipt_integrity_failure`. |

**Receipt identity and receipt content integrity are two separate things (Ruling 4):**

- **`receipt_id`** is a *stable identity* over the non-temporal identity fields (§H.4,
  domain `migration-import/receipt`). Because it excludes timestamps, a duplicate
  replay resolves to the same identity and the coordinator returns the **exact stored
  receipt unchanged — including its original `attempt_timestamp`,
  `verification_timestamp`, and stored `receipt_integrity_digest`** (§G.3). Replay is
  a lookup; it never recomputes timestamps.
- **`receipt_integrity_digest`** is a *full-content integrity seal* over the complete
  immutable receipt — `receipt_id`, `receipt_version`, candidate id + digest,
  assessment id + version, `review_decision_id`, `specification_digest`,
  `authorization_context_id`, `authorization_context_digest`, `idempotency_key`,
  `import_attempt_id`, `record_id`, `record_supersedes`,
  `supersession_refs`, `commit_generation`, `verification_status`, **and both
  timestamps** — with an explicit **integrity domain tag** and schema version distinct
  from the `receipt_id` identity domain (§H.4 vs §H.6). Tampering with **either
  timestamp** or any other immutable field is detected as `receipt_integrity_failure`
  at load and recovery (§I.8), even though such tampering does not change `receipt_id`.

---

## C. Review-decision provenance

A review decision is the load-bearing artifact of this phase. It is a strict,
dedicated contract (it does **not** reuse `MemoryRecord`, mirroring Phase 40E's
refusal to reuse permissive Active Memory records). Every field below is
**required** unless marked optional; a decision missing any required field fails
contract validation and cannot be constructed, so it can never reach the import
path.

| Field | Required | Purpose |
| --- | --- | --- |
| `reviewer_id` | yes | Stable actor identifier (operator id / stable slug). Not a boolean; an anonymous or empty reviewer fails validation. |
| `review_policy_version` | yes | The review-policy contract version under which the decision was made (`memory-migration-import.v1` review-policy tag). Bound into `review_decision_id` (§H.9) so a decision made under a different policy version is a distinct decision, never silently equated. |
| `decision_timestamp` | yes | Caller-supplied instant the decision was made. **Excluded from `review_decision_id`** (§H.9) — audit-only for decision identity — but it **is** the authorizing decision's authoritative content used as the resulting record's `created_at` (§F.3). A copy that differs *only* in `decision_timestamp` is therefore the **same** decision (idempotent), never a renewal (§H.9, §D.7). |
| `status` | yes | Closed enum: `approved` / `rejected` / `deferred`. No other value is representable. |
| `reason` | yes | Non-empty, bounded free text stating *why*. An approval with no reason fails validation. |
| `notes` | optional | Additional bounded context. |
| `candidate_id` | yes | The exact Phase 40F candidate the decision is about. |
| `content_digest` | yes | The exact candidate byte digest the decision was made against (binds the decision to specific bytes). |
| `assessment_report_id` | yes | The exact Phase 40G report id reviewed. |
| `assessment_version` | yes | The Phase 40G ruleset version reviewed. |
| `evidence_references` | yes, ≥1 | Typed references to the assessment report, dry-run findings, and/or candidate provenance the reviewer relied on. |
| `supersedes_decision_id` | optional | The prior decision this one directly supersedes for the same logical candidate line, when the reviewer is explicitly renewing review (§D.7). When present it MUST reference an existing decision for the same `candidate_id` line. |
| `renewal_revision` | optional (default `0`) | Non-negative integer **renewal discriminator** and an identity member of `review_decision_id` (§H.9, Codex-7). It lets a reviewer record a genuinely distinct **renewal** even when every other material field is unchanged (a re-affirmation): incrementing it yields a distinct `review_decision_id`. It is **not** a timestamp and is not read from a clock. A renewal with a changed `content_digest`/`assessment_*` need not touch it; a renewal with no other material change **must** increment it (and carry `supersedes_decision_id`). Absent/`0` for an original decision. |

> A plain `approved = true` field **never independently authorizes mutation.** The
> `status` enum only *names* the decision; authority to import requires the whole
> record — reviewer, timestamp, reason, the exact candidate digest, the exact
> assessment identity/version, and evidence — and that whole record must still be
> valid, unchanged, and non-contradictory at import time (§E). The import path
> re-derives `review_decision_id` from its fields and rejects a record whose stored
> id disagrees, so a forged or edited decision cannot be presented.

Contradictory evidence (e.g., an `approved` decision whose referenced assessment
verdict is `blocked`, or whose evidence points at a different candidate) is a
fail-closed condition (`contradictory_evidence`, §J), not a soft warning.

**Review-decision supersession is a decision-lineage concern, not an
import-attempt-ordering concern.** A renewed decision references the decision it
supersedes directly through `supersedes_decision_id` (§D.7); `attempt_sequence`
(§G.2) plays **no** part in review-decision ordering.

### C.1 The reviewed-import specification (reviewer-authored record content)

**The Phase 40F `MemoryMigrationCandidate` does not carry a `MemoryRecordKind`, a
structured `MemoryClaim`, or a `project_id`.** Its own contract states it "carries no
`MemoryRecordKind`, no evidence, no confidence"; concretely it carries `content`
(raw text), `content_digest`, `provenance`, and an optional `target_scope`
(`MemoryScope | None`) — and nothing more that could stand in for a record's kind,
claim triple, or project. A `MemoryRecord`, by contrast, **requires** `kind`, a
structured `claim` (subject/predicate/value/value_kind), and a non-empty `project_id`
(§F.3). Phase 40H therefore **must not** claim the candidate supplies these fields and
**must not** derive them heuristically (no kind selection from text, no claim
synthesis, no project guessing).

Instead, a mandatory, reviewer-approved **`ReviewedImportSpecification`** (a **new
typed contract introduced by Phase 40H** in the `memory_migration_import.py` models
module, §L; **not** an extension of `MemoryMigrationCandidate` and **not** a reuse of
`MemoryRecord`) carries exactly the record content the candidate cannot. It is
**supplied and authorized by the human review boundary** — the same boundary that
records the review decision — and the coordinator **validates and executes it without
any semantic inference, AI adjudication, automatic kind selection, claim synthesis,
project guessing, or lifecycle promotion.**

| Field | Required | Purpose |
| --- | --- | --- |
| `specification_version` | yes | Contract name/version tag (`memory-migration-import.v1`). |
| `candidate_id` | yes | The exact Phase 40F candidate this specification is bound to. |
| `content_digest` | yes | The exact candidate byte digest (binds the specification to specific bytes). |
| `assessment_report_id` | yes | The exact Phase 40G report id. |
| `assessment_version` | yes | The exact Phase 40G ruleset version. |
| `review_decision_id` | yes | The authorizing review decision (§C) this specification serves. |
| `target_kind` | yes | The reviewer-approved `MemoryRecordKind`. A closed-enum member the reviewer selected; never inferred from candidate text. |
| `claim` | yes | The **complete structured** `MemoryClaim` (subject, predicate, value, `value_kind`, optional summary) the reviewer authored/approved. Never synthesized from prose by the coordinator. |
| `observed_at` | optional | The reviewer-authored **claimed observation instant** for the imported claim — the source of the resulting `MemoryRecord.observed_at` (the real 37B model's "claimed observation time", **distinct from `created_at`**, §F.3, Codex-6). Canonical UTC ISO-8601 with an explicit offset; timezone-naive/malformed → `invalid_reviewed_specification`. **Reviewer-authored only** — the coordinator validates format but **never invents, derives, or equates it with `decision_timestamp`** or any wall clock. Absent ⇒ record `observed_at = None`. It is authoritative record content, so it participates in `specification_digest` (§H.5) and `record_id` (§H.3). |
| `kind_claim_policy_version` | yes | The **kind↔claim compatibility policy version** (§C.2) under which `(target_kind, claim)` was authored and must be validated. Sealed by `specification_digest`; a mismatch with the coordinator's active policy version fails closed (`kind_claim_incompatible`, §C.2). |
| `project_id` | yes | The **validated** target project id (non-empty). Checked for **exact equality** against the authorization context's `authorized_project_id` (§C.3); never guessed. |
| `scope` | optional | An optional `MemoryScope`. When present it MUST be an **exact member** of the authorization context's `authorized_scopes` set (§C.3) — equality by the §H.0 canonical comparison, **no** parent/child/broader/narrower relationship is inferred (the real `MemoryScope` model defines **no** hierarchy). When **absent**, the record is project-level and is authorized **only if** the context's `project_level_authorized` flag is set (§C.3). It is never fabricated. |
| `authorization_context_id` | yes | The `authorization_context_id` (§C.3) of the project/scope authorization context that authorizes this `project_id`/`scope`. |
| `authorization_context_digest` | yes | The sealed `authorization_context_digest` (§H.10) of that context, recomputed and matched at import and recovery. |
| `evidence_references` | yes, ≥1 | Typed references mirroring/consistent with the review decision's evidence. |
| `source_type` | yes | Pinned to `MemorySourceType.IMPORTED_DOCUMENT`. Any other value fails validation. |
| `source_provenance` | yes | Canonical source metadata: `source_id` = the stable candidate-derived slug, optional `display_label`, optional `session_id` (§F.3). |
| `supersession_refs` | optional | The applicable forward `SUPERSEDES` reference(s) (0..1 prior `record_id`) the reviewer authorized for a renewed import of the same logical candidate line (§D.7). |
| `specification_digest` | yes | Canonical SHA-256 over every field above **except `specification_digest` itself** (§H, domain `migration-import/specification`), sealing the whole reviewer-authored specification. |

**Construction and validation ownership.** The **human review boundary constructs and
authorizes** the specification (it, and only it, chooses `target_kind`, authors the
`claim`, authors any `observed_at`, and sets `project_id`/`scope`). The **coordinator
validates** it and refuses to proceed on any failure — it never fills a missing field,
never repairs one, and never adjudicates content.

**Validation is a fixed precedence (Codex-8); the first matching check fails closed and
no later check runs**, so exactly one diagnostic owns each failure and none overlap
(§J):

1. **Presence** — a request for an approved candidate that carries **no** specification →
   `missing_reviewed_specification`.
2. **Structural/typed validity (model layer)** — the Pydantic contract itself:
   `extra="forbid"`, every required field present, `target_kind` a valid
   `MemoryRecordKind` **member**, `claim` subject/predicate/value present and bounded,
   `value_kind` a valid `ClaimValueKind` **member**, `project_id` non-empty,
   `source_type == IMPORTED_DOCUMENT`, and `observed_at` (when present) a timezone-aware
   ISO-8601 instant. Any structural/enum-membership failure → `invalid_reviewed_specification`
   (**owned by the model**, raised before any semantic check).
3. **Integrity/staleness** — `specification_digest` is recomputed over the §H.5 members
   and must match; **any** post-authorization alteration of **any** field (including the
   `claim`, `target_kind`, or `observed_at`) → `specification_integrity_failure`. Checked
   before semantics because an altered specification is untrustworthy to interpret.
4. **Binding to the reviewed decision** — `candidate_id`, `content_digest`,
   `assessment_report_id`, `assessment_version`, and `review_decision_id` must match the
   re-validated candidate/assessment and the approving decision **exactly** →
   `specification_binding_mismatch`.
5. **Project/scope authorization (exact, no hierarchy — Codex-4)** — the referenced
   **`ProjectScopeAuthorizationContext` (§C.3)** is resolved, its
   `authorization_context_digest` recomputed and matched, and its non-revoked/non-expired
   validity confirmed. Then **two separate, exact checks**: (a) `project_id` must equal
   the context's `authorized_project_id` **exactly** (byte-for-byte after §H.0
   canonicalization); (b) a present `scope` must be an **exact member** of the context's
   `authorized_scopes` set (no parent/child/broader/narrower/ordering relationship is ever
   inferred — the real `MemoryScope` model defines none), and an **absent** `scope` is
   authorized **only if** `project_level_authorized` is set. A missing context →
   `missing_authorization_context`; an altered/stale one →
   `authorization_context_integrity_failure`; revoked/expired →
   `authorization_context_revoked` / `authorization_context_expired`; a
   cross-project/cross-decision/cross-candidate binding → `authorization_context_mismatch`;
   a `project_id` ≠ `authorized_project_id`, a `scope` **not an exact member** of
   `authorized_scopes`, or an absent scope without `project_level_authorized` →
   `unauthorized_project_scope`.
6. **Kind/claim compatibility (policy layer)** — only a structurally valid,
   integrity-intact, correctly-bound, authorized specification reaches this check.
   `target_kind` and `claim` are validated against the **closed, versioned kind↔claim
   compatibility policy (§C.2)** owned by the named `KindClaimCompatibilityValidator`, at
   the specification's `kind_claim_policy_version`. The coordinator **checks** compatibility
   against the policy; it does **not** choose, infer, or synthesize either. A valid-member
   `target_kind` with **no** policy rule (unmapped kind), a valid-member `value_kind`
   **outside** the kind's permitted set, or a `kind_claim_policy_version` the validator
   does not recognize → `kind_claim_incompatible`. (Pure structural/enum-membership
   failures never reach here; they were `invalid_reviewed_specification` at step 2.)

**Canonical digest field membership.** `specification_digest` covers **all** fields in
the table above except itself, using the repository canonical-JSON + SHA-256
convention with the `migration-import/specification` domain tag (§H). It therefore
seals kind, claim, `observed_at`, project, scope, source, supersession intent, the
kind/claim policy version, and the four content-identity bindings together — no subset
can be altered undetected.

**Idempotency and record-id consequences (how specifications relate to replay).**
The stable idempotency key (§G.1) **includes `specification_digest`**, and the
deterministic `record_id` derives over the specification's record content
(kind/claim/project/scope) plus the content-identity provenance (§H.3). Therefore:

- **Two *different* specifications for the same candidate** (a different `target_kind`,
  a different `claim`, or a different `project_id`/`scope`) have **different
  `specification_digest`s** ⇒ **distinct idempotency keys** ⇒ they are **distinct
  reviewed inputs**, each requiring its own approval. Because their record content
  differs they also derive **different `record_id`s** — two records, two receipts,
  never a silent overwrite.
- **Re-presenting the *same* specification** (same `specification_digest`) is the
  ordinary idempotent replay: same key, same `record_id`, the exact stored receipt
  returned unchanged (§G.3).
- A specification that collides on a related key with a **materially different**
  already-recorded attempt (e.g. the same key mapped to a different content-identity)
  is the typed **`conflicting_replay`** (§G.3), never a merge.

The specification is the **only** place these record-content fields originate; the
coordinator's job is to *validate and execute*, faithfully mapping the approved
specification onto a `MemoryRecord` (§F.3) with no inference of its own.

### C.2 Kind↔claim compatibility policy (closed, versioned, validator-owned)

**What the existing contract already enforces (and does not).** The frozen Phase 37B
`MemoryClaim` (`app/models/active_memory.py`) already enforces, at its own edge: a
non-empty, stripped `subject` and `predicate`; a bounded `value` (`≤ 2048` chars); a
`value_kind` that is a member of the closed `ClaimValueKind` enum (`string` / `boolean`
/ `integer` / `float` / `timestamp` / `identifier` / `enum`); an optional bounded
`summary`; and `extra="forbid"`. `MemoryRecordKind` is likewise a closed six-member
enum (`project_fact`, `project_decision`, `project_constraint`, `phase_status`,
`repository_state`, `capability`). What the base contract does **not** enforce is any
relationship **between** the record's `kind` and the shape of its `claim` — every kind
structurally accepts every claim triple and every `value_kind`. Phase 40H's
import-specific validator adds exactly that missing relationship, and nothing else; it
does not re-implement the field-level checks the model already performs.

**The policy is a concrete, closed, versioned artifact owned by a named validator.** A
new `KindClaimCompatibilityValidator` (in the `memory_migration_import.py` models
module, §L) owns a single policy constant
**`KIND_CLAIM_COMPATIBILITY_POLICY_VERSION = "kind-claim-compat.v1"`** and the closed
mapping below. The coordinator delegates to this validator; it never inlines its own
rules and never chooses or synthesizes a kind or claim. The specification's
`kind_claim_policy_version` (§C.1) must equal the validator's active version, or the
pairing fails closed (`kind_claim_incompatible`) — a policy-version mismatch is never
silently accepted.

**Every currently importable target kind, and its permitted claim shape (`v1`).** All
six `MemoryRecordKind` members are importable. For **every** kind the required claim
fields are exactly the `MemoryClaim` triple — non-empty `subject`, non-empty
`predicate`, non-empty bounded `value` — plus a `value_kind` drawn from the per-kind
permitted set below; `summary` is permitted-optional for every kind; **no** field
outside the `MemoryClaim` contract is permitted (the model's `extra="forbid"` already
rejects unknown members, and the validator additionally rejects a `value_kind` outside
the per-kind set). No kind permits an empty claim, and none requires a field the
`MemoryClaim` contract cannot carry.

| `target_kind` | Permitted `value_kind` set (`v1`) | Rationale |
| --- | --- | --- |
| `project_fact` | `string`, `boolean`, `integer`, `float`, `timestamp`, `identifier`, `enum` | A fact may assert any bounded scalar. |
| `project_decision` | `string`, `boolean`, `identifier`, `enum` | A decision names a chosen outcome/option, not a measurement. |
| `project_constraint` | `string`, `boolean`, `integer`, `float`, `enum` | A constraint bounds or forbids; numeric thresholds are allowed, opaque identifiers are not. |
| `phase_status` | `string`, `enum`, `boolean`, `identifier` | A phase status is a named state or a merged/blocked flag. |
| `repository_state` | `string`, `boolean`, `identifier`, `timestamp` | Branch/head/clean/observed-at style repository facts. |
| `capability` | `string`, `boolean`, `enum`, `identifier` | A capability names a discrete ability and whether it holds. |

**Fail-closed and closure rules:**

- **Unsupported / unmapped kind fails closed.** The mapping is exhaustive over the
  current closed enum. If a future `MemoryRecordKind` member is added upstream **without**
  a corresponding `v1` (or later) policy entry, that kind has **no approved rule** and
  every import naming it fails closed as `kind_claim_incompatible`. The validator never
  invents a permitted set for an unmapped kind.
- **The coordinator cannot choose or infer a kind.** `target_kind` comes only from the
  reviewer-approved `ReviewedImportSpecification` (§C.1). The validator receives the
  pair and answers compatible / incompatible; it never selects a kind from candidate
  text, and it never rewrites or synthesizes a claim.
- **No claim synthesis or semantic reinterpretation.** The validator checks *shape and
  membership* only (required fields present, `value_kind` in the permitted set for the
  kind). It does not interpret, normalize, or "repair" claim semantics; the claim's
  `subject`/`predicate`/`value`/`summary` text is preserved exactly (§H.0).
- **Policy version is bound into identity.** `kind_claim_policy_version` is a sealed
  member of `specification_digest` (§H.5), so a specification authored under one policy
  version cannot be re-interpreted under another without changing the specification
  identity — a materially different reviewed input requiring its own approval.

**Diagnostic and precedence (Codex-8).** `kind_claim_incompatible` (§J) is the **policy
layer** and is reached **only** at precedence step 6 (§C.1) — after presence, structural
validity, integrity, binding, and authorization have all passed. It fires for a
valid-member `MemoryRecordKind` with **no** policy rule (unmapped kind), a valid-member
`value_kind` **outside** the kind's permitted set, or a `kind_claim_policy_version` the
validator does not recognize. It is **strictly disjoint** from
`invalid_reviewed_specification`, which owns every **structural/enum-membership** failure
the model raises first (a non-member `value_kind`/`target_kind`, a missing triple field, an
`extra` field, a blank subject/predicate). A single input can never trigger both: a
non-member enum is structural (`invalid_reviewed_specification`); a member enum in a
forbidden *combination* is policy (`kind_claim_incompatible`). An *altered-after-review*
claim is neither — it is caught earlier as `specification_integrity_failure` (step 3).

**Tests (§K):** every permitted `(kind, value_kind)` pairing accepted; every invalid
`(kind, value_kind)` pairing rejected; an unmapped/unsupported kind rejected; a
malformed/empty claim rejected; and a `kind_claim_policy_version` mismatch rejected —
all `kind_claim_incompatible` except the pure structural cases.

### C.3 Project/scope authorization context (typed, boundary-owned)

`unauthorized_project_scope` cannot be a coordinator judgment call over free-floating
inputs: the coordinator must never invent authorization, guess a project, admit a scope
outside the explicit authorized set, or treat *repository location* (which repo the
process runs in) as authorization.
Phase 40H therefore introduces a concrete typed **`ProjectScopeAuthorizationContext`**
(in the `memory_migration_import.py` models module, §L), **constructed and authorized by
the human review/authorization boundary** — the same boundary that records the review
decision — and merely **validated and executed** by the coordinator.

| Field | Required | Purpose |
| --- | --- | --- |
| `authorization_context_version` | yes | Contract tag (`memory-migration-import.v1`). |
| `authorization_policy_version` | yes | The authorization-policy version under which this grant was issued; bound into `authorization_context_id` (§H.10). |
| `authorization_context_id` | yes | Canonical id over the context's own fields (§H.10). |
| `authorized_project_id` | yes | The single project the grant authorizes. `project_id` equality is checked against **this**. |
| `authorized_scopes` | yes (set) | The **explicit allowed-scope set** (a `MemoryScope` list treated as a set, §H.0 sorted + de-duplicated). A specification `scope` is authorized **only if it is an exact member** of this set — no parent/child/broader/narrower/ordering relationship is ever inferred (the real `MemoryScope` model defines **none**, Codex-4). May be **empty only when** `project_level_authorized` is `true` (a project-level-only grant); a grant that authorizes neither any scope nor project-level import authorizes nothing and is rejected. Duplicate/malformed members are handled deterministically (below). |
| `project_level_authorized` | optional (default `false`) | Explicit boolean authorizing a **project-level** import (a specification with **no** `scope`). When `false`, an absent specification `scope` is `unauthorized_project_scope`. This replaces any notion of a scope "hierarchy": project-level is its own explicit grant, not an implicit broadening of a scope member. |
| `authorizing_principal_id` | yes | The actor/principal that authorized the grant (stable id/slug); not a boolean. |
| `review_decision_id` | yes | The review decision this grant serves (§C, §H.9). The grant **references the decision** (authorization → decision); the decision never references the grant (acyclic, §H.0a). |
| `candidate_id` + `content_digest` | yes | The exact candidate identity + bytes the grant is bound to. |
| `assessment_report_id` + `assessment_version` | yes | The exact Phase 40G assessment the grant is bound to. |
| `issued_at` | yes | Caller-supplied issuance instant. **Immutable authorization content**: it is **excluded from `authorization_context_id`** (the *semantic identity*, §H.10) so a timestamp can never become an authorization shortcut and retries stay stable, **but it IS included in `authorization_context_digest`** (the *complete integrity seal*, §H.10, Codex-5) so tampering with it is detected. It is audit metadata for identity purposes, never for integrity purposes. |
| `expires_at` | optional | Caller-supplied expiry instant; when present and `< decision_timestamp`/import time the grant is expired and fails closed. Identity-bearing (§H.10). |
| `revoked` | optional (default `false`) | Explicit revocation flag; a revoked grant authorizes nothing. Identity-bearing (§H.10). |
| `authorization_context_digest` | yes | Canonical SHA-256 over **every field above except itself — INCLUDING `issued_at`** (§H.10, an **integrity** domain). This is the *complete* envelope seal; the claim of completeness is therefore honest (Codex-5). |

**Ownership and lifecycle.**

- **Who constructs it:** the human review/authorization boundary (it, and only it, sets
  `authorized_project_id`, `authorized_scopes`, and `authorizing_principal_id`).
- **Who validates it:** the coordinator, via a named `ProjectScopeAuthorizationValidator`
  (§L). It recomputes `authorization_context_digest` (**including `issued_at`**, §H.10),
  checks non-revocation/non-expiry, and enforces the binding below. It **never** fills,
  repairs, broadens, or adds to any field (it never adds a scope to `authorized_scopes`).
- **Who authorizes it:** the `authorizing_principal_id` through the review/authorization
  boundary — never the coordinator, and never the repository the process happens to run
  in.

**Binding and checks (all fail-closed, §J).**

- **Bound to the specification:** the `ReviewedImportSpecification` carries
  `authorization_context_id` + `authorization_context_digest` (§C.1); a missing context
  is `missing_authorization_context`; a recompute mismatch or any post-issuance
  alteration **of any field, including `issued_at`** (§H.10), is
  `authorization_context_integrity_failure`.
- **Bound to the review decision and candidate:** the context's `review_decision_id`,
  `candidate_id`, `content_digest`, `assessment_report_id`, and `assessment_version`
  must equal the re-validated decision/candidate/assessment exactly; any mismatch
  (including a **cross-project** context, i.e. `authorized_project_id` ≠ the
  specification `project_id`, or a context issued for a different decision/candidate) is
  `authorization_context_mismatch`.
- **`project_id` equality (separate check):** the specification `project_id` must equal
  `authorized_project_id` **exactly** (byte-for-byte after the §H.0 canonicalization);
  no prefix, parent, or "compatible" project is accepted. Project identity and scope
  authorization are **two independent checks** — passing one never implies the other.
- **Scope = exact set membership, no hierarchy (Codex-4):** a specification `scope` is
  authorized **only if it is an exact member** of `authorized_scopes` (equality by the
  §H.0 canonical `MemoryScope` comparison — `scope_type` **and** `scope_id` both equal).
  **No** parent/child, broader/narrower, or ordering relationship is inferred or accepted;
  the coordinator can never convert one scope into another. Any `scope` that is not an
  exact member — **including** one that a human might consider "broader" or "narrower" —
  is `unauthorized_project_scope`. A **missing** specification `scope` (project-level
  record) is authorized **only when** `project_level_authorized` is `true`; an absent
  scope against a grant with `project_level_authorized = false` is
  `unauthorized_project_scope`.
- **Empty / unknown / malformed / duplicate scopes are deterministic:** an
  `authorized_scopes` that is **empty** authorizes no scoped import (and the grant is
  valid only if `project_level_authorized` is `true`); an **unknown** `scope_type` cannot
  exist (the `MemoryScopeType` enum is closed — a non-member fails model validation as
  `invalid_reviewed_specification`/contract error before authorization); **duplicate**
  members are de-duplicated by the §H.0 set-like canonicalization (they never change the
  digest and never expand the grant); a structurally **malformed** scope fails contract
  validation. None of these ever silently widens the grant.
- **Revoked / expired / stale / altered / cross-project all fail closed:** `revoked` →
  `authorization_context_revoked`; expired → `authorization_context_expired`; altered
  (digest mismatch, including a tampered `issued_at`) → `authorization_context_integrity_failure`;
  cross-project or cross-decision → `authorization_context_mismatch`.
- **Adding a scope requires a new/renewed grant:** the authorized set is immutable and
  sealed by the digest, so authorizing an additional scope requires issuing a **new**
  `ProjectScopeAuthorizationContext` (a new `authorization_context_id`), never editing an
  existing grant.

**Identity propagation.** `authorization_context_id` and `authorization_context_digest`
enter: the **specification digest** (§H.5, via the spec fields), the **idempotency key**
(§G.1/§H.1, transitively through `specification_digest`, and named there explicitly), the
**record's ledger provenance** (the ledger attempt/receipt, **not** the authoritative
record content — §F.3, Ruling 5), the **receipt** (§B.3) and its
`receipt_integrity_digest` (§H.6), the **durable intent** (§E step 14), and **recovery
validation** (§I.7 re-checks the intent's authorization-context binding before any
finalize). A retry of the exact reviewed input references the **same** authorization
context, so identity and idempotency are unchanged.

**The coordinator may validate and execute this context, but may not invent
authorization, guess a project, admit a scope outside the explicit authorized set, or
treat repository location as authorization.**

**Identity vs digest, and lifecycle handling (Codex-5).**

- **`authorization_context_id` (semantic identity)** is derived over the identity-bearing
  members **excluding `issued_at`** (§H.10): policy version, `authorizing_principal_id`,
  `authorized_project_id`, `authorized_scopes` (set-like), `project_level_authorized`, the
  decision/candidate/assessment bindings, `expires_at`, and `revoked`. Excluding
  `issued_at` keeps a re-issued-but-identical grant idempotent and stops a timestamp from
  becoming an authorization shortcut.
- **`authorization_context_digest` (complete integrity seal)** covers **every** immutable
  field **including `issued_at`** (§H.10). The completeness claim is therefore honest:
  tampering with `issued_at`, `expires_at`, `revoked`, or any binding is detected as
  `authorization_context_integrity_failure`.
- **Audit timestamp handling:** `issued_at` is retained for audit; it affects integrity
  (digest) but not identity (`authorization_context_id`).
- **Retry:** a retry of the exact reviewed input references the **same** grant (same
  `authorization_context_id` and same digest), so identity and idempotency are unchanged.
- **Expiration** is evaluated against `expires_at` at import/recovery time (fail closed if
  past); **revocation** is evaluated against `revoked` (fail closed if set).
- **Duplicate equality:** two grants with byte-identical members (including `issued_at`)
  share both id and digest and are the same grant. Two grants identical **except**
  `issued_at` share the same `authorization_context_id` (identity) but differ in digest;
  the specification pins a specific `authorization_context_digest`, so it resolves to the
  exact issued grant.
- **Same-id/different-content collision:** a stored grant whose recomputed digest ≠ the
  specification's pinned `authorization_context_digest`, or two grants sharing an
  `authorization_context_id` but differing in an identity member, fail closed as
  `authorization_context_integrity_failure` (never silently merged).

**Identity propagation and acyclicity.** `authorization_context_id` binds
`review_decision_id` (authorization → decision), and the reverse binding is prohibited, so
the graph stays acyclic (§H.0a). `authorization_context_id`/`authorization_context_digest`
then flow forward into the specification digest, idempotency key, receipt, intent, and
recovery validation.

**Diagnostics:** `missing_authorization_context`, `authorization_context_integrity_failure`,
`authorization_context_revoked`, `authorization_context_expired`,
`authorization_context_mismatch`, and the existing `unauthorized_project_scope` (§J).

**Tests (§K):** valid grant authorizes exact project + exact-member scope (and a
`project_level_authorized` grant authorizes a scope-less spec); project mismatch, a scope
**not an exact member** (whether a human would call it broader or narrower), an absent
scope without `project_level_authorized`, missing context, altered/stale digest
(**including a tampered `issued_at`**), revoked, expired, and cross-project/cross-decision
bindings each fail closed with the mapped code.

---

## D. Persistence lifecycle

### D.1 Ledger workflow states

These are **migration-ledger workflow states**, tracked in the ledger. They are
distinct from the Active Memory record's own `lifecycle_state` (which, for every
imported record, is `INACTIVE` — §F.1).

```
candidate_received  →  assessment_completed  →  awaiting_review
                                                     |
                        ┌────────────────────────────┼────────────────────────────┐
                        v                            v                            v
                    approved                     rejected                     deferred
                        |                       (terminal*)                  (non-terminal)
                        v
                import_intended
                   |         |
                   v         v
             import_verified   import_failed
              (terminal)       (non-terminal; safe retry)
                   |
                   v
             uncertain_commit  → (recovery, §I.7) →  import_verified | import_failed
```

### D.2 State meanings

- **candidate_received** — a Phase 40F candidate exists and is referenced.
- **assessment_completed** — a Phase 40G report exists over the candidate's set.
- **awaiting_review** — no valid non-superseded decision yet exists for the exact
  `(candidate_id, digest, assessment_id, version)` tuple.
- **approved / rejected / deferred** — a review decision of that status is the
  current effective (non-superseded) decision for the tuple.
- **import_intended** — a distinct import attempt has durably recorded its *intent*
  (planned `target_record_id`, observed `commit_generation`) but the receipt is not
  yet committed. This is the window that makes uncertain commits detectable (§I).
- **import_verified** — a receipt exists, the snapshot and ledger `commit_generation`
  agree, and the `record_id` resolves in the Active Memory snapshot (the only
  success terminal).
- **import_failed** — an attempt did not commit; no receipt exists and the planned
  record is confirmed absent from the Active Memory snapshot (safe to retry).
- **uncertain_commit** — an intent exists, no receipt exists, and whether the Active
  Memory record durably persisted cannot yet be determined. Not a success and not a
  safe retry until recovery resolves it (§I.7).

### D.3 Terminal vs non-terminal

- **Terminal:** `import_verified` (success), `rejected` (\*terminal for that exact
  reviewed input; a *different* input — new digest or new assessment — is a fresh
  `awaiting_review`, not a re-opening of the rejected one).
- **Non-terminal:** `awaiting_review`, `deferred`, `import_intended`,
  `import_failed`, `uncertain_commit` (resolved only by recovery).

### D.4 Prohibited transitions

- `awaiting_review`/`deferred`/`rejected` → `import_intended` **without** a valid,
  non-superseded `approved` decision. Forbidden.
- Any state → `import_intended`/`import_verified` **without** a valid, digest-matching
  `ReviewedImportSpecification` (§C.1) bound to that exact decision. Forbidden — the
  coordinator constructs the record **only** from the approved specification and never
  infers kind, claim, project, or scope. A missing, invalid, kind/claim-incompatible,
  mis-bound, unauthorized, or stale specification fails closed
  (`missing_reviewed_specification` / `invalid_reviewed_specification` /
  `kind_claim_incompatible` / `specification_binding_mismatch` /
  `unauthorized_project_scope` / `specification_integrity_failure`, §J).
- Any state → `import_intended`/`import_verified` **without** a valid, non-revoked,
  non-expired, digest-matching `ProjectScopeAuthorizationContext` (§C.3) bound to the
  exact project/scope/decision/candidate. Forbidden — a missing, altered, revoked,
  expired, or cross-project authorization context fails closed
  (`missing_authorization_context` / `authorization_context_integrity_failure` /
  `authorization_context_revoked` / `authorization_context_expired` /
  `authorization_context_mismatch`, §J). Repository location is **never** authorization.
- A **superseded** approval authorizing import. Forbidden — a decision with a later
  superseding decision authorizes nothing (§D.7).
- `import_failed`/`uncertain_commit` → `import_verified` **without** a fresh, fully
  re-validated attempt or a successful recovery finalize (§I.7). A failed or
  uncertain attempt never "upgrades" to verified by assertion.
- Any state → `import_verified` **without** the receipt's `record_id` resolving in
  the Active Memory snapshot **and** the snapshot/ledger `commit_generation` agreeing
  (§I). Forbidden by construction.
- Editing a recorded decision's `status`, `reason`, `reviewer_id`, `digest`, or
  assessment binding in place. Forbidden — records are immutable (§B, §D.6).
- `approved` for tuple *X* authorizing import of tuple *Y* (different candidate,
  digest, assessment, or version). Forbidden — the import path binds to the exact
  tuple.
- Mutating the Active Memory record in place to "re-import." Forbidden — a changed
  import is a new `record_id` superseding the old via `supersession_refs` (§D.7,
  §F.2), honoring the Active Memory store's immutability.
- **Transitioning an imported `INACTIVE` Active Memory record directly to
  `SUPERSEDED`.** Forbidden and structurally impossible: the Phase 37C
  `LIFECYCLE_TRANSITIONS` table has **no `INACTIVE → SUPERSEDED` edge**
  (`INACTIVE` may move only to `ACTIVE` or `ARCHIVED`). Phase 40H therefore **never
  calls `transition_lifecycle` in the import path**; supersession of an imported
  record is expressed **only** through the *newer* record's `supersession_refs`
  (§D.7, §F.2), leaving the prior record `INACTIVE` and its "superseded" standing a
  *derived* relationship.

### D.5 Retry and stale-record rules

- **Retry:** after `import_failed`, a retry re-runs the full verified-import
  precondition set (§E) from scratch under a **new** `import_attempt_id` (§G). There
  is no shortcut path.
- **Stale record:** an `approved` decision whose candidate digest or assessment no
  longer matches the present candidate/assessment is **stale**; it is not deleted
  (history is preserved) but it fails the import preconditions and is reported
  (`stale_approval`, §J).

### D.6 Append-only vs updated

State transitions are **append-only through controlled records.** The ledger never
edits an existing record's field. A superseding decision is a *new* decision record
that references the one it supersedes (`supersedes_decision_id`); effective status is
computed as the newest non-superseded decision for a tuple, exactly as Phase 40D/40G
compute readiness rather than reading it off a record. Import attempts likewise
append status/intent records. This makes the whole history auditable and makes "who
changed what, when" answerable from the ledger alone.

### D.7 Supersession, renewed review, tie and cycle rules (deterministic)

Two supersession relationships are kept **separate**: **review-decision
supersession** (a lineage over decisions) and **Active Memory record supersession**
(a lineage over imported records). Neither uses `attempt_sequence` for ordering.

**Review-decision supersession (decision lineage):**

- **Renewed review required when** the candidate digest changes (re-parsed bytes) or
  the assessment identity/version changes (re-assessed set, or ruleset version bump).
  The prior approval no longer matches the exact reviewed input and authorizes
  nothing; a new `awaiting_review` applies until a new decision is recorded.
- **A renewal is always a distinct decision (Codex-7).** A renewed decision **directly
  references** the decision it supersedes via `supersedes_decision_id` **and** differs
  from that predecessor in at least one identity-bearing member so it derives a
  **distinct** `review_decision_id` (§H.9). Normally the discriminator is the changed
  `content_digest` or `assessment_*` that triggered the renewal; when the reviewer
  re-affirms with **no other material change**, they increment `renewal_revision`, which
  is itself an identity member. A "renewal" that changes **only** `decision_timestamp`
  (same `renewal_revision`, same material fields) is **not** a renewal — it is the same
  decision (idempotent, §H.9) and fails no check because it simply resolves to the
  recorded decision. Validation requires that the predecessor exists, belongs to the same
  `candidate_id` line, that the renewal derives a `review_decision_id` **distinct** from
  its predecessor's (else `incomplete_review_provenance` — a self-superseding or
  non-advancing renewal is rejected), and that the renewal's own candidate identity,
  digest, and assessment identity/version are internally consistent with the review
  lineage it claims.
- The **effective head** of a decision line is the unique newest non-superseded
  decision. The graph is walked before any insert. It fails closed on:
  a missing predecessor (`incomplete_review_provenance`), a cycle
  (`supersession_cycle`), or **two or more unsuperseded heads** for one line
  (`supersession_tie`). The `review_decision_id` (a content-derived canonical id,
  §H.1) is used **only** as a deterministic validation/tiebreak mechanism where two
  candidate orderings are otherwise semantically equal — never to *pick a winner*
  among genuinely ambiguous heads (that is a tie and fails closed).
- **A superseded approval cannot authorize import** (§D.4).

**Active Memory record supersession (record lineage):**

- **Changed-byte identity:** different bytes ⇒ different `content_digest` ⇒ a
  distinct reviewed input ⇒ a **new** resulting `record_id`. A **retry of the same
  reviewed input** (same decision, same authored content, same `created_at`) reproduces
  the **same** `record_id` (§H.3) ⇒ idempotent (§G), never a second record; a distinct
  decision authoring different content (including a different `created_at =
  decision_timestamp`) is a distinct `record_id` (a distinct record), not a merge.
- **Changed-assessment behavior:** a changed `report_id`/version invalidates the
  prior approval (renewed review) and, on re-approval, yields a **new** `record_id`
  that supersedes the prior import of the same logical candidate line. The new
  record's `supersession_refs` carry a single `SUPERSEDES` link to the prior
  `record_id`; the prior record is **not** transitioned (§D.4) — its superseded
  standing is the derived inverse the Phase 37C model already defines
  (`SUPERSEDED_BY` is never stored, only derived).
- **Deterministic supersession ordering (records):** when a new import supersedes a
  prior one, ordering is a **total order** over `(decision_timestamp, record_id)` —
  caller-supplied decision time first, and the content-derived `record_id` as the
  final, always-decisive tiebreak. No clock is read; ordering is fully determined by
  recorded fields. `attempt_sequence` is **not** part of record ordering.
- **Tie rejection:** a state that would leave **two** active (non-superseded) heads
  for one logical candidate line — two distinct records with identical ordering keys
  through `record_id` — is rejected fail-closed as `supersession_tie` (§J) rather
  than silently picking one head.
- **Cycle rejection:** a proposed supersession whose `record_supersedes` links would
  close a cycle in the record supersession graph (A supersedes B … supersedes A) is
  rejected fail-closed as `supersession_cycle` (§J). The graph is walked before any
  insert; a cycle is never persisted. (The Phase 37C single-stored-direction
  `SUPERSEDES` design keeps chains acyclic by construction; Phase 40H validates it
  explicitly before authoring the link.)

---

## E. Verified-import contract (the ordered protocol)

The reviewed-import operation (`import_reviewed_candidate`) is the only path that
creates an Active Memory record from a candidate. The complete ordered protocol,
**entirely under the coordinator's exclusive writer lock (§I.4)**, is:

1. **Acquire the coordinator lock** (§I.4), with bounded timeout/poll/attempts; on
   failure return `lock_unavailable` (retryable) or `stale_lock_ambiguous` (fail
   closed) as appropriate.
2. **Load and validate both durable stores** — the migration ledger and the Active
   Memory snapshot (§A.3, §A.4) — running the load-time integrity **detection** scan
   (§I.8), which **recomputes and matches the `ledger_integrity_digest` (§H.7) and
   `snapshot_integrity_digest` (§H.8) before trusting any contained value** (§I.9). A
   cold start with neither present initializes both at generation 0.
3. **Evaluate the N/N+1 uncertain-commit exception, then the shared commit
   generation.** **Before** applying the ordinary equality rule, test the single
   bounded mismatch of §I.3a: ledger at generation `N`, snapshot at exactly `N+1`, a
   durable intent present for the reviewed input, and no verified receipt. If and only
   if that exact state holds, route to the uncertain-commit recovery entry path
   (§I.7); its validated finalize (or fail-closed) result stands in for this step.
   Otherwise apply the ordinary rule — the ledger's and the snapshot's recorded
   `commit_generation` must be **equal**; any other inequality → `generation_mismatch`,
   fail closed (§I.3). The exception is reachable **ahead of** the general
   generation-equality rejection, never after it.
4. **Reload / revalidate the candidate.** Re-obtain the Phase 40F candidate (and,
   where the request carries the artifact reference, re-establish its provenance)
   rather than trusting a caller-passed blob.
5. **Recompute and compare the byte digest.** Recompute the candidate
   `content_digest` (Phase 40F SHA-256 convention) and compare it to the digest the
   review decision was made against. Mismatch → `changed_digest`.
6. **Confirm the reviewed candidate has not changed.** `candidate_id` and its
   provenance fingerprints must match the reviewed decision exactly (`stale_candidate`
   on mismatch).
7. **Confirm the reviewed assessment identity/version has not changed.** The Phase
   40G `report_id` and ruleset version must match the reviewed decision exactly
   (`changed_assessment` on mismatch).
8. **Confirm required review provenance exists** and is complete: reviewer id,
   timestamp, reason, candidate id + digest, assessment id + version, ≥1 evidence
   reference (`missing_review` / `incomplete_review_provenance`).
9. **Confirm the decision is `approved` and is the current non-superseded head** for
   the tuple (`rejected_candidate` / `deferred_candidate` / `stale_approval`); reject
   a superseded approval (§D.7).
10. **Cross-check evidence for contradictions** (approval over a `blocked`
    assessment, evidence pointing at a different candidate, etc.) →
    `contradictory_evidence`.
11. **Validate supersession** (§D.7): reject `supersession_tie` / `supersession_cycle`
    / missing predecessor before any write.
12. **Validate the `ReviewedImportSpecification`, then resolve idempotency.** First
    validate the reviewer-approved specification (§C.1): it must be present
    (`missing_reviewed_specification`), structurally valid (`invalid_reviewed_specification`),
    **kind/claim-compatible under the closed versioned policy** (§C.2,
    `kind_claim_incompatible`), exactly bound to this candidate/digest/
    assessment/decision (`specification_binding_mismatch`), backed by a valid, non-revoked,
    non-expired, correctly-bound **`ProjectScopeAuthorizationContext`** (§C.3,
    `missing_authorization_context` / `authorization_context_integrity_failure` /
    `authorization_context_revoked` / `authorization_context_expired` /
    `authorization_context_mismatch`), project/scope-authorized against that context
    (`unauthorized_project_scope`), and integrity-intact via a recomputed
    `specification_digest` (`specification_integrity_failure`). The coordinator does
    **not** infer, synthesize, or repair any specification field, and **never treats
    repository location as authorization**. Then compute the
    stable idempotency key (§G.1, §H.1) — which **includes `specification_digest`**. If
    a committed receipt already exists for it, **return that exact stored receipt and
    its `record_id` unchanged** — no new record (`duplicate_replay`). If a *materially
    different* attempt collides on a related but non-identical input, fail closed
    (`conflicting_replay`).
13. **Fail closed** for any missing, stale, contradictory, or mismatched evidence.
    The default is refusal; only a fully consistent set proceeds.
14. **Allocate the next attempt sequence under the lock** as `(count of prior
    attempts for this idempotency key) + 1` (§G.2), and **persist a durable intent** —
    append a new `import_attempt` in `intent_state = intended` carrying the planned
    `target_record_id` and the currently-loaded `commit_generation`, committed via
    the ledger CAS write (§I.5). This is the point after which an interruption is
    *recoverable* rather than ambiguous.
15. **Construct the deterministic `MemoryRecord`** under the Active Memory contract
    (INACTIVE, UNVERIFIED, §F.1) **from the validated `ReviewedImportSpecification`
    (§C.1)** — `kind`, `claim`, `project_id`, and optional `scope` come **only** from
    the approved specification (never the candidate, never inference); `created_at =
    decision_timestamp`, and `observed_at` = the specification's reviewer-authored
    `observed_at` (or `None`), kept distinct (§F.3, Codex-6); the record carries **no**
    attempt/decision/authorization audit (Ruling 5) — with `record_id` derived over the
    **complete** record content per §H.3 and provenance mapped per §F.3.
16. **Build a PRIVATE candidate store off-guard and insert into IT — never the published
    live store (Codex-2).** Reconstruct a fresh `InMemoryActiveMemoryStore` from the last
    validated durable snapshot via `ActiveMemorySnapshotStore.load` (all-or-nothing,
    §A.4) — this candidate store is the coordinator's private working copy and is **not**
    the holder's published reference and **not reachable by any runtime reader**. Insert
    the record into that **private candidate** through the store's own seam only (§F.2);
    the expensive build+insert happens **without** the holder write guard. A
    `DuplicateRecordError` whose existing record is **completely canonically equal** (full
    `model_dump`, §F.3, Ruling 4) is the already-inserted case; **any** field difference is
    `record_identity_collision` (fail closed). Then **fully validate the candidate store**
    (structural + per-record contract re-validation). The published live store is untouched
    and still serves readers at generation `N`.
17. **Persist the private candidate as the new Active Memory snapshot at the next commit
    generation** (`commit_generation + 1`) via `ActiveMemorySnapshotStore.persist` over the
    **candidate** store (§A.4), atomic temp-swap, sealing `snapshot_integrity_digest`
    (§H.8). On any snapshot failure, apply the **failure rule** (§I.6); because nothing was
    published, the live store is still the untouched validated `N` store.
18. **Persist the receipt and completed attempt in the ledger with the same commit
    generation** — write the deterministic receipt (§B.3) linking candidate, digest,
    assessment, review decision, attempt, `commit_generation`, and the exact
    `record_id` (and `record_supersedes` when applicable), advance the attempt to
    `committed`, and advance the ledger `commit_generation` to match the snapshot, via
    the ledger CAS write (§I.5). **This durable ledger commit is the reporting commit
    point** — but reported success still additionally requires the reload-verify (19) and
    the publish (20).
19. **Reload and integrity-verify both durable envelopes and exact linkage** — re-read
    both durable stores under the still-held lock and confirm (integrity digests first,
    §I.9): both envelopes verify, the receipt exists, its `record_id` resolves in the
    reloaded snapshot, the two `commit_generation` values agree, and the record's complete
    content matches (§I.7 finalize check). A failure here fails closed / quarantines
    (§I.6) — the live store is still the untouched `N` store, never a partial one.
20. **Publish the validated candidate as the live store, LAST (Codex-2).** Only now — after
    the durable snapshot (`N+1`), receipt, ledger advance (`N+1`), and reload-verify all
    succeed — call the holder's `publish(candidate, expected_generation=N,
    new_generation=N+1)` to perform the **O(1) reference swap** under the shortest
    write-guard boundary (§A.6). Readers see either the complete old validated store (`N`)
    or the complete new validated store (`N+1`), never a partial mutation. **Only if
    `publish` succeeds** is `import_verified` reported. If `publish` raises
    `live_store_replacement_failure`, the durable truth is already `N+1` but the swap did
    not complete: the coordinator maps it to `import_service_quarantined` and **does not
    report success** — startup/recovery reconstructs+publishes the live store from the
    committed `N+1` snapshot, and a later replay returns the committed receipt (§I.6, §I.7).
21. **Release the lock** in a `finally` (success, handled failure, and exception
    paths all release — §I.4).

> The durable ledger receipt is the **reporting** commit point, but reported success
> **additionally requires** matching durable snapshot `commit_generation`, exact record
> linkage, **and a successful `publish` swap** (steps 17–20). No imported record becomes
> visible through the published live store until the durable snapshot and verified
> ledger/receipt state are persisted **and** validated (Codex-2). A receipt is *verified*
> only when its linked snapshot generation and ledger generation agree (§I.3).

### E.1 What "verified import" proves — and does not

**Proves:** the exact candidate bytes that were reviewed (digest-identical) were
imported; the exact assessment the reviewer saw still applies; a complete,
attributable, non-contradictory, non-superseded approval authorized it; and the
resulting Active Memory record (owned by the Active Memory store, durable in the
snapshot at an agreed `commit_generation`) is deterministically linked to all of that
by an immutable receipt referencing its exact `record_id`. Re-running the same
reviewed input yields the same receipt and the same `record_id`, and no second record.

**Does not prove:** that the imported statement is factually **true**. Byte integrity
and review provenance are not truth adjudication. Accordingly the resulting record is
imported evidence with a conservative standing (§F.1): it is not `human_confirmed`
truth merely because a human approved *importing it*, and it is never auto-activated
into the trusted baseline by this phase. No LLM or automated process decides truth
anywhere in the path.

---

## F. Mutation authority and provenance mapping

**One explicit mutation boundary:**

> Only the reviewed-import path (the import coordinator's `import_reviewed_candidate`)
> creates an Active Memory record from a migration candidate, and it does so
> **exclusively through the Active Memory store's own insertion seam (§F.2)** — never
> by owning, copying, or bypassing that store.

- Parsing, projection, validation, assessment, dry-run, inspection, and
  review-record creation **must not** mutate Active Memory. Recording a review
  decision writes a *decision* to the migration ledger; it does not touch Active
  Memory.
- **No automatic candidate approval.** Approval is a human act recorded as a review
  decision; nothing derives approval.
- **No semantic promotion inferred from parsing success.** A candidate that parsed
  cleanly, hashed cleanly, and assessed `ready_for_review` is still just a candidate
  until a human decision plus a verified import exist.
- **No LLM or automated truth adjudication** anywhere in the path.

### F.1 Standing of the resulting Active Memory record

The imported record is created **inactive** (`LifecycleState.INACTIVE`) and
**unverified** (`VerificationState.UNVERIFIED`) — it is imported history a human
chose to bring in, not an adjudicated active fact. Both values are already
first-class members of the existing Active Memory enums, so no enum or contract
change is required. Promotion to `active` / `human_confirmed` (active-state
calculation, contradiction handling) and any lifecycle retirement remain deferred
Active Memory work already named in the roadmap and are **not** part of Phase 40H.
This preserves the Phase 40E/40F invariant that imported material is never verified
truth automatically, while still letting a human durably persist a reviewed candidate.

### F.2 The authorized Active-Memory-insertion seam

Phase 40H inserts through the **existing** Active Memory store boundary, not a new
one:

- **Seam:** `MemoryStore.insert(record: MemoryRecord) -> MemoryRecord` in
  [`app/store/active_memory_store.py`](../../apps/backend/app/store/active_memory_store.py),
  called on the coordinator's **private candidate store** — the fresh
  `InMemoryActiveMemoryStore` it reconstructs from the last validated durable snapshot
  (§A.4, §E step 16), **never the holder's published live store** (Codex-2/3). The
  coordinator never holds, injects, or mutates the published store; it constructs a
  `MemoryRecord` from the validated `ReviewedImportSpecification` (§C.1) with a
  deterministic caller-supplied `record_id` (§H.3), inserts it into the private candidate,
  and later publishes the validated candidate through the holder's `publish` swap (§A.6,
  §E step 20). The published store changes **only** by whole-store replacement, never by an
  in-place insert.
- **Duplicate semantics are reused, not reinvented.** The store already raises
  `DuplicateRecordError` on a colliding `record_id`. Because Phase 40H's `record_id`
  is a pure function of the reviewed content-identity, a duplicate insert means *this
  exact content should already exist*. The coordinator then compares the existing
  stored record to the one it would have written using the **complete canonical
  `MemoryRecord` equality projection (§F.3, Ruling 4)** — every authoritative stored
  field via the store's own `serialize()`/`model_dump(mode="json")` shape, not a
  hand-selected subset. On a **complete** match it treats this as the already-inserted
  case and reconciles against the ledger intent (§I.7); on **any** field difference it
  fails closed as `record_identity_collision` (§J).
- **Supersession is authored on the new record only — `transition_lifecycle` is NOT
  called.** A changed re-import writes a *new* record whose `supersession_refs` carry
  a single `SUPERSEDES` link to the prior `record_id`, exactly as the Active Memory
  store already models supersession (forward-direction only; the inverse is derived).
  The prior imported record stays `INACTIVE`; Phase 40H **does not** invoke
  `transition_lifecycle` in the verified-import transaction, because the only
  transition it would want (`INACTIVE → SUPERSEDED`) is **not permitted by the Phase
  37C lifecycle table** and the ruling forbids changing that table here. The store's
  `transition_lifecycle` remains available for other, independently-valid transitions
  outside this phase; Phase 40H's import path simply never uses it.
- **Durability-before-visibility handshake (Codex-2).** Because the Active Memory store is
  in-memory with caller-owned serialize/restore, the *effect* of the insert is first made
  durable by the mandatory `ActiveMemorySnapshotStore` (§A.4) over the **private candidate**
  at generation `N+1` **before** the ledger receipt is committed (§E steps 17–18), and the
  candidate is only **published** to runtime readers **after** the durable snapshot,
  receipt, and reload-verify all succeed (§E steps 19–20). No reader ever sees the imported
  record before it is durably persisted and verified. Phase 40H does **not** re-home Active
  Memory records into the ledger to fake durability.

### F.3 Candidate-to-`MemoryRecord` provenance mapping

Phase 40H maps a reviewed candidate **and its reviewer-approved
`ReviewedImportSpecification` (§C.1)** onto the **existing** `MemoryRecord` fields.
The candidate supplies its identity, digest, and provenance; the **specification
supplies the record's `kind`, structured `claim`, `project_id`, and optional `scope`**
— fields the candidate does **not** carry (§C.1) and that the coordinator never infers.
Provenance is **not** left as unspecified free-form metadata: Phase 40H defines a
typed `MigrationProvenance` sub-model (in the new `memory_migration_import.py` models
module, §L) whose canonical dump populates `MemoryRecord.metadata["migration_provenance"]`.
The `metadata: dict[str, Any]` field is the Phase 37B contract's **documented
forward-compatible extension point**; specifying its exact shape in Phase 40H's own
module means **no change to the frozen Phase 37B `active_memory.py` contract is
required or proposed.**

**The authoritative record carries only content; every decision/attempt/authorization
fact lives in the ledger (Rulings 4 & 5).** The single most important rule of this
mapping: the authoritative `MemoryRecord` — including its `metadata.migration_provenance`
block, `created_at`, and `observed_at` — is a **pure, deterministic function of the
reviewed record content plus the content-identity provenance**. It carries **no**
`import_attempt_id`, **no** `attempt_sequence`, **no** attempt timestamp, and **no**
decision-, specification-, authorization-, or idempotency-specific field. Those are
attempt-/decision-specific facts that would destabilize the record across retries and
across two decisions that legitimately share a `record_id`; they are held **only** in
the ledger (import-attempt records, durable intents, receipts, recovery metadata,
ledger audit history), and the link from ledger to record is the receipt's `record_id`
reference (ledger → record), **never** a record → attempt back-reference.

**On the authoritative `MemoryRecord` (participates in `record_id` and complete
equality, §H.3):**

| Migration value | Carried by (existing `MemoryRecord` surface) |
| --- | --- |
| **Record kind / claim / project / scope** | `kind`, `claim` (subject/predicate/value/value_kind/summary), `project_id`, optional `scope` — **all from the reviewer-approved `ReviewedImportSpecification` (§C.1)**, never from the candidate, never inferred |
| **Deterministic source** | `source = MemorySource(source_type=IMPORTED_DOCUMENT, source_id=<stable candidate slug>, display_label?, session_id?)` from the specification's `source_type`/`source_provenance` |
| **Content-identity provenance** | `metadata.migration_provenance = {candidate_id, content_digest, assessment_report_id, assessment_version}` **only** — the four content-identity values, canonically dumped; **no** decision/attempt/authorization/idempotency member |
| **Standing** | `lifecycle_state = INACTIVE`, `verification_state = UNVERIFIED` (§F.1); `confidence = None`; `evidence_ids = []`; `verification = None` |
| **Supersession** | `supersession_refs = [SupersessionReference(kind=SUPERSEDES, target_record_id=<prior>, created_at=<decision_timestamp>)]` from the specification's authorized `supersession_refs` (0..1) |
| **Deterministic timestamps (distinct, never substituted — 37B §13)** | `created_at = decision_timestamp` of the authorizing decision (the moment the record was *recorded*; stable across retries of that decision; the store neither stamps nor rewrites it). `observed_at =` the specification's reviewer-authored **`observed_at`** (the *claimed observation time* of the imported content) when present, else `None`. The two are **semantically distinct** exactly as the real `MemoryRecord` keeps them (active_memory.py: `observed_at` = claimed observation time; `created_at` = when recorded) and are **never equated**: the coordinator validates the specification's `observed_at` format but never derives it from `decision_timestamp`, a wall clock, or the candidate (Codex-6). Both participate in `record_id` (§H.3). |

**In the ledger only (never on the record):** `review_decision_id`,
`specification_digest`, `authorization_context_id` + `authorization_context_digest`,
`idempotency_key`, `evidence_references`, `import_attempt_id`, `attempt_sequence`, and
the receipts. These are the decision/attempt/authorization audit; they are queryable
from the ledger and linked to the record by `record_id`.

**Why `record_id` covers the complete record content (design decision, Ruling 4).**
`record_id` (§H.3) is derived over the **entire** authoritative record content above —
kind/claim/project/scope, source, standing, `supersession_refs`, the content-identity
provenance block, `created_at`, and `observed_at` — so that **`record_id` equality is
equivalent to complete canonical record equality** by construction. Rationale: this
collapses "duplicate `record_id`" and "duplicate content" into one fact, so the store's
`DuplicateRecordError` gate has exactly one honest interpretation. `created_at` is
included as the authorizing decision's `decision_timestamp` (not a wall-clock read), so
a *retry of the same reviewed input* reproduces the identical record and `record_id`
(Ruling 5), while *two genuinely distinct decisions* — which differ in ≥1 identity-bearing
decision field (distinct `review_decision_id`, §H.9) and typically in authored content or
in their recorded `decision_timestamp` — deterministically produce **distinct
`record_id`s** (two distinct records), never a silent merge and never a forced collision.
A copy differing **only** in `decision_timestamp` is the *same* decision (§H.9) and the
*same* record — not a distinct one (Codex-7).

**The complete canonical `MemoryRecord` equality projection (Ruling 4).** The
duplicate-insert gate compares the incoming record against the stored record using the
store's **own** serialization — `MemoryRecord.model_dump(mode="json")` canonicalized by
the §H.0 rules (sorted keys, UTF-8), i.e. exactly the per-record shape
`InMemoryActiveMemoryStore.serialize()` emits. It is **not** a hand-selected subset and
cannot drift from the model: every authoritative stored field participates — `record_id`,
`kind`, the complete `claim`, `project_id`, `scope`, `source` (type + `source_id` +
`display_label` + `session_id`), `verification_state`, `lifecycle_state`, `confidence`,
`evidence_ids`, `verification`, `supersession_refs`, `observed_at`, `created_at`, and the
complete `metadata` block. Three cases are kept distinct:

- **Exact duplicate replay** — same `record_id` **and** complete canonical content
  equality: the already-inserted case; reconcile against the ledger intent (§I.7) and
  return the stored receipt (§G.3). No second record.
- **Record identity collision** — same `record_id` but **any** canonical field differs:
  `record_identity_collision`, fail closed (only reachable via tampering or an
  astronomically unlikely hash collision, since `record_id` covers the whole content).
- **Reviewed input with a different `record_id`** — a distinct proposed authoritative
  record subject to normal validation (a new record, possibly superseding a prior one
  via `supersession_refs`, §D.7).

Any difference produces `record_identity_collision` (same id) or `conflicting_replay`
(a materially different attempt colliding on a related reviewed-input key, §G.3), and is
**never** silently accepted. **Tests mutate each compared field individually** (§K).

> **Minimal-model-change note.** The existing `metadata` extension point safely
> carries all migration provenance as a typed, namespaced block, so **no Phase 37B
> model change is required.** If a future independent audit instead requires these
> values promoted to first-class typed fields on `MemoryRecord`, that is a **named,
> separate Phase 37B contract change** — explicitly out of scope here and listed as
> deferred (§N), not silently performed by Phase 40H.

---

## G. Idempotency and replay

### G.1 Stable idempotency key inputs

The stable idempotency key is the canonical id (§H.1) over exactly: `candidate_id`,
`content_digest`, `assessment_report_id`, `assessment_version`, `review_decision_id`,
and `specification_digest`. These six identify "this exact reviewed input." Nothing
time-based, random, or request-envelope-based enters the key. **The key is stable
across retries** — every retry of the same reviewed input (same specification) computes
the same key. Including `specification_digest` is what makes two **different**
specifications for the same candidate **distinct reviewed inputs** with distinct keys
(§C.1): each requires its own approval, and re-presenting the *same* specification is
the ordinary idempotent replay.

### G.2 Distinct attempt ids via a deterministic monotonic sequence (retries only)

While the idempotency key is stable, **every attempt gets a distinct
`import_attempt_id`** (§H.2), keyed off `attempt_sequence`. `attempt_sequence` is
**scoped only to retries under one stable reviewed-input idempotency key** — it is
**not** a review-decision ordering key (§C, §D.7). It is a deterministic monotonic
integer assigned **under the exclusive writer lock** as `(count of prior attempts
recorded in the ledger for this idempotency key) + 1`. The first attempt is `1`, its
retry is `2`, and so on. It is **persisted, append-only, unique, and contiguous per
idempotency key**, and it is **validated during load** (a gap or duplicate in the
per-key sequence is `corrupt_ledger`, §J). Consequences:

- attempt ids never collide, so a retry is a first-class, separately-auditable ledger
  record rather than an overwrite of the prior attempt;
- the sequence is reconstructible purely from durable ledger state (no counter held
  only in memory), so recovery (§I.7) can compute the next sequence deterministically;
- the *receipt* is keyed by the stable idempotency key (at most one committed), so
  many distinct attempts still yield at most one Active Memory record.

### G.3 Behavior

- **Duplicate valid request** (same key, prior committed receipt): return the **exact
  existing receipt unchanged** and its existing `record_id`. No new attempt commits a
  second record. Idempotent replay is a lookup, not a re-import (`duplicate_replay`).
- **Deterministic receipt lookup:** the committed receipt is addressable by the
  idempotency key, so a replay is answered from the ledger deterministically.
- **Successful replay:** returns the same `receipt_id` and same `record_id` as the
  original — byte-identical result.
- **Retry after failure:** if no committed receipt exists for the key, a retry
  acquires a **new** `import_attempt_id` (§G.2), re-runs §E fully, and may create the
  (first and only) receipt.
- **Distinct decisions over identical authored content:** a **genuinely distinct**
  approved decision (distinct `review_decision_id`: it differs in ≥1 identity-bearing
  field — e.g. `reviewer_id`, `reason`, `evidence_references`, or `renewal_revision` —
  **not** merely in `decision_timestamp`, §H.9) whose specification authors
  **byte-identical record content** — including the same recorded
  `created_at = decision_timestamp` — over the same `content_digest` + assessment has a
  *different* idempotency key (it includes `review_decision_id` via a distinct
  `specification_digest`) but derives the *same* complete-content `record_id` (§H.3). Its
  import finds **complete canonical equality** at the insert gate (§F.3), reuses the
  already-existing record, and writes its own receipt referencing that `record_id` — one
  record, a second audited receipt. A distinct decision whose specification authors
  **different** record content — a different recorded `created_at = decision_timestamp`,
  a different `observed_at`, or different kind/claim/project/scope — derives a
  **different** `record_id` (a distinct record, §C.1, §F.3), never a merge and never a
  collision. A copy that changes **only** `decision_timestamp` is the *same* decision
  (§H.9) and resolves to the recorded decision and its one record — it is not a second
  record.
- **Concurrency:** two concurrent requests for the same key cannot both create a
  record. The exclusive writer lock (§I.4) serializes them and the persisted-revision
  CAS (§I.5) rejects a stale writer (`revision_conflict`); one wins and the other
  resolves to the winner's receipt (`duplicate_replay`). No lost update, no double
  record.
- **Conflicting replay detection:** the *same* candidate digest presented under a
  *different* assessment or a *different* review decision is a distinct reviewed input
  requiring its own approval; if it collides with an existing but **materially
  different** attempt it is reported (`conflicting_replay`), never silently merged.

> Approved candidates import **exactly once** for the same reviewed input; duplicate
> valid requests return the same deterministic result rather than creating another
> Active Memory record.

---

## H. Canonical identity derivation

Every derived identity is a pure function of typed content. The derivation is the
repository's canonical-JSON + SHA-256 convention (reused from Phase 40E/40F/40G — no
new scheme), pinned here so field boundaries are unambiguous.

### H.0 Shared canonicalization + collision policy (all identifiers and digests)

**This one policy governs every Phase 40H digest and deterministic identifier**, so no
two of them can be derived by subtly different rules: the reviewed-input idempotency key
(§H.1), `import_attempt_id` (§H.2), `MemoryRecord.record_id` (§H.3), `receipt_id`
(§H.4), `specification_digest` (§H.5), `receipt_integrity_digest` (§H.6),
`ledger_integrity_digest` (§H.7), `snapshot_integrity_digest` (§H.8),
`review_decision_id` (§H.9), and `authorization_context_id` + `authorization_context_digest`
(§H.10). Their acyclic derivation order is fixed in §H.0a.

- **Serialization:** canonical **UTF-8 JSON**; **object keys sorted** lexicographically
  by Unicode code point at **every** nesting level (nested objects canonicalized
  recursively; object boundaries are explicit — a nested model is a nested JSON object,
  never a flattened string).
- **Domain separation + versioning:** an explicit **`schema` field** =
  `"memory-migration-import.v1"` and an explicit **`domain` tag** naming the exact
  value type (below). Identity domains and integrity domains are **distinct tags**, so
  an identity value and an integrity value over the same members can never be confused
  (§H.6, §H.7, §H.8).
- **Unicode normalization:** all string members are compared and encoded in **Unicode
  NFC**. NFC is applied for *encoding stability only*; it never rewrites stored semantic
  content (below).
- **Whitespace + case are preserved, not normalized away.** Phase 40H performs **no**
  destructive normalization of semantic content. Where the frozen contracts already
  strip at their own edge — `MemoryClaim.subject`/`predicate`, `MemoryScope.scope_id`,
  `MemorySource.source_id` (leading/trailing strip) — that stripped value is what the
  model stores and therefore what is canonicalized; Phase 40H adds **no further**
  trimming, case-folding, or internal-whitespace collapsing. Claim `value`/`summary`
  text, in particular, is **case- and whitespace-significant and preserved exactly**.
  Identifiers and digests are **case-sensitive**; digest hex output is **lowercase**.
- **Typed values, no lossy stringification:** strings as strings, integers as JSON
  integers, booleans as JSON booleans, enums as their **`StrEnum` wire literal**
  (e.g. `project_fact`, `imported_document`). No structured value is collapsed to a
  display string.
- **UUIDs:** none are minted — every identifier here is content-derived lowercase hex;
  no random/UUID field participates in any identity.
- **Timestamps:** represented as their canonical `model_dump(mode="json")` ISO-8601
  string with an explicit UTC offset (timezone-naive values are rejected at the contract
  edge). **Audit/ordering** timestamps are **excluded from every *identity*** —
  `decision_timestamp` from `review_decision_id`; `issued_at` from
  `authorization_context_id`; `attempt_timestamp`/`verification_timestamp` from
  `import_attempt_id`/`receipt_id`. **Two categories of timestamp are authoritative
  *content* and therefore participate:**
  - the specification's **`observed_at`** and the record's derived `created_at`
    (= `decision_timestamp`) and `observed_at` are authoritative **record content**, so
    they participate in `specification_digest` (§H.5, the one exception to "no timestamp in
    an identity domain" — because they *are* record content, not audit metadata) and in
    `record_id` (§H.3);
  - the **integrity digests** deliberately cover **every** immutable field including all
    timestamps: `receipt_integrity_digest` (both receipt timestamps),
    `authorization_context_digest` (`issued_at`, Codex-5), `ledger_integrity_digest`, and
    `snapshot_integrity_digest`.
- **Null vs absent:** an **absent optional field is omitted** from the canonical object;
  an explicit `null` is emitted **only** where null is a semantically meaningful value
  (e.g. `record_supersedes` uses an explicit null token to distinguish "no predecessor"
  from an omitted field). A field is never both omittable and null-bearing for the same
  meaning.
- **List ordering:** **authored-order lists preserve their order** (`evidence_references`,
  `supersession_refs`); **set-like collections are sorted and de-duplicated** by their
  canonical member encoding (`authorized_scopes`) so member order can never change a
  digest.
- **Path normalization:** **no filesystem path participates in any identity or digest.**
  Ledger/snapshot/lock locations are configuration, never identity inputs; a path that
  surfaces in a raw `OSError` is mapped to a typed `persistence_failure` (§J).
- **Hash:** **SHA-256** over the canonical encoded bytes, **lowercase hex**.

**Collision response (fail closed).** Because every value is domain-tagged, versioned,
and derived by this one policy, a same-identifier/different-canonical-content condition
can only arise from tampering, storage corruption, or an astronomically unlikely hash
collision. Every such condition **fails closed** with the applicable explicit
diagnostic — `record_identity_collision` (record ids), `receipt_integrity_failure`
(receipt id/integrity), `specification_integrity_failure` (specification digest),
`authorization_context_integrity_failure` (authorization digest), `review_decision_collision`
(decision ids), `corrupt_ledger`/`corrupt_active_memory_snapshot` (envelope integrity),
and the catch-all `canonical_identity_collision` for any other identifier — and is
**never** silently merged or overwritten (§J).

### H.0a Acyclic identity dependency order (Codex-1)

Every derived identity is a pure function of already-existing content, and the
derivation graph is a **strict DAG** — no identifier requires its own downstream
derivative. The single authoritative creation/derivation order is:

1. **candidate identity + `content_digest`** — Phase 40F output, upstream (exists first).
2. **assessment identity + version** (`assessment_report_id`, `assessment_version`) —
   Phase 40G output, upstream.
3. **`review_decision_id`** (§H.9) — derived over the decision's own fields +
   candidate/digest/assessment + evidence + `supersedes_decision_id` + `renewal_revision`.
   **Depends on 1–2 only; it does *not* depend on any authorization, specification,
   attempt, record, or receipt identity.**
4. **`authorization_context_id`** and **`authorization_context_digest`** (§H.10) — derived
   over the authorization grant's fields, **including `review_decision_id`** (subordinate
   binding, authorization → decision). Depends on 1–3; the decision never depends on it.
5. **`specification_digest`** (§H.5) — over the reviewer-authored specification fields,
   including `review_decision_id`, `authorization_context_id`,
   `authorization_context_digest`, `target_kind`, `claim`, `project_id`, `scope`,
   `observed_at`. Depends on 1–4.
6. **`idempotency_key`** (§H.1) — over candidate/digest/assessment + `review_decision_id`
   + `specification_digest` + `authorization_context_id`. Depends on 1–5.
7. **`import_attempt_id`** (§H.2) — over `(idempotency_key, attempt_sequence)`. Depends on
   6.
8. **`record_id`** (§H.3) — over the complete authoritative record content
   (kind/claim/project/scope/source/standing/supersession/content-identity provenance/
   `created_at`/`observed_at`). Depends on the specification content (5) and the decision's
   `decision_timestamp` (as `created_at`); it is **independent of** the attempt, receipt,
   authorization, and specification *digest* values (they are ledger-only audit, §F.3).
9. **`receipt_id`** (§H.4) — over `idempotency_key`, `import_attempt_id`, `record_id`,
   `record_supersedes`, `authorization_context_id`, `commit_generation`. Depends on 6–8.
10. **integrity digests** — `receipt_integrity_digest` (§H.6), `ledger_integrity_digest`
    (§H.7), `snapshot_integrity_digest` (§H.8): full-content seals computed **last** over
    already-formed content (they are never inputs to any identity).

No arrow ever points backward. In particular authorization (4) → decision (3) is the only
edge between those two objects; the reverse edge is prohibited, which is the fix for the
former review/authorization cycle.

### H.1 Reviewed-input idempotency key

- **domain:** `migration-import/reviewed-input`
- **exact members:** `candidate_id`, `content_digest`, `assessment_report_id`,
  `assessment_version`, `review_decision_id`, `specification_digest`,
  `authorization_context_id`. (`specification_digest` already seals the
  `authorization_context_id`/`authorization_context_digest` binding via §H.5; the id is
  also named here explicitly so the reviewed-input key is self-evidently
  authorization-bound.)
- No timestamps, no attempt data, no request envelope. This is "the exact reviewed
  input." `review_decision_id` is itself the canonical id over the decision's fields
  (a decision-domain id) and `specification_digest` is the canonical id over the
  reviewer-approved specification (§H.5), so a renewed decision (new
  `review_decision_id`) **or** a different specification (new `specification_digest`)
  forms a **distinct** reviewed input even over identical bytes/assessment — that is a
  new approval to be audited, and it is *not* a conflicting replay unless it collides
  with a materially different existing attempt (§G.3).

### H.2 `import_attempt_id`

- **domain:** `migration-import/attempt`
- **exact members:** `idempotency_key`, `attempt_sequence`.
- `attempt_sequence` obeys the persistence/uniqueness/contiguity rules of §G.2.

### H.3 Deterministic `MemoryRecord.record_id`

- **domain:** `migration-import/record`
- **exact members — the *complete* authoritative record content:** the reviewer-approved
  specification's record content (`kind`, `claim` subject/predicate/value/value_kind/
  summary, `project_id`, optional `scope` — from the `ReviewedImportSpecification`,
  §C.1, **never the candidate**); the deterministic `source`
  (`source_type`/`source_id`/`display_label?`/`session_id?`); the fixed standing
  (`lifecycle_state = inactive`, `verification_state = unverified`, `confidence = null`,
  `evidence_ids = []`, `verification = null`); the authorized `supersession_refs`; the
  content-identity provenance block (`candidate_id`, `content_digest`,
  `assessment_report_id`, `assessment_version`); and the deterministic
  `created_at` (= the authorizing decision's `decision_timestamp`) and `observed_at`
  (= the specification's reviewer-authored `observed_at`, or null — §C.1, Codex-6). In other
  words, **every field the store would serialize** (§F.3), so `record_id` equality is
  **equivalent to complete canonical record equality** by construction.
- **Deliberately excluded (ledger-only audit, never on the record):** `review_decision_id`,
  `renewal_revision`, `specification_digest`,
  `authorization_context_id`/`authorization_context_digest`,
  `idempotency_key`, `import_attempt_id`, `attempt_sequence`, `attempt_timestamp`, and
  `verification_timestamp`. The **only** timestamps that participate are the two
  authoritative-content ones: `created_at` (= the authorizing decision's
  `decision_timestamp`) and `observed_at` (the specification's reviewer-authored claimed
  observation instant, §C.1, Codex-6) — both included above. This is why a **retry of the
  same reviewed input** reproduces the same `record_id` (§B.1, §G.3, Ruling 5); why a
  specification with different record content — including a different
  `created_at = decision_timestamp` or a different `observed_at` — produces a **new**
  `record_id` (§C.1, §F.3); and why a changed digest or changed assessment produces a
  **new** `record_id` that supersedes the prior one (§D.7).
- **Canonical record equality** (the duplicate-insert gate, §F.3) compares the
  **complete** `MemoryRecord.model_dump(mode="json")` — this exact member set plus
  `record_id` itself — not a subset; a matching `record_id` with **any** differing
  field is `record_identity_collision`.

### H.4 `receipt_id`

- **domain:** `migration-import/receipt` (an **identity** domain)
- **exact members:** `idempotency_key`, `import_attempt_id`, `record_id`,
  `record_supersedes` (or an explicit null token), `authorization_context_id`, and
  `commit_generation`.
- **Deliberately excluded:** `attempt_timestamp`, `verification_timestamp`, and every
  other temporal field — so `receipt_id` is a stable function of the linkage and a
  duplicate replay returns the exact stored receipt unchanged (§B.3, §G.3). The
  full-content **`receipt_integrity_digest` is computed differently** — over the whole
  immutable receipt *including* both timestamps (§H.6), a separate concern from
  identity.

### H.5 `specification_digest`

- **domain:** `migration-import/specification` (an **identity** domain)
- **exact members:** every `ReviewedImportSpecification` field (§C.1) **except**
  `specification_digest` itself — contract name/version, `candidate_id`,
  `content_digest`, `assessment_report_id`, `assessment_version`, `review_decision_id`,
  `target_kind`, the complete structured `claim`, the reviewer-authored **`observed_at`**
  (or explicit null), `kind_claim_policy_version` (§C.2), `project_id`, optional `scope`,
  `authorization_context_id`, `authorization_context_digest` (§C.3), `evidence_references`,
  `source_type`, `source_provenance`, and applicable `supersession_refs`.
- **Excluded:** nothing except `specification_digest` itself. The specification's one
  timestamp, **`observed_at`, is authoritative record content (not audit metadata), so it
  is included** (Codex-6) — this is why two specifications differing only in `observed_at`
  are distinct reviewed inputs (distinct `specification_digest` ⇒ distinct idempotency key)
  that also derive distinct `record_id`s (§H.3), which keeps idempotency and record
  identity consistent (never a same-key/different-record `conflicting_replay`). The digest
  seals the reviewer-authored record content (incl. `observed_at`), its four
  content-identity bindings, the kind/claim policy version, and the authorization-context
  binding so no subset can be altered undetected. A recompute mismatch is
  `specification_integrity_failure` (§C.1, §J).

### H.6 `receipt_integrity_digest`

- **domain:** `migration-import/receipt-integrity` (a distinct **integrity** domain
  tag, separate from the `migration-import/receipt` identity domain of §H.4), with its
  own schema version tag, so an identity value and an integrity value can never be
  confused.
- **exact members:** the **complete immutable receipt content** — every §B.3 field
  **including `attempt_timestamp` and `verification_timestamp`** — and **excluding only
  `receipt_integrity_digest` itself**: `receipt_id`, `receipt_version`, `candidate_id`,
  `content_digest`, `assessment_report_id`, `assessment_version`, `review_decision_id`,
  `specification_digest`, `authorization_context_id`, `authorization_context_digest`,
  `idempotency_key`, `import_attempt_id`, `record_id`,
  `record_supersedes`, `supersession_refs`, `commit_generation`, `verification_status`,
  `attempt_timestamp`, `verification_timestamp`.
- **Purpose:** a **full-content integrity seal**. Altering **either timestamp** or any
  other immutable field changes this digest and is detected as
  `receipt_integrity_failure` at load and recovery (§I.8), even though such a change
  does **not** alter `receipt_id`. A duplicate replay returns the stored receipt
  **with its original timestamps and original `receipt_integrity_digest` unchanged**
  (§G.3); the digest is never recomputed on replay.

### H.7 `ledger_integrity_digest`

- **domain:** `migration-import/ledger-integrity` (a distinct **integrity** domain tag),
  with its own schema-version tag.
- **exact members:** the **complete immutable ledger envelope** except
  `ledger_integrity_digest` itself — the envelope **type/domain tag**, `schema_version`,
  `ledger_revision`, `commit_generation`, and **every** contained member in canonical
  order: review decisions, evidence references, import attempts (with `intent_state`),
  durable intents, receipts (each carrying its own §H.6 `receipt_integrity_digest`), and
  idempotency/recovery metadata.
- **Purpose:** seals the whole ledger file so tampering with **any** envelope field —
  `commit_generation`, `ledger_revision`, a decision, an attempt, an intent, a receipt,
  a provenance member, or the per-key `attempt_sequence` — is detected. A recompute
  mismatch is **`corrupt_ledger`**, fail closed (§I.9). The N/N+1 recovery path may read
  the ledger's `commit_generation` **only after** this digest verifies (§I.9); an
  untrusted generation value never authorizes recovery.

### H.8 `snapshot_integrity_digest`

- **domain:** `migration-import/snapshot-integrity` (a distinct **integrity** domain
  tag), with its own schema-version tag.
- **exact members:** the **complete immutable snapshot envelope** except
  `snapshot_integrity_digest` itself — the envelope **type/domain tag**,
  `schema_version = "active-memory-snapshot.v1"`, `commit_generation`, and the exact
  inner 37C payload (`contract_version = "active-memory.v1"`, the `records` list emitted
  by `InMemoryActiveMemoryStore.serialize()`), records in the store's own stable order.
- **Purpose:** seals the whole snapshot file so tampering with the generation or **any**
  record is detected. A recompute mismatch is **`corrupt_active_memory_snapshot`**, fail
  closed (§I.9). The N/N+1 recovery path may read the snapshot's `commit_generation` and
  planned record **only after** this digest verifies (§I.9).

### H.9 `review_decision_id`

- **domain:** `migration-import/review-decision` (an **identity** domain)
- **exact members (complete, versioned, domain-separated):** `review_policy_version`
  (§C), `reviewer_id`, `status`, `reason`, `notes` (or explicit null), `candidate_id`,
  `content_digest`, `assessment_report_id`, `assessment_version`, `evidence_references`
  (authored order), `supersedes_decision_id` (or explicit null), and `renewal_revision`
  (a non-negative integer, default `0`, §C). These are exactly the fields that make one
  decision **materially distinct** from another.
- **Acyclic by construction — no `authorization_context_id` member (Codex-1).** The
  `authorization_context_id` is **deliberately not** a member of `review_decision_id`.
  The review decision is the **authoritative object that exists first**; the
  `ProjectScopeAuthorizationContext` is a **subordinate object created afterward that
  references the decision** (its `review_decision_id` is one of *its* members and of
  `authorization_context_id`/`authorization_context_digest`, §H.10). Deriving the
  decision id from the authorization id — while the authorization id already derives from
  the decision id — would be an **impossible circular derivation**; the plan forbids it.
  The one-directional binding (authorization → decision, never the reverse) keeps the
  identity graph a strict DAG (see the dependency-order statement in §H.0a) while still
  binding authorization completely into the reviewed input downstream: the
  `ReviewedImportSpecification` carries **both** `review_decision_id` and
  `authorization_context_id` and seals them into `specification_digest` (§H.5), and the
  idempotency key names both (§H.1). Authorization therefore cannot be reused across an
  unrelated decision, and a review decision can never silently change its own downstream
  authorization.
- **Deliberately excluded:** `decision_timestamp` (audit-only, §B.2) and any other
  temporal field — retained on the record as an audit field (and used as the record's
  `created_at`, §F.3) but **never** part of decision identity. Because
  `decision_timestamp` is excluded, **two submissions that differ *only* in
  `decision_timestamp` derive the same `review_decision_id` and are the *same* decision**
  (an idempotent duplicate, not a renewal, not a distinct decision — §D.7, Codex-7): the
  first recorded decision is authoritative and its recorded `decision_timestamp` stands.
  A differing `decision_timestamp` alone never creates a second decision and never a
  second record.
- **Compatibility with the actual Phase 40G model (honest).** Phase 40G owns the
  **assessment** contract only — `MigrationCandidateAssessmentReport` (`report_id`,
  `review_readiness`, `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION`) in
  [`memory_migration_candidate_assessment.py`](../../apps/backend/app/models/memory_migration_candidate_assessment.py).
  There is **no Phase 40G review-*decision* model**; the review decision is a **new
  Phase 40H contract** (§C) that *references* the 40G assessment by `report_id` +
  version. Deriving `review_decision_id` therefore requires **no change to any Phase 40G
  file**. If a future implementation ever needs to change the 40G assessment contract,
  that file is named honestly in the implementation map (§L) — but this derivation does
  not.
- **Renewal / supersession (deterministic discriminator, Codex-7):** a **true renewal**
  is a *new, distinct* decision that carries `supersedes_decision_id` (the predecessor it
  renews) **and** differs from that predecessor in at least one identity-bearing member.
  Normally that discriminator is a changed `content_digest` or `assessment_*` (the usual
  reason review is re-opened, §D.7); when a reviewer must record a genuinely distinct
  re-affirmation with **no other material change**, they increment the explicit
  `renewal_revision` integer, which is itself an identity member and therefore yields a
  **distinct** `review_decision_id`. A copy that changes **only** `decision_timestamp`
  (same `renewal_revision`, same material fields) is **not** a renewal — it is the same
  decision (above). The effective head of a decision line is the newest non-superseded
  decision (§D.7).
- **Duplicate / collision:** two submissions with byte-identical identity members
  (regardless of `decision_timestamp`) derive the same id and are the *same* decision
  (idempotent); a same-id/**different**-canonical-identity-content state is
  `review_decision_collision`, fail closed (§H.0, §J). A differing `decision_timestamp`
  under identical identity members is **not** a collision (the timestamp is not an
  identity member) — it resolves to the recorded decision.
- **Rejected / deferred identity:** `status` is a member, so an `approved`, a `rejected`,
  and a `deferred` decision over the same input have **distinct** ids and never collide.
- **Multiple heads, cycles, missing predecessors:** fail closed as `supersession_tie` /
  `supersession_cycle` / `incomplete_review_provenance` (§D.7) before any insert.

### H.10 `authorization_context_id` and `authorization_context_digest`

Two **separate** derivations over the same grant — an *identity* and a *complete
integrity seal* — kept distinct exactly as `receipt_id` (§H.4) and
`receipt_integrity_digest` (§H.6) are (Codex-5):

- **`authorization_context_id` — identity.** domain `migration-import/authorization-context`
  (an **identity** domain). **members:** `authorization_policy_version`,
  `authorized_project_id`, `authorized_scopes` (sorted set-like, §H.0),
  `project_level_authorized`, `authorizing_principal_id`, `review_decision_id`,
  `candidate_id`, `content_digest`, `assessment_report_id`, `assessment_version`,
  `expires_at` (or explicit null), and `revoked`. **Excludes** `issued_at` (so a re-issued
  identical grant is idempotent and a timestamp never becomes an authorization shortcut)
  and excludes `authorization_context_id`/`authorization_context_digest` themselves. It
  binds `review_decision_id` (authorization → decision) and is therefore **acyclic**
  (§H.0a).
- **`authorization_context_digest` — complete integrity seal.** domain
  `migration-import/authorization-context-integrity` (a distinct **integrity** domain tag,
  with its own schema-version tag, so an identity value and an integrity value can never
  be confused). **members:** **every** `ProjectScopeAuthorizationContext` field
  (§C.3) **except `authorization_context_digest` itself — INCLUDING `issued_at`** and
  including `authorization_context_id`. Because it covers `issued_at`, the completeness
  claim is honest: altering `issued_at`, `expires_at`, `revoked`, `project_level_authorized`,
  any authorized scope, or any binding changes this digest and is detected as
  `authorization_context_integrity_failure` (§C.3, §J), even though such a change does not
  alter `authorization_context_id`.
- **Consistency:** the plan never describes `authorization_context_digest` as "complete"
  while excluding an immutable field; `issued_at` is the one field the earlier draft
  excluded, and it is now inside the digest. `issued_at` is excluded **only** from the
  semantic identity, where its exclusion is justified (audit-only timestamp).

**Distinct-reviewed-input vs conflicting-replay (clarified):** different assessments
or different review decisions over the same bytes form **distinct reviewed inputs**
(distinct idempotency keys, §H.1) that each require their own approval; they are
handled idempotently and, where they share a `record_id`, reuse the existing record
(§G.3). They become a typed **`conflicting_replay`** only when a request collides on a
related key with an existing but **materially different** attempt (e.g., an attempt
already recorded for that key referencing a different content-identity), never a
silent merge.

---

## I. Atomicity, concurrency, coordination, and recovery

This section is written to the hard constraint: **there is no single atomic commit
spanning the durable JSON ledger and the durable Active Memory snapshot.** The plan
does not pretend otherwise. Instead it defines a *recoverable two-artifact protocol*
whose durable reporting commit point is the ledger receipt, bound to the snapshot by a
shared **commit generation**, guarded by **one coordinator lock** and **per-file CAS**,
with an explicit recovery routine and an explicit quarantine.

### I.1 Why cross-store atomicity is not claimed

The migration ledger and the Active Memory snapshot are **two independent durable
files** with **two independent `os.replace` operations**. Two independent durability
domains cannot be committed by one filesystem operation. Any claim of a single atomic
swap covering "attempt + memory record + receipt" would be false. Phase 40H therefore
uses **ordering + a durable intent + a shared generation + recovery**, not fictional
atomicity.

### I.2 Transaction boundary and commit point

The import of one candidate is a *logical* transaction across the two durable
artifacts, ordered so the durable ledger is the authoritative record of the outcome
(the full ordered protocol is §E). In brief:

1. durably record the **intent** (`import_attempt`, `intent_state = intended`, planned
   `target_record_id`, observed `commit_generation`) via the ledger CAS write (§I.5);
2. insert the record into a **private candidate store** (reconstructed off-guard from the
   last validated durable snapshot, §F.2, §E step 16 — **not** the published live store)
   and **durably persist that candidate as the Active Memory snapshot at
   `commit_generation + 1`** (§A.4);
3. durably record the **receipt** and advance the ledger's `commit_generation` to the
   same `+1`, advancing the attempt to `committed`, via the ledger CAS write;
4. after reload-verify, **publish** the validated candidate to the holder as the live store
   (O(1) swap, §A.6) — the point at which the record becomes visible to readers.

**The reporting commit point is step 3 — the durable receipt** — but **visibility is
deferred to step 4** (Codex-2). A receipt is written **after** the snapshot durably
reflects the record at the new generation, so *a committed receipt whose generation
matches the snapshot implies a durable record*. The record is not visible through the
published live store until step 4 succeeds. The converse gap (a durable snapshot at `+1`
with no receipt, and no publish) is exactly the recoverable window §I.7 resolves, and it
reconstructs+publishes the live store from the durable `N+1` snapshot.

### I.3 Shared persisted commit generation

A persisted monotonic integer **`commit_generation`** is recorded in **both** durable
artifacts — the ledger document and the Active Memory snapshot envelope (§A.4).

- **Initialization:** a cold start with **neither** artifact present initializes both
  at `commit_generation = 0` under the coordinator lock. A start with exactly **one**
  present is a torn/absent state → fail closed (`snapshot_missing` or `corrupt_ledger`
  as applicable).
- **Validation:** at startup and at the top of every import (§E steps 2–3), **under
  the coordinator lock**, both artifacts are loaded and their recorded generations
  compared. **Before** applying the equality rule, the single bounded N/N+1 exception
  (§I.3a) is evaluated: if the state is exactly ledger `N` / snapshot `N+1` with a
  durable intent and no receipt, it routes to recovery (§I.7). **Otherwise** the
  generations **must be equal**; any other inequality → `generation_mismatch`, fail
  closed. The exception is checked **ahead of** this rejection, never after it.
- **Increment:** each successful verified import advances the generation by **exactly
  1** — the snapshot is written at `N+1` (step 2) and the ledger receipt/generation is
  written at `N+1` (step 3).
- **Receipt verification rule:** a receipt is **verified only when its linked snapshot
  generation and the ledger generation agree.** A receipt at generation `N+1` over a
  snapshot still at `N` (torn write between steps 2 and 3) is not a verified success —
  it is the recoverable window (§I.7).
- **No false atomicity:** generation equality is a **cross-check that detects a torn
  cross-file write**, not a claim that both files were written atomically. It is what
  makes the two-file protocol *recoverable*, not *atomic*.

`commit_generation` (the shared cross-store epoch) is distinct from `ledger_revision`
(the ledger file's internal lost-update CAS token, §I.5): a single import advances the
ledger `ledger_revision` on each of its ledger writes, and advances the shared
`commit_generation` exactly once.

### I.3a The one allowed N/N+1 uncertain-commit exception (evaluated first)

Ordinary startup and every import entry require **equal** ledger and snapshot
`commit_generation` (§I.3). **Before** that equality rule is applied, recovery must
recognize **exactly one** bounded, well-formed mismatch and route it to the
uncertain-commit recovery entry path (§I.7) instead of rejecting it. This is the
recoverable window created when step 2 (snapshot at `N+1`) succeeded but step 3 (ledger
receipt + generation advance) had not yet committed (§I.2, §I.6 last row).

**The one allowed mismatch — every clause required:**

- the **ledger** generation is `N`;
- the ledger contains the **durable intent** (`import_attempt`, `intent_state =
  intended`) for the reviewed input, complete and valid;
- the **snapshot** generation is exactly `N + 1`;
- the snapshot contains the deterministic `MemoryRecord` the intent planned;
- **no verified receipt** exists for that effect.

Only this exact state is an exception. It is checked **ahead of** the general
`generation_mismatch` rejection so it is reachable at all (a later, blanket
equality-only check would otherwise reject it first). The recovery entry path (§I.7)
performs the full validation before it may finalize; nothing is finalized here.

**Everything else is prohibited and fails closed** (never routed to this exception):
any other generation inequality (including snapshot `< N`, snapshot `> N+1`, or a gap
greater than one), a **missing/invalid intent**, a snapshot record that is **not the
exact deterministic record** the intent planned, any **provenance difference**, an
**unexpected receipt** already present, a **record-identity collision**, or an
`attempt_sequence` inconsistency → `generation_mismatch` / `corrupt_ledger` /
`corrupt_active_memory_snapshot` / `record_identity_collision` / `uncertain_commit_result`
as applicable (§J), and reviewed imports are quarantined where §I.6 requires it. The
allowed exception is a **single `+1` step with a matching durable intent and no
receipt** — nothing wider.

### I.4 The coordinator and its one concrete lock protocol

**One import coordinator (§A.2) owns a single exclusive writer lock** covering the
whole transaction and recovery: ledger reload, snapshot reload, generation validation,
intent persistence, in-memory insertion, snapshot persistence, receipt persistence,
and the reload-and-verify step. Readers (idempotent replay lookup, inspection) do not
take the writer lock and never mutate.

**One concrete, Windows-compatible, dependency-free protocol is selected — not a menu
of alternatives.** The lock is an **atomic exclusive lock-file creation** using the
Python standard library's `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. This
single primitive is atomic-create-or-fail on both Windows and POSIX and needs no third
-party dependency.

> **Not** used, and **not** presented as interchangeable alternatives: `msvcrt.locking`
> (Windows-only byte-range locking) and `fcntl.flock` (POSIX-only advisory locking) are
> explicitly **rejected** for this feature because they are platform-specific and would
> force a divergent two-path implementation. `O_EXCL` create is the one portable
> mechanism chosen; the others are named here only to record that they were considered
> and declined.

- **Owner metadata** (written as the exclusive-create payload, atomically, since the
  file did not previously exist): `owner_pid`, `created_at` (lock creation time, for the
  stale threshold), `host`/`boot_id` where determinable, and **`operation_identity` =
  the stable reviewed-input idempotency key** (§G.1). The idempotency key is known
  *before* an attempt is allocated, so it is a valid operation identity at acquisition.
- **Malformed lock metadata is unambiguous and fails closed.** If an existing lock
  file is present but its payload is **unreadable, truncated, non-JSON, or missing a
  required owner field** (`owner_pid`/`created_at`/`operation_identity`), ownership and
  liveness **cannot be established**, so the lock is treated as **ambiguous, never
  reclaimable** → typed **`malformed_lock_metadata`**, fail closed (no acquire, no
  reclaim, no deletion). Malformed metadata is never treated as "stale and therefore
  reclaimable"; only a *well-formed* payload can ever qualify for the conservative
  stale-reclaim path below.
- **The lock never contains `import_attempt_id` before the attempt exists.** The
  attempt id is allocated *after* the lock is held and the intent is about to be written
  (§E step 14). If desired for observability, the lock payload MAY be **updated
  in-place after attempt allocation** to add `import_attempt_id`, but the lock's
  validity and release never depend on that field — only `owner_pid` +
  `operation_identity` determine ownership.
- **Bounded acquisition:** a configurable **acquisition timeout**, **polling interval**,
  and **maximum attempts**, all env-overridable. On exhaustion the caller receives
  `lock_unavailable` (fail closed, retryable) — the coordinator does not proceed
  concurrently.
- **Stale-lock recovery is conservative and fails closed on ambiguity.** A lock is
  reclaimed **only when both**: (a) the recorded `owner_pid` is **positively validated
  to no longer exist** (POSIX: `os.kill(pid, 0)` semantics; Windows: a stdlib
  `ctypes` `OpenProcess` existence probe — still dependency-free), and the probe is
  **conclusive**; **and** (b) the lock's age exceeds the configured **stale threshold**.
  If process existence **cannot be conclusively determined**, or `host`/`boot_id`
  indicate a different machine/boot than the current one, ownership is **ambiguous** →
  `stale_lock_ambiguous`, fail closed (no reclaim). A conclusively-dead owner past the
  threshold allows a single atomic reclaim (remove-then-`O_EXCL`-create) under audit.
- **Release** removes the lock file **only if the current process still owns it**
  (`owner_pid` + `operation_identity` match), in a `finally`, covering all three paths:
  **success**, **handled failure** (any typed fail-closed result), and **exception**.
  A release that finds a foreign owner does not delete it and logs a safe diagnostic.
- **Release/deletion failure is unambiguous and does not fabricate success.** If the
  owned lock cannot be deleted or released (the `os.remove` raises, or the file is
  already gone, or ownership can no longer be confirmed at release time), the
  coordinator maps it to a typed **`lock_release_failure`** with safe diagnostic
  context (no path echoed): the *operation's own* typed result is unchanged (a verified
  import already durably committed and published, §E steps 18–20, stays verified; a
  fail-closed/quarantine result stays that), but the **release anomaly is surfaced, never
  swallowed**, and a subsequent
  acquirer treats the possibly-orphaned lock through the conservative stale/ambiguous
  rules above (a *foreign* or *malformed* leftover is never force-deleted). Release
  failure never silently leaves a caller believing the lock is cleanly freed.

### I.5 Persisted revision + compare-and-swap (per-file, ledger)

Every **ledger** write is additionally guarded by a persisted monotonic
`ledger_revision`:

- a writer reads the current revision `R` (from disk, under the lock);
- it stages the next document with `R+1`;
- immediately before `os.replace`, it re-reads the on-disk revision and proceeds only
  if it is still `R`; otherwise it aborts with `revision_conflict` (§J).

Atomic replacement alone is **insufficient** because two writers could each read `R`,
each stage `R+1`, and the later replace would clobber the earlier without either
noticing. CAS on the persisted revision detects that lost-update race and refuses it.
The exclusive writer lock (§I.4) is the *primary* mutual exclusion; CAS is
defense-in-depth. **Atomic file replacement alone is explicitly not treated as
sufficient** for either the concurrency guarantee (CAS) or the cross-store guarantee
(shared generation, §I.3).

### I.6 Preparation/persist/publish failure and quarantine

Because the whole import is prepared on a **private candidate store** and the live store
is **published only at the very end** (§E steps 16–20, Codex-2), most failures never touch
the published store at all — the live store simply keeps serving the untouched validated
generation `N`, and the coordinator drops the private candidate. Specifically:

1. **the published live store is never mutated in place** — the record was inserted into
   the private candidate (§E step 16), so there is **no uncommitted live mutation to
   discard**; on any preparation, snapshot-persist, receipt-persist, or reload-verify
   failure the coordinator simply **drops the private candidate** and the published store
   stays at the last validated `N`;
2. **on a failure *after* the durable snapshot at `N+1` but before or during publish**, the
   durable snapshot may already exist at `N+1`; recovery (§I.7) reconstructs a fresh store
   from that durable snapshot and, on a full-checklist pass, **publishes it through the
   holder** (§A.6). Readers observe either the prior validated store or the reconstructed
   replacement, never a partially restored one;
3. **preserve the durable intent** already written at step 14 and **mark the attempt
   `failed` or `uncertain`** as appropriate (below);
4. **never create a verified receipt on a failed path, and never report success on a failed
   `publish`** (a failed publish → `import_service_quarantined`, §E step 20);
5. if a required **reconstruct/validate/publish of the live store fails** (a typed
   `live_store_replacement_failure`, §A.6), **quarantine/disable reviewed imports** (mapped
   to `import_service_quarantined`, §J) until startup recovery succeeds — the holder keeps
   serving the last validated store for read-only access but rejects new reviewed imports
   rather than operating on unknown in-memory state;
6. **return a typed fail-closed result.**

Equivalent behavior for the specific failure modes:

| Failure | What is (un)certain | Action | Attempt state |
| --- | --- | --- | --- |
| **Candidate build/insert/validate failure** (§E step 16) | Nothing durable past the intent; live store untouched at `N`; nothing published | Drop the private candidate; safe to retry | `failed` |
| **Snapshot temp-write failure** (before `os.replace`) | Destination untouched; no `+1` snapshot exists; nothing published | Drop the private candidate; live store still `N`; safe to retry | `failed` |
| **Snapshot replacement failure** (`os.replace` raised) | Destination may or may not have been swapped; nothing published | Drop the candidate; if a valid `+1` snapshot with the planned record is present but no receipt → hand to recovery; else → failed; live store still `N` | `uncertain` if a `+1` snapshot may exist, else `failed` |
| **Ledger receipt-persistence failure** (after snapshot success at `+1`) | Durable record exists at `+1`; no receipt; ledger generation still `N`; nothing published | Leave the intent; on recovery, the `+1` snapshot + matching intent **prove the effect** → finalize by writing the receipt, advancing ledger generation, and **publishing** the reconstructed store (idempotent completion) | `uncertain` → recovery `committed` |
| **Publish (final swap) failure** (§E step 20, after durable `N+1` commit) | Durable truth is `N+1`; live store still published at `N` | Holder raises `live_store_replacement_failure`; **do not report success**; **quarantine** reviewed imports until startup recovery reconstructs+publishes from the durable `N+1` snapshot; keep serving the last validated store for read-only | `committed` durably; operation → `import_service_quarantined` |
| **Live-store reconstruct/publish failure during recovery** (holder cannot restore last-validated durable state) | Authoritative in-memory state is unknown | Holder raises `live_store_replacement_failure`; **quarantine** reviewed imports until startup recovery; keep serving the last validated store for read-only, do not operate on unknown state | `uncertain`; `live_store_replacement_failure` → `import_service_quarantined` |

In every case: **never a verified receipt without a durable snapshot record at the
agreed generation**, **never an imported record visible through the published live store
before it is durably persisted and verified**, and **never a retained live mutation that
never became durable** (the live store is only ever *replaced* by a fully validated
store, never mutated in place).

### I.7 Uncertain-commit recovery (explicit routine, incl. the N/N+1 entry path)

Recovery is an **explicit operation**, not a load-time side effect. It is reached
either when an intent exists without a matching committed receipt (`uncertain_commit`),
or via the **dedicated N/N+1 uncertain-commit recovery entry path** — the single
bounded ledger-`N` / snapshot-`N+1` state (§I.3a) routed here **before** the ordinary
generation-equality rejection. The entry path is a *separate* recovery entry for
exactly that state; it does not weaken the ordinary equality rule for any other state.

**Under the coordinator lock, recovery validates — every check required — before it
may finalize anything:**

1. **reacquires the coordinator lock** (§I.4);
2. **reloads both durable stores** and **validates both artifact envelopes and their
   integrity FIRST** — recomputes and matches the **`ledger_integrity_digest`** (§H.7)
   and the **`snapshot_integrity_digest`** (§H.8), then the per-envelope structure
   (type/domain tag, `schema_version`, `ledger_revision`) and each receipt's recomputed
   `receipt_integrity_digest` (§H.6, §I.8). **No generation value is read or trusted
   until both envelope integrity digests verify** (§I.9); a mismatch is `corrupt_ledger`
   / `corrupt_active_memory_snapshot`, fail closed, and reviewed imports are quarantined
   (§I.6);
3. **only after integrity passes, confirms the generation relationship for the entry
   path is exactly `N+1 = N + 1`** — a gap greater than one, `< N`, or any other
   inequality is **not** the exception and fails closed (`generation_mismatch`, §I.3a);
   the classifier never uses an untrusted generation to authorize recovery;
4. **finds the durable intent** by its **stable idempotency identity** (§G.1) and
   confirms it is **complete and valid** (`intent_state = intended`, planned
   `target_record_id`, observed generation);
5. **locates the deterministic `MemoryRecord` by `record_id`** in the reloaded snapshot
   and confirms the **`record_id` matches** the intent's planned id;
6. **validates complete canonical `MemoryRecord` equality — not `record_id` alone**: the
   located record's **entire** `model_dump(mode="json")` (§F.3, Ruling 4) — every field,
   including the content-identity `metadata.migration_provenance` block and the
   deterministic `created_at`/`observed_at` — must equal the record the intent's
   specification determines; any field difference is `record_identity_collision`;
7. **validates the full reviewed linkage:** candidate, assessment, review decision, the
   **`ReviewedImportSpecification` (`specification_digest`, §C.1)**, and the
   **`ProjectScopeAuthorizationContext` (`authorization_context_id` +
   `authorization_context_digest`, §C.3)** referenced by the intent all resolve, verify,
   and agree (the authorization context is re-checked non-revoked/non-expired and
   correctly bound), and the record's **`supersession_refs` match** the authorized
   specification;
8. **confirms no contradictory attempt or receipt exists** for the key (no second
   materially different attempt, no already-present verified receipt, no
   `record_identity_collision`) and that **`attempt_sequence` remains valid**
   (contiguous, non-duplicate, §G.2);
9. **finalizes only after every check above passes:** recovery **persists the completed
   attempt and the verified receipt** (with a freshly computed `receipt_integrity_digest`
   over the full receipt content, §H.6) at the snapshot's generation, **advances the
   ledger `commit_generation` to `N+1`**, advancing the attempt to `committed` (idempotent
   completion), then **reconstructs the live in-memory store from the durable `N+1`
   snapshot and publishes it through the holder** (§A.6, so the recovered record becomes
   visible exactly as a normal import's step 20 would), and returns success. If that final
   publish fails, it maps to `import_service_quarantined` (the durable state is already
   `N+1`; a subsequent startup/recovery publishes it) — success is not reported until the
   live store reflects `N+1`;
10. **otherwise fails closed — no historical-generation restoration is ever attempted
    (Ruling 6).** Phase 40H retains **only** the current ledger and the current snapshot;
    it keeps **no** multi-generation snapshot history and **no** journal, so there is no
    "last mutually valid generation" to roll back to and the plan never claims one. The
    only recoveries available are therefore: (a) the single forward N/N+1 finalize of
    step 9; and (b) reconstructing the **live in-memory store** from the **currently
    validated durable snapshot** (§A.6) — which is *not* historical-generation
    restoration, only reloading the one retained snapshot. Concretely:
    - planned record **absent** from the snapshot and **no** receipt → mark the attempt
      `failed` (safe retry under a new attempt id); the current validated artifacts are
      left exactly as they are;
    - any linkage/provenance/supersession/attempt-sequence/**integrity** check **fails**,
      or durable state is **unreadable or internally inconsistent** → return the typed
      fail-closed code (`uncertain_commit_result` / `corrupt_ledger` /
      `corrupt_active_memory_snapshot` / `record_identity_collision`) **and quarantine
      reviewed imports** (`import_service_quarantined`) pending **operator repair or a
      future, separately-designed recovery mechanism**;
    - a **proven snapshot-`N+1` effect is never discarded** merely to force generation
      equality, and **neither durable artifact is ever silently rewritten** to guess a
      common generation;
11. **never guesses success.** A committed receipt is only ever produced when the
    durable record provably exists at the agreed generation and **every** check passes;
    every other outcome is either a clean `failed` (safe retry) or a fail-closed
    quarantine, never an invented rollback.

### I.8 Partial-write **detection** (separate from recovery)

Detection is strictly separated from the recovery *action*:

- a crash mid-write leaves only an orphan temp sibling (never the destination); load
  ignores temp siblings and loads the last good file;
- **load-time integrity scan (detection only), envelope integrity checked FIRST:** the
  whole-ledger **`ledger_integrity_digest` (§H.7)** and the whole-snapshot
  **`snapshot_integrity_digest` (§H.8)** are recomputed and matched **before any
  contained value (including either `commit_generation`) is trusted** — a mismatch is
  `corrupt_ledger` / `corrupt_active_memory_snapshot`. Then: every receipt must reference
  an existing `import_attempt`, a `record_id`, a `specification_digest`, an
  `authorization_context_id`, and a `commit_generation`; `ledger_revision` and the
  per-key `attempt_sequence` must be self-consistent and contiguous; the snapshot must
  validate structurally and per-record; the two artifacts' generations must agree (or be
  the one bounded N/N+1 exception, §I.3a, evaluated **only after** both envelope digests
  verify); each receipt's recomputed `receipt_id` (§H.4) must match its stored one; and
  each receipt's recomputed **`receipt_integrity_digest` (§H.6) — covering the complete
  immutable content including both `attempt_timestamp` and `verification_timestamp`** —
  must match its stored one, so tampering with either timestamp or any other content
  field is detected. Violations are *reported*, never auto-fixed, as
  `partial_write_detected`, `corrupt_ledger`, `corrupt_active_memory_snapshot`,
  `snapshot_missing`, `generation_mismatch`, `missing_linked_attempt`,
  `missing_linked_memory_record`, or `receipt_integrity_failure` (§J). The load **fails
  closed** on any violation.
- detection **does not** claim recovery. Turning a detected anomaly into a resolved
  state is only ever done by the explicit §I.7 routine under the writer lock. A load
  that detects a problem reports it and refuses; it does not silently repair.

> A committed, verified receipt must never exist unless its exact resulting Active
> Memory record exists and resolves in the snapshot **at the agreed commit
> generation**. This is the core invariant, enforced at commit (ordering + durable
> snapshot before receipt + shared generation, §I.2/§I.3) and re-checked at load
> (detection scan, §I.8), with ambiguity resolved only by explicit recovery (§I.7).

### I.9 Envelope integrity validation points and the exhaustive generation-state table

**When both envelope integrity digests (§H.7, §H.8) are recomputed and matched:** at
**startup**; **before every ordinary import** (§E step 2); **before N/N+1 recovery
classification** (§I.3a — the classifier is unreachable until integrity passes);
**during recovery** (§I.7 step 2); **after every persistence step** that rewrites an
envelope (the writer re-reads and verifies what it wrote); and **during the
reload-and-verify** step (§E step 19). A mismatch **fails closed** with the applicable
`corrupt_ledger` / `corrupt_active_memory_snapshot` code and **quarantines** reviewed
imports (§I.6). **The N/N+1 path may inspect generation values only after both envelopes
pass structural and integrity validation; it never uses an untrusted generation to
authorize recovery.**

**Exhaustive durable-generation state behavior (after both envelope integrity digests
verify).** Only the single forward N/N+1-with-intent state is recoverable; every other
state fails closed. There is no historical-generation restoration (Ruling 6).

| Durable state | Classification | Action |
| --- | --- | --- |
| **Missing snapshot** (ledger present) | torn/absent | `snapshot_missing`, fail closed, quarantine |
| **Missing ledger** (snapshot present) | torn/absent | `corrupt_ledger`, fail closed, quarantine |
| **Neither present** (cold start) | fresh | initialize **both** at `commit_generation = 0` under the lock (not an error) |
| **Corrupt snapshot** (integrity/structure/per-record) | corruption | `corrupt_active_memory_snapshot`, fail closed, quarantine; no generation trusted |
| **Corrupt ledger** (integrity/structure/`attempt_sequence`) | corruption | `corrupt_ledger`, fail closed, quarantine; no generation trusted |
| **Ledger `N` / snapshot `N`** | consistent | normal steady state; proceed |
| **Ledger `N` / snapshot `N+1` + exact durable intent + no receipt** | the one recoverable window (§I.3a) | route to §I.7 forward-finalize; on full-checklist pass, write receipt + advance ledger to `N+1`; else `failed` (safe retry) or fail-closed quarantine |
| **Ledger `N+1` / snapshot `N`** | receipt-ahead-of-effect (never allowed by ordering) | `generation_mismatch`, fail closed, quarantine — the effect is not proven durable; **snapshot is never rewritten** to force equality |
| **Gap > 1** (either direction) | not the bounded exception | `generation_mismatch`, fail closed, quarantine |
| **Invalid generation values** (non-int, negative, unreadable) | corruption | `corrupt_ledger` / `corrupt_active_memory_snapshot`, fail closed, quarantine |
| **Equal generations but mutually inconsistent artifacts** (e.g. a receipt whose `record_id` is absent from the snapshot) | corruption | the specific code (`missing_linked_memory_record`, etc.), fail closed |

In no case is a proven snapshot-`N+1` effect discarded to force equality, and in no case
is either durable artifact silently rewritten to guess a common generation. Recovery of
the *live in-memory store* is only ever a reload of the **currently validated durable
snapshot** (§A.6), never a synthesized historical generation.

---

## J. Diagnostics and information safety

Typed, closed-vocabulary diagnostic codes (severity fixed per code, following the
Phase 40E/40F/40G pattern where a caller cannot downgrade a finding). Names are
normalized to the canonical taxonomy below.

| Code | Trigger | Disposition |
| --- | --- | --- |
| `stale_candidate` | Candidate id/provenance no longer matches the reviewed decision | fail closed |
| `changed_digest` | Recomputed candidate digest ≠ reviewed digest | fail closed |
| `changed_assessment` | Assessment id/version ≠ reviewed assessment | fail closed |
| `missing_review` | No review decision for the tuple | fail closed |
| `incomplete_review_provenance` | Decision missing required reviewer/timestamp/reason/evidence, or a dangling intra-ledger reference (incl. a missing `supersedes_decision_id` predecessor) | fail closed |
| `rejected_candidate` | Effective decision is `rejected` | fail closed (no mutation) |
| `deferred_candidate` | Effective decision is `deferred` | fail closed (no mutation) |
| `stale_approval` | Approved decision whose candidate digest or assessment no longer matches the present input, or which has been superseded | fail closed (no mutation) |
| `contradictory_evidence` | Approval contradicts assessment verdict or points at a different candidate | fail closed |
| `missing_reviewed_specification` | **(precedence 1)** An approved candidate presented with **no** `ReviewedImportSpecification` (§C.1) | fail closed |
| `invalid_reviewed_specification` | **(precedence 2 — model layer)** Specification/claim structurally invalid: `extra="forbid"`, missing required field, blank subject/predicate/value, over-bound value, a `value_kind`/`target_kind`/`source_type` **not a valid enum member**, or a timezone-naive/malformed `observed_at` — pure contract failures the model raises **before** any semantic check | fail closed |
| `specification_integrity_failure` | **(precedence 3)** Recomputed `specification_digest` (§H.5) ≠ stored — a specification (incl. its claim/kind/`observed_at`) **altered after review**; checked before semantics | fail closed |
| `specification_binding_mismatch` | **(precedence 4)** Specification candidate/digest/assessment/`review_decision_id` ≠ the reviewed decision | fail closed |
| `unauthorized_project_scope` | **(precedence 5 — authorization)** Specification `project_id` ≠ the context's `authorized_project_id`, **or** a `scope` that is **not an exact member** of `authorized_scopes` (§C.3; any non-member, regardless of any human notion of broader/narrower — no hierarchy exists), **or** an absent scope without `project_level_authorized` | fail closed |
| `kind_claim_incompatible` | **(precedence 6 — policy layer)** A structurally valid, integrity-intact, correctly-bound, authorized specification whose `(target_kind, claim)` violates the closed versioned kind↔claim policy (§C.2): a valid-member kind with **no policy rule** (unmapped kind), a valid-member `value_kind` **outside** the kind's permitted set, or an unrecognized `kind_claim_policy_version`. **Never** overlaps `invalid_reviewed_specification` (structural failures resolve at precedence 2) | fail closed |
| `missing_authorization_context` | An approved candidate/specification presented with **no** `ProjectScopeAuthorizationContext` (§C.3) | fail closed |
| `authorization_context_integrity_failure` | Recomputed `authorization_context_digest` (§H.10) ≠ stored — altered/stale authorization context | fail closed |
| `authorization_context_revoked` | The authorization context's `revoked` flag is set | fail closed |
| `authorization_context_expired` | The authorization context's `expires_at` precedes the decision/import time | fail closed |
| `authorization_context_mismatch` | Authorization context bound to a different project/decision/candidate/assessment than the specification (incl. cross-project) | fail closed |
| `supersession_tie` | Two distinct records/decisions would become active heads of one logical line with identical ordering keys | fail closed |
| `supersession_cycle` | Proposed supersession links would close a cycle in the supersession graph | fail closed |
| `duplicate_replay` | Same idempotency key as an existing committed receipt | return the **exact stored receipt** (idempotent) |
| `conflicting_replay` | Same digest under a different assessment/decision colliding with a materially different existing attempt | fail closed (distinct input) |
| `record_identity_collision` | A matching `record_id` whose **complete** canonical `MemoryRecord.model_dump(mode="json")` (§F.3, Ruling 4) does **not** match — any single field differs | fail closed |
| `review_decision_collision` | Two review decisions share a `review_decision_id` (§H.9) but differ in canonical content | fail closed |
| `canonical_identity_collision` | Any other same-identifier/different-canonical-content condition not covered by a more specific collision/integrity code (§H.0) | fail closed |
| `lock_unavailable` | The exclusive writer lock is held by another live owner within the bounded acquisition budget | fail closed (retryable) |
| `stale_lock_ambiguous` | A lock whose owner liveness cannot be conclusively determined, or from a different host/boot | fail closed (no reclaim) |
| `malformed_lock_metadata` | An existing lock file's payload is unreadable/truncated/non-JSON or missing a required owner field — ownership/liveness cannot be established | fail closed (no reclaim, never treated as stale) |
| `lock_release_failure` | An owned lock could not be deleted/released cleanly; the anomaly is surfaced, never swallowed (§I.4) | fail closed (surfaced; operation's own typed result unchanged) |
| `revision_conflict` | The persisted `ledger_revision` changed under a writer (CAS failure) | fail closed (retryable) |
| `generation_mismatch` | Ledger and Active Memory snapshot `commit_generation` disagree in any way **other than** the one bounded N/N+1 recovery exception (§I.3a), which is routed to recovery first | fail closed |
| `snapshot_missing` | Expected Active Memory snapshot absent when its counterpart ledger state exists | fail closed |
| `corrupt_active_memory_snapshot` | Snapshot **`snapshot_integrity_digest` (§H.8) mismatch**, structurally invalid, or fails per-record contract validation | fail closed |
| `corrupt_ledger` | Ledger **`ledger_integrity_digest` (§H.7) mismatch**, structurally invalid, or internally inconsistent (incl. non-contiguous `attempt_sequence`) | fail closed |
| `persistence_failure` | Ledger or snapshot load/save failed (bounded, typed) | fail closed |
| `partial_write_detected` | Load-time scan found an incomplete/interrupted write (detection only) | fail closed; hand to explicit recovery |
| `missing_linked_attempt` | A receipt references an `import_attempt_id` that does not exist | fail closed |
| `missing_linked_memory_record` | A receipt's `record_id` does not resolve in the Active Memory snapshot | fail closed |
| `receipt_integrity_failure` | A receipt's recomputed `receipt_id` (§H.4) **or** its recomputed full-content `receipt_integrity_digest` (§H.6, covering both `attempt_timestamp` and `verification_timestamp`) disagrees with its stored value | fail closed |
| `uncertain_commit_result` | Intent exists without a matching committed receipt and durable state cannot determine the outcome | fail closed; resolved only by §I.7 recovery, never reported as success |
| `live_store_replacement_failure` | The `AuthoritativeActiveMemoryStoreHolder` could not atomically reconstruct/validate/swap the live store (§A.6) | fail closed; mapped to `import_service_quarantined` |
| `import_service_quarantined` | Safe reload/replacement of durable state failed; reviewed imports are disabled until startup recovery succeeds (read-only access still served from the last validated store) | fail closed (service disabled) |

**Information safety (reused Phase 40E/40F/40G rule):** diagnostics carry closed-enum
literals, counts, and record-local identifiers/digests (non-reversible hashes) only.
They **never** leak filesystem paths (ledger, snapshot, or lock-file locations),
database internals (there is no DB), credentials, raw exception strings/tracebacks,
candidate body text, exported conversation content, PIDs beyond a bounded owner marker,
or declared paths. Digests are hashes, not content. A path that appears in a raw
`OSError` is mapped to a typed `persistence_failure` with no path echoed.

---

## K. Test matrix

Layers: **C** = contract/model tests, **S** = service/coordinator tests (over a temp
ledger + temp snapshot + injected in-memory Active Memory store), **A** =
adapter/persistence tests (ledger, snapshot, lock), **I** = cross-store integration
tests (coordinator + real `InMemoryActiveMemoryStore` + real snapshot store + real lock),
**R** = regression over existing Phase 40E–40G and Phase 37B/37C suites. All are backend
`pytest`. No network, no real Active Memory activation, hermetic temp-dir artifacts
(Phase 39B convention: `HIVEMIND_MIGRATION_IMPORT_PATH` /
`HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` overrides / injected paths so no developer
profile is touched).

| # | Case | Layer | Expected result |
| --- | --- | --- | --- |
| 1 | Approved candidate imports exactly once | S/I | one receipt, one `record_id` resolvable in the snapshot, idempotent on replay |
| 2 | Rejected candidate never mutates memory | S | `rejected_candidate`, zero records inserted |
| 3 | Deferred candidate never mutates memory | S | `deferred_candidate`, zero records inserted |
| 4 | Changed candidate bytes invalidate approval | S | `changed_digest`, fail closed, no insert |
| 5 | Changed assessment invalidates approval / requires renewed review | S | `changed_assessment`, fail closed |
| 6 | Duplicate request returns the **exact stored receipt** | S/I | same `receipt_id` + `record_id`, byte-identical receipt, no second record |
| 7 | Concurrent duplicate requests cannot create duplicate records | A/I | exclusive lock + CAS: exactly one record; loser → winner's receipt |
| 8 | Stale writer loses CAS | A | `revision_conflict`; stale write refused; last good ledger intact |
| 9 | Exclusive writer lock enforced; bounded timeout | A | second writer gets `lock_unavailable` within the acquisition budget; never concurrent mutation |
| 10 | Stale lock: conclusively-dead owner past threshold reclaimed; ambiguous owner refused | A | dead+stale → single reclaim; inconclusive/other-host → `stale_lock_ambiguous`, no reclaim |
| 11 | Distinct `import_attempt_id` per retry; stable idempotency key; attempt-sequence integrity | S/C | `attempt_sequence` 1,2,3… contiguous per key; gap/dup → `corrupt_ledger`; one stable key; one committed receipt |
| 12 | Canonical identity serialization + domain separation + §H.0 rules | C | idempotency/attempt/record/receipt/specification/receipt-integrity/ledger-integrity/snapshot-integrity/review-decision/authorization values stable, sorted-key UTF-8 NFC canonical JSON, domain-tagged (identity vs integrity domains distinct); null-vs-absent, set-like sorting, authored-order lists, no-path, lowercase-hex all honored; claim value/summary whitespace+case preserved exactly; cross-domain collisions impossible; no timestamps in any *identity* except the record's own `created_at`/`observed_at`; both timestamps in the *integrity* digests |
| 13 | Provenance mapping: record carries **content-identity tier only**; audit is ledger-only; `observed_at` source | C/S | record `metadata.migration_provenance` = candidate/digest/assessment **only**; `review_decision_id`/`specification_digest`/`authorization_context_id`/`idempotency_key`/`evidence_references`/`import_attempt_id`/`attempt_sequence`/`renewal_revision` are **absent from the record** and present in the ledger; kind/claim/project/scope from the specification (§C.1); `source_type = IMPORTED_DOCUMENT`; `created_at = decision_timestamp` and `observed_at =` the specification's reviewer-authored `observed_at` (or `None`) — **never derived from `decision_timestamp` or a clock, kept distinct** (§F.3, Codex-6); exact replay reproduces the same `record_id`; a changed spec `observed_at` yields a **distinct** `specification_digest` **and** `record_id`; no Phase 37B model change |
| 14 | Duplicate `record_id` with **complete** canonical equality reuses the record | S/I | already-inserted case: complete `model_dump` equality → one record, second receipt referencing it |
| 15 | Any single differing field under the same `record_id` | S/I | mutate each of `kind`/`claim`/`project_id`/`scope`/`source`/standing/`supersession_refs`/`created_at`/`observed_at`/`metadata` individually → `record_identity_collision`, fail closed |
| 16 | Receipt contract fields present; identity separated from full-content integrity | C | all §B.3 fields; `receipt_id` (§H.4) stable across differing timestamps; `receipt_integrity_digest` (§H.6) recomputes and verifies over the complete content including both timestamps |
| 17 | Receipt references the exact resulting `record_id` | C/S | link resolves in the snapshot; forged/dangling link rejected |
| 18 | Receipt with missing linked attempt detected | A | `missing_linked_attempt`, fail closed |
| 19 | Receipt with missing linked memory record detected | A/I | `missing_linked_memory_record`, fail closed |
| 20 | Receipt integrity failure detected (incl. either-timestamp tamper) | A | altering `attempt_timestamp`, `verification_timestamp`, or any other immutable field → recomputed `receipt_integrity_digest` (§H.6) mismatch → `receipt_integrity_failure`, fail closed |
| 21 | Corrupt / internally inconsistent ledger detected | A | `corrupt_ledger`, fail closed, no silent repair |
| 22 | Partial write detected (not "recovered") at load | A | `partial_write_detected`; temp sibling ignored; last good file loads; no success claimed |
| 23 | Snapshot path + environment override honored | A | `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` wins; side-effect-free resolution |
| 24 | Initial startup load (cold start) | I | neither artifact present → both initialized at generation 0 under the lock |
| 25 | Missing or corrupt snapshot | A/I | `snapshot_missing` / `corrupt_active_memory_snapshot`, fail closed |
| 26 | Shared-generation mismatch | A/I | ledger and snapshot generations disagree → `generation_mismatch`, fail closed |
| 27 | Failure during private-candidate prep / before snapshot durability | I | no verified receipt; **published live store never mutated** (still `N`); private candidate dropped; attempt `failed`; nothing ever became visible (Codex-2) |
| 28 | Publish is last; no pre-durability visibility | I | a reader concurrent with an import in flight sees generation `N` (old validated store) until the durable `N+1` snapshot+receipt+reload-verify all pass **and** `publish` swaps; it **never** observes the imported record before durability; a publish failure after durable `N+1` → quarantine (no false success), later reconstructed from the `N+1` snapshot |
| 29 | Quarantine when reload fails | I | `import_service_quarantined`; reviewed imports disabled until startup recovery |
| 30 | Interrupted snapshot temp write | A/I | destination untouched; drop the private candidate; published live store still `N`; safe retry |
| 31 | Interrupted snapshot replacement | A/I | uncertain if `+1` may exist → recovery; else failed; never false success |
| 32 | Receipt persistence failure after snapshot success | I | `+1` snapshot + intent prove effect → recovery finalizes receipt (idempotent) |
| 33 | Uncertain commit — record present, no receipt → recovery finalizes | I | §I.7 writes receipt at snapshot generation, returns stored success, idempotent |
| 34 | Uncertain commit — record absent, no receipt → recovery fails safe | I | attempt marked `failed`, safe retry; no false success |
| 35 | Uncertain commit — durable state unreadable/inconsistent → typed fail-closed + quarantine | I/A | `uncertain_commit_result` / `corrupt_*`; **no historical-generation restoration attempted**; reviewed imports quarantined pending operator repair; never reported as success |
| 36 | Uncertain recovery validates exact record equality, not `record_id` alone | I | recovery rejects a `record_id` match whose content-identity/provenance differs |
| 37 | No cross-store atomicity is claimed/relied on | I | interrupting between snapshot and receipt is recoverable via shared generation, not silently committed |
| 38 | Prohibited `INACTIVE → SUPERSEDED` behavior is never invoked | S/I | import path never calls `transition_lifecycle`; supersession expressed via `supersession_refs` only |
| 39 | `supersession_refs` behavior against the actual store | I | new record's `SUPERSEDES` link authored on the newer record; prior record stays `INACTIVE`; `SUPERSEDED_BY` derived, never stored |
| 40 | Deterministic record supersession ordering | S/C | total order over (decision_timestamp, record_id); `attempt_sequence` not used |
| 41 | Record supersession tie rejected | S | `supersession_tie`, fail closed |
| 42 | Record supersession cycle rejected | S | `supersession_cycle`, fail closed, nothing persisted |
| 43 | Independent review-decision supersession via `supersedes_decision_id` | S/C | decision lineage ordered by explicit predecessor link; `attempt_sequence` not used |
| 44 | Review lineage: multiple heads, ties, missing predecessors, cycles | S | `supersession_tie` / `incomplete_review_provenance` / `supersession_cycle`, fail closed |
| 45 | Superseded approval cannot authorize import | S | `stale_approval`, no insert |
| 46 | Missing reviewer fails validation | C | decision cannot be constructed |
| 47 | Missing reason fails validation | C | decision cannot be constructed |
| 48 | Missing evidence fails validation | C | decision cannot be constructed (≥1 required) |
| 49 | Missing timestamp fails validation | C | decision cannot be constructed |
| 50 | Contradictory review evidence fails closed | S | `contradictory_evidence`, no insert |
| 51 | Conflicting replay (same digest, different assessment/decision, materially different attempt) | S | `conflicting_replay`, fail closed |
| 52 | Approval boolean alone does not authorize | S | a decision reduced to `status` only fails validation/preconditions |
| 53 | Imported record standing is INACTIVE + UNVERIFIED | I | inserted record carries the conservative standing; never auto-active |
| 54 | Diagnostics leak no path/secret/raw content | S | planted sensitive values never appear in any diagnostic |
| 55 | Full cross-store startup and recovery integration | I | startup loads+validates both stores under the lock; recovery resolves the uncertain window end-to-end |
| 56 | Existing Active Memory store contracts remain regression-clean | R | Phase 37B/37C suites unchanged and passing; `MemoryStore` seam unmodified in behavior |
| 57 | Existing Phase 40E–40G contracts remain regression-clean | R | 40E/40F/40G suites unchanged and passing |
| 58 | Full backend suite passes during implementation | R | green (baseline count + new Phase 40H tests) |
| 59 | Candidate carries no kind/claim/project; specification supplies them | C | `MemoryMigrationCandidate` exposes no `kind`/`claim`/`project_id`; the constructed `MemoryRecord`'s kind/claim/project/scope derive **only** from the `ReviewedImportSpecification`; coordinator never infers |
| 60 | Missing / invalid / mis-bound / unauthorized / stale specification; **diagnostic precedence** | S/C | `missing_reviewed_specification` / `invalid_reviewed_specification` / `specification_binding_mismatch` / `unauthorized_project_scope` / `specification_integrity_failure`, each fail closed; **fixed precedence (Codex-8):** missing → structural(`invalid`) → integrity(`specification_integrity_failure`) → binding → authorization → kind/claim policy; a specification that is simultaneously structurally invalid *and* kind/claim-incompatible yields `invalid_reviewed_specification` (structural wins); an altered-after-review spec yields `specification_integrity_failure` (not `kind_claim_incompatible`) |
| 61 | Distinct specifications for one candidate are distinct reviewed inputs | S/I | different `target_kind`/`claim`/`project` → different `specification_digest` → different idempotency key **and** different `record_id`; two records, two receipts; materially different collision → `conflicting_replay` |
| 62 | Idempotency key + `record_id` bind the exact specification | C | key includes `specification_digest` (§H.1); `record_id` covers specification record content (§H.3); re-presenting the same specification is idempotent |
| 63 | N/N+1 recovery exception is evaluated **before** ordinary generation equality | I | ledger `N` / snapshot `N+1` / intent present / no receipt is routed to §I.7 recovery; the general `generation_mismatch` rejection never fires first for this state |
| 64 | Every other generation inequality fails closed (not the exception) | A/I | gap > 1, snapshot `< N` or `> N+1`, missing/invalid intent, non-exact record, provenance/supersession diff, unexpected receipt, or bad `attempt_sequence` → `generation_mismatch` / `corrupt_*` / `record_identity_collision` / `uncertain_commit_result`, never finalized |
| 65 | N/N+1 recovery finalize validates the full checklist | I | §I.7 finalizes only after envelopes/integrity, `N+1 = N+1`, intent, `record_id`, complete record equality, provenance, candidate/assessment/decision/specification linkage, supersession, no contradictory attempt/receipt, and `attempt_sequence` all pass |
| 66 | Holder `publish` replacement: readers observe prior or replacement, never partial | I | during `publish`, concurrent readers see either the last validated store or the fully reconstructed/validated replacement; no partially restored store and no pre-durability record is ever observed |
| 67 | Holder quarantine behavior | I | `live_store_replacement_failure` → `import_service_quarantined`; new reviewed imports rejected; unrelated read-only access still served from the last validated store; cleared only after locked startup/recovery validation |
| 68 | Same-process multithreading: holder in-process guard + filesystem lock | A/I | concurrent same-process threads serialized by the holder's in-process synchronization seam **and** the `O_EXCL` lock; exactly one record; no partial read; no double write |
| 69 | Malformed lock metadata never reclaimed | A | unreadable/truncated/missing-owner lock payload → `malformed_lock_metadata`, fail closed, no reclaim, no deletion |
| 70 | Lock release/deletion failure surfaced, not swallowed | A | an owned lock that cannot be released → `lock_release_failure` surfaced; the operation's own committed/fail-closed result unchanged; a foreign/malformed leftover is never force-deleted |
| 71 | Kind↔claim policy: every permitted `(kind, value_kind)` pairing accepted | C | all six kinds × their §C.2 permitted `value_kind` sets validate |
| 72 | Kind↔claim policy: every invalid pairing rejected | C | each `value_kind` outside a kind's set → `kind_claim_incompatible`, fail closed |
| 73 | Kind↔claim policy: unsupported/unmapped kind + malformed claim + policy-version mismatch; **non-overlap** | C | a valid-member `MemoryRecordKind` with no policy rule (unmapped kind), a valid-member `value_kind` outside the kind's set, and an unrecognized `kind_claim_policy_version` → `kind_claim_incompatible`; a **non-member** `value_kind`/`target_kind`, missing triple field, or `extra` field → `invalid_reviewed_specification` (structural, at the model, before policy) — the two codes never both fire for one input (Codex-8) |
| 74 | Authorization context: valid grant authorizes exact project + **exact-member** scope; project-level | S/C | `project_id == authorized_project_id` **and** `scope` an exact member of `authorized_scopes` accepted; a scope-less spec accepted **iff** `project_level_authorized`; import proceeds; **no hierarchy is ever consulted** (§C.3, Codex-4) |
| 75 | Authorization context: project mismatch / non-member scope / absent scope | S | cross-project → `authorization_context_mismatch`; a `scope` that is **not an exact member** (whether a human would call it broader or narrower) → `unauthorized_project_scope`; absent scope without `project_level_authorized` → `unauthorized_project_scope`; project and scope checks are independent |
| 76 | Authorization context: missing / altered (incl. `issued_at`) / revoked / expired; duplicate/malformed scopes | S/C | `missing_authorization_context` / `authorization_context_integrity_failure` (**including a tampered `issued_at`**, Codex-5) / `authorization_context_revoked` / `authorization_context_expired`, each fail closed; duplicate `authorized_scopes` members de-duplicated (digest unchanged), empty scopes valid only with `project_level_authorized` |
| 77 | Authorization context: repository location is never authorization | S | a request with no valid context is refused regardless of which repo the process runs in |
| 78 | Ledger envelope integrity: alter every field individually | A | mutate `commit_generation`, `ledger_revision`, any decision/attempt/intent/receipt/provenance member → recomputed `ledger_integrity_digest` (§H.7) mismatch → `corrupt_ledger`, fail closed |
| 79 | Snapshot envelope integrity: alter generation or any record | A | mutate `commit_generation` or any record → recomputed `snapshot_integrity_digest` (§H.8) mismatch → `corrupt_active_memory_snapshot`, fail closed |
| 80 | Envelope integrity verified before any generation value trusted | I/A | a snapshot with a tampered generation but stale digest is rejected on integrity **before** N/N+1 classification runs; untrusted generation never authorizes recovery |
| 81 | `import_attempt_id`/`attempt_sequence` absent from authoritative record; retry stability | S/I | constructed record and `record_id` identical across retries; the record never contains attempt/decision/authorization audit; the receipt links by `record_id` only |
| 82 | `review_decision_id` derivation (§H.9): members, renewal, timestamp-only, rejected/deferred, collision, **acyclicity** | C | id binds policy-version/reviewer/status/reason/candidate/digest/assessment/evidence/predecessor/`renewal_revision`; **`decision_timestamp` and any `authorization_context_id` excluded** (a copy differing only in `decision_timestamp` is the *same* decision — idempotent, not a renewal); an incremented `renewal_revision` yields a distinct id; rejected vs approved distinct; same-id/different-identity-content → `review_decision_collision`; the review→authorization graph is verified **acyclic** (authorization references the decision, never the reverse, §H.0a) |
| 83 | Review lineage cycles/heads/missing predecessors under `review_decision_id` | S | `supersession_cycle` / `supersession_tie` / `incomplete_review_provenance`, fail closed |
| 84 | Exhaustive generation-state table (§I.9) | I/A | each row (missing/corrupt/`N`-`N`/`N`-`N+1`/`N+1`-`N`/gap>1/invalid/inconsistent) yields its mapped outcome; only the one N/N+1-with-intent state finalizes forward |
| 85 | No historical-generation restoration (Ruling 6) | I | unrecoverable states quarantine; no rollback to a non-retained generation; proven `N+1` effect never discarded; neither artifact silently rewritten |
| 86 | Holder never leaks a raw store (no caller callbacks); lock acquisition/release failure at both layers | A/I | every holder operation returns a record/copy/collection/scalar/`None`, **never** an `InMemoryActiveMemoryStore`; there is **no** `read(fn)`/`mutate(fn)` callback surface and a caller cannot obtain, retain, or mutate the live store outside `publish` (Codex-3); the only mutation is `publish(validated_store)`; filesystem-lock-then-write-guard order; release reverse order; acquisition/release failure at either layer surfaced, no partial swap |

The full backend suite MUST pass during the implementation phase; these cases are
authored then, not now.

---

## L. Implementation map (mandatory, smallest credible; not implemented in this phase)

Tightly bounded and independently auditable. This is a **three-store** integration
(ledger + Active Memory snapshot + in-memory Active Memory store) **reached through a
mandatory live-store holder**, so the map names the **existing modules Phase 40H must
exercise or integrate with**, not only net-new files. The map is **mandatory** — the
`ReviewedImportSpecification` contract, the `ActiveMemorySnapshotStore`, the
`AuthoritativeActiveMemoryStoreHolder`, and the lock protocol are **committed
components, not conditional fallbacks**. Nothing below is written during planning.

| File | New/Mod | Responsibility | Preserves / integrates |
| --- | --- | --- | --- |
| `apps/backend/app/models/memory_migration_import.py` | New | `memory-migration-import.v1` **workflow** contracts only: review decision (with `review_policy_version`, `supersedes_decision_id`, **`renewal_revision`**, §C/§D7), evidence reference, the **`ReviewedImportSpecification`** (§C.1: `target_kind`, complete structured `claim`, reviewer-authored **`observed_at`**, `kind_claim_policy_version`, validated `project_id`, optional exact-member `scope`, `authorization_context_id`/`authorization_context_digest`, `source_type = IMPORTED_DOCUMENT`, source/provenance, supersession refs, `specification_digest`), the **`ProjectScopeAuthorizationContext`** (§C.3, incl. `authorized_scopes` set + **`project_level_authorized`** + `issued_at`), the named **`KindClaimCompatibilityValidator`** + `KIND_CLAIM_COMPATIBILITY_POLICY_VERSION` policy (§C.2, pure, precedence-owned), the named **`ProjectScopeAuthorizationValidator`** (§C.3, pure, **exact set membership, no hierarchy**), the **acyclic** identity helpers — `review_decision_id` (§H.9, **excludes `authorization_context_id`**), `authorization_context_id` (§H.10, excludes `issued_at`) and `authorization_context_digest` (§H.10, **includes `issued_at`**) — per the §H.0a dependency order, import attempt (`attempt_sequence`, `intent_state`, observed `commit_generation`), receipt (§B.3, incl. `commit_generation`, `verification_status`, both timestamps, `specification_digest`, authorization ids, and the full-content **`receipt_integrity_digest`**), `MigrationProvenance` sub-model (**content-identity tier only**, §F.3), `commit_generation`/`ledger_revision` types, canonical identity/integrity helpers + domain tags for **all eleven values** (§H.1–§H.10, split `authorization_context_id`/`_digest`, incl. `ledger_integrity_digest`/`snapshot_integrity_digest`), the shared **§H.0 canonicalizer**, closed diagnostic taxonomy (§J), ledger + snapshot **envelope** documents (with type tags + integrity digests). `extra="forbid"`, pinned versions. **Does not redefine `MemoryRecord`; references its `kind`/`claim`/`project_id`/`scope`/`observed_at`/enums, which the candidate does not carry. No Phase 40G contract change (the review *decision* is Phase-40H-owned; 40G owns only the assessment).** | Phase 40E/40F/40G contracts; the `MemoryRecord`/`MemoryClaim`/`MemoryRecordKind`/`MemoryScope` types (read-only); **references** (not copies of) `MemoryRecord.record_id` |
| `apps/backend/app/services/memory_migration_import_store.py` | New | Durable **ledger** adapter: versioned-JSON ledger, OS-path resolution + `HIVEMIND_MIGRATION_IMPORT_PATH` override, bounded load with typed failures, atomic append-with-CAS write (§I.5), `commit_generation` on the ledger doc (§I.3), **`ledger_integrity_digest` seal + verify (§H.7)**, load-time integrity **detection** scan (§I.8, §I.9). | Phase 39B `RepositoryWorkspaceConfigService` persistence pattern (path resolution, atomic temp-swap, typed errors) |
| `apps/backend/app/services/active_memory_snapshot_store.py` | New (**mandatory**) | Durable **Active Memory snapshot** owner (§A.4): serialize/load/validate/atomic-replace over the existing `InMemoryActiveMemoryStore.serialize()`/`restore()`; `active-memory-snapshot.v1` envelope carrying `commit_generation` + **`snapshot_integrity_digest` seal + verify (§H.8)**; path resolution + `HIVEMIND_ACTIVE_MEMORY_SNAPSHOT_PATH` override; startup load; typed failures (`snapshot_missing`, `corrupt_active_memory_snapshot`, `generation_mismatch`, `persistence_failure`, `partial_write_detected`). **Wraps, never rewrites, the store; never re-homes records into the ledger.** | Phase 37C serialize/restore boundary; Phase 39B atomic-write pattern |
| `apps/backend/app/services/migration_import_lock.py` | New | The **single** exclusive lock-file protocol (§I.4): `os.O_CREAT | os.O_EXCL | os.O_WRONLY` atomic create, owner metadata (`owner_pid`, `created_at`, `operation_identity` = idempotency key, host/boot), bounded acquire (timeout/poll/max-attempts), conservative stale detection with positive PID-absence validation (stdlib only), ownership-checked release in success/failure/exception. | Standard library only; no new dependency |
| `apps/backend/app/services/active_memory_store_holder.py` | New (**mandatory**) | The **`AuthoritativeActiveMemoryStoreHolder`** (§A.6): owns the current **published** authoritative `InMemoryActiveMemoryStore` reference; exposes **holder-owned read/query operations** (`find_record`/`get_record`/`list_records`/`snapshot_payload`/`current_generation`/`quarantine_state`) returning copy-safe results and a single **`publish(replacement, expected_generation, new_generation)`** swap — **no `read(fn)`/`mutate(fn)` callbacks and no operation that returns/lends/mutates the raw store** (Codex-3); provides the explicit **shared-read / exclusive-write in-process guard** with the fixed **filesystem-lock-then-write-guard acquisition order** and reverse-order exception-safe release (§A.6.1); the coordinator builds+validates the replacement **off-guard** from `ActiveMemorySnapshotStore.load`, and `publish` does the **O(1) swap under the shortest write-guard boundary**; distinguishes failed candidate construction from failed swap; exposes quarantine state + reason safely; rejects new reviewed imports while quarantined while still serving read-only from the last validated store; produces `live_store_replacement_failure`. **Wraps the store; never modifies the store class; never persists; never re-homes records; never mutates the published store in place.** | Phase 37C `InMemoryActiveMemoryStore` (wrapped unchanged); Phase 39B typed-failure discipline |
| `apps/backend/app/services/memory_migration_import.py` | New | The **import coordinator** (§A.2): owns the lock lifecycle; the ordered protocol (§E) — record review decision, **validate the `ReviewedImportSpecification` (§C.1)** including **kind/claim policy (§C.2)** and **authorization context (§C.3)** in fixed precedence, allocate attempt sequence, persist intent, **build a private candidate store from the durable snapshot and insert into it via the Active Memory seam (§A.6, §F.2)** with the **complete `model_dump` equality gate (§F.3)**, persist the candidate as snapshot at `+1` (§A.4), commit receipt (with `receipt_integrity_digest`) at matching generation, reload-and-verify linkage, then **`publish` the validated candidate last** (§E step 20); idempotent replay lookup (§G); **prep/persist/publish failure + quarantine** (§I.6); **uncertain-commit recovery incl. the N/N+1 entry path evaluated only after envelope-integrity validation and before generation equality, finalizing by writing the receipt and publishing from the durable snapshot** (§H.7/§H.8, §I.3a, §I.7, §I.9); startup load+validate of both stores under the lock (§I.3). Constructs the `MemoryRecord` **only** from the validated specification (`created_at = decision_timestamp`, `observed_at` from the spec; **no attempt/decision/authorization audit on the record**) — never infers kind/claim/project; **never obtains or mutates the published live store** (Codex-2/3). | The §C–§J rules; **depends on** the existing `MemoryStore` protocol **via the holder**; Phase 40F candidate + Phase 40G report contracts reused unchanged |
| `apps/backend/app/services/migration_import_paths.py` *(or fold into the store modules)* | New (thin) | Side-effect-free **configuration/path resolution** shared by the ledger and snapshot stores (OS-appropriate base + env overrides), reusing the Phase 39B resolver shape. | Phase 39B `resolve_workspace_config_path` pattern |
| `apps/backend/app/store/active_memory_store.py` | **Existing — integration touchpoint (class unchanged; published instance never handed out)** | The **authoritative Active Memory store**. Phase 40H uses its existing `insert`, `DuplicateRecordError`, and `serialize`/`restore` seam **unchanged**, and **does not call `transition_lifecycle` in the import path** (§F.2). The *class internals are not modified*. The **published** instance is owned and served exclusively through the holder (§A.6) and is **never handed to callers**; the coordinator's `insert` runs on a **private candidate instance it reconstructs from the durable snapshot** (`InMemoryActiveMemoryStore.restore`/`from_records`), which becomes authoritative only via the holder's `publish` swap (Codex-2/3). | Phase 37B/37C behavior; `MemoryRecord` identity/immutability/lifecycle table unchanged |
| `apps/backend/app/routers/active_memory.py` | **Existing — explicitly separate, unchanged** | The current **stateless request-scoped** read path builds its own throwaway `InMemoryActiveMemoryStore.from_records(...)` and never persists; it is **not** the authoritative live reference and is **outside** Phase 40H's mutation path, so it needs no change. **If a future durable Active Memory runtime introduces an app-lifespan/injected store, that store MUST be obtained through the holder (§A.6)** — a named, separate future change, not made here. | Unchanged; documents the ownership boundary honestly |
| `apps/backend/app/models/active_memory.py` | **Existing — read-only dependency** | Source of `MemoryRecord`, `LifecycleState.INACTIVE`, `VerificationState.UNVERIFIED`, `MemorySourceType.IMPORTED_DOCUMENT`, `SupersessionReference`/`SupersessionKind.SUPERSEDES`, and `metadata`. Phase 40H **reuses** these; **no enum, field, or contract change is required or proposed** (§F.3). | Phase 37B contract, unchanged |
| `apps/backend/app/services/__init__.py` / `app/models/__init__.py` | **Existing — possible touch** | **Any required package exports** for the new modules, if and only if the package uses explicit `__init__` re-exports; additive only. | Existing export convention |
| `apps/backend/tests/test_memory_migration_import_contracts.py` | New | Contract tests: §K rows 11–13, 16, 40, 43, 46–49, 52, **59, 60 (contract validity), 62, 71–73 (kind/claim policy), 76 (context validity), 82 (review_decision_id)**; identity/integrity derivation + domain separation (§H.0–§H.10); `ReviewedImportSpecification`/`ProjectScopeAuthorizationContext` validity; immutability. | — |
| `apps/backend/tests/test_memory_migration_import_store.py` | New | Ledger adapter tests: §K rows 8, 11, 18, 20, 21, 22, **78 (ledger envelope integrity), 80**; CAS, atomicity, integrity **detection** (incl. `receipt_integrity_digest` and `ledger_integrity_digest`), typed failures. | — |
| `apps/backend/tests/test_active_memory_snapshot_store.py` | New | Snapshot store tests: §K rows 22–26, 30, 31, **79 (snapshot envelope integrity), 80**; path/env override, startup load, missing/corrupt snapshot, generation stamping, `snapshot_integrity_digest`, interrupted writes. | Exercises, does not modify, the Active Memory store |
| `apps/backend/tests/test_active_memory_store_holder.py` | New (**mandatory**) | Holder tests: §K rows 66, 67, 68, **81, 86**; reconstruct-off-guard then O(1) `publish` swap, reader observes prior-or-replacement never partial (and never a pre-durability record), **no raw store escapes any holder operation and there is no `read(fn)`/`mutate(fn)` callback** (Codex-3), quarantine + read-only-during-quarantine, `live_store_replacement_failure`, **same-process multithreaded** access + lock acquisition/release-failure at both layers. | Exercises, does not modify, the Active Memory store |
| `apps/backend/tests/test_migration_import_lock.py` | New | Locking tests: §K rows 9, 10, **68 (filesystem-lock side), 69, 70, 86 (release-failure)**; O_EXCL exclusivity, bounded timeout, stale/ambiguous ownership, malformed metadata, release/deletion failure, release paths. | Standard library only |
| `apps/backend/tests/test_memory_migration_import_service.py` | New | Coordinator tests: §K rows 1–6, 14, 15, 17, 40–45, 50–52, 54, **60, 61, 64, 74–77 (authorization), 83**; over temp ledger + temp snapshot + the holder-served store. | — |
| `apps/backend/tests/test_memory_migration_import_integration.py` | New | Cross-store integration/recovery: §K rows 1, 6, 7, 19, 24, 27–39, 53, 55, **61, 63, 65, 84 (generation-state table), 85 (no restoration)**; over the coordinator + real `InMemoryActiveMemoryStore` (via the holder) + real snapshot store + real lock. | Exercises, does not modify, the Active Memory store |
| `docs/planning/phase-40h-reviewed-persistence-verified-import-planning.md` | Mod (this doc) | The plan. | — |

Regression (§K 56–58) runs the existing Phase 37B/37C and 40E/40F/40G suites and the
full backend suite; **no existing test file is edited**, and the Active Memory store's
behavior is asserted unchanged. Net-new source surface is **six modules** — models
(which additionally hosts the pure `KindClaimCompatibilityValidator`,
`ProjectScopeAuthorizationValidator`, the `review_decision_id` helper, the shared §H.0
canonicalizer, and the **eleven** §H.1–§H.10 identity/integrity helpers — §H.10 splits
into `authorization_context_id` and `authorization_context_digest`), ledger store,
snapshot store, live-store holder, lock, coordinator; **plus an optional thin path helper**
(so **six or seven** modules depending on whether the path helper is folded in) — and
**seven test files** (contracts, ledger store, snapshot store, holder, lock, service,
integration, now covering §K rows 1–86). The two new validators are pure additions to the models
module rather than separate modules, keeping the auditable surface minimal without
hiding them. Named existing integration touchpoints (unchanged): the Active Memory
store, the Active Memory model, and the stateless Active Memory router. **No Phase 40G
file changes** — the review *decision* is Phase-40H-owned; Phase 40G owns only the
assessment. This is the smallest credible integration for a human-gated,
crash-recoverable, two-artifact reviewed import, and small enough for one independent
audit.

---

## M. API boundary

**Decision: no new public API in Phase 40H.** Default upheld.

Reviewed import is a durable, security-sensitive local operation; the smallest
foundation is a coordinator + two persistence adapters + a lock helper integrating the
existing Active Memory store, exercised by tests, matching how Phase 37C (store) and
Phase 39B (config service) landed before any endpoint. An HTTP surface would add
request-validation, auth-posture, and error-mapping concerns that are out of scope for
establishing the mutation boundary and are unnecessary to prove the contract.

If a later phase believes an endpoint is necessary (e.g., a review/approval workflow
UI), it must: (1) justify it separately, (2) define a narrow thin-router boundary that
only validates a request contract and maps typed results to safe responses (no
persistence/digest/lifecycle logic in the router), and (3) be marked as **requiring
explicit approval before implementation**. No endpoint is created in this planning
phase, and none is created by the proposed Phase 40H implementation above.

---

## N. Deferred work (explicitly out of scope)

Explicitly deferred and **not** part of Phase 40H:

- Frontend work of any kind (no review/approval/import UI).
- Grounded Synthesis Producer implementation (Phase 40I).
- Automatic approval or any derived/inferred approval.
- LLM or semantic truth adjudication.
- Active-state calculation / promotion of imported records to `active` /
  `human_confirmed`, and any **lifecycle retirement** of imported records (remains
  deferred Active Memory work).
- Any change to the Active Memory record contract, enums, identity rule, or **lifecycle
  transition table** (Phase 40H reuses them unchanged; it never adds an
  `INACTIVE → SUPERSEDED` edge and never calls `transition_lifecycle` in the import
  path).
- Promotion of migration provenance from the typed `metadata.migration_provenance`
  block to first-class typed `MemoryRecord` fields (a named, separate Phase 37B contract
  change if a future audit requires it, §F.3).
- Knowledge Graph mutation.
- Source Registry mutation.
- Obsidian mutation / write-back.
- Repository Observer mutation.
- Broad persistence replacement or migrating the existing Active Memory store to a new
  durable medium (beyond the thin, explicitly-scoped `ActiveMemorySnapshotStore` of
  §A.4, which wraps the existing serialize/restore boundary).
- **PostgreSQL / any server database migration.**
- Phase 36K (paused and untouched).
- Operational deployment, service install, scheduled tasks, background daemons.
- Screenshots and demo evidence.
- A public API / endpoint (see §M).
- Anything beyond the smallest reviewed-import foundation.

---

## Acceptance-criteria coverage

| Criterion | Section |
| --- | --- |
| Active Memory store remains authoritative | A.1 |
| Import coordinator is an orchestration boundary, not a competing store | A.2 |
| MigrationImportStore owns workflow records only | A.3 |
| Mandatory durable `ActiveMemorySnapshotStore` (module, interface, config, startup, integrity, failures) | A.4 |
| Authorized Active-Memory-insertion seam; `transition_lifecycle` not called | F.2 |
| No duplication/wrapping of authoritative records | A.1, A.4, B, F.2 |
| Imported records INACTIVE; no `INACTIVE → SUPERSEDED`; supersession via `supersession_refs` | D.4, D.7, F.1, F.2 |
| Candidate-to-`MemoryRecord` provenance mapping (named fields, no unspecified metadata) | F.3 |
| Reviewer-approved `ReviewedImportSpecification` supplies kind/claim/project the candidate lacks; validated, never inferred | C.1, F.3, H.3, H.5 |
| No nonexistent kind/claim/project attributed to `MemoryMigrationCandidate` | C.1, F.3, H.3 |
| **Concrete closed versioned kind↔claim compatibility policy; named validator; policy-version binding; `kind_claim_incompatible`** (Blocker 1) | C.2, H.5, J, K (71–73) |
| **Typed `ProjectScopeAuthorizationContext` with named owner + complete binding + digest into spec/idempotency/receipt/intent/recovery; non-member scope rejected (exact set membership); repo location ≠ authorization** (Blocker 2) | C.3, H.10, E, I.7, J, K (74–77) |
| **Complete integrity digests seal both durable envelopes; verified before any generation trusted** (Blocker 3) | A.3, A.4, H.7, H.8, I.8, I.9, K (78–80) |
| **Duplicate acceptance compares the complete stored `MemoryRecord` via model serialization, not a subset** (Blocker 4) | F.3, H.3, I.7, K (14, 15, 36) |
| **`import_attempt_id` absent from stable authoritative record; attempt/decision/authorization audit ledger-only; retry-stable** (Blocker 5) | F.3, B.1, G.3, H.3, K (13, 81) |
| **No impossible historical-generation restoration; unrecoverable states quarantine** (Blocker 6) | I.6, I.7, I.9, K (35, 84, 85) |
| **Shared canonicalization + collision policy covering every identifier/digest** (Gap 7) | H.0, J, K (12) |
| **Complete `review_decision_id` derivation (versioned, domain-separated); compatible with the actual 40G model** (Gap 8) | C, H.9, J, K (82, 83) |
| **Explicit holder read/write-guard boundaries, lock ordering, no-escape callbacks** (Gap 9) | A.6, A.6.1, L, K (66–68, 86) |
| **Acyclic review/authorization identity graph; `review_decision_id` excludes `authorization_context_id`; dependency-order statement** (Codex-1) | H.0a, H.9, H.10, C.3, K (82) |
| **No pre-durability live-store visibility: private candidate store, durable-then-verify, publish last** (Codex-2) | A.2, A.6, A.6.1, E (16–20), F.2, F.3, I.2, I.6, I.7, K (27, 28, 66) |
| **No raw-store escape: holder-owned read/query/publish operations, no caller callbacks** (Codex-3) | A.6, A.6.1, F.2, L, K (86) |
| **Scope authorization = exact set membership, no invented hierarchy; `project_level_authorized`** (Codex-4) | C.1, C.3, H.10, J, K (74, 75) |
| **Authorization digest is complete: `issued_at` in `authorization_context_digest`, excluded only from `authorization_context_id`** (Codex-5) | C.3, H.0, H.10, J, K (76) |
| **`observed_at` explicit reviewer-authored source; distinct from `created_at`; in `specification_digest`/`record_id`; retry-stable** (Codex-6) | C.1, F.3, H.0, H.3, H.5, K (13) |
| **Timestamp-only review decision is the *same* decision (idempotent); renewal via `renewal_revision`/`supersedes_decision_id`** (Codex-7) | B.1, C, D.7, G.3, H.9, K (82) |
| **Malformed-claim/spec diagnostics have fixed non-overlapping precedence and owners** (Codex-8) | C.1, C.2, J, K (60, 73) |
| Mandatory `AuthoritativeActiveMemoryStoreHolder`; **publish-last** replacement; reader synchronization; quarantine | A.6, F.2, I.6 |
| Explicit N/N+1 uncertain-commit exception evaluated before ordinary generation equality (and only after envelope integrity) | I.3, I.3a, I.7, I.9, E |
| Receipt identity vs full-content integrity (`receipt_integrity_digest` covers both timestamps) | B.3, H.4, H.6, I.8 |
| Same-process multithreading tests (in-process seam + filesystem lock); malformed-lock-metadata + release-failure mappings | I.4, J, K (68–70) |
| Receipt references exact `record_id` + full receipt contract | B.3, E, I.2 |
| Shared persisted `commit_generation` (init/validate/increment/mismatch; verified only on agreement) | I.3 |
| No false cross-store atomicity; recoverable protocol | I.1–I.3 |
| One coordinator; one concrete Windows-compatible dependency-free lock protocol; stale/ambiguous rules; release paths | I.4 |
| Concurrency: exclusive writer + persisted-revision/CAS | I.4, I.5 |
| Ordered intent/effect/receipt protocol incl. reload-and-verify | E, I.2 |
| Post-insert failure rollback + quarantine (all failure modes) | I.6 |
| Uncertain-commit recovery with exact record equality, not `record_id` alone | I.3a, I.7 |
| Canonical identity/integrity derivation for all eleven values (identity vs integrity domains, membership, timestamp rules; **acyclic dependency order**) | H.0, H.0a, H.1–H.10 |
| Stable idempotency key + distinct monotonic attempt ids (retries only) | G.1, G.2, H.1, H.2 |
| Review-decision supersession independent of attempt ordering | C, D.7, G.2 |
| Supersession ordering / tie / cycle / missing predecessor / changed-byte / changed-assessment | D.7 |
| Normalized diagnostic taxonomy incl. all required codes | J |
| Partial-write detection separated from recovery | I.7, I.8 |
| Expanded test matrix | K |
| Mandatory, bounded, auditable implementation map incl. existing modules + tests | L |
| Fail-closed behavior | E, I, J |
| Explicit deferred work | N |
| Explicit API boundary | M |

Phase 36K remains **paused and untouched** by this plan. This document persists
nothing, imports nothing, and implements no runtime; it defines the Phase 40H
foundation only, and that foundation is **proposed and pending a further independent
audit** before any implementation is unlocked.
