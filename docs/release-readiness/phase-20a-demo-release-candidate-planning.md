# Phase 20A — Demo Release Candidate Planning + Final Portfolio Readiness Scope

Parent label: **devdevbuilds**

**Status: complete (planning / documentation only).** Phase 20A adds **no**
backend feature, endpoint, validation rule, middleware, frontend code, test,
dependency, persistence, auth, AI/LLM, graph/source/query mutation, screenshot,
or branding/styling change. It defines the **final demo release-candidate scope**
for Hive|Mind — what must be true, shown, evidenced, and disclosed — before any
final portfolio polish, screenshot capture, README narrative hardening, UI
tightening, release tagging, or public-facing writeup begins. Nothing here changes
behavior.

This document is the release-candidate companion to the
[Roadmap](../roadmap.md), the portfolio-facing [Demo Guide](../demo-guide.md), the
[Intelligence Surface Plan](../intelligence-surface-plan.md), and the completed
release-readiness arc:

- [Phase 19A — Security Cohesion + Release Readiness Planning](../security/phase-19a-security-cohesion-release-readiness-planning.md)
- [Phase 19B — Release Readiness QA + Demo Evidence Pass](phase-19b-release-readiness-qa-demo-evidence.md)

> **Status honesty:** Phase 20A does **not** claim Hive|Mind is production-ready,
> production-secure, or feature-complete. It claims the project has reached a point
> where a **clean, honest, demo/portfolio release candidate** can be scoped from
> the *existing* deterministic, read-only surfaces — and it locks that scope so the
> final-polish phases that follow do not drift into new features or inflated
> claims.

---

## Purpose

The Phase 18 security arc and the Phase 19A/19B release-readiness passes closed the
"is it hardened and is it honest" questions. What remains before Hive|Mind can be
shown as a finished portfolio piece is a different question: **what, exactly, is
the demo release candidate, and what does "done" look like for it?**

Phase 20A exists to answer that question *before* any polish work starts. Its job
is to:

- state the **current demo-ready story** plainly from the existing surfaces;
- define the **clean portfolio narrative** the project should tell;
- enumerate the **demo candidate surfaces** to be shown, with per-surface evidence
  and overstatement guards;
- provide a **portfolio readiness checklist** a reviewer or future phase can act on;
- define a **screenshot / demo evidence plan** to be executed in a *later* phase
  (no screenshots are created here);
- list the **known limitations** to disclose rather than hide;
- mark what is **explicitly out of scope** for the final demo candidate; and
- recommend a **controlled sequence** of final-readiness phases after 20A.

This is the punch list you write before the open-house walkthrough: it does not
paint a wall or stage a room, it decides which rooms get shown, what counts as
"ready," and which renovations are deliberately not part of this showing — so the
later passes execute against a locked scope instead of inventing one under
pressure.

---

## Current Project Position

Hive|Mind today, from the existing codebase and the Phase 13–19 record:

- **Source Registry / import foundation is complete.** Backend registry, frontend
  panel and inspector, and the Obsidian adapter/import pipeline with a frontend
  import action surface are all shipped and demo-stable.
- **Knowledge Graph read-only visualization exists.** The Knowledge Graph API and
  a read-only panel with a deterministic custom SVG visualization and inspector
  sync are shipped.
- **Intelligence Report surfaces are present and backend-derived.** All four
  sections render in a read-only panel:
  - **Temporal Knowledge Decay** — backend-derived from deterministic timestamp
    thresholds (Phase 13A).
  - **Dreaming Suggestions** — backend-derived from deterministic
    `duplicate` / `orphan` / `stale` rules with an explainable evidence trail
    (Phase 14C).
  - **Provenance Chains** — backend-derived from existing source / import / node /
    edge records (Phase 15C).
  - **Query Trails** — backend-derived `source_followup` / `knowledge_gap` /
    `related_query_cluster` projections over store structure (Phase 16C), **limited
    by no persisted query history** — `repeated_query` / `unresolved_question`
    stay deferred.
- **Security hardening and API edge-case validation are complete.** The Phase
  18A–18F arc delivered a threat model, defensive validation + error safety, an
  edge-case triage, an edge-case validation MVP, and two regression/evidence
  passes (267 full backend tests passing at the 18F snapshot).
- **Release-readiness documentation exists.** Phase 19A consolidated the security
  arc into one release-readiness view; Phase 19B recorded the whole-project
  readiness posture, a Demo Evidence Checklist, and explicit Release Readiness
  Boundaries.

In short: the *capabilities* are built and the *honesty framing* is written. Phase
20A turns that into a scoped, finishable release candidate.

---

## Final Demo Story

The clean portfolio narrative, stated once so every later surface can echo it
consistently:

> **Hive|Mind is a local-first developer knowledge intelligence dashboard that
> organizes imported knowledge sources, visualizes their relationships, and derives
> deterministic, read-only intelligence signals — temporal decay, dreaming
> suggestions, provenance chains, and query trails — from existing structure rather
> than from any AI/LLM call.**

The narrative leans on five things the project actually is:

- **Deterministic backend logic.** Every intelligence signal is derived by
  reviewable, testable rules over the store — no model inference, no randomness, no
  hidden state.
- **Read-only intelligence surfaces.** Reports project existing structure; they
  never mutate the store, sources, or graph. Repeated reads are side-effect-free.
- **Controlled scope.** The project does a bounded set of things well instead of
  gesturing at many. Deferred work is named, not implied-as-present.
- **Evidence-backed derivation.** Each surface carries a backend-owned evidence
  trail, and each phase maps its claims back to tests and to the threat model.
- **Security-conscious API validation.** The request → API boundary is defended
  and leak-free for the edges in scope, with reproducible regression evidence.
- **Portfolio-grade architecture documentation.** The roadmap, per-phase docs, QA
  evidence, and this release-candidate plan make the system auditable end to end.

The story's strength is its honesty: it is precise about being a *deterministic,
local, demo-grade* tool, which is more credible than an inflated "AI knowledge
platform" claim a reviewer would see through.

---

## Demo Candidate Surfaces

The surfaces that should appear in the final portfolio demo. For each: what it
demonstrates, why it matters, what evidence backs it, and what must **not** be
overstated.

### README / repo landing page
- **Demonstrates:** the one-paragraph story, the phase status, the setup path, and
  the map into the docs.
- **Why it matters:** it is the first (often only) thing a reviewer reads; it sets
  expectations the rest of the demo must meet.
- **Evidence needed:** accurate phase/status block, working setup commands, and
  links that resolve to existing docs.
- **Do not overstate:** no "production-ready," "AI-powered," or "secure" framing;
  the README must match the deterministic/local/demo-grade story.

### App dashboard overview
- **Demonstrates:** the assembled product — console, registry, graph, and
  intelligence report in one shell.
- **Why it matters:** shows the surfaces cohere into a single tool, not a folder of
  prototypes.
- **Evidence needed:** a populated demo/import state where each panel renders real
  derived content.
- **Do not overstate:** it is a local single-user dashboard, not a multi-user or
  hosted product.

### Source Registry
- **Demonstrates:** registering and inspecting imported knowledge sources.
- **Why it matters:** it is the foundation every downstream signal derives from.
- **Evidence needed:** a populated registry with at least one inspectable source.
- **Do not overstate:** sources are local records; there is no live sync or remote
  catalog.

### Obsidian Import Action Panel
- **Demonstrates:** importing an Obsidian vault into the registry/store.
- **Why it matters:** it is the concrete "bring your own knowledge" entry point.
- **Evidence needed:** an import summary reflecting a real vault/fixture import.
- **Do not overstate:** import is a one-shot read; there is **no live filesystem
  watcher** and no write-back to the vault.

### Knowledge Graph panel
- **Demonstrates:** the read-only relationship visualization with inspector sync.
- **Why it matters:** it makes the imported structure legible at a glance.
- **Evidence needed:** a rendered graph over the demo/import state.
- **Do not overstate:** it is a read-only visualization; there is **no graph
  editing or mutation** from the UI.

### Intelligence Report panel
- **Demonstrates:** the four backend-derived, read-only signals in one report.
- **Why it matters:** it is the project's differentiating surface and the core of
  the story.
- **Evidence needed:** the report rendering each section from backend derivation
  (not fixtures) with visible evidence trails, plus clean empty states.
- **Do not overstate:** signals are deterministic MVP derivations, not AI insight;
  empty/limited sections are honest, not bugs.
  - **Temporal Knowledge Decay** — deterministic timestamp-threshold statuses;
    advisory, never mutating.
  - **Dreaming Suggestions** — conservative `duplicate` / `orphan` / `stale` rules
    with an evidence trail; suggestions are advisory and never auto-applied.
  - **Provenance Chains** — existing source/import/node/edge lineage only; lineage
    is shown, never invented.
  - **Query Trails** — structural `source_followup` / `knowledge_gap` /
    `related_query_cluster` projections; **does not include persisted user query
    history** (deferred categories disclosed).

### API contract documentation
- **Demonstrates:** the stable, additive request/response contracts.
- **Why it matters:** it shows the system is designed and documented, not ad hoc.
- **Evidence needed:** `docs/api-contract.md` matching the live routes/models.
- **Do not overstate:** contracts are additive and stable for the demo; not a
  versioned public API.

### Security / release readiness documentation
- **Demonstrates:** the threat model, the 18A–18F hardening arc, and the 19A/19B
  readiness posture.
- **Why it matters:** it proves security was reasoned about and evidenced, not
  decorated.
- **Evidence needed:** the existing security and release-readiness docs, linked and
  consistent.
- **Do not overstate:** demo-grade defensive posture only — **not** production
  security (no auth, rate limiting, deployment hardening, etc.).

### QA evidence docs
- **Demonstrates:** reproducible test counts and per-surface QA passes.
- **Why it matters:** it backs every "it works" claim with a recorded check.
- **Evidence needed:** the existing QA evidence docs and the documented backend
  test command.
- **Do not overstate:** evidence reflects the recorded snapshots; it is not a CI
  guarantee or a coverage promise.

---

## Portfolio Readiness Checklist

Items a reviewer (or a later 20-series phase) can act on. These are **not**
implemented in Phase 20A — this phase only defines the checklist.

- [ ] **README accuracy** — story, capabilities, and phase block match the actual
  build.
- [ ] **Roadmap accuracy** — `docs/roadmap.md` reflects Phase 20A and the next
  planned phase.
- [ ] **Current phase status alignment** — README and roadmap agree on the active
  phase; no contradictory labels.
- [ ] **Demo setup instructions** — backend + frontend run steps are present and
  correct.
- [ ] **Backend test command documented** — the command that reproduces the
  recorded test counts is written down.
- [ ] **Frontend build command documented** — the build/run command is written down.
- [ ] **API contract docs linked** — README/roadmap link to `docs/api-contract.md`.
- [ ] **Security docs linked** — threat model + 18/19 arc reachable from the
  landing docs.
- [ ] **Intelligence surface docs linked** — surface plan + per-section derivation
  docs reachable.
- [ ] **Screenshots needed but not invented** — placeholders/targets identified;
  real captures deferred to a later phase (see below).
- [ ] **Known limitations documented** — the limitations section below is reflected
  where users will look.
- [ ] **No stale phase labels** — no lingering "active: Phase 19B" once 20-series
  status advances.
- [ ] **No misleading AI/LLM claims** — nothing implies model inference; signals
  are deterministic.
- [ ] **No unsupported production-readiness claims** — no "production-ready,"
  "secure," or "SaaS" framing.
- [ ] **No broken internal links** — doc-to-doc links resolve (verify manually
  where practical).

---

## Screenshot / Demo Evidence Plan

**No screenshots are created in Phase 20A.** This section defines *what should be
captured later*, once the demo scope is locked, so the capture phase has a target
list instead of improvising.

Suggested future screenshot targets:

- Full dashboard overview (all panels in one populated state).
- Source Registry populated state (with an inspectable source).
- Obsidian Import summary (post-import result).
- Knowledge Graph visualization (rendered over the demo state).
- Intelligence Report overview (all four sections visible).
- Temporal Decay section.
- Dreaming Suggestions section.
- Provenance Chains section.
- Query Trails section.
- An error / empty state, if it shows the honest "nothing derivable yet" behavior
  clearly.

> **Authenticity rule:** screenshots must reflect **real app state** produced by
> normal demo-fixture or import behavior. No invented, mocked, hand-edited, or
> staged-beyond-real-behavior images. If a section is empty in a real run, capture
> the real empty state rather than fabricating content.

The existing [Screenshot Checklist](../screenshot-checklist.md) is the working
reference for the capture phase; Phase 20A does not modify it.

---

## Known Limitations To Disclose

Disclosed deliberately so the demo stays honest:

- **No AI/LLM integration.** Every signal is deterministic rule-based derivation;
  there is no model inference, embedding, or vector search.
- **No live Obsidian watcher.** Import is a one-shot read; there is no filesystem
  watcher and no write-back to the vault.
- **No mutation controls for graph / intelligence surfaces.** The graph and the
  Intelligence Report are read-only; suggestions are advisory and never
  auto-applied.
- **Query Trails do not include persisted user query history yet.** The
  `repeated_query` / `unresolved_question` categories stay blocked until query
  history is persisted; fabricating query-memory records would be dishonest.
- **Some intelligence signals are intentionally deterministic MVP derivations.**
  They are conservative by design; richer signals are future work, not present
  capability.
- **Demo / portfolio-ready, not production / SaaS-ready.** Single-user, local, no
  network exposure; not hardened or operated as a hosted service.
- **No auth system beyond the scoped backend validation / security hardening
  work.** There are no users, sessions, roles, or permissions — only the defensive
  API boundary documented in the 18-series arc.

---

## Out-of-Scope For Final Demo Candidate

Explicitly blocked for the final demo candidate (each would be its own future
phase if ever justified):

- New intelligence systems / a fifth surface.
- New graph mutation behavior.
- A full auth / roles / permissions system.
- Production deployment work.
- Multi-user support.
- Cloud sync.
- LLM integration.
- Embeddings / vector database.
- Major dashboard redesign.
- New source adapters (unless separately scoped).
- A live filesystem watcher.
- A large performance refactor.

These are not deficiencies to fix before the demo — they are deliberately outside
the demo candidate so the final passes finish the *existing* scope instead of
expanding it.

---

## Recommended Next Phases

A controlled sequence after 20A. These are **recommendations**; status is recorded
on the roadmap only as conventions require.

- **Phase 20B — Final README + Portfolio Narrative Hardening.** Make the README and
  landing docs tell the locked story consistently, with accurate status, setup, and
  links. Documentation only.
- **Phase 20C — Final Demo Screenshot + Evidence Capture Pass.** Execute the
  screenshot/evidence plan against real app state. Capture only.
- **Phase 20D — Release Candidate QA + Repo Hygiene Verification.** Re-run and
  record the documented test commands, verify links and phase-label consistency,
  and confirm repo hygiene. QA only.
- **Phase 20E — Final Portfolio Packaging / Public Presentation Pass.** Assemble
  the public-facing writeup and any release tagging, drawing on the locked scope and
  captured evidence.

The sequence is intentionally polish → capture → verify → present, with planning
(20A) first, so each step consumes a locked input from the one before it.

---

## Rationale Notes

- **Why planning comes before final polish.** Polishing against an unlocked scope
  produces churn: a screenshot taken before the surface list is fixed gets
  re-taken, a README paragraph written before the story is locked gets rewritten.
  Locking scope first makes every later pass a single, finishable step instead of a
  moving target.
- **Why screenshots should wait until scope is locked.** Screenshots are the most
  expensive artifact to redo and the easiest to render stale by any surface or copy
  change. Capturing them only after 20B hardens the narrative avoids re-shooting and
  guarantees the images match the final story.
- **Why limitations should be disclosed instead of hidden.** A portfolio project's
  credibility depends on not overclaiming. A reviewer who finds an undisclosed gap
  discounts the whole project; a reviewer who sees the gaps named up front trusts
  the rest. Disclosed limitations are a strength signal, not a weakness.
- **Why no new features should be added during final release-candidate planning.**
  New features re-open settled surfaces, invite new bugs, and push the finish line
  outward — the opposite of what a release candidate needs. The discipline that got
  the project here (additive, read-only-first, deterministic) is best served by
  *finishing* the existing scope, not extending it.
- **Why deterministic / read-only intelligence should remain the central demo
  story.** It is the project's most defensible and distinctive claim: every signal
  is reviewable, testable, and side-effect-free. Trading that for an "AI" framing
  would swap a credible, auditable story for one a knowledgeable reviewer would
  immediately probe and find hollow. The deterministic story is both the honest one
  and the stronger one.

---

## Acceptance Criteria

Phase 20A is complete when:

- The Phase 20A planning document exists (this file).
- The roadmap reflects Phase 20A and the recommended next step (Phase 20B).
- README phase/status is updated only if needed.
- No application code changed.
- No package / dependency / lockfile / build-config files changed.
- No frontend / backend behavior changed.
- The final demo release-candidate scope is clear.
- The remaining portfolio-readiness work is listed.
- The guardrails and limitations are explicit.

---

## Scope confirmation

Phase 20A did **not**:

- add backend or frontend features, endpoints, validation, or middleware;
- add or change any test or any application code;
- change any API contract or runtime behavior;
- add AI/LLM, embeddings, persistence, or query history;
- mutate graph / source / query / intelligence behavior;
- add or change dependencies, package files, lockfiles, or build configs;
- change styling/CSS, branding, or image assets;
- create, invent, or stage any screenshot;
- create a release tag or perform any deployment;
- perform a broad refactor or cleanup outside the Phase 20A documentation scope.

The change set is documentation only: this planning document plus narrow status
updates to the roadmap and (if needed) the README. **No application behavior
changed** and **no request contract changed.**

---

## Final status

Phase 20A is **complete as a demo release-candidate planning / final
portfolio-readiness scoping pass**. The demo story is stated, the demo candidate
surfaces and their evidence/overstatement guards are enumerated, the portfolio
readiness checklist and screenshot/evidence plan are defined, the known limitations
and out-of-scope items are explicit, and a controlled next-phase sequence is
recommended.

No claim is made that Hive|Mind is production-ready, production-secure, or
feature-complete. The claim is narrower and honest: the project's existing
deterministic, read-only surfaces and its documented security/readiness posture are
sufficient to scope a clean **demo/portfolio release candidate**, and this phase
locks that scope so the final-polish phases finish it without drift.
