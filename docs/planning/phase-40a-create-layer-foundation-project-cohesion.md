# Phase 40A — Grounded Synthesis Foundation Planning + Project Cohesion

**Type:** Planning, architecture, documentation, and project-cohesion phase.
**Runtime code changed:** none. **Status:** documentation and Codex formal review
complete locally, pending final independent audit (Jules), coordinator
reconciliation (ChatGPT), and the devdevbuilds human merge gate. Antigravity is
offline through July 26, 2026 and is not part of this phase.

**Terminology note:** the historical planning label for this phase — and the name
retained by its Git branch (`phase-40a-create-layer-foundation-project-cohesion`),
its original commit, and its on-disk paths — is *Create Layer Foundation Planning
+ Project Cohesion*. The architecture this phase establishes is now formally named
the **Grounded Synthesis Layer**; *Create Layer* is deprecated terminology.
*Musings* and *The Loom* are internal capabilities within that layer.

**Parent label:** devdevbuilds (human decision-maker and merge gate).
**Composition mode:** `sequential-isolated`.

---

## 1. Purpose

Define the architectural, product, governance, roadmap, documentation, and
design-cohesion foundation for a new Hive|Mind **Grounded Synthesis Layer** — the capability
that lets Hive|Mind's grounded read-only intelligence *produce* useful development
outputs (proposals, drafts, plans, packets, bounded artifacts) while remaining
evidence-grounded and never becoming an autonomous code generator or silent
repository mutator.

This phase is **planning only**. It writes and reconciles documentation; it
introduces no runtime, contract, endpoint, UI, service, dependency, or repository
mutation.

## 2. Context at start of phase

- Phase 39D (Repository Observer End-to-End Workflow Hardening + Failure-State QA)
  is completed, merged, and normalized on `main`.
- Phase 36K (Full-Hand Gesture Live Camera QA + Control Tuning) remains **paused
  and untouched**.
- Current priority: dependable daily use and grounded synthesis capability.
  Premium frontend polish, webcam work, screenshots, branding expansion, and
  unrelated visual experimentation remain deferred unless explicitly reopened.

### 2.1 Locked baseline

- Canonical repository path: `C:\Users\britb\Documents\hive-mind`
- Remote (`origin`): `https://github.com/britbufkin1225-web/hive-mind.git`
- Locked Phase 40A baseline SHA (`origin/main`):
  `16e8cbdc5e0bae56b61242fe106f22c760d6344d`
- Branch: `phase-40a-create-layer-foundation-project-cohesion`
- Merge-base of branch and `origin/main`: the locked baseline SHA (no divergence).

> Remote-ownership note: `origin` resolves to `britbufkin1225-web/hive-mind`, the
> same remote used by every prior phase (39A–39D PRs). The phase brief names
> `devdevbuilds` as the repository owner and human merge gate; that governance role
> is preserved regardless of the Git remote's account name. This is flagged for the
> human gate rather than treated as a blocker, because it matches established
> project history.

## 3. What Phase 40A defines

Phase 40A produces or updates the following documentation:

1. **Grounded Synthesis Layer architecture document** —
   [`docs/create-layer-architecture.md`](../create-layer-architecture.md).
   Canonical description of purpose, product boundary, relationships to the
   Intelligence Layer / Active Memory / Repository Observer / context packets, the
   proposed synthesis workflow, request/result lifecycle, evidence and provenance
   requirements, review/approval boundaries, authority/mutation restrictions,
   failure states, security considerations, future extensibility, rejected
   alternatives, decision rationale, and a data-flow diagram.
2. **This phase planning document** —
   `docs/planning/phase-40a-create-layer-foundation-project-cohesion.md`.
3. **Roadmap integration** — a Grounded Synthesis track (40A–40G) added to
   [`docs/roadmap.md`](../roadmap.md).
4. **README reconciliation** — [`README.md`](../../README.md) updated to describe
   the true post-39D state and the next direction, with the Grounded Synthesis
   Layer clearly
   labeled as planned.
5. **Design-asset cohesion assessment** —
   [`docs/design-asset-cohesion-assessment.md`](../design-asset-cohesion-assessment.md).
6. **Data-flow diagram** — included in the architecture document (§13 there).
7. **Decision rationale** — included in the architecture document (§14–§15 there)
   and summarized in this plan.

## 4. Mandatory architectural principles (carried into the foundation)

The Grounded Synthesis Layer foundation commits to these principles (full treatment in the
architecture doc):

1. **Evidence before synthesis** — every meaningful output identifies its evidence.
2. **Proposal before mutation** — early phases produce drafts/proposals/plans/
   packets/patches only; no direct repository mutation.
3. **Human-reviewed execution** — devdevbuilds remains the decision-maker and
   merge gate.
4. **Deterministic boundaries** — deterministic extraction/validation/selection/
   assembly/policy/packaging stays separate from any future generative behavior.
5. **Explicit confidence and limitations** — outputs identify missing context,
   conflicting evidence, assumptions, unsupported claims, and validation needs.
6. **No silent authority escalation** — read/propose authority never becomes
   write/commit/merge/deploy authority implicitly.
7. **Reusable synthesis contracts** — typed, versioned contracts (planned, not
   built here).
8. **Auditability** — enough metadata to explain request, evidence, rules, output,
   producer, human decision, and any external application.

## 5. What remains conceptual (defined, not implemented)

- The `grounded-synthesis.v1` contract family (synthesis request, grounding packet, synthesis
  result) — described as documentation examples only; no runtime schema exists.
- The synthesis workflow, request/result lifecycle, failure states, and authority
  model — specified as design targets, not code.
- The grounding packet as a superset of the existing context packet — a design
  relationship, not an implemented service.
- Any generative/model-backed behavior — explicitly out of scope and deferred.

## 6. What is ready for implementation

Phase 40A leaves the following ready to be scoped as concrete implementation
phases, in order:

- **40B — Synthesis Request, Grounding Packet, and Result Contract Types.** Introduce `grounded-synthesis.v1`
  backend Pydantic models + mirrored frontend TypeScript + parity test. Pure
  contracts, no service/endpoint/runtime — mirrors the Phase 37B contract phase.
- **40C — Deterministic Grounded Synthesis Packet Service MVP.** A backend-only,
  deterministic, read-only producer that assembles a grounding packet and emits a
  synthesis result from supplied evidence. No persistence, no mutation, no AI/LLM.
- **40D — Synthesis Evidence, Provenance, and Validation Guardrails.** Deterministic
  policy/validation, confidence/freshness indicators, scope exclusions, and
  fail-closed bounds.

These are ready because the architecture, boundaries, and vocabulary are now
fixed; each maps directly onto an existing, proven Hive|Mind pattern
(contracts → deterministic service → guardrails).

## 7. What is explicitly deferred

- **40E — Grounded Synthesis API + Read-Only Frontend Workspace** (surface work; after
  the deterministic producer and guardrails exist).
- **40F — Review, Approval, Export, and Agent Handoff Workflow** (human gate +
  Agent Lab handoff).
- **40G — End-to-End QA, Operator Documentation, and Release Readiness.**
- Any AI/LLM runtime integration, generative behavior, patch-application engine,
  in-app repository mutation, or output persistence.
- All frontend polish, webcam/gesture work (Phase 36K stays paused), branding
  expansion, and screenshot work.

## 8. Recommended next phase

**Phase 40B — Synthesis Request, Grounding Packet, and Result Contract Types.**

Rationale: the foundation is now defined, and the lowest-risk, highest-leverage
next step is the same one that anchored the Active Memory track — settle the typed,
versioned wire contracts first, with backend/frontend parity, before any service
or endpoint consumes them. 40B introduces no runtime behavior and cannot mutate
anything, so it is safely reviewable and unblocks 40C.

## 9. Decision rationale (summary)

Full rationale and rejected alternatives live in the architecture document
(§14–§15). Key decisions:

- **Grounded synthesis on read-only intelligence, not an autonomous generator** —
  preserves Hive|Mind's evidence-first credibility while adding real productivity.
- **Deterministic core; generative behavior isolated and deferred** —
  reproducibility and auditability are the project's value; a non-deterministic
  core would undermine both.
- **Typed versioned contracts over ad hoc strings** — mirrors the successful
  `active-memory.v1` / `repo-observer.v1` discipline.
- **No in-app repository mutation; export/handoff only** — upholds *no silent
  authority escalation* and keeps the merge gate human.
- **Grounding packet as a superset of the context packet** — one provenance
  discipline, no duplicated evidence logic.

## 10. Roadmap sequence added

The following provisional Grounded Synthesis track was added to the roadmap
(names may be refined by later phases with justification):

- **40A** — Grounded Synthesis Foundation Planning + Project Cohesion (this phase)
- **40B** — Synthesis Request, Grounding Packet, and Result Contract Types
- **40C** — Deterministic Grounded Synthesis Packet Service MVP
- **40D** — Synthesis Evidence, Provenance, and Validation Guardrails
- **40E** — Grounded Synthesis API and Read-Only Workspace
- **40F** — Review, Approval, Export, and Agent Handoff Workflow
- **40G** — End-to-End QA, Operator Documentation, and Release Readiness

## 11. Multi-agent composition

Composition mode: `sequential-isolated`. Agents must not perform overlapping
repository writes simultaneously.

| Order | Agent | Role |
| --- | --- | --- |
| 1 | Claude Code | Primary planner and documentation implementer (this commit). |
| 2 | Codex | Formal architecture, contract, and implementation-readiness reviewer. |
| 3 | Jules | Final independent auditor and bounded documentation hardener. |
| — | Antigravity | Offline through July 26, 2026; not participating in this phase. |
| 4 | ChatGPT | Coordinator and final report reconciler. |
| 5 | devdevbuilds | Human merge gate. |

Auditing agents must not amend, squash, or rewrite the primary commit. Any
justified hardening lands as a separate commit identifying the reviewing agent. No
agent may push, open a PR, merge, delete branches, or modify `main` unless
explicitly instructed by devdevbuilds.

## 12. Allowed vs forbidden scope (as executed)

**Allowed (documentation) files touched:**

- `README.md`
- `docs/roadmap.md`
- `docs/create-layer-architecture.md` (new)
- `docs/design-asset-cohesion-assessment.md` (new)
- `docs/planning/phase-40a-create-layer-foundation-project-cohesion.md` (new)

**Forbidden and confirmed untouched:** backend/frontend runtime code, API
contracts, schemas, databases, persistence logic, Repository Observer
implementation, Active Memory implementation, PowerShell runtime tooling, package
manifests, dependency locks, unrelated tests, screenshots/binary assets, branding
files, webcam/gesture functionality, Phase 36K materials, deployment behavior,
and authentication/authorization behavior. No AI/LLM integration, autonomous
mutation, automated commit/push/merge, patch-application engine, code-generation
service, output persistence, or new dependency was introduced.

## 13. Validation performed

- `git diff --check` (whitespace/conflict) — clean.
- Conflict-marker search across changed files — none.
- Local Markdown link review for new/changed docs — resolved.
- Mermaid syntax review of the architecture data-flow diagram.
- Roadmap/README status-language reconciliation (the Grounded Synthesis Layer described as
  planned, not implemented).
- Confirmation that no runtime files changed (diff limited to Markdown docs).
- Confirmation that Phase 36K materials were not touched.

(Exact commands and results appear in the final phase report.)

## 14. Known limitations

- This is a planning phase: the Grounded Synthesis Layer does not exist as runtime.
- Conceptual contracts are illustrative; real field-level contracts are a 40B
  decision.
- The remote account name differs from `devdevbuilds` (see §2.1); the human gate
  should confirm this matches intent.
- Design-asset assessment is bounded and changes no binary assets (see the
  assessment doc).

## 14.1 Codex hardening rationale

The formal review verified five implementation-readiness defects and corrected
them within the existing architecture document:

1. **Contract lifecycle incompleteness** — `docs/create-layer-architecture.md`
   §12 did not require version discriminators, canonical serialization,
   compatibility/extension behavior, typed failures, evidence hashes, or
   post-synthesis drift handling. Leaving these decisions implicit would let 40B
   create incompatible backend/frontend contracts. The bounded correction records
   requirements without implementing schemas; this belongs in 40A because 40B is
   explicitly contract-first.
2. **Collapsed authority declaration** — §8 represented authority as one level,
   which could imply that proposal or artifact authority carries write-adjacent
   authority. The correction separates each capability and makes grants
   non-inheriting and fail-closed. This is a Phase 40A safety boundary.
3. **Incomplete failure and security coverage** — §§9–10 omitted workspace/path
   isolation, corrupt or poisoned evidence, unsupported requests, producer and
   validation failures, retry/partial export behavior, persistence corruption,
   unavailable handoff, and stale results. The correction adds architectural
   failure behavior only, preventing 40B–40F from treating these as successful or
   silently recoverable states.
4. **Ambiguous Loom boundary and thin secondary contracts** — §12 treated
   `LoomContext` and `GroundingPacket` as near synonyms and named `Musing`,
   `WorkPacket`, `ArtifactExport`, and `ReviewRecord` without minimum safety
   semantics. The correction makes Loom context internal/ephemeral and the packet
   the validated producer handoff, then records minimum traceability and review
   requirements. This preserves layer boundaries before implementation.
5. **Factual and terminology drift** — this plan listed the wrong sequential
   reviewers and retained two implementation-facing `create` terms; the design
   assessment retained one non-historical Create Layer claim. Correcting those
   statements keeps the Phase 40A record and canonical terminology truthful.

## 15. Recommended next phase (restated)

**Phase 40B — Synthesis Request, Grounding Packet, and Result Contract Types** — settle the typed,
versioned `grounded-synthesis.v1` contracts with backend/frontend parity before any
consuming service. No runtime behavior; safely reviewable; unblocks 40C.

## 16. Reference documents

- [Grounded Synthesis Layer architecture](../create-layer-architecture.md)
- [Roadmap](../roadmap.md)
- [Design-asset cohesion assessment](../design-asset-cohesion-assessment.md)
- [Active Agent Memory + Verification Layer reference](../active-agent-memory-verification-layer.md)
- [Repository Observer operator workflow](../operator-repository-observer.md)
- [Agent Lab contribution governance](../agent-lab/README.md)
- [README](../../README.md)
