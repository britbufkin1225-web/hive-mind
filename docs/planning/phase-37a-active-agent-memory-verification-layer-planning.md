# Phase 37A — Active Agent Memory + Verification Layer Planning

**Phase:** Phase 37A — Active Agent Memory + Verification Layer Planning.
**Track:** Track 2 — Agent Intelligence Infrastructure (parallel to Track 1 —
Spatial Interaction, whose active implementation phase remains **Phase 36K —
Full-Hand Gesture Live Camera QA + Control Tuning**).
**Status:** Planning / architecture / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, model,
database, package, dependency, lockfile, build/runtime configuration,
screenshot, or demo-evidence change. **No persistence, no in-memory store, no
API route, no frontend component or overlay, no ingestion, no report parser,
no repository watcher, no contradiction engine, no active-state code, no
context-packet code, no AI/LLM processing, no embeddings, no vector search,
no graph mutation, no autonomous memory mutation, no new dependency.**
**Relationship:** Defines a *new* Track-2 architecture. It does **not** displace,
rewrite, or complete Phase 36K, and it does **not** claim that live gesture
tuning is finished. It complements — without depending on, or being depended
on by — the existing Hive|Mind intelligence surfaces (Source Registry,
Knowledge Graph, Intelligence Report, Provenance Chains, Query Trails,
Temporal Knowledge Decay). Pairs with the reusable
[Active Agent Memory + Verification Layer reference](../active-agent-memory-verification-layer.md),
the [roadmap](../roadmap.md), and the [README](../../README.md) phase table.

> **One-line framing.** Chat history remembers *that something was said*.
> This layer is meant to remember *what is currently true*, *why we believe
> it*, and *when to stop believing it* — as small, evidence-backed,
> supersedable records, computed into a trustworthy pre-action baseline, with
> humans keeping authority over decisions and mutation. Phase 37A writes the
> concept. It ships no runtime.

---

## 1. Executive summary

### 1.1 What the layer is

The **Active Agent Memory + Verification Layer** (hereafter "the layer") is a
proposed subsystem that stores project knowledge as small, typed, immutable
**memory records** — each carrying a single **claim** (for example, "Phase 36J
is merged into `main`", "gesture control is opt-in and off by default", "the
canonical repo path is `C:\Users\britb\Documents\hive-mind`"). Each record
carries **evidence references**, a **verification state**, a **source
authority**, timestamps, and optional **supersession** links to the record it
replaces. From the accumulated records, the layer deterministically computes an
**active set** — the subset of records considered *currently true* — and can
emit a read-only **context packet**: a bounded, evidence-traceable baseline an
agent or human can read *before* proposing or performing work.

The layer is **not** a chatbot memory, a note dump, or a semantic index. Its
defining behaviors are **verification** (claims are checked against evidence and
labelled with how strongly they are believed) and **supersession** (newer
verified knowledge deactivates older knowledge without erasing history).

### 1.2 Why Hive|Mind needs it

Hive|Mind is built across many sequential "phases", each producing prose
reports (in chat, in commits, in `README.md`, in `docs/roadmap.md`). Those
reports are point-in-time statements. They go stale silently: a report that was
accurate when written ("implemented locally on branch X") becomes misleading
once the world moves on (X was never merged; a later phase superseded the
decision). Nothing today *computes* which of the many overlapping statements is
still true. The result is recurring, concrete pain — contradictory phase-status
claims, "completed" features that never merged, lost decisions, repeated
rediscovery of the same constraints, and agents acting from a wrong baseline
(see §2). The layer exists to make "what is currently true, and how sure are
we?" a **deterministic, inspectable computation** instead of an act of chat
archaeology.

### 1.3 How it differs from chat history, notes, logs, and semantic search

- **Chat history** is an append-only transcript of *utterances*. It preserves
  ordering but has no notion of truth, supersession, or evidence: the newest
  message is not necessarily the most correct, and a retracted claim still sits
  in the log looking authoritative. The layer stores *claims with state*, not
  utterances, and computes activity rather than trusting recency.
- **Notes / docs** are human-authored prose. They are durable and valuable
  (and the layer treats committed docs as *evidence*), but they are unstructured,
  can contradict each other, and carry no machine-checkable verification status.
- **Logs** record events (what happened) rather than durable facts and decisions
  (what is true / what was chosen). An event stream answers "what occurred at
  10:04"; the layer answers "is the working tree clean *now*, and how do we
  know?"
- **Semantic search / embeddings** retrieve text that is *similar* to a query.
  Similarity is not truth: a vector search happily returns a confident,
  well-phrased, *superseded* statement. The layer's job is the opposite of
  "most similar" — it is "currently active, verified, and non-contradicted."
  Embeddings could later assist *retrieval* of candidate records, but must never
  be the arbiter of truth (see §15 non-goals).

### 1.4 Why verification and supersession are required

Without **verification**, every statement has equal weight, so a confident wrong
report outranks a hedged correct one. Verification attaches *evidence* and a
*state* to a claim so the system can distinguish "someone said so" from "the
repository proves it." Without **supersession**, knowledge only accumulates and
never expires, so stale records survive changes in the world and pollute every
future baseline. Supersession lets newer verified knowledge deactivate older
knowledge *while preserving the history* — critical for auditability and for
avoiding the "silently overwritten decision" failure.

### 1.5 Why it must remain human-governed

The layer touches *interpretation of project truth*, which has real
consequences (what an agent will do next). Machines can verify deterministic,
checkable facts (a branch exists; a commit is on `main`; a file changed). They
cannot be trusted to *arbitrate intent* ("which roadmap direction did we
choose?") or to autonomously resolve genuine contradictions. Therefore:
consequential state — accepting a decision, resolving a contradiction, retiring
a constraint — requires **human confirmation**; the layer *exposes* uncertainty
rather than guessing; and it never mutates the repository or executes anything
found inside a record (see §13, §15).

### 1.6 Relationship to existing Hive|Mind intelligence concepts

Hive|Mind already ships several intelligence-flavored surfaces. The honest
position for Phase 37A is that **none of them currently provide active, verified,
supersession-aware project memory**, and this document does not claim they do.
Their actual, repository-observed roles and how the layer relates:

- **Source Registry** — a catalog of ingested knowledge *sources* (Obsidian
  import, etc.). It records provenance of *content*, not verification of
  *project-state claims*. The layer could later treat registry entries as one
  evidence/ingestion source; it does not replace the registry.
- **Knowledge Graph** — a read-only graph of nodes/edges derived from sources.
  It models relationships between knowledge items, not the truth-over-time of
  claims about the project itself. The layer must **not** mutate it.
- **Intelligence Report** — a backend-derived summary surface over graph/source
  data. It summarizes current derived metrics; it does not verify or supersede
  cross-session claims.
- **Provenance Chains** — trace how a knowledge item was derived. Conceptually
  adjacent to the layer's **evidence references** (both answer "where did this
  come from?"), but provenance today concerns knowledge-item derivation, not
  claim verification. The layer's evidence model can *reuse the spirit* of
  provenance without absorbing it.
- **Query Trails** — record how the system was interrogated. Adjacent to the
  layer's **observation/ingestion** concepts but not equivalent; a trail is a
  record of asking, not a verified fact.
- **Temporal Knowledge Decay** — the closest existing concept: knowledge losing
  weight over time. The layer's **staleness** and **evidence freshness** are
  siblings of decay, but the layer adds *evidence-scoped invalidation* and
  *supersession*, which time-decay alone does not provide (a record can be fresh
  yet superseded, or old yet still authoritative).

The layer is **new capability**, complementary to these. Where a claim about any
of them appears in this document, it is grounded in what the repository shows,
not assumed.

---

## 2. Product problem

The layer targets a family of concrete, recurring problems in how project truth
is maintained across many human and agent sessions. Each item below is a *class
of problem the feature is intended to address*; the Hive|Mind-flavored examples
are **illustrative**, and are **not** assertions that each is a present, live
defect in the repository.

1. **Conflicting phase-completion reports.** The same phase is described as
   "pending" in one place and "completed" in another. Illustrative: two session
   summaries disagree on whether a "36-series" phase is done; nothing computes
   which is current.
2. **Feature branches described as completed even when not merged.** A report
   says a phase is "implemented" while the change lives only on a feature branch
   that never reached `main`. (This exact hazard is recorded as real project
   knowledge — see [[phase-31-32-merge-gap]]: "31I/32A/32A.5 are branch-only,
   NOT on main.")
3. **Stale statements surviving repository-state changes.** A "working tree is
   clean" or "branch X is the canonical implementation branch" claim outlives the
   state it described; later readers treat it as still true.
4. **Agents relying on old summaries instead of current repository truth.** A new
   session reads a prior summary and proceeds from it without re-checking the
   repository, inheriting whatever was stale.
5. **User decisions lost across sessions.** A roadmap direction or guardrail the
   user chose in one session is not durably represented, so a later session
   re-opens or contradicts it.
6. **Repeated rediscovery of project rules and constraints.** The same
   constraints (canonical repo path, docs-only phase discipline, read-only graph
   contract, opt-in webcam) are re-derived from scratch each session.
7. **Unverified agent reports treated as facts.** A confidently worded agent
   report is absorbed as truth without evidence (commit, branch, test, merge).
8. **Source-controlled truth disagreeing with conversational summaries.** The
   committed docs/code say one thing; the chat summary says another; no rule
   decides which wins *for that kind of claim*.
9. **Incomplete reports lacking commit / branch / test / merge evidence.** A
   status claim arrives with no attached, checkable evidence, yet is stored as if
   verified.
10. **Actions proposed from an incorrect baseline.** An agent proposes work
    against a wrong assumption about current state (wrong active phase, wrong
    branch, wrong "already done").
11. **Accumulated chat history becoming hard to search and reason about.** The
    signal (current decisions and facts) is buried under a growing transcript;
    "what is true now?" requires archaeology.
12. **Records correct-when-created but later obsolete.** A record can be
    perfectly accurate at write time and simply *age out* of correctness as the
    world changes; the system must model this without calling the original record
    a lie (see §3, *stale* vs *false*).

**Representative Hive|Mind-style scenario (illustrative).** A session summary
states "Phase 36J complete and merged." The roadmap's honest status separately
records that live-camera tuning is *still required* and evidence capture is
*deferred*. A repository-state record shows PR #152 merged the 36J foundation to
`main`, but shows *no* record verifying live-camera tuning. A naive reader could
conflate "the foundation merged" with "the phase's live tuning is done." The
layer's intended behavior: keep "36J foundation merged" as a *verified*
repository-state fact, keep "live-camera tuning complete" as an *unverified*
capability claim (no evidence), and surface the gap in the context packet —
rather than letting one confident sentence imply both. (This mirrors the honest
status already written into the roadmap and [[phase-32i-live-webcam-hardware-blocker]].)

---

## 3. Terminology

A stable vocabulary for Phase 37B contracts. These are **conceptual**
definitions, not schemas.

- **Memory record** — the atomic stored unit: one claim plus its metadata
  (evidence references, verification state, source authority, timestamps,
  identity, lifecycle/verification states, optional supersession links).
  Conceptually **immutable**; changes are represented by appending new records
  or new state entries (see §9).
- **Claim** — the single proposition a record asserts (a subject + predicate +
  value, e.g. subject "Phase 36J", predicate "merge-status", value "merged into
  main"). A claim is the *content*; a record is the claim *plus its standing*.
- **Fact** — a claim about how the world *is* (state), independent of anyone's
  preference. Facts are verifiable against evidence. Example: "commit `195f1fc`
  exists."
- **Observation** — a *reported* claim from some observer at a moment, not yet
  verified. Observations are how facts and reports enter the system; an
  observation becomes a (verified) fact only after evidence supports it.
- **Decision** — a claim about what the project *chose* to do or value (intent).
  Decisions are not verified true/false against the repository; they are
  *authored* by humans and can be *superseded* by later decisions. Example:
  "gesture control stays opt-in and off by default."
- **Constraint** — a durable rule the project agrees to hold (a special,
  long-lived decision). Example: "docs-only phases must not edit source." Active
  until explicitly retired by a human.
- **Phase status** — a claim about a phase's lifecycle position (planned /
  in-progress / implemented-on-branch / merged / verified / deferred).
- **Repository state** — a claim about checkable VCS/build reality (branch
  exists, commit exists, PR merged, tree clean, files changed, test command
  result). The most machine-verifiable claim category.
- **Capability** — a claim that some behavior exists and works (e.g. "elastic
  node-pull is implemented", "live-camera gesture tuning is complete"). Verified
  by code/test/runtime evidence, *scoped* to what the evidence actually shows.
- **Evidence** — any artifact that supports or refutes a claim (command output,
  commit id, PR state, source reference, test/CI output, runtime response,
  screenshot, committed doc, structured report, human confirmation).
- **Evidence reference** — a stored, *inspectable* pointer to a piece of evidence
  (e.g. a commit hash, a file path + line range, a PR number, a captured command
  output id), with type, scope, source, and timestamp — never opaque prose.
- **Verification** — the act/result of checking a claim against its evidence and
  assigning a verification state. Deterministic for MVP; never LLM-arbitrated.
- **Verification state** — how strongly the claim is currently believed given its
  evidence (§7). Distinct from lifecycle state.
- **Trust** — a *policy* input: how much authority a given source type carries
  *for a given claim category* (§5). Trust is not the same as truth; a
  high-trust source can still be wrong or unevidenced.
- **Confidence** — a graded belief signal (may be qualitative bands, not
  necessarily a single float) reflecting evidence strength/agreement. **Distinct
  from verification state**: confidence describes *how strong the support is*;
  verification state describes *what standing the claim has*.
- **Contradiction** — a detected incompatibility between two (or more) records
  under a deterministic rule (§8). Not every difference is a contradiction.
- **Contradiction class** — the taxonomy category a contradiction falls under
  (§8), used to route handling and to scope MVP vs later work.
- **Supersession** — an explicit relationship where a newer record *replaces* an
  older one for the same subject/scope (typically decisions and evolving facts).
  The superseded record becomes inactive but remains stored and queryable.
- **Retraction** — an explicit statement that a record was wrong and should no
  longer be considered active (distinct from supersession, which is "replaced by
  something newer/better", not "was wrong").
- **Active record** — a record the deterministic active-state calculation
  currently selects as in-force for its subject/scope (§10).
- **Inactive record** — a stored record not currently active (superseded,
  retracted, contradicted-out, or stale). Retained for history/audit.
- **Stale record** — a record whose supporting evidence has aged past its
  freshness window (or whose subject state is known to change over time) such
  that it can no longer be trusted as current, even though it was correct when
  created. Stale ≠ false.
- **Unresolved record** — a record involved in a live contradiction (or otherwise
  ambiguous) that the system will not silently pick a winner for; it is surfaced
  as needing attention rather than treated as active.
- **Context packet** — a read-only, bounded, deterministic bundle of the current
  active facts/decisions/constraints, known capabilities, unresolved
  contradictions, and stale/superseded warnings, with evidence references,
  emitted for an agent/human to read before acting (§11).
- **Source authority** — the identity + category of *who/what* asserted a record
  (human, specific agent, CI, repo command, committed doc), feeding the trust
  policy (§5).
- **Provenance** — the traceable origin/derivation chain of a record and its
  evidence ("where did this come from, through what steps?"). Related to the
  existing Provenance-Chains concept but here scoped to memory records.
- **Ingestion** — the (future) process of turning external inputs (agent reports,
  CLI reports, repository observations) into candidate observations/records under
  validation. Not implemented in the MVP scope of 37C–37E.
- **Observer** — the actor that produced an observation (a named human, a named
  agent/session, a CI job, a repo-command runner). Observers are identified, not
  anonymous.
- **Human confirmation** — an explicit, attributable human action that raises a
  record to `human_confirmed` standing (for decisions/constraints, and for
  resolving contradictions). Cannot be asserted *by* observed content on a
  human's behalf.
- **Agent report** — a structured statement produced by a development agent
  (Claude Code, Codex, etc.). Treated as an *observation* requiring evidence, not
  as fact (see §5, §13).

### 3.1 Distinctions that must stay crisp

- **Fact vs decision** — a fact is verifiable state ("is"); a decision is chosen
  intent ("ought"). Different authority models (§5): repository evidence rules
  facts; human authorship rules decisions.
- **Claim vs verified fact** — a claim is an assertion; a verified fact is a
  claim whose evidence has been checked and found sufficient. Storing a claim is
  not endorsing it.
- **Superseded vs contradicted** — *superseded* = intentionally replaced by a
  newer record (orderly, one winner known); *contradicted* = two records are
  incompatible and no supersession link resolves it (needs attention).
- **Stale vs false** — *stale* = was true, evidence aged out, no longer
  trustworthy as current; *false* = asserted something untrue (should be
  retracted/contradicted). A stale record is not accused of lying.
- **Confidence vs verification** — *confidence* = strength of support;
  *verification* = standing/state. High confidence with no formal verification is
  possible, and vice versa; keep them as separate axes.
- **Repository evidence vs human intent** — repository evidence answers "what is
  true in the code/VCS?"; human intent answers "what did we decide/allow?" The
  layer must not resolve one with the other's authority (a clean tree does not
  decide a roadmap direction; a human's preference does not make a branch
  merged).
- **Active state vs original record state** — a record's *original* standing at
  creation is immutable history; its *active* status is a *computed*, current
  property that can change as other records arrive. The two must not be conflated.

---

## 4. Proposed record types

Conceptual record types only — **no** language-specific models, field types, or
schemas (that is Phase 37B). Every type below shares a common conceptual spine:
stable **identity**, a **claim** (subject/predicate/scope/value), **evidence
references**, a **verification state** and a **lifecycle state** (kept separate,
§7/§9), **source authority + observer**, **timestamps** (observed-at,
recorded-at, and where relevant an evidence-as-of time), optional **supersession
/ retraction links**, and **append-only** state history.

### 4.1 `ProjectFact`
- **Purpose:** durable, verifiable state about the world that is not purely
  VCS-mechanical (e.g. "the graph has 7 nodes / 6 edges in the demo dataset").
- **Example claims:** "the demo dataset is 7 nodes / 6 edges"; "the canonical
  repo path is `C:\Users\britb\Documents\hive-mind`."
- **Required conceptual fields:** identity, subject, predicate, value, evidence
  references, verification state, source authority, timestamps.
- **Optional:** scope qualifiers, confidence band, supersession link, notes.
- **Identity / dedup:** keyed by subject + predicate + scope; a new observation
  of the same key updates (via a new record) rather than duplicating.
- **Evidence:** at least one evidence reference to reach `verified`.
- **Verification:** deterministic where checkable; else `unverified`/
  `human_confirmed`.
- **Lifecycle:** may become stale (evidence freshness) or superseded (value
  changed).
- **Supersession:** later fact for the same key supersedes earlier.
- **Human approval:** not required to *record*; may be required to *retire*.
- **In context packet:** yes, when active.

### 4.2 `ProjectDecision`
- **Purpose:** a chosen direction / accepted behavior / prioritization.
- **Example claims:** "gesture control stays opt-in, off by default"; "Track 1
  active implementation phase is 36K"; "adopt Track 2 agent-intelligence
  infrastructure."
- **Required fields:** identity, subject, decision statement, deciding human
  (observer), rationale/notes, timestamps, verification state.
- **Optional:** supporting evidence references (committed docs), supersession
  link, scope, review status.
- **Identity / dedup:** keyed by decision subject/topic; a newer decision on the
  same topic supersedes.
- **Evidence:** committed docs are *supporting* evidence, not the authority; the
  authority is the human. A decision can be active with human authorship and no
  repository evidence yet.
- **Verification:** reaches `human_confirmed` by explicit human action; not
  machine-"verified true".
- **Lifecycle:** active until superseded/retracted by a human; decisions do not
  go *stale* by mere time (they are intent, not perishable state) — but may be
  flagged if their supporting evidence disappears.
- **Supersession:** central; supersession chains represent decision evolution.
- **Human approval:** required to become authoritative.
- **In context packet:** yes (active decisions are core baseline).

### 4.3 `ProjectConstraint`
- **Purpose:** a durable guardrail the project holds itself to.
- **Example claims:** "docs-only phases must not edit source"; "graph stays
  read-only"; "no new dependencies without explicit approval."
- **Required fields:** identity, constraint statement, authoring human,
  timestamps, verification state, active/retired lifecycle.
- **Optional:** rationale, scope (which phases/areas), supporting evidence
  (CLAUDE.md / guardrail docs), supersession link.
- **Identity / dedup:** keyed by constraint topic; retirement/replacement is
  explicit and human.
- **Evidence:** committed guardrail docs are strong supporting evidence.
- **Verification:** `human_confirmed`.
- **Lifecycle:** long-lived; retired only by explicit human action, never by
  staleness.
- **Supersession:** a revised constraint supersedes the prior.
- **Human approval:** required.
- **In context packet:** yes (active constraints are prohibitions/guardrails an
  agent must see before acting).

### 4.4 `PhaseStatusRecord`
- **Purpose:** track a phase's lifecycle position with evidence.
- **Example claims:** "Phase 36J foundation merged into `main` (PR #152)";
  "Phase 37A is documentation-only, in progress"; "Phase 36K live-camera tuning:
  not yet verified."
- **Required fields:** identity, phase id, claimed status, evidence references,
  verification state, source authority, timestamps.
- **Optional:** branch, PR reference, scope note (e.g. "foundation only, tuning
  pending"), supersession link.
- **Identity / dedup:** keyed by phase id + status dimension; multiple
  *incompatible active* statuses for one phase is a contradiction trigger (§8).
- **Evidence:** merge/branch/PR/commit evidence required for merged/verified
  claims.
- **Verification:** deterministic against repository-state evidence where
  possible.
- **Lifecycle:** an "in progress" record is superseded by a "merged" record when
  evidence supports it; the old one becomes inactive, not deleted.
- **Supersession:** yes, along the phase's progression.
- **Human approval:** not required to record; human confirmation may finalize
  "verified/complete" for non-mechanical criteria (e.g. "tuning feels right").
- **In context packet:** yes — active phase + verified-completed phases.

### 4.5 `RepositoryStateRecord`
- **Purpose:** capture point-in-time, machine-checkable VCS/build reality.
- **Example claims:** "working tree clean at T"; "branch
  `phase-37a-…` exists"; "commit `e196c41` is HEAD of `main`"; "`git diff
  --check` clean."
- **Required fields:** identity, subject (branch/commit/tree/command), asserted
  value, evidence reference (command output / VCS query), as-of timestamp,
  observer.
- **Optional:** command invocation details, host identity, scope.
- **Identity / dedup:** keyed by subject + as-of; inherently time-bounded.
- **Evidence:** the command output / VCS query *is* the evidence; a repo-state
  claim without such evidence is weak by policy.
- **Verification:** `verified` only with attached machine evidence; freshness
  matters most here.
- **Lifecycle:** **expires quickly** — repo state is perishable; these records go
  *stale* by design after a short freshness window and must not be treated as
  current beyond it.
- **Supersession:** a newer as-of observation supersedes the older for the same
  subject.
- **Human approval:** not required.
- **In context packet:** only the *freshest* repo baseline, explicitly
  timestamped; stale ones are excluded or shown as warnings.

### 4.6 `CapabilityRecord`
- **Purpose:** assert that a behavior exists and works, scoped to evidence.
- **Example claims:** "elastic node-pull implemented (`spatialHiveElasticity.ts`)";
  "full-hand tracking foundation implemented"; "live-camera gesture *feel* —
  unverified."
- **Required fields:** identity, capability subject, claimed state
  (present/absent/partial), evidence references, verification state, timestamps,
  source authority.
- **Optional:** scope (what the evidence actually demonstrates vs not), related
  phase, supersession link.
- **Identity / dedup:** keyed by capability subject; partial/scoped claims must
  encode their scope to avoid over-claiming.
- **Evidence:** source references + tests + runtime; **screenshots prove only
  visible UI state, not merge/behavioral correctness** (§6).
- **Verification:** scoped — "implemented" verified by code/test does *not* imply
  "validated live"; those are separate capability claims.
- **Lifecycle:** may go stale if code changes; may be superseded by a later
  capability observation.
- **Supersession:** yes.
- **Human approval:** may be required for subjective capability ("feel is good").
- **In context packet:** yes — known verified capabilities + explicit
  unverified/partial gaps.

### 4.7 `EvidenceRecord`
- **Purpose:** a first-class, inspectable record *of a piece of evidence*, so
  multiple claims can reference the same evidence and its freshness/validity can
  be tracked centrally.
- **Example claims:** "command output of `git status --short` at T = clean";
  "PR #152 state = merged"; "file `spatialHiveElasticity.ts` exists at commit C."
- **Required fields:** identity, evidence type (§6), content reference (hash /
  path+range / PR id / captured-output id), scope, source, timestamp.
- **Optional:** validity/expiry window, invalidation link, host/observer.
- **Identity / dedup:** keyed by type + content reference; identical evidence is
  shared, not duplicated.
- **Evidence:** it *is* the evidence; but it must be a *reference*, never
  executable content and never trusted prose.
- **Verification:** an evidence record's own trust derives from its type/source
  and freshness, not from being present.
- **Lifecycle:** can be **invalidated** (repo moved on) which cascades to
  freshness of referencing claims.
- **Supersession:** newer evidence for the same subject can supersede.
- **Human approval:** not required (except human-confirmation evidence, which is
  itself a human action).
- **In context packet:** referenced (for traceability), not necessarily inlined
  in full.

### 4.8 `ContradictionRecord`
- **Purpose:** record a detected incompatibility between records under a
  deterministic rule, with its class and involved records.
- **Example claims:** "PhaseStatusRecord A (pending) contradicts B (merged) for
  Phase X, with no merge evidence for B."
- **Required fields:** identity, contradiction class (§8), references to the
  conflicting records, the rule that fired, detection timestamp, resolution
  status.
- **Optional:** suggested (non-authoritative) resolution, human-resolution link.
- **Identity / dedup:** keyed by the set of involved records + class; a
  re-detected identical contradiction updates rather than floods (see §13
  contradiction-flooding risk).
- **Evidence:** references the evidence (or lack thereof) that made the conflict
  deterministic.
- **Verification:** the *detection* is deterministic; the *resolution* is human
  or supersession-driven.
- **Lifecycle:** open → resolved (by supersession, retraction, or human
  decision) → archived; never auto-resolved by the layer choosing a winner.
- **Supersession:** not typically superseded; resolved and retained.
- **Human approval:** required to resolve consequential contradictions.
- **In context packet:** yes — **unresolved contradictions are a first-class
  section** (agents must see them before acting).

### 4.9 `VerificationRecord`
- **Purpose:** an append-only record of a verification *event* — what was
  checked, against what evidence, with what outcome, by whom/what.
- **Example claims:** "PhaseStatusRecord P checked against PR-merge evidence at T
  → verified"; "CapabilityRecord C checked → partially_verified (code present,
  no live test)."
- **Required fields:** identity, target record reference, evidence references
  considered, resulting verification state, checker identity (deterministic
  rule / human), timestamp.
- **Optional:** notes, superseded-by-later-verification link.
- **Identity / dedup:** keyed by target + checker + timestamp; verifications
  accrete as history.
- **Evidence:** references the evidence it weighed.
- **Verification:** it *is* the verification trail; supports auditability.
- **Lifecycle:** immutable event; a later verification can update the target's
  current state without erasing the earlier event.
- **Supersession:** later verification supersedes earlier *for the target's
  current state*, but both events remain.
- **Human approval:** human verifications are attributable human actions.
- **In context packet:** summarized (verification summary), not fully inlined.

### 4.10 `ContextPacket`
- **Purpose:** the read-only, deterministic, bounded output bundle (§11). It is a
  *derived view*, not a stored source of truth; conceptually a record type for
  contract purposes only.
- **Example content:** active baseline (repo state, active phase, verified
  completed phases, active decisions/constraints, known capabilities), unresolved
  contradictions, stale/superseded warnings, evidence references, verification
  summary, generation timestamp, prohibited-assumptions list.
- **Required fields:** generation timestamp, the included active records (by
  reference), contradiction section, warnings section, evidence references.
- **Optional:** scope/filter used, ordering key.
- **Identity / dedup:** ephemeral/derived; identified by generation time + input
  snapshot.
- **Evidence:** carries references through so every asserted line is traceable.
- **Verification:** reflects the verification state of its constituents; adds
  none of its own.
- **Lifecycle:** generated on demand, read-only, not authoritative storage.
- **Supersession:** each generation supersedes the prior *view* (not the
  underlying records).
- **Human approval:** not required to read; must never perform mutation.
- **In context packet:** it *is* the packet.

---

## 5. Trust model

The trust model is **domain-aware**: authority depends on the *claim category*,
not a single global ranking. A naive "source type X always beats Y" rule is
wrong here — the repository is the authority on whether a branch merged, but the
*human* is the authority on which roadmap direction was chosen.

### 5.1 Authority by claim category

**Repository-state claims** (branch/commit exists, PR merged, tree clean, files
changed, test command result). Machine-generated repository/CI evidence normally
**outranks** unsupported conversational statements. A confident chat claim of
"merged" loses to VCS evidence of "no merge." Human statements do not *make* a
branch merged; they can only prompt a re-check.

**Product-intent claims** (selected roadmap direction, accepted guardrails,
approved design behavior, user priority, deferred-feature decisions). Explicit
**human decisions are authoritative**. Committed documentation provides *durable
supporting evidence* (and helps detect drift), but the human's decision, not the
doc, is the authority. Repository evidence cannot *override* an intent decision
(code doing X does not prove the project *chose* X — it may be unfinished, or a
bug).

**Implementation-behavior claims** (frontend behavior exists, endpoint contract
changed, persistence added, gesture control opt-in, graph mutation absent).
**Source code, tests, runtime evidence, and committed docs are weighed
together**, scoped to what each actually demonstrates. Code presence supports
"implemented"; a passing test supports "works for the tested cases"; a runtime
response supports "behaves so at runtime"; a screenshot supports "looked like
this." None alone proves the whole claim; the verification is *scoped* to the
evidence.

### 5.2 Handling the hard cases

- **Strong evidence supporting a low-authority source.** Evidence can lift a
  low-authority observation: a chat report *with* attached VCS/test evidence is
  treated on the strength of the *evidence*, not the speaker. Trust gates the
  *unevidenced* case; evidence is what actually verifies.
- **High-authority statements without evidence.** A high-authority source (even a
  human) asserting a *repository-state* claim without evidence yields at most an
  `unverified` fact — recorded, surfaced, but not `verified`. (For *intent*
  claims, a human's word *is* the authority, so this differs by category.)
- **Multiple evidence items.** Aggregate (§6.2): concordant evidence raises
  confidence; the strongest-scope, freshest evidence dominates; conflicting
  evidence triggers contradiction handling rather than silent averaging.
- **Evidence covering only part of a claim.** Verification is scoped to the
  covered part; the uncovered part stays unverified. ("Code exists" verified;
  "works live" not.) Over-claiming is prevented by recording scope.
- **Evidence that later becomes stale.** Freshness invalidation demotes the
  claim's standing (verified → stale) without deleting it (§6, §9).
- **Human overrides.** A human may confirm, retract, or resolve; the override is
  itself an attributable, stored action (a human-confirmation event), never
  silent, and never assertable by observed content on the human's behalf (§13).
- **Unverifiable claims.** Claims with no checkable evidence and no human
  authority remain `unverified`/`unresolvable` and are surfaced as such — never
  promoted by confidence of phrasing.
- **Conflicting machine and human evidence.** Resolve *by category*: for a
  repository-state claim, machine evidence wins and any human "it's merged" is
  flagged as unsupported; for an intent claim, the human decision wins and code
  is treated as (possibly incomplete) implementation, not intent. Cross-category
  conflicts (a human claims a *fact*) are surfaced, not silently reconciled.
- **Source-specific authority.** Every record carries source authority +
  observer so the policy can apply the right rule; anonymous or unidentified
  sources get the weakest treatment.

### 5.3 Trust principles

Trust is a *policy layer over evidence*, not a substitute for it. It decides
what happens when evidence is *absent or partial*. Where evidence is present and
in-scope, evidence governs. Trust must be **deterministic and inspectable** for
the MVP (a fixed category→authority policy), never an LLM judgment.

---

## 6. Evidence hierarchy

Evidence answers "why should this claim be believed?" The model ranks evidence
by *strength for the claim it is being used to support*, and always records
*scope* so evidence is not stretched beyond what it shows.

### 6.1 Proposed strength ordering (claim-relative, strongest first)

1. **Explicit human confirmation** — for *intent* claims (decisions,
   constraints, subjective capability). Authoritative for what the project chose;
   not proof of repository facts.
2. **Repository command output / VCS queries** — commit ids, branch refs,
   PR-merge state, `git status`/`git diff --check`, file existence at a commit.
   Strongest for *repository-state* claims.
3. **Test output / CI output** — proves behavior *for the tested cases* and the
   environment that ran; strong for *implementation-behavior* claims within test
   scope.
4. **Runtime API responses** — proves runtime behavior at observation time; good
   for behavior claims, perishable.
5. **Source-code references** — file + line range at a commit; proves code
   *exists/shape*, not that it runs correctly.
6. **Source-controlled documentation** — committed docs; durable supporting
   evidence, especially for intent (records what was written down) and scope.
7. **Structured CLI reports / structured agent reports** — machine-shaped
   reports; only as strong as the evidence references they *carry* (a report
   asserting "merged" is weak unless it includes VCS evidence).
8. **Screenshots** — prove *visible UI state* at capture time; **do not** prove
   merge status, branch state, or non-visible behavior.
9. **Video evidence** — proves an observed sequence occurred on screen; scoped
   like screenshots, plus temporal behavior; still not proof of VCS/merge facts.
10. **Conversational summaries** — human/agent prose; weakest as *evidence*
    (though a human's prose *decision* is authoritative as *intent*, that is the
    trust model, not evidence strength).
11. **Inferred / reconstructed context** — lowest; never sufficient alone; must
    be re-verified.

### 6.2 Scope discipline (worked examples)

- A **screenshot** may demonstrate the graph rendered with 7 nodes; it may **not**
  prove the branch was merged or that gesture control works live.
- A **clean `git status`** proves working-tree state *at that moment*; it does
  **not** prove runtime behavior or that a feature works.
- A **commit hash** proves a commit *exists*; it does **not** prove that commit
  is on `main` (that needs a merge/branch query).
- A **passing test** proves the tested cases pass in that environment; it does
  **not** prove untested paths or subjective "feel."

### 6.3 Evidence dimensions the model must carry

- **Strength** — claim-relative rank (above).
- **Scope** — exactly what the evidence demonstrates (and, implicitly, what it
  does not).
- **Freshness** — how current; each evidence type has a different perishability
  (repo-state: minutes/short; committed doc: durable; human decision: durable
  until superseded).
- **Source** — who/what produced it (feeds §5).
- **Timestamp** — when captured / as-of.
- **References** — inspectable pointer(s), never opaque or executable content.
- **Invalidation** — a signal/link that this evidence is no longer valid (repo
  moved on, superseded), cascading to referencing claims' freshness.
- **Aggregation** — how multiple evidence items combine: concordant in-scope
  evidence raises confidence and can jointly verify; the freshest, strongest,
  in-scope item dominates; discordant evidence produces a contradiction, not an
  average.

---

## 7. Verification states

The layer separates **verification state** (how strongly a claim is believed
given evidence) from **lifecycle state** (§9, where the record sits in its life:
active/superseded/retracted/archived). Overloading both into one enum makes
"superseded" (a lifecycle fact) and "contradicted" (a truth signal) ambiguous;
they are kept distinct axes.

### 7.1 Proposed verification states

- **`unverified`** — recorded, no sufficient evidence checked yet. Default entry
  state for observations.
- **`partially_verified`** — some in-scope evidence supports part of the claim;
  other parts remain unproven (e.g. code exists, live behavior untested).
- **`verified`** — sufficient in-scope, fresh evidence supports the claim under
  the deterministic rules for its category.
- **`human_confirmed`** — an attributable human explicitly affirmed the claim
  (primary path to authority for *intent* claims; can also over-attest a fact,
  recorded as human-attested).
- **`contradicted`** — an active deterministic contradiction involves this record
  and it is not the resolved winner; it must not be treated as active.
- **`superseded`** — a newer record replaced it (this is *also* reflected in
  lifecycle; carried here so the verification view is self-consistent).
- **`retracted`** — explicitly withdrawn as wrong.
- **`stale`** — its supporting evidence aged past freshness; was believable, no
  longer trustworthy as current.
- **`unresolvable`** — cannot be verified (no checkable evidence, no human
  authority) and cannot be safely activated; surfaced as uncertainty.

### 7.2 Rules and interactions

- **Permitted transitions (illustrative):** `unverified` →
  `partially_verified` → `verified`; any → `human_confirmed` (by human action);
  `verified`/`human_confirmed` → `stale` (freshness lapse); any active →
  `superseded` (newer record) or `retracted` (explicit) or `contradicted` (rule
  fires). Terminal-ish states (`retracted`, `superseded`) are not silently
  reverted; a *new* record is created instead.
- **Mutual exclusivity:** a record has exactly one *current* verification state,
  but its full **history** of verification events is retained (VerificationRecord,
  §4.9). "Current" is a computed head over an append-only trail.
- **Separation from lifecycle:** verification state answers "believe it?";
  lifecycle answers "is it in force?". `superseded`/`contradicted` appear in both
  views intentionally, but the canonical lifecycle transition is recorded once
  and mirrored, not duplicated as independent truth.
- **Who may assign:** deterministic rules assign `unverified`/
  `partially_verified`/`verified`/`stale`/`contradicted`/`superseded`/
  `unresolvable`; only humans assign `human_confirmed` and only humans (or an
  explicit supersession/retraction) finalize consequential resolutions.
- **Evidence required:** `verified` needs in-scope, fresh evidence of adequate
  strength for the category (§5/§6); `partially_verified` needs evidence for the
  covered part; `stale` is triggered by freshness lapse of previously sufficient
  evidence; `human_confirmed` needs an attributable human action.
- **Human vs machine interaction:** human confirmation can raise standing for
  intent; it does **not** fabricate repository facts (a human cannot make an
  unmerged branch "verified merged" — that stays human-attested/unverified until
  VCS evidence exists). Machine verification can flag a human-confirmed *fact* as
  unsupported, surfacing the mismatch rather than overriding silently.
- **Context-packet eligibility:** only `verified`, `human_confirmed`, and
  clearly-scoped `partially_verified` records may enter the active baseline;
  `contradicted`/`unresolvable` appear only in the *contradictions/uncertainty*
  sections; `stale`/`superseded` appear only as *warnings*, never as current
  baseline.

---

## 8. Contradiction classes

A taxonomy for *deterministic* incompatibility. Phase 37D will implement only a
narrow MVP subset; the taxonomy names both the MVP classes and later ones, and
distinguishes true contradictions from mere differences.

### 8.1 MVP contradiction classes (targeted for Phase 37D)

1. **Duplicate phase status.** Same phase with incompatible active statuses
   (pending *and* completed), or multiple branches each claiming to be *the*
   canonical implementation branch for one phase. Fires when two active
   `PhaseStatusRecord`s for one phase assert mutually exclusive states.
2. **Pending vs merged.** One record says "implemented locally / on branch,"
   another says "merged into `main`," and repository evidence shows no merge (or
   a stale pending record persists after a *verified* merge). Directly targets
   the [[phase-31-32-merge-gap]] hazard.
3. **Frontend-only vs backend modifications.** A phase constrained to
   frontend-only work while evidence lists backend files changed; or a "no API
   changes" claim while schema/API files changed. Fires on constraint-vs-evidence
   incompatibility.
4. **Current vs superseded decision.** A newer approved decision replaces an
   earlier direction, but *both* remain marked active (so an agent could act on
   the older one). Fires when two active `ProjectDecision`s cover the same topic
   with no supersession link resolving them.
5. **Clean vs dirty working-tree reports.** Two reports assert incompatible
   working-tree states for overlapping time and repository context; or a "clean"
   report lacks repository evidence; or an old "dirty" record remains active
   after a later *verified* "clean" state.

### 8.2 Later contradiction classes (named, not MVP)

Test-passed vs failing CI; capability-implemented vs missing-code; dependency-
unchanged vs lockfile-modified; no-persistence vs database-migration; read-only
vs mutation behavior; endpoint-unchanged vs contract-change; security-constraint
vs unsafe-implementation; evidence-scope mismatch; temporal conflict; identity
collision; incompatible human decisions.

### 8.3 Difference vs contradiction (what does *not* fire)

Not every difference is a contradiction. Distinguish:

- **Direct contradiction** — two records make incompatible claims about the same
  subject/scope at overlapping validity → contradiction.
- **Temporal replacement** — a newer record supersedes an older via an explicit
  link → *not* a contradiction (orderly supersession).
- **Missing evidence** — a claim lacks evidence → *unverified*, not a
  contradiction (unless it collides with an evidenced counter-claim).
- **Scope mismatch** — two records describe different scopes that only *look*
  similar → not a contradiction; may need scope clarification.
- **Ambiguity** — under-specified subject/scope prevents a deterministic verdict
  → surfaced as *unresolved/ambiguous*, not asserted as contradiction.
- **Duplicate records** — same claim recorded twice → dedup, not contradiction.
- **Stale record** — an old record that simply aged → staleness handling, not
  contradiction (unless a *stale* record remains active against a *fresh
  verified* counter-claim, which is exactly the MVP §8.1(2)/(5) pattern).
- **Policy violation** — a record that breaks a constraint (e.g. secret content)
  → rejected/flagged by validation, a security concern (§13), not a
  claim-contradiction.

The MVP rules must be conservative: prefer surfacing "unresolved / needs
attention" over asserting a contradiction the rule cannot deterministically
prove.

---

## 9. Lifecycle rules

A memory record moves through a lifecycle that **preserves history** rather than
overwriting. The strong conceptual direction: records are **immutable**; change
is expressed by **appending** new records and new state/verification events, and
by **supersession/retraction links** — never by in-place mutation or deletion.

### 9.1 Stages

- **Creation** — an observation is recorded with identity, claim, source
  authority/observer, timestamps, and initial `unverified` state.
- **Validation** — structural checks (well-formed, bounded, no secrets, safe
  references) before acceptance (§13). Malformed/oversized/secret-bearing
  records are rejected, not stored raw.
- **Evidence attachment** — evidence references may be added *after* creation via
  new evidence/verification events (the claim record itself stays immutable; its
  evidence set grows through appended links).
- **Verification** — deterministic (or human) checks assign/raise verification
  state, each producing a `VerificationRecord` event.
- **Activation** — the active-state calculation (§10) may select the record as
  in-force for its subject/scope.
- **Contradiction detection** — rules (§8) may mark it `contradicted` and open a
  `ContradictionRecord`.
- **Supersession** — a newer record for the same subject/scope replaces it via an
  explicit link; the superseded record becomes inactive, retained, queryable.
- **Retraction** — an explicit "this was wrong" event deactivates it (distinct
  from supersession).
- **Staleness** — freshness lapse of supporting evidence demotes it to `stale`;
  it leaves the active baseline but is retained.
- **Archival** — inactive records (superseded/retracted/stale/contradicted-out)
  remain stored for audit and history; archival is a view/retention concept, not
  deletion.
- **Context-packet eligibility** — recomputed per §7.2 / §11 whenever a packet is
  generated.

### 9.2 Rules

- **When a record becomes active:** only when the active-state calculation (§10)
  selects it — it is the current, in-scope, non-superseded, non-contradicted,
  fresh, adequately-verified record for its subject. Recency alone never
  activates.
- **May unverified records be active?** As a rule, **no** for facts/repository
  claims/capabilities — an unverified fact should not be presented as current
  baseline (it may appear as an *observation with uncertainty*). Decisions and
  constraints are the deliberate exception: they can be active on **human
  authorship** even before repository evidence exists (intent precedes
  implementation).
- **Human-confirmed decisions before repository evidence:** allowed to be active
  (intent is authoritative and may precede code). Supporting repository evidence,
  when it later appears, strengthens confidence and enables drift detection.
- **Repository-state expiry:** `RepositoryStateRecord`s expire quickly by
  freshness policy; a stale repo-state record must not remain active. The layer
  prefers "no fresh baseline available — re-observe" over serving a stale one.
- **Permanent decisions vs temporary observations:** decisions/constraints are
  durable (retired only by humans); repository-state and many facts are
  perishable (expire by freshness). The record type carries its perishability.
- **Repeated observations:** a new observation of an existing subject/predicate
  creates a *new* record that either confirms (raising confidence/refreshing
  evidence) or supersedes the prior — it does not mutate the earlier record.
- **Evidence added after creation:** yes — via appended evidence/verification
  events; the claim record stays immutable.
- **Immutability / append-only:** records are immutable; state changes are
  append-only events; supersession/retraction are explicit links. This yields a
  full audit trail.
- **Supersession chains:** represented as explicit "supersedes / superseded-by"
  links forming a chain; the *head* of a chain is the candidate active record;
  the rest are inactive-but-queryable history.
- **Superseded records queryable:** yes — always retained and inspectable
  (crucial for "why did this change, and when?").
- **Contradiction resolution recorded:** resolutions (human decision,
  supersession, retraction) are stored as events on the `ContradictionRecord`;
  nothing is silently auto-resolved.
- **Correcting wrong records without erasing history:** via retraction +
  a new correct record, never by editing or deleting the wrong one.
- **Timestamp / source identity in lifecycle:** activation and staleness
  calculations use observed-at / as-of timestamps and source authority; identity
  (subject+predicate+scope) drives supersession and dedup.

---

## 10. Active-state calculation

"Which facts and decisions are *currently* active?" must be a **deterministic
computation**, not a heuristic and not "newest wins."

### 10.1 Inputs and method

For a given subject/scope, the calculation considers:

- **Record identity** — subject + predicate + scope defines the "slot" being
  computed.
- **Subject/predicate matching + scope** — only records about the same slot
  compete; scope mismatches are separated, not merged.
- **Supersession references** — a superseded record is excluded; the head of the
  supersession chain is the candidate.
- **Verification state** — only `verified` / `human_confirmed` (and clearly
  scoped `partially_verified`, for the covered part) are eligible; `contradicted`
  / `unresolvable` / `stale` / `retracted` / `superseded` are excluded from the
  active baseline.
- **Contradiction state** — if the slot has an *unresolved* contradiction, the
  calculation does **not** pick a winner; it returns "unresolved" for that slot
  and surfaces the contradiction (§11).
- **Evidence freshness** — perishable claims past their freshness window are
  `stale` and excluded.
- **Temporal ordering** — used only *after* the above filters, to prefer the most
  recent *among still-eligible, evidenced* records — never as the primary
  selector.
- **Human authority** — for intent slots, a human-authored/confirmed decision
  outranks inferred ones; human resolution settles a contested slot.
- **Context-specificity** — activity can be scope-relative (a decision active for
  one phase/area need not be active globally).

### 10.2 Determinism and "no safe active record"

The calculation must be **pure and reproducible**: same records in → same active
set out. When **no** record can be safely selected (all stale, or an unresolved
contradiction, or only unverified observations), the calculation must return an
**explicit "no active record / unresolved"** for that slot — and the layer must
*expose that uncertainty* rather than guessing or silently defaulting to the
newest. Exposing "we don't currently know" is a first-class, desired outcome.

---

## 11. Pre-action context packet concept

The **`ContextPacket`** (to be *generated* in Phase 37E, not now) is a read-only
bundle an agent/human reads to establish a reliable baseline *before* proposing
or performing work. It is the layer's primary user-facing payoff: instead of
chat archaeology, an agent starts from a computed, evidence-traceable snapshot of
"what is currently true, decided, and uncertain."

### 11.1 Proposed sections

- **Project identity** — repo, canonical path, current branch.
- **Current repository baseline** — freshest `RepositoryStateRecord`s (branch,
  HEAD, tree state), explicitly timestamped.
- **Active roadmap position** — active track(s) and active phase(s).
- **Active phase** — the in-progress phase(s) with scope.
- **Completed verified phases** — phases with merge/verification evidence.
- **Active product decisions** — human-authored/confirmed decisions in force.
- **Active constraints and guardrails** — prohibitions an agent must honor.
- **Known capabilities** — verified capabilities *and* explicit unverified/partial
  gaps.
- **Unresolved contradictions** — first-class; the open `ContradictionRecord`s.
- **Stale / superseded warnings** — what *not* to rely on, and why.
- **Evidence references** — inspectable pointers backing each asserted line.
- **Verification summary** — counts/standing of what is verified vs not.
- **Relevant recent changes** — recent superseding records / new facts.
- **Prohibited assumptions** — explicit "do not assume X" list derived from
  known gaps and constraints.
- **Context-generation timestamp** — when the packet was computed.

### 11.2 Rules

- **Eligibility:** only active (`verified`/`human_confirmed`/scoped
  `partially_verified`) records enter the baseline sections; contradictions and
  uncertainty go to their own sections; stale/superseded go only to warnings.
- **Ordering:** deterministic (e.g. by section, then subject, then as-of time) so
  the same inputs render the same packet.
- **Maximum scope:** bounded — the packet is a baseline, not a data dump; it
  references rather than inlines bulky evidence, and it must have size limits
  (§13 bounded-payloads).
- **Deterministic output:** pure function of the current record set + generation
  time; no randomness, no LLM phrasing that could vary truth.
- **Contradiction visibility:** unresolved contradictions are always shown — never
  hidden by picking a side.
- **Evidence traceability:** every asserted line carries evidence references.
- **Uncertainty presentation:** "unknown / unresolved / unverified" is shown
  explicitly, not omitted (omission reads as "fine").
- **Read-only in MVP:** generating a packet must never mutate records, resolve
  contradictions, or trigger any side effect. It is a *view*.
- **How an agent should use it:** read the packet first; treat baseline as the
  starting truth; honor constraints/prohibited-assumptions; *stop and ask a
  human* when the packet shows an unresolved contradiction or missing baseline
  relevant to the intended action — do not paper over uncertainty.

---

## 12. Integration boundaries

Conceptual relationships only. **Naming an integration here does not authorize
implementing it in Phase 37A** (or in any phase before it is explicitly scoped).

- **Source Registry** — potential *ingestion* source of content provenance; the
  layer may reference registry entries as evidence. It does not replace or mutate
  the registry.
- **Knowledge Graph** — the layer may *reference* graph facts as evidence but must
  **never mutate** the graph; the graph stays read-only. The layer is not a graph
  store.
- **Intelligence Report** — could *consume* the context packet to enrich a
  summary later; the layer does not depend on the report.
- **Provenance Chains** — conceptual kin to evidence references; a future
  integration could align provenance with evidence provenance. Not merged here.
- **Query Trails** — a possible ingestion/observation input (what was asked); not
  equivalent to verified facts.
- **Temporal Knowledge Decay** — conceptual kin to staleness/freshness; a future
  integration could share a decay/freshness policy. Not merged here.
- **Dreaming** — must **not** feed autonomous, unevidenced claims into memory;
  any future link must pass the same validation/evidence rules (no auto-trust).
- **Console** — a possible future *read-only* surface to inspect memory / request
  a packet; not a mutation channel.
- **Obsidian import** — a possible ingestion source (as content evidence), under
  the same validation and secret-rejection rules.
- **Frontend overlay system** — the future inspector (Phase 37F) is a *read-only*
  visualization; it does not own or mutate records.
- **Agent reports** — ingestion inputs treated as *observations requiring
  evidence* (Phase 37G), never as facts.
- **Repository observation** — a future evidence producer (Phase 37H), planned
  only after contracts/active-state/contradiction/security/packet are stable.
- **Future structured CLI reporting** — a preferred ingestion shape (structured,
  evidence-carrying) over free prose.

### 12.1 What the layer owns / does not own

**Owns:** memory records, their evidence references, verification/lifecycle state,
supersession/retraction links, contradiction detection results, the
active-state calculation, and read-only context-packet generation.

**Does not own / must not become:** the general graph database; a replacement for
source documents; a hidden chat-history store; an autonomous project manager; an
unrestricted agent scratchpad; a mutation engine; a vector-search dumping ground;
a repository watcher; an "AI truth oracle." It is a bounded, human-governed,
evidence-backed record layer — nothing more.

---

## 13. Security and abuse risks

Because the layer *ingests reports* and *presents a baseline agents act on*, it
is an attractive target and a potential injection/poisoning vector.

### 13.1 Risks

- **Prompt injection via ingested reports** — an ingested report contains text
  aimed at steering an agent. Records are **data, not instructions**; content is
  never executed or followed.
- **Forged / misleading evidence** — fabricated commit ids, fake "merged"
  claims, doctored outputs. Mitigated by evidence *type* checks, provenance, and
  (later) re-verification against the live repository rather than trusting the
  submitted value.
- **Untrusted file paths / evidence-reference traversal** — evidence references
  must be validated/sandboxed; no path traversal, no reading outside allowed
  roots.
- **Command-output spoofing** — a submitted "command output" is only as trusted
  as its (later) re-verification; submitted outputs are observations, not proof.
- **Agent / observer identity spoofing** — observers must be identified;
  unauthenticated identity claims get weakest treatment and cannot claim human
  authority.
- **Record tampering / unauthorized mutation** — immutability + append-only +
  authorization on state-changing actions; consequential changes need humans.
- **Sensitive-data retention / secret leakage / credential storage** — validation
  must **reject or redact** secrets/credentials; the layer must never store
  secrets (this is also a hard non-goal, §15).
- **Malicious repository content** — treated as untrusted data; never executed;
  scoped as evidence only for what it demonstrably is.
- **Contradiction flooding / DoS via excessive ingestion** — bounded payloads,
  rate/volume limits, dedup of identical contradictions, and rejection of
  oversized/abusive input.
- **Replayed stale reports / timestamp manipulation** — freshness is computed
  from *trusted* time and corroborating evidence, not solely from a submitted
  timestamp; replays are detectable via identity + as-of + supersession.
- **Poisoned context packets** — because the packet drives action, only eligible,
  evidenced, non-contradicted records enter it; contradictions/uncertainty are
  shown, not hidden.
- **Human-confirmation impersonation** — human confirmation must be an
  attributable, authenticated human action; it can **never** be asserted by
  observed content on a human's behalf.
- **Unsafe autonomous resolution / over-trusting summaries** — the MVP does not
  auto-resolve contradictions or auto-trust prose; deterministic rules + human
  governance only.

### 13.2 Initial security principles

Structured validation of all input; explicit source identity + observer;
evidence provenance; least privilege; **no command execution from memory
records**; **no automatic trust of ingested prose**; deterministic contradiction
rules for the MVP; bounded payloads and volume; full auditability;
append-only historical trace where practical; human review for consequential
decisions; redaction or rejection of secrets; and **no autonomous repository
mutation**.

---

## 14. MVP definition

The minimum useful product is a **deterministic, evidence-backed, human-governed
record layer with read-only context generation** — no AI arbitration, no
autonomy, no mutation. It aligns to the sequence:

```text
Phase 37A — Planning (this phase)
Phase 37B — Contract Types / Schema Alignment
Phase 37C — Deterministic Memory Store MVP
Phase 37D — Contradiction Detection MVP
Phase 37E — Pre-Action Context Packet
Phase 37F — Active Memory Frontend Inspector
Phase 37G — Agent Session Ingestion Planning
Phase 37H — Repository Observer Planning
```

The initial product prioritizes: **deterministic records**; **explicit
evidence**; **active-state calculation**; **narrow contradiction rules**;
**read-only context generation**; **inspectability**; and **human governance**.
Everything harder (ingestion at scale, repository observation, richer
contradiction classes) is deferred behind stable contracts.

---

## 15. Non-goals

Phase 37A and the initial MVP do **not** authorize any of the following:

LLM-based truth arbitration; autonomous contradiction resolution; autonomous
project decisions; autonomous repository changes; unrestricted chat ingestion;
background repository watching; semantic-memory embeddings as the source of
truth; vector-database introduction; knowledge-graph mutation; persistent agent
personalities; hidden memory; user surveillance; credential storage; secret
retention; agent-to-agent trust without evidence; cross-project memory leakage;
a broad event-sourcing rewrite; replacement of Git or source-controlled
documentation; UI implementation; API implementation; database implementation;
schema implementation; frontend type implementation; backend type
implementation; new dependencies.

Those are the province of later, explicitly approved phases.

---

## 16. Phase 37B readiness proposal

**Phase 37B — Active Memory Contract Types / Schema Alignment** should be limited
to *contract/type definitions* (backend and frontend) for: memory records;
evidence records; contradiction records; verification states; supersession
references; and context-packet responses.

Phase 37B must **not** include: persistence; ingestion; contradiction execution;
context-packet generation logic; frontend inspector implementation; repository
observation; autonomous verification; or any AI/LLM logic.

### 16.1 Contract questions Phase 37B must resolve

1. **Identity model** — what exactly composes a record's stable identity
   (subject + predicate + scope?) and how are supersession/dedup keys derived?
2. **Claim shape** — is a claim a structured subject/predicate/value triple, and
   what is the controlled vocabulary for predicates per record type?
3. **Two-axis state** — how are verification state and lifecycle state
   represented as *separate* fields, and what are their permitted values and
   (documented) transitions?
4. **Evidence reference schema** — the fields for an evidence reference (type,
   content reference, scope, source, timestamp, validity window) and the closed
   set of evidence types.
5. **Confidence representation** — bands vs numeric, and how (or whether) it is
   distinct from verification state in the contract.
6. **Supersession / retraction links** — directionality, chain representation,
   and how the "head" is identified.
7. **Contradiction record shape** — how conflicting-record sets, the fired rule,
   the class, and resolution status are represented.
8. **Context-packet response shape** — section structure, how references (not
   inlined bulk) are carried, ordering keys, and the uncertainty/contradiction
   sections.
9. **Timestamps** — which time fields exist (observed-at, recorded-at,
   evidence-as-of) and their semantics/precision.
10. **Source authority + observer** — how identity/category are typed, and how
    "human" is distinguished from "agent" from "machine/CI."
11. **Scope / context-specificity** — how scope is expressed so active-state can
    be computed per-scope.
12. **Bounds** — max sizes/limits in the contract to support §13 bounded
    payloads.
13. **Frontend/backend parity** — ensuring the read-only inspector contract
    (37F) can consume the same types without a divergent second model.

---

## 17. Later-phase roadmap

Documentation of intended responsibilities only. **Do not implement these here.**

- **Phase 37C — Deterministic Memory Store MVP:** create records; retrieve
  records; attach evidence; supersede records; calculate active state; reject
  malformed records. Deterministic, in-scope, no AI, human-governed mutation.
- **Phase 37D — Contradiction Detection MVP:** implement the §8.1 deterministic
  classes only — duplicate phase status; pending vs merged; frontend-only vs
  backend modifications; current vs superseded decision; clean vs dirty
  working-tree reports. Conservative: surface "unresolved" over false positives.
- **Phase 37E — Pre-Action Context Packet:** generate a read-only bundle from
  verified facts/decisions, including evidence and unresolved contradictions;
  no mutation, no autonomous decisions.
- **Phase 37F — Active Memory Frontend Inspector:** a contextual, read-only
  overlay showing active facts, decisions, evidence, contradictions,
  verification status, and supersession chains.
- **Phase 37G — Agent Session Ingestion Planning:** plan structured ingestion
  from Claude Code reports, Codex reports, ChatGPT sessions, and CLI-generated
  structured reports — as evidence-carrying observations, not trusted facts.
- **Phase 37H — Repository Observer Planning:** plan repository observation only
  *after* record contracts, active-state calculation, contradiction handling,
  security boundaries, and context-packet behavior are stable and proven.

---

## Appendix A — Guardrail compliance for this phase

- **Documentation-only.** No `apps/`, `packages/`, backend/frontend source, API
  routes, schemas, models, database code, tests, package files, lockfiles,
  build/runtime configuration, screenshots, or demo evidence were modified. No
  dependency added.
- **No runtime concepts implemented** — no persistence, storage, API, frontend
  component/overlay, ingestion, report parser, repository watcher, contradiction
  engine, active-state code, context-packet code, AI/LLM processing, embeddings,
  vector search, graph mutation, or autonomous memory mutation.
- **Track 1 unchanged.** Phase 36K — Full-Hand Gesture Live Camera QA + Control
  Tuning remains the active spatial-interaction implementation track and is **not**
  displaced, rewritten, or claimed complete by this phase. This document makes
  **no** claim that live gesture tuning is finished.
- **Honest evidence posture.** Existing-feature descriptions (§1.6) are grounded
  in what the repository shows; illustrative examples (§2) are labelled as
  illustrative, not asserted as live defects.
