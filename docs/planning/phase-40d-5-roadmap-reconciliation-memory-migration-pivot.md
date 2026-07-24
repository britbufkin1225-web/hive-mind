# Phase 40D.5 — Roadmap Reconciliation + Memory Migration Pivot

**Status:** documentation-only, implemented locally / pending independent audit
and the devdevbuilds human merge gate.
**Type:** documentation and roadmap-reconciliation phase only (no runtime,
contract, schema, API, dependency, frontend, asset, or test change).
**Depends on:** [Phase 40D](phase-40d-synthesis-evidence-provenance-validation-guardrails.md)
being merged on `main` (the deterministic, read-only validation guardrails over
assembled `SynthesisContextPacket` records).
**Supersedes:** the provisional future-phase numbering (40E–40G) recorded in the
Phase 40A–40D documents while they were authored. Those historical planning
records are **not rewritten**; this decision record is the authority on the
active forward sequence.

## 1. Status and decision

**Decision:** Insert a memory-migration track ahead of Grounded Synthesis
*production*, and reconcile the active roadmap to a single authoritative
Phase 40D.5–40K sequence.

Phase 40D.5 is a **documentation-only** decision record and roadmap
reconciliation. It changes no backend or frontend code, no contract, schema, API,
dependency, or asset, and adds no test. It resolves a numbering and sequencing
contradiction that had accumulated across the Phase 40A–40D documents and
establishes the memory-migration track as the next implemented work.

The decision it records:

- Phase 40D is **merged/complete** on `main`.
- **Memory migration precedes Grounded Synthesis production.** Before Hive|Mind
  builds a synthesis *producer*, it must be able to bring a user's own history
  into Active Memory as reviewable candidates through an explicit,
  provenance-preserving, fail-closed boundary.
- The previously documented active sequence — Phase 40E "Grounded Synthesis API
  and Read-Only Workspace", Phase 40F "Review, Approval, Export, and Agent Handoff
  Workflow", Phase 40G "End-to-End QA" — is **superseded**. That work is not
  cancelled; it is renumbered later in the sequence (40I, 40J, 40K) so the
  migration track can land first.

## 2. Context and the contradiction being resolved

The Grounded Synthesis track was planned before the memory-migration need was
made explicit. As authored, the Phase 40A–40D documents implied that the next
implemented work after the validation guardrails would be the read-only
synthesis API and workspace (a provisional "Phase 40E"), followed by a review /
export / handoff workflow (a provisional "Phase 40F").

That sequence is now internally inconsistent with the project's actual next
direction:

- The Grounded Synthesis Layer synthesizes over **grounded evidence Hive|Mind
  already holds**. Its usefulness scales with the quality and breadth of that
  evidence.
- A large, deliberately deferred source of grounded evidence is the user's own
  prior work — for example, a user-controlled **ChatGPT export** or a **curated
  migration bundle** the user assembles themselves.
- Building a synthesis *producer* before there is any safe, reviewable way to
  bring that history in would mean synthesizing over a narrower evidence base
  than the layer is designed for, and would defer the migration-safety design to
  a point where a producer already depends on it.

Phase 40D.5 resolves the contradiction by sequencing migration **before**
production and reconciling every active document to the same numbering. The
active roadmap, README status, and architecture reconciliation note now describe
one authoritative sequence rather than three overlapping ones.

## 3. Why memory migration precedes synthesis production

- **Evidence before synthesis.** The layer's mandatory first principle is that
  synthesis is grounded in verified evidence. Broadening the grounded evidence
  base — safely — is therefore a prerequisite to a producer, not a follow-on.
- **Trust boundary first.** The riskiest part of intake is the *boundary*: what
  is allowed in, what is rejected, and how provenance is preserved. Designing
  that boundary while there is no producer pulling on it keeps it honest and
  fail-closed, rather than shaped by a producer's convenience.
- **No premature coupling.** A synthesis producer built first would either ignore
  migrated history (making migration pointless) or assume an intake path that
  does not yet exist (making the producer speculative). Migration first avoids
  both.

## 4. Why Phases 40A–40D remain valid

Nothing in Phases 40A–40D is invalidated by this pivot:

- **Phase 40A** defines the Grounded Synthesis Layer architecture, terminology,
  authority restrictions, failure states, and security posture. All of it still
  holds; only the *ordering* of later phases changes.
- **Phase 40B** established the `grounded-synthesis.v1` contract family. Migration
  contracts (a separate future family) do not alter it.
- **Phase 40C** established deterministic, read-only grounding-context assembly
  over evidence Hive|Mind already holds. Migrated candidates, once reviewed and
  persisted in a later phase, become additional grounded evidence that the same
  assembly can package — no assembly change is implied here.
- **Phase 40D** established the deterministic validation guardrails over assembled
  packets. That trust boundary is unchanged and is, in spirit, the model the
  migration track follows: deterministic, read-only, fail-closed, provenance-
  preserving.

The provisional future-phase *numbers* those documents carried (40E/40F/40G) are
the only thing this decision supersedes. Their **architecture and reasoning are
retained**.

## 5. Why contracts and intake safety precede parsing

The migration track itself is sequenced contracts-and-safety-first:

- **Phase 40E (Memory Migration Contract + Intake Safety Foundation)** defines the
  versioned intake contract family and a deterministic, read-only intake-safety
  assessment over declared metadata **before** any export is parsed.
- A parser that runs before the intake boundary exists would have to invent its
  own ad hoc safety rules (path handling, entry-type handling, bounds, duplicate
  and identity rules) inline. Defining the contract and the fail-closed
  assessment first gives the parser a trustworthy boundary to produce into.
- The intake-safety assessment operates on **declared** metadata only: it opens no
  files, extracts no archives, reads no bytes, and touches no filesystem, network,
  or Git. It reports readiness or blocking diagnostics; it does not parse.

## 6. Why parsing and candidate projection precede reviewed persistence

- **Phase 40F (Export Parser + Candidate Projection)** parses a user-controlled
  export or curated bundle — only after Phase 40E has judged the intake safe — and
  projects its contents into **candidate** memory records. Candidates are
  inactive, unverified, provenance-linked proposals; they are not truth and are
  not persisted as authoritative state.
- **Phase 40G (Reviewed Persistence + Verified Import)** is the first phase that
  may persist anything, and only for candidates a human has reviewed. Verified
  import is a human-gated act, consistent with devdevbuilds remaining the merge
  gate for every repository- and memory-affecting decision.
- Persisting before parsing and review would import unreviewed material as
  authoritative memory — exactly the "imported material is verified truth" claim
  this track refuses to make. Parsing produces candidates; review verifies them;
  only then may persistence occur.

## 7. Why Hive|Mind claims no direct access to private ChatGPT system memory

Hive|Mind does **not** and will not claim direct, account-to-account access to any
provider's private system memory:

- There is no supported, authorized interface for a third-party tool to read a
  user's private ChatGPT system memory directly, and asserting otherwise would be
  both false and a security/privacy overreach.
- The project's honesty principle (implemented-versus-planned stated plainly)
  forbids describing a capability the product does not and should not have.
- Migration is therefore defined entirely around **artifacts the user controls
  and provides** — not around reaching into another system.

## 8. Why migration relies on user-controlled exports or curated bundles

- **User agency and consent.** A user-controlled export (for example, a ChatGPT
  data export the user requests and downloads) or a **curated bundle** the user
  assembles is data the user already owns and explicitly hands to Hive|Mind. The
  user decides what enters the boundary.
- **Reviewability.** An explicit artifact can be assessed, parsed into candidates,
  and human-reviewed before anything is persisted. A live, opaque account link
  could not be bounded, replayed, or audited the same way.
- **Determinism and auditability.** A fixed export artifact yields deterministic
  intake identities and a reproducible assessment. Every migrated record can be
  traced back to the artifact and rule that produced it.

## 9. The authoritative Phase 40D.5–40K sequence

This is the single active forward sequence. It supersedes any earlier 40E–40G
numbering in the Phase 40A–40D documents.

| Phase | Title | Status |
| --- | --- | --- |
| Phase 40D.5 | Roadmap Reconciliation + Memory Migration Pivot | Documentation-only (this record) |
| Phase 40E | Memory Migration Contract + Intake Safety Foundation | Planned |
| Phase 40F | Export Parser + Candidate Projection | Planned |
| Phase 40G | Reviewed Persistence + Verified Import | Planned |
| Phase 40H | Grounded Synthesis Producer MVP | Planned |
| Phase 40I | Grounded Synthesis API + Read-Only Workspace | Planned |
| Phase 40J | Review, Approval, Export, and Agent Handoff Workflow | Planned |
| Phase 40K | End-to-End QA, Operator Documentation, and Release Readiness | Planned |

Every phase past 40D.5 is **planned**, not implemented. No migration capability,
export parsing, reviewed persistence, verified import, synthesis producer, API,
workspace, or review workflow exists today.

## 10. The dependency gate that must pass before Phase 40E

Phase 40E may not begin until this documentation gate is satisfied:

- Phase 40D is merged on `main`.
- This Phase 40D.5 decision record exists and is merged.
- The active roadmap (`docs/roadmap.md`), the README status, and the architecture
  reconciliation note all describe the single authoritative Phase 40D.5–40K
  sequence with no residual active 40E–40G ("API / Review-Export / QA") sequence.
- The Grounded Synthesis Layer remains the formal layer name; *Musings* and *The
  Loom* remain capabilities or modes within it, never renamed to the layer.
- Phase 36K remains paused and untouched.

Phase 40E is a contract-and-safety phase; it must not absorb parsing (40F),
persistence or verified import (40G), or any synthesis-production work
(40H onward).

## 11. Scope and explicit non-goals

**In scope (this phase):** the decision record; reconciling `docs/roadmap.md`,
`README.md`, and `docs/create-layer-architecture.md` to the authoritative
sequence; stating plainly that all migration and later synthesis-production work
is planned.

**Explicit non-goals (this phase does not do any of these):**

- Implement memory migration, ChatGPT export parsing, or archive extraction.
- Implement candidate projection, reviewed persistence, or verified import.
- Implement the Grounded Synthesis producer, API, workspace, or review workflow.
- Add or change any backend or frontend code, contract, schema, API, package,
  dependency, or asset.
- Add tests, screenshots, images, or visual assets.
- Add AI/LLM integration or embeddings.
- Claim direct access to private ChatGPT system memory or automatic
  account-to-account migration.
- Describe any planned capability as working today.
- Touch Phase 36K.

## 12. Historical future-phase numbering this decision supersedes

While Phases 40A–40D were authored, the forward sequence was provisionally
numbered:

- Provisional Phase 40E — Grounded Synthesis API and Read-Only Workspace.
- Provisional Phase 40F — Review, Approval, Export, and Agent Handoff Workflow.
- Provisional Phase 40G — End-to-End QA, Operator Documentation, and Release
  Readiness.

Those numbers are **retained as historical evidence** inside the Phase 40A–40D
planning records, which are not rewritten. This decision record supersedes that
numbering for all **active** documentation: the same three work items are now
Phase 40I, Phase 40J, and Phase 40K respectively, after the memory-migration
track (40E–40G) and the synthesis producer MVP (40H).

## 13. Validation and acceptance criteria

This documentation-only phase is validated by inspection, not by backend or
frontend tests (none are required, and none were run):

- Changed paths are exactly within the allowlist: `README.md`,
  `docs/roadmap.md`, `docs/create-layer-architecture.md`, and this record.
- `git diff --check` reports no whitespace errors.
- No genuine merge-conflict markers exist in `README.md` or `docs`.
- Every active phase reference uses the reconciled Phase 40D.5–40K sequence; only
  the historical Phase 40A–40D records retain their original provisional
  numbering, and this record clearly supersedes it.
- Every migration statement distinguishes implemented behavior from planned work
  and makes no claim of direct private-memory access, automatic migration,
  existing export parsing, verified-truth import, existing synthesis production,
  or AI/LLM/embedding integration.
- Every added or changed relative Markdown link resolves.
- Phase 36K remains paused and untouched.

## Data-flow direction (planned, not implemented)

```text
User-controlled ChatGPT export or curated bundle   (user provides; no direct
                |                                    private-memory access)
                v
   Phase 40E — Memory Migration Contract + Intake Safety
                |   (declared metadata only; fail-closed; no parsing)
                v
   Phase 40F — Export Parser + Candidate Projection
                |   (inactive, unverified, provenance-linked candidates)
                v
   Phase 40G — Reviewed Persistence + Verified Import
                |   (human-reviewed; only then persisted)
                v
   Phase 40C grounding assembly  ->  Phase 40D validation  ->  Phase 40H producer
```

Everything downstream of the user-provided artifact is **planned**. Phase 40D.5
adds none of it; it only records the decision and reconciles the documentation.
