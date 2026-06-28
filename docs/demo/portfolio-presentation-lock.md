# Hive|Mind — Portfolio Presentation Lock

Parent label: **devdevbuilds**

**Status: Phase 20C — Final Demo Script + Portfolio Presentation Lock
(documentation only).** This document locks the **presentation spine** for
Hive|Mind: the fixed narrative, surface order, and honesty boundaries the project
will present with, so the demo story stops moving before any further UI work
begins. It changes no backend, frontend, API, schema, dependency, or test
behavior.

It is the companion to the [Final Demo Script](final-demo-script.md) (the spoken
walkthrough) and consumes the locked scope from the
[Phase 20A Demo Release Candidate Planning](../release-readiness/phase-20a-demo-release-candidate-planning.md).

---

## Why a presentation lock

Polishing UI against an unlocked story produces churn: a panel reworked before the
narrative is fixed gets reworked again. Locking the presentation spine first makes
every later pass — screenshot capture, UI tightening, public writeup — a single
finishable step against a fixed input instead of a moving target. UI work is
**intentionally deferred** until this lock holds.

## Locked one-line story

> **Hive|Mind is a local-first developer knowledge intelligence dashboard that
> organizes imported knowledge sources, visualizes their relationships, and derives
> deterministic, read-only intelligence signals — temporal decay, dreaming
> suggestions, provenance chains, and query trails — from existing structure rather
> than from any AI/LLM call.**

Every surface, doc, and screenshot should echo this story without drift.

## Locked surface order

The demo presents surfaces in data-flow order. This order is fixed for the demo
candidate:

1. README / repo landing
2. Backend health + API docs
3. Source Registry
4. Obsidian Import
5. Knowledge Graph
6. Intelligence Report (Temporal Decay → Dreaming → Provenance → Query Trails)
7. Hive Console
8. Agent Lab docs

The per-surface narration lives in the
[Final Demo Script](final-demo-script.md#7-what-each-major-surface-demonstrates).

## Locked honesty boundaries

These claims are fixed and must not drift in any presentation artifact:

- **Deterministic, not AI.** Every intelligence signal is reviewable rule-based
  derivation; there is no model inference, embedding, or vector search.
- **All four Intelligence sections are backend-derived and read-only.** None is
  fixture-backed (Query Trails became backend-derived in Phase 16C).
- **Read-only surfaces.** The graph and the Intelligence Report never mutate the
  store, sources, or graph; suggestions are advisory and never auto-applied.
- **One-shot import.** No live Obsidian watcher and no write-back to the vault.
- **No persisted query history yet.** `repeated_query` / `unresolved_question`
  stay deferred; nothing fabricates query memory.
- **Demo-grade, not production.** Single-user, local, no network exposure; a
  defensive API posture from the Phase 18 arc, **not** production-hardened
  security. No auth, users, roles, or permissions.
- **Agent-assisted, human-reviewed.** Agents propose, organize, draft, or review;
  **devdevbuilds remains the decision-maker, reviewer, validator, and merge gate.**

## What this lock intentionally defers

- UI expansion and dashboard redesign.
- Screenshot/evidence capture (executed against real app state in a later capture
  pass; see the
  [Phase 20A screenshot/evidence plan](../release-readiness/phase-20a-demo-release-candidate-planning.md#screenshot--demo-evidence-plan)).
- Query memory persistence, richer decay signals, new intelligence surfaces.
- AI/LLM, embeddings, auth, multi-user, cloud sync, production deployment.

## Presentation-lock checklist

- [x] One-line story locked and echoed across landing docs.
- [x] Surface order fixed for the demo candidate.
- [x] Honesty boundaries enumerated and consistent with README/roadmap.
- [x] Final demo script authored as the canonical walkthrough.
- [x] Deferred work named, not implied as present.
- [ ] Screenshot/evidence capture — deferred to a later capture pass.
- [ ] UI tightening — deferred until after presentation lock.

## Relationship to other docs

- [Final Demo Script](final-demo-script.md) — the spoken/written walkthrough.
- [Phase 20A Demo Release Candidate Planning](../release-readiness/phase-20a-demo-release-candidate-planning.md)
  — the locked release-candidate scope, surfaces, evidence guards, and limitations.
- [Roadmap](../roadmap.md) — phase history and future tracks.
- [Demo Guide](../demo-guide.md) / [Screenshot Checklist](../screenshot-checklist.md)
  — framing reference and the capture target list for the later capture pass.
