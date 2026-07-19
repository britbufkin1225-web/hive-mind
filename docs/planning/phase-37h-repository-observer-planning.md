# Phase 37H — Repository Observer Planning

**Phase:** Phase 37H — Repository Observer Planning.
**Track:** Track 2 — Agent Intelligence Infrastructure (parallel to Track 1 —
Spatial Interaction, whose active implementation phase remains **Phase 36K —
Full-Hand Gesture Live Camera QA + Control Tuning**, which is **paused — not
completed**).
**Status:** Planning / architecture / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, model,
database, package, dependency, lockfile, build/runtime configuration,
subprocess execution, Git invocation from application code, filesystem scan,
watcher, screenshot, or demo-evidence change. **No repository observer runtime,
no Git adapter, no ingestion, no contradiction execution, no context-packet
change, no GitHub integration, no AI/LLM behavior.**
**Relationship:** Extends the Track 2 [Active Agent Memory + Verification Layer](../active-agent-memory-verification-layer.md)
by specifying a *future* evidence provider — the **Repository Observer** — that
would convert deterministic repository state into evidence records and candidate
memory records for that layer's separate ingestion, contradiction, and
context-packet services. It does **not** displace, rewrite, or resume Phase 36K,
and it makes no claim that any observer runtime exists. Pairs with the
[Phase 37A planning doc](phase-37a-active-agent-memory-verification-layer-planning.md),
the [Active Memory reference](../active-agent-memory-verification-layer.md), the
[roadmap](../roadmap.md), and the [README](../../README.md).

> **One-line framing.** The Repository Observer is meant to *look at a local Git
> repository and report what is deterministically true about it* — identity,
> branch, working tree, commits, remotes, operation state — as bounded,
> evidence-backed, read-only observations. It is an **evidence provider, not an
> autonomous developer**. It never edits, commits, switches branches, pushes,
> pulls, merges, executes project code, or mutates memory. Phase 37H writes the
> contract and the boundaries. It ships no runtime.

---

## 1. Executive summary

### 1.1 What the observer is

The **Repository Observer** (hereafter "the observer") is a proposed backend
subsystem that inspects a single local Git repository **without mutating it** and
produces an **immutable observation snapshot**: a bounded, deterministically
ordered, read-only record of repository identity, branch state, working-tree
state, commit history, remote-tracking state, changed-file summaries, and
in-progress Git operation state (merge, rebase, cherry-pick, bisect). From that
snapshot it derives **evidence records** and **candidate memory records** that a
*separate* ingestion layer may later feed into the Active Memory and Verification
Layer.

The observer's defining behaviors are **read-only observation** (it runs
inspection commands and reads filesystem metadata, never mutation commands) and
**evidence honesty** (each reported fact is tagged with the evidence class that
supports it, and claims that local Git cannot prove — most importantly remote
pull-request state — are explicitly marked as unverified rather than asserted).

### 1.2 Why Hive|Mind needs it

Hive|Mind's Active Memory layer already models evidence-backed claims about the
project (Phase 37A–37G), but every claim today is **supplied by a human or an
agent** through the read-only context-packet endpoint and inspector. There is no
component that derives repository facts *directly* from the repository. Agents
and users therefore lack a trustworthy, structured, machine-produced view of:

- repository identity (canonical path, remotes, primary remote)
- current branch and HEAD commit
- working-tree state (clean vs. dirty)
- staged, unstaged, and untracked changes
- recent commit history and commit metadata
- changed paths, renames, and deletions
- diff summaries (statistics, not raw content)
- merge / rebase / cherry-pick / bisect operation state
- remote-tracking state (upstream, ahead/behind)
- tags and configured remotes
- pull-request or issue references *when independently verified*
- test / validation evidence *when supplied by a validated execution layer*
- documentation-drift signals
- implementation claims that conflict with repository truth

The recurring failure this addresses is **stale, confidently-wrong prose**: a
completion report says "merged to `main`" when the commit is unreachable from
`main`; a report says "tree is clean" while changes are staged; a report says "a
file was untouched" while it appears in the diff. The observer exists to put a
deterministic, evidence-scoped repository truth **next to** those claims so the
Active Memory contradiction detector can compare them — without the observer
itself deciding who wins.

### 1.3 What Phase 37H delivers

This phase delivers **only documentation**: the observer's product problem,
responsibilities and non-responsibilities, repository identity model, observation
snapshot contract, evidence hierarchy, Active Memory integration boundary,
contradiction opportunities, security and trust model, deterministic ordering and
overflow rules, a narrow MVP definition, deferred scope, a test strategy,
acceptance criteria, a conservative follow-on phase sequence, and open questions.
No code, schema, dependency, or runtime behavior is added.

---

## 2. Problem statement

Hive|Mind advances phase by phase, and each phase produces prose reports (in
chat, commits, `README.md`, `docs/roadmap.md`, and evidence documents). Those
reports are point-in-time statements that go stale silently. The Active Memory
layer can *store and compare* claims, but it cannot *originate* repository facts;
it depends entirely on what a caller hands it.

Without a repository observer:

- A claim like "Phase 37G is merged" can only be checked against another
  human-entered claim, never against the repository itself.
- "Working tree is clean" cannot be confirmed from evidence; it is trusted prose.
- "This branch was created from `main`" and "this commit is reachable from
  `main`" are unverifiable from within the memory layer.
- Documentation drift (README says one thing, roadmap says another, Git shows a
  third) is invisible until a human notices.

The observer's job is to make these facts **machine-observable, bounded, and
evidence-scoped** so later services can detect contradictions deterministically.
Crucially, the observer must also be honest about the **limits of local Git**:
local history alone does not prove that a pull request merged, that CI passed, or
that a remote branch was deleted. Those require external GitHub or execution
evidence the observer does not fabricate.

---

## 3. Goals

1. Define a **read-only** repository observer that never mutates the repository,
   the memory store, or Git configuration.
2. Specify a **deterministic** observation snapshot: same repository state in →
   same snapshot out, with total ordering on every collection.
3. Specify an **evidence hierarchy** so every reported fact is tagged with the
   evidence class that supports it.
4. Draw a hard **integration boundary**: the observer produces evidence and
   candidate records; separate services own normalization, dedup, contradiction
   detection, context-packet selection, persistence, policy, and presentation.
5. Enumerate the **deterministic contradictions** the observer's output could
   later enable, and separate the ones needing external GitHub/CI evidence.
6. Provide a defensive-security **threat model** for inspecting an untrusted
   repository, with bounded output, no hook execution, and argument-array process
   execution over shell interpolation.
7. Define **bounded behavior** and explicit **overflow / error** semantics.
8. Define a **narrow, implementable MVP** and an explicit deferred list.
9. Sequence conservative follow-on phases, each independently reviewable.

---

## 4. Non-goals

Phase 37H does **not**:

- implement the observer, a Git adapter, or any subprocess execution;
- run Git commands from application code or scan the filesystem;
- add Pydantic models, TypeScript interfaces, API endpoints, persistence, or
  database tables;
- add ingestion, contradiction execution, context-packet changes, or GitHub
  integration;
- add dependencies, AI/LLM behavior, or a filesystem watcher;
- modify frontend, backend runtime, tests, graph, Obsidian, or MediaPipe files;
- touch Phase 36K work;
- produce screenshots or fabricated evidence.

It also does not, even in the future design, make the observer an autonomous
developer, a repository mutator, a truth oracle, or an AI summarizer (see §7 and
§9).

---

## 5. Terminology

- **Observer** — the proposed read-only repository inspection subsystem.
- **Observation snapshot** — an immutable, bounded, deterministically ordered
  read-only record of repository state at one observation time.
- **Direct fact** — a value read straight from Git command output or filesystem
  metadata (e.g. current branch name, HEAD SHA).
- **Derived fact** — a value computed deterministically from direct facts (e.g.
  "clean" from an empty status; "ahead/behind" from rev-list counts).
- **Externally supplied claim** — data given to the observer by another layer
  (e.g. a test result from a validated execution source), not observed by it.
- **Unverified assumption** — something not proven by available evidence (e.g.
  "the PR merged" from local history alone); reported as such, never asserted.
- **Evidence record** — a bounded pointer + class describing what supports a
  fact, aligned with the Active Memory `EvidenceType` vocabulary.
- **Candidate record** — a proposed Active Memory `MemoryRecord`-shaped fact the
  observer offers to ingestion; the observer never writes it to the store.
- **Adapter** — the internal boundary around Git inspection operations that turns
  command execution into structured results or structured errors.
- **Overflow metadata** — explicit markers recording that a bounded collection
  was truncated, and by how much, rather than silently dropping data.
- **Fail-closed** — on ambiguity, error, or a mutation temptation, stop and emit
  a structured error/warning rather than guessing or acting.

---

## 6. Repository identity model

The observer must identify a repository **deterministically** so later
observations of the same repository can be correlated without depending on
volatile details like absolute path alone.

### 6.1 Proposed identity fields

- **observer schema version** — the observation contract version (e.g.
  `repo-observer.v1`), decoupled from package version.
- **repository ID** — a stable, content-derived identifier (see §6.2).
- **canonical local path** — the resolved, normalized repository root.
- **repository directory name** — the leaf directory name of the root.
- **remote URLs** — all configured remotes, name → URL, deterministically
  ordered.
- **normalized primary remote** — the `origin` URL (or a documented fallback)
  reduced to a normalized form (scheme/host/path without credentials).
- **current branch** — the checked-out branch, or an explicit detached-HEAD
  marker.
- **HEAD SHA** — the full commit hash at HEAD.
- **upstream reference** — the configured upstream (`refs/remotes/...`) or
  explicit "none".
- **detected default branch** — the remote's default branch when discoverable,
  else an explicit "unknown".
- **repository state** — normal / merging / rebasing / cherry-picking /
  bisecting / detached / bare / unavailable.
- **observation timestamp** — caller-supplied observation time (the observer does
  not read the wall clock; see §12 and §10).
- **observer version** — the observer implementation version.

### 6.2 Repository ID derivation (proposed, not finalized)

The repository ID should prefer a **stable, non-volatile** basis. Candidate
strategy: derive from the **normalized primary remote URL** when a remote exists
(so the same project cloned to two paths correlates), and fall back to the
**canonical local path** when there is no remote. The precise algorithm,
collision handling, and whether to combine remote + root are **open questions**
(§21) and are **not finalized in this phase**. Persistence of the identity is
also deferred.

### 6.3 Identity edge-case behavior

- **directory moved** — path changes; if a remote exists, remote-derived ID
  stays stable; a path-only ID would change. Report both fields so the divergence
  is visible.
- **remote changed** — remote-derived ID changes; report the old vs. new remote
  as observable, not silently rewritten.
- **cloned again** — same remote → same remote-derived ID, different path;
  correlation is intended.
- **multiple worktrees** — each worktree has its own path and HEAD; the observer
  observes the *targeted* worktree only and records that a linked worktree layout
  was detected.
- **no remote** — fall back to path-based ID; mark `normalized primary remote` as
  "none"; downstream must not assume a GitHub identity.
- **not on a branch (detached HEAD)** — `current branch` is an explicit
  detached-HEAD marker; identity still resolves via HEAD SHA + path/remote.
- **shallow repository** — mark history as shallow; reachability and ahead/behind
  claims are bounded and flagged (see §5 unverified assumption + §8).
- **Git unavailable** — identity resolution fails closed with a structured error;
  no partial identity is fabricated.

Persistence behavior for identity is **not finalized** in this phase.

---

## 7. Observer responsibilities and non-responsibilities

### 7.1 What the observer may observe

- repository root and Git availability
- current branch and HEAD commit
- upstream branch and ahead/behind state
- clean or dirty working tree
- staged, unstaged, and untracked files
- recent commit history (bounded) and commit metadata
- changed paths, including rename and deletion information
- diff **summaries** (statistics only; not raw content in the MVP)
- merge / rebase / cherry-pick / bisect operation state
- tags and configured remotes
- repository configuration **relevant to observation only** (see §9 for hostile
  config handling)
- selected documentation status markers (bounded, structured reads)
- test / validation evidence **explicitly supplied by another execution layer**

The observer must classify every reported item into exactly one of:

1. **direct repository fact** — from Git output or filesystem metadata;
2. **derived repository fact** — computed deterministically from direct facts;
3. **externally supplied claim** — handed in by another layer;
4. **unverified assumption** — not proven by available evidence (reported as
   such, never as a fact);
5. **unsupported data** — requested but unavailable; reported as an explicit
   gap, never guessed.

### 7.2 What the observer must not do

The observer must never:

- edit files, create/amend commits, or stage/unstage changes;
- switch, create, or delete branches;
- stash, reset, or clean the repository;
- push, pull, fetch-with-write, or merge;
- rebase, cherry-pick, or resolve conflicts;
- open, close, or merge pull requests;
- execute arbitrary project code or install dependencies;
- change Git configuration;
- execute repository hooks or arbitrary repository scripts;
- mutate Active Memory records (ingestion is a separate decision);
- infer that tests passed merely because test files exist;
- infer that a phase merged merely because a branch or commit exists;
- claim GitHub state (PR merged, remote branch deleted, CI passed) without
  verified GitHub/CI evidence.

Mutation is **fail-closed**: if any code path could mutate, it must instead emit a
structured error and perform nothing.

---

## 8. Observation snapshot contract (proposal)

The snapshot is a **read-only**, immutable value with conceptual sections. This
phase specifies its shape and rules conceptually; it introduces **no** Pydantic or
TypeScript types.

### 8.1 Conceptual sections

- **repository identity** — the §6 fields.
- **branch state** — current branch / detached marker, HEAD SHA, upstream ref,
  detected default branch.
- **working-tree state** — clean/dirty flag; staged, unstaged, untracked path
  summaries.
- **commit state** — bounded recent commits with metadata (SHA, author, committer,
  dates, subject); reachability results only where explicitly requested.
- **remote-tracking state** — remotes (name → normalized URL), upstream,
  ahead/behind counts (bounded, flagged when shallow).
- **changed-file summaries** — per-path status (added/modified/deleted/renamed),
  rename old→new, binary flag; counts, not raw content.
- **operation state** — normal / merging / rebasing / cherry-picking / bisecting,
  with conflict presence flagged.
- **evidence records** — the evidence backing each reported group (§11).
- **warnings** — deterministic non-fatal conditions (shallow history, truncation,
  detached HEAD, submodule boundary crossed, encoding fallback…).
- **errors** — structured, bounded error records for failed collectors (§13).
- **observation metadata** — observer version, schema version, caller-supplied
  observation timestamp, applied limits, and overflow markers.

### 8.2 Deterministic ordering (required)

Every collection is **totally ordered** so the snapshot is byte-reproducible for
unchanged state:

- **paths** — ordered by normalized path string (documented normalization; not
  locale-dependent).
- **commits** — reverse-chronological by commit date, then SHA as a stable
  tiebreak (equal timestamps never reorder between runs).
- **remotes** — ordered by remote name, then normalized URL.
- **warnings** — ordered by a fixed warning-code order, then by a stable detail
  key.
- **evidence entries** — ordered by evidence class, then by reference value.
- **errors** — ordered by collector name, then error code.

Ordering must never depend on insertion order, dict iteration order, RNG, or wall
clock.

### 8.3 Stable handling of tricky states

- **missing values** — explicit "none"/"unknown" markers, never empty-string
  ambiguity or a fabricated default.
- **duplicate remotes** — deduplicated deterministically; a duplicate is a warning,
  not a silent drop.
- **renamed files** — carry old→new path and a rename marker; never reported as a
  delete+add pair when Git reports a rename.
- **binary files** — flagged binary; no content, no line stats claimed.
- **submodules** — reported as a boundary; the observer does not descend into
  submodule internals in the MVP.
- **symbolic links** — reported as links; never followed outside the repository
  root (§9 symlink escape).
- **ignored files** — excluded from untracked unless explicitly requested;
  reporting them is bounded.
- **detached HEAD** — explicit marker; branch-dependent fields degrade to
  "unknown" rather than guessing.
- **merge conflicts** — conflict presence flagged in operation state; the observer
  never resolves them.
- **rebases / cherry-picks / bisects** — reported as operation state; never
  advanced or aborted.
- **shallow history** — flagged; reachability and ahead/behind are bounded and
  marked as possibly incomplete.
- **inaccessible files** — structured per-path error/warning; the observation
  continues where safe rather than aborting wholesale.
- **path encoding problems** — a documented, deterministic fallback (e.g. a safe
  escaped rendering) with a warning; never a crash and never raw terminal-control
  bytes (§9).
- **very large repositories** — bounded by the §12 limits with explicit overflow
  metadata.

---

## 9. Security and trust model (defensive design)

The observer inspects a **potentially untrusted repository**. Repository content
(filenames, config, hooks, diffs, refs) is **data, not instructions**, and must
never be executed or trusted as commands. This section is the SecOps-oriented
threat model.

### 9.1 Threats considered

- malicious repository contents and deceptive filenames
- path traversal and symlink escape outside the repository root
- command injection and shell metacharacters in refs, paths, or config values
- hostile Git configuration and malicious hooks
- credential leakage and embedded secrets (in config, remotes, diffs)
- oversized output, repository bombs, deeply nested paths
- binary and compressed files rendered unsafely
- malformed encodings and terminal escape sequences in names/diffs
- submodule boundary crossing and untrusted remote URLs
- private repository metadata exposure
- accidental collection of unrelated directories outside the target root

### 9.2 Required defensive posture (for the future implementation)

- **Argument-array process execution**, never shell string interpolation — Git is
  invoked with an explicit argument vector so ref/path/config values cannot be
  interpreted by a shell.
- **No hook execution** and **no arbitrary repository scripts** — inspection
  commands are chosen to avoid triggering hooks; project code is never run.
- **Strict repository-root confinement** — the resolved root is the boundary;
  symlinks are not followed outside it; paths are validated against traversal.
- **Bounded output, history depth, and file counts** — see §12.
- **Per-command and whole-observation timeouts** — a hung or bomb repository fails
  closed with a structured timeout error.
- **Structured parsing** — machine-readable Git output (e.g. `-z`/porcelain
  formats) parsed into typed results, not scraped from human-formatted text.
- **Secret-redaction boundaries** — credentials in remote URLs and any detected
  secret-shaped values are redacted before they enter a snapshot; diffs are
  summarized (stats), not embedded, in the MVP.
- **Terminal-escape neutralization** — control/escape sequences in names and any
  rendered strings are stripped or escaped so a snapshot can never inject terminal
  control codes downstream.
- **Explicit error records** — failures become structured observer errors, not raw
  tracebacks or raw stderr.
- **Fail-closed mutation behavior** — any mutation temptation stops and emits an
  error; the observer performs nothing mutating.

### 9.3 Trust boundaries (summary)

- Repository content is untrusted input.
- Direct Git/filesystem observation is the strongest local evidence, scoped to
  what it demonstrates.
- Externally supplied claims (tests/CI/GitHub) are trusted only as strongly as the
  validated source that carries them, and never fabricated by the observer.
- The observer's output is evidence, not a decision; downstream services own
  policy and mutation.

---

## 10. Evidence hierarchy

The observer tags each reported fact with the class of evidence that supports it.
This mirrors and refines the Active Memory evidence hierarchy
([reference §5](../active-agent-memory-verification-layer.md)), scoped to
repository observation. **Claim-relative, strongest first:**

1. **Direct Git command output** — porcelain/structured output of read-only Git
   inspection commands.
2. **Direct filesystem metadata** — existence, type, size, mode read under
   repository-root confinement.
3. **Parsed repository documents** — bounded, structured reads of source-controlled
   docs (e.g. a roadmap status marker).
4. **Test or build output supplied by a validated execution source** — never run
   by the observer; only accepted from a trusted execution layer.
5. **User-provided statements** — human claims handed to the observer.
6. **Agent-generated summaries** — prose from an agent; only as strong as the
   evidence it carries.
7. **Unsupported assumptions** — no backing evidence; reported as unverified, never
   as fact.

### 10.1 Which evidence may support which claim

| Claim | May be supported by | Must NOT be asserted from |
|---|---|---|
| working tree is clean | direct Git status output (1) | agent prose (6) alone |
| branch aligned with upstream | direct rev-list ahead/behind (1), non-shallow | shallow history without a flag |
| phase is merged (to `main`) | direct reachability of the commit from `main` (1) | a branch or commit merely existing |
| pull request is merged | verified GitHub evidence (4/external) | local history alone (unverified) |
| tests passed | validated execution/CI output (4) | test files existing (unsupported) |
| documentation is current | parsed doc marker (3) vs. observed Git facts (1) | assuming currency |
| implementation exists | source-code reference (5) + direct facts (1) | a filename implying behavior |
| a file was untouched | absence from the diff (1) | a report saying so (6) alone |
| a branch was deleted | direct local/remote ref absence (1) for local; verified GitHub (4) for remote | assuming remote deletion locally |
| a commit is reachable from `main` | direct reachability query (1) | a commit hash existing |

**Local Git history alone does not always prove remote pull-request state.** PR
merge/close status, remote-branch deletion, and CI results require verified
external GitHub/execution evidence; without it, the observer reports them as
**unverified**.

---

## 11. Active Memory integration boundary

The observer **produces evidence and candidate records**; it does not ingest,
normalize, dedup, detect contradictions, select context packets, persist, decide
policy, or present. Those are owned by the existing Active Memory and Verification
services ([reference](../active-agent-memory-verification-layer.md)).

### 11.1 Candidate record categories (proposed)

Mapped to the existing `active-memory.v1` vocabulary where possible; **no new
contract is authored in this phase**:

- **repository fact** → `repository_state` / `project_fact` candidate
- **branch fact** → `repository_state` candidate scoped to a branch
- **commit fact** → `repository_state` / `project_fact` candidate
- **workspace fact** (clean/dirty, staged/untracked) → `repository_state`
  candidate
- **validation evidence** (externally supplied) → `EvidenceRecord` candidate
  (`test_output` / `ci_output`), never asserted by the observer
- **implementation claim** → `capability` / `project_fact` candidate, scoped to
  what source evidence demonstrates
- **documentation claim** → `project_fact` candidate carrying a parsed-doc
  evidence reference
- **contradiction candidate** → a *signal* that two claims may conflict, handed to
  the Phase 37D detector; the observer never finalizes a contradiction
- **stale-state warning** → a `PacketWarning`-style candidate for aged evidence

### 11.2 Ownership split

| Owned by the observer | Owned by separate services |
|---|---|
| read-only repository observation | record normalization |
| evidence classification | deduplication |
| candidate record proposal | contradiction detection (37D) |
| bounded snapshot emission | context-packet selection (37E) |
| structured errors/warnings | persistence |
| — | policy decisions |
| — | user-facing presentation |

The observer hands a snapshot (and derived candidates) to ingestion and stops.
**Ingestion is not implemented in this phase**, and the observer never mutates the
store.

---

## 12. Bounded behavior and performance

All limits are **explicit, configured, and fail-closed with overflow metadata** —
never silent truncation.

Proposed safeguards:

- **maximum commit history depth** — bound recent-commit collection.
- **maximum changed-file count** — bound working-tree/diff path collections.
- **maximum diff-stat entries** — bound per-file statistics.
- **maximum output bytes** — bound per-command and per-snapshot output.
- **per-command timeout** — bound any single Git/filesystem operation.
- **whole-observation timeout** — bound the entire observation.
- **binary-file handling** — flagged, never content-embedded.
- **large monorepositories** — bounded by the above; overflow metadata records
  what was omitted.
- **submodules** — reported as boundaries, not descended into.
- **repeated observations** — deterministic and side-effect free, so re-running is
  safe and comparable.

When a bound is hit, the snapshot carries **overflow metadata** (which collection,
the applied limit, and how many items were omitted) rather than dropping data
silently. Determinism requires that truncation itself be ordered (the *first N*
under the §8.2 ordering are kept).

---

## 13. Error and overflow behavior

- **Command failures** become **structured observer errors** (collector name,
  error code, bounded message), never raw tracebacks or raw stderr.
- **Git unavailable / not a repository / inaccessible root** fail the observation
  closed with a single structured error and no fabricated partial identity.
- **Partial failures** (one collector fails, others succeed) are reported per
  collector: the snapshot carries the successful sections plus an explicit error
  record for the failed one, where continuing is safe.
- **Timeouts** (per-command or whole-observation) produce a structured timeout
  error and stop further work fail-closed.
- **Overflow** is reported via §12 overflow metadata, deterministically truncated.
- **Encoding / control-sequence problems** produce a warning plus a safe rendered
  value; never a crash and never raw terminal-control output.

Error and warning collections are themselves bounded and ordered (§8.2).

---

## 14. Observation lifecycle

A future observation should proceed as an ordered, read-only pipeline:

1. **Validate repository target** — confirm the caller-supplied path is inside an
   approved root and is intended for observation.
2. **Resolve repository root** — canonicalize and confine; detect bare/worktree
   layouts; fail closed if Git is unavailable.
3. **Establish observation limits** — apply the §12 bounds and timeouts up front.
4. **Collect direct Git facts** — branch, HEAD, upstream, status, remotes,
   operation state, bounded commits, changed paths (argument-array, structured
   output).
5. **Collect bounded filesystem facts** — confined metadata only; no traversal
   outside root; no symlink escape.
6. **Normalize results** — decode safely, redact secrets, neutralize control
   sequences, apply deterministic ordering.
7. **Derive deterministic state** — clean/dirty, ahead/behind, reachability (only
   where requested), operation state.
8. **Generate evidence records** — tag each fact with its evidence class (§10).
9. **Generate warnings** — shallow, truncated, detached, submodule-boundary,
   encoding-fallback, etc.
10. **Produce an immutable observation snapshot** — bounded, ordered, byte-stable
    for unchanged state.
11. **Hand the snapshot to a separate ingestion layer** — the observer stops here;
    it never ingests or mutates.

### 14.1 Trigger model (MVP recommendation)

The MVP should be **request-triggered / manually refreshed** (and optionally
session-triggered), **not** a live filesystem watcher and **not** background
polling. A watcher adds concurrency, resource, and security surface (inotify
limits, event storms, partial-write races) with little MVP value; it stays
deferred unless a later phase clearly justifies it.

---

## 15. Command and adapter boundary

Plan an internal **adapter layer** around Git inspection so the rest of the system
depends on structured results, not on subprocess mechanics. **No commands or
subprocess code are implemented in this phase.**

Conceptual read-only operations:

- resolve repository root
- read status (porcelain/structured)
- read branch state
- read HEAD
- read upstream state (ahead/behind)
- list remotes
- inspect recent commits (bounded)
- inspect changed paths (with rename/delete info)
- inspect operation state (merge/rebase/cherry-pick/bisect)
- test commit reachability (only where requested)
- collect bounded diff statistics

Every operation:

- runs via **argument-array execution** (no shell interpolation);
- is **read-only** (no mutation verbs);
- turns failures into **structured observer errors** (§13), never raw tracebacks;
- respects the §12 bounds and timeouts;
- returns typed results the rest of the observer consumes.

---

## 16. Deterministic ordering rules (consolidated)

Restating §8.2 as a single normative reference for implementers:

- collections are **totally ordered**; equal primary keys break ties on a stable
  secondary key (SHA, normalized path, warning code, evidence reference);
- ordering never depends on insertion order, dict order, RNG, or wall clock;
- truncation keeps the **first N** under the defined order and records overflow;
- the snapshot is **byte-reproducible** for identical repository state and
  identical caller inputs (including the caller-supplied observation timestamp).

---

## 17. MVP scope

The smallest useful future Repository Observer MVP:

- repository root validation and confinement
- repository identity (§6 fields)
- current branch (or detached marker)
- HEAD SHA
- upstream reference
- ahead/behind state (flagged when shallow)
- clean / dirty state
- staged paths
- unstaged paths
- untracked paths
- recent bounded commits with metadata
- remotes (name → normalized, redacted URL)
- merge / rebase / cherry-pick / bisect operation state
- deterministic warnings (shallow, truncated, detached, submodule boundary,
  encoding fallback)
- an immutable, bounded, ordered observation snapshot
- focused unit tests (see §19)

The MVP is **backend-only, read-only, deterministic, single-repository, and
locally targeted**, with argument-array execution, bounded output, timeouts, and
fail-closed errors.

---

## 18. Deferred scope

Explicitly out of the MVP:

- GitHub API integration
- pull-request ingestion
- issue ingestion
- filesystem watcher
- automatic background polling
- commit creation or any mutation
- patch / diff-content generation or ingestion
- autonomous fixes
- dependency installation
- test execution
- full diff-content ingestion (MVP is stats-only)
- repository-wide semantic indexing
- AI/LLM summarization
- frontend visualization
- persistence of snapshots or identity

Each deferred item is a candidate for a later, independently scoped phase (§20).

---

## 19. Test strategy (for the future implementation)

When the observer is built, testing should be **deterministic and hermetic**:

- **Fixture repositories** created programmatically in a temp directory per test
  (init, commit, branch, stage, rebase-in-progress, detached HEAD, shallow clone,
  submodule boundary), then observed — no dependence on the developer's real repo.
- **Deterministic assertions** — same fixture in → same snapshot out; assert exact
  ordering and byte-stability where feasible.
- **Caller-supplied clock/inputs** — tests inject the observation timestamp; the
  observer reads no wall clock, matching the Active Memory store/detector
  convention.
- **Security cases** — deceptive filenames, control-sequence names, symlink to
  outside root, hostile config values, oversized/bomb fixtures (bounded), binary
  files; assert redaction, escaping, confinement, timeout, and fail-closed
  behavior.
- **Overflow cases** — exceed each §12 bound; assert overflow metadata and ordered
  truncation, not silent drops.
- **Error cases** — Git unavailable, not-a-repo, inaccessible path, per-collector
  failure; assert structured errors, no raw tracebacks.
- **No mutation** — assert the fixture repository is byte-identical before and
  after observation.

Tests must not run the frontend or require network/GitHub access.

---

## 20. Future phase sequence

A conservative follow-on sequence after Phase 37H (naming adjustable only if the
roadmap requires):

- **Phase 37I — Repository Observer Contract Types / Schema Alignment** — define
  the `repo-observer.v1` snapshot/evidence/identity contracts (backend Pydantic +
  mirrored frontend types + parity test); no runtime.
- **Phase 37J — Deterministic Git Adapter Foundation** — the read-only,
  argument-array adapter with structured errors, bounds, and timeouts; hermetic
  fixture tests; no snapshot assembly yet.
- **Phase 37K — Repository Observation Snapshot Service MVP** — assemble the §17
  MVP snapshot over the adapter; deterministic ordering, overflow, warnings;
  backend-only.
- **Phase 37L — Repository Observation API Foundation** — a thin, read-only
  endpoint over the snapshot service (mirroring the Phase 37F pattern); no
  persistence.
- **Phase 37M — Read-Only Repository Observer Frontend Inspector** — implemented
  a read-only inspector over the observation snapshot (mirroring the Phase 37G
  pattern).
- **Phase 37N — Repository Observer Frontend Integration QA + Hardening** —
  verified and lightly hardened the Phase 37M inspector.
- **Phase 37O — Deterministic Repository Drift Analysis MVP** — implemented
  backend-only read-only working-state drift analysis from the current `HEAD`
  baseline, without persistence or ingestion.
- **Phase 37P and later — Active Memory Repository Evidence Ingestion,
  contradiction integration, and end-to-end QA** — separate future decisions
  that turn observer output into candidate records/evidence, feed eligible
  contradictions into the Phase 37D detector, and validate the full path; owned
  outside the observer.

Each phase remains independently scoped and reviewable, and none is authorized by
this planning phase.

### 20.1 Phase 37J implementation reconciliation

Phase 37J later implemented the planned Git adapter foundation only. The
implemented backend module is
`apps/backend/app/services/repository_git_adapter.py`, with tests in
`apps/backend/tests/test_repository_git_adapter.py`. It uses an internal
allowlist of read-only Git commands, argument-array execution with `shell=False`,
explicit repository `cwd`, a 5 second per-command timeout, 262,144 stdout bytes,
8,192 stderr bytes, 512-character bounded excerpts, and a 200 file-observation
limit. It parses NUL-delimited porcelain-v2 status output and converts direct Git
evidence into the existing Phase 37I `repo-observer.v1` contracts with
deterministic path ordering, warning records, limitations, overflow metadata, and
honest completeness.

The implementation does not change this planning document's deferred scope:
there is still no snapshot service phase, API route, watcher, polling loop,
filesystem crawler, source-file reading, persistence, Active Memory ingestion,
GitHub integration, frontend visibility, AI/LLM behavior, automatic remediation,
or repository mutation.

---

## 21. Contradiction opportunities

Deterministic contradictions the observer's output could eventually enable, split
by whether local observation alone suffices.

### 21.1 Immediately deterministic (local Git evidence only)

- **completion report says tree is clean while observation shows changes** — clean
  vs. dirty (aligns with the implemented `clean_vs_dirty_working_tree` class).
- **a report says a file was untouched while the diff contains that file** —
  path present in changed-file summary.
- **local `main` described as aligned while it is ahead or behind upstream** —
  ahead/behind counts contradict "aligned".
- **a branch described as deleted while it still exists locally** — local ref
  present.
- **a commit hash that does not exist** — resolution fails.
- **documentation says a phase is merged but the commit is not reachable from
  `main`** — reachability query is local and deterministic (given a non-shallow
  clone).
- **a branch created from the wrong base** — merge-base/ancestry is locally
  checkable (bounded, non-shallow).
- **README and roadmap disagree** — two parsed local doc markers conflict.
- **repository remote does not match the expected project remote** — normalized
  remote vs. an expected value.

### 21.2 Requires external GitHub or execution evidence

- **documentation says a phase is active while GitHub shows the PR merged** — PR
  state is remote; local history does not prove it.
- **a report says tests passed without attached validation evidence** — needs
  validated CI/execution output; test files existing proves nothing.
- **a branch described as deleted while it still exists remotely** — remote ref
  state needs verified GitHub evidence.
- **pending vs. merged where "merged" means the PR merged** — the local
  `pending_vs_merged` class compares *stored claims*; proving actual remote merge
  needs GitHub evidence.

The observer must classify each opportunity's evidence requirement and **never
assert a §21.2 contradiction from local data alone**. Finalizing any contradiction
is the Phase 37D detector's job (Phase 37N integration), not the observer's.

---

## 22. Acceptance criteria

Phase 37H is complete only when:

- the work is documentation-only;
- the Repository Observer product problem is clearly defined (§1–§2);
- observer responsibilities and non-responsibilities are explicit (§7);
- repository identity is planned (§6);
- the observation snapshot contract is planned (§8);
- the evidence hierarchy is defined (§10);
- Active Memory integration boundaries are defined (§11);
- deterministic contradiction opportunities are documented (§21);
- security and trust boundaries are documented (§9);
- bounded behavior and overflow rules are documented (§12–§13, §16);
- the MVP is narrow and implementable (§17);
- future phases are sequenced (§20);
- the README remains product-focused;
- roadmap status is consistent;
- Phase 36K remains paused and untouched;
- no source, tests, schemas, dependencies, or runtime behavior are changed.

---

## 23. Open questions requiring later implementation decisions

- **Repository ID algorithm** — remote-derived vs. path-derived vs. combined;
  collision handling; normalization rules for remote URLs (§6.2). Not finalized
  here.
- **Identity persistence** — whether/where observed identity is stored, and how it
  correlates observations over time.
- **Reachability cost** — how to bound reachability/ancestry queries on large or
  shallow repositories without weakening the deterministic guarantee.
- **Documentation-marker parsing** — which structured markers count as
  "documentation status" and how strictly to parse them.
- **Externally supplied evidence contract** — the exact shape by which a validated
  execution/CI/GitHub source hands evidence to the observer.
- **Trigger cadence beyond MVP** — if/when session-triggered or watched observation
  is justified, and its concurrency/security controls.
- **Timezone-aware timestamps** — align with the Active Memory open question on
  strict UTC-aware timestamps (37B §11.4).
- **Snapshot schema evolution** — versioning and migration of `repo-observer.v1`
  once real consumers exist.

These are recorded so they are decided deliberately in later phases, not silently
assumed at implementation time.
