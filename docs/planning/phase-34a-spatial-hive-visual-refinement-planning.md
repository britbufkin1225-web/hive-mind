# Phase 34A — Spatial Hive Visual Refinement Planning

**Phase:** Phase 34A — Spatial Hive Visual Refinement Planning.
**Status:** Planning / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, screenshot, or runtime change. **No new graph engine, no true
3D, no WebGL, no new dependency.**
**Relationship:** Builds directly on the shipped 2.5D Spatial Hive foundation —
the [Phase 33A 2.5D Spatial Knowledge Surface Planning](phase-33a-2-5d-spatial-knowledge-surface-planning.md),
the [Phase 33B 2.5D Spatial Hive Visual Contract + Implementation Readiness](phase-33b-2-5d-spatial-hive-visual-contract-readiness.md)
and its concise reusable [2.5D Spatial Hive Visual Contract](../2-5d-spatial-hive-visual-contract.md),
the Phase 33C foundation (PR #131) and Phase 33D UX/motion hardening (PR #132),
and the [Phase 33E 2.5D Spatial Hive QA + Screenshot Evidence](demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)
evidence pass. Complements the [roadmap](../roadmap.md) and the
[README](../../README.md) phase table.

> **One-line framing.** Phases 33C–33E built and verified a working 2.5D Spatial
> Hive. Phase 34A plans the *next refinement wave* — not more features, but a
> sharper, more premium, more dimensional, more alive, more readable, and more
> portfolio-grade version of the surface that already exists — while keeping the
> disciplined graph-primary architecture intact. This phase writes the direction;
> it changes no runtime behavior.

---

## 1. Executive summary

Phase 34A plans the **next Spatial Hive visual refinement wave** that follows the
33C/33D/33E 2.5D foundation-and-evidence pass. The 2.5D surface now exists in the
running app: deterministic near/mid/far depth tiers, a selected-node lift to the
near tier, ambient living-hive motion, and preserved overlays/inspector/keyboard
behavior, all captured against the connected local runtime in Phase 33E.

The foundation works. What it now needs is **refinement, not expansion**. The
purpose of Phase 34A is to define — before any frontend code is touched — the
direction for a focused visual-quality wave that makes the graph feel more
premium, more dimensional, more alive, and more readable, so it reads as a
portfolio-grade surface rather than a competent first implementation. This is a
planning artifact only: it names the refinement targets, the principles that
bound them, the non-goals that keep them safe, and the concrete implementation
(34B) and evidence (34C) phases that would follow.

Nothing here is implemented. No React component, CSS rule, dependency, or graph
behavior changes in Phase 34A.

---

## 2. Current baseline

The current Spatial Hive surface — as shipped in Phase 33C, hardened in Phase
33D, and QA-verified in Phase 33E — is the starting point this refinement wave
builds on. Its verified state:

- **Deterministic 2.5D depth tiers.** Nodes are placed on discrete near/mid/far
  depth tiers with a monotonic scale relationship and bounded opacity/aura
  falloff. Placement is deterministic (degree-ranked plus id-hash spread), so the
  same graph data yields the same depth structure on every reload.
- **Near/mid/far graph rendering.** All three tiers are present and legible at
  rest; the depth read is visible without interaction, and edges inherit the
  nearer endpoint's tier so the depth ordering stays coherent.
- **Selected-node focus priority.** Selecting a node lifts it to the near tier
  with legible labels and coherent incident edges; related nodes organize around
  it and unrelated nodes recede but stay readable.
- **Living-hive breathing / aura motion.** An ambient, low-amplitude,
  deterministic breathing / pulsing / aura rhythm gives the colony a living feel
  without a random walk, physics, or layout instability.
- **Preserved overlays, inspector, keyboard behavior, and orbital-control
  compatibility.** The graph stays the dominant surface with bounded overlays and
  dock (no sidebar / dashboard / card-grid regression); the selection inspector,
  the Escape dismissal order, focus management, and the opt-in orbital graph
  control remain intact and read-only.
- **Connected-runtime evidence captured in Phase 33E.** The frontend build
  passes and the Phase 33E automated browser QA (16/16 checks) verified the depth
  read, the selected-node lift, overlay bounding, reduced-motion behavior, and a
  clean console/network, against the connected local runtime (frontend `:5173` →
  backend `:8787`), with a refreshed `phase-33e-spatial-hive-*` screenshot set.

**Honest limitation carried forward.** Webcam / live hand-motion evidence is
**still not claimed** unless separately verified. Consistent with the Phase 32K
camera-blocked evidence policy, the opt-in orbital graph control remains
implemented-but-unverified by live hand motion; no motion-control liveness is
claimed by this phase or by 33E.

---

## 3. Why this phase exists

The 2.5D foundation is working — that is exactly why the next work should be
**refinement rather than more feature expansion**. Three concrete reasons:

- **The foundation is proven; the polish is not maximized.** 33C/33D shipped a
  correct, deterministic, reduced-motion-safe depth system, and 33E proved it
  renders and behaves as specified. That closes the "does it work" question and
  opens the "does it feel premium" question — which is a tuning-and-composition
  problem, not a new-capability problem.
- **Adding more features now would dilute the surface.** The graph-primary
  architecture is deliberately restrained. The highest-leverage next move is to
  sharpen what exists — depth believability, node/edge readability, graph
  atmosphere, focus cinematics — rather than bolt on new overlays, new data, or
  new interaction modes that compete with the graph.
- **Portfolio impact comes from finish, not surface area.** For a portfolio /
  demo piece, the difference between "competent" and "memorable" is presentation
  quality: how believable the depth reads, how controlled the motion feels, how
  obvious focus is, how clean the composition looks in a screenshot. That is the
  work this wave targets.

---

## 4. Visual refinement principles

The refinement wave must stay inside the principles that made the graph-primary
surface credible. These bound every 34B decision:

- **The graph remains the primary surface.** Refinement sharpens the graph; it
  never demotes it. The graph stays the full-viewport viewfinder.
- **Overlays stay secondary and non-competing.** The masthead, dock, inspector,
  and explorer stay bounded, translucent, and summoned — never permanent framing
  that competes with the graph for attention or color.
- **Dimensionality must improve readability, not become decoration sludge.**
  Every depth, glow, parallax, or atmosphere effect has to earn its place by
  making the structure *easier* to read. If an effect adds visual noise without
  adding legibility or believable depth, it does not ship.
- **Motion must feel alive but controlled.** Ambient motion stays low-amplitude,
  deterministic, and restrained. Alive, not busy; a breathing colony, not a
  screensaver.
- **Selected / focused states must stay obvious.** No refinement may soften the
  clarity of what is selected. The focused node and its neighborhood must read
  instantly, at a glance, in motion and at rest.
- **Visual density should feel intentional, not noisy.** Richness is welcome only
  where it is composed. Density that reads as clutter is a regression.
- **No fake terminal cosplay.** No fabricated "hacker" chrome, scan-lines, fake
  telemetry, or decorative liveliness that implies capability the app does not
  have.
- **No SaaS dashboard / sidebar regression.** The refinement must not
  reintroduce persistent sidebars, dashboard columns, or card-grid framing.
- **No full 3D dependency jump yet.** The depth stays a well-composed 2.5D
  illusion over the existing SVG/React view model. No Three.js / R3F / WebGL leap
  is authorized by this wave.

---

## 5. Refinement targets

The concrete refinement categories this wave should address. Each is a
*direction*, not yet a spec — 34B turns the chosen subset into numbers and named
states.

- **Depth atmosphere / parallax illusion.** Strengthen the sense that the field
  has real depth — subtle atmospheric falloff, restrained parallax between tiers,
  and a background treatment that reads as space behind the colony rather than a
  flat backdrop. Must stay legible and must not fight the tier scale.
- **Node material and glow hierarchy.** Make nodes read as objects with a
  consistent material language and a clear glow hierarchy (near vs. far, selected
  vs. related vs. ambient), so importance is legible from the material itself, not
  just from position.
- **Edge depth and routing polish.** Sharpen how edges express depth and
  relationship — nearer edges more present, farther edges receding — and reduce
  crossing/clutter so the connective structure reads cleanly at every tier.
- **Cluster / group field presence.** Give source / topic / type / size clusters
  a subtle field presence so groups read as coherent neighborhoods without adding
  hard containers or dashboard-like grouping chrome.
- **Selected-node cinematic focus.** Elevate the focus state from "lifted" to
  genuinely cinematic — a composed, obvious, premium moment when a node is
  selected — while keeping the transition controlled and the neighborhood legible.
- **Ambient hive motion restraint.** Re-tune the living-hive motion for restraint
  and cohesion, so it reads as a single organism breathing rather than many
  independent jitters. Alive, quiet, deterministic.
- **Overlay-to-graph spatial relationship.** Refine how overlays sit *over* the
  spatial field — their elevation, translucency, and shadow relationship to the
  depth field — so they feel spatially related to the graph rather than pasted on.
- **Reduced-motion compatibility.** Every refinement must degrade cleanly under
  `prefers-reduced-motion`: the depth read and selection clarity survive with
  motion flattened, and nothing relies on motion alone to convey state.
- **Responsive viewport behavior.** The refined surface must hold up across
  viewport sizes — depth, readability, and focus clarity intact from wide desktop
  down to narrow viewports, with overlays staying bounded.
- **Portfolio screenshot composition.** Bias the refined defaults toward
  compositions that read well in a still capture — a resting state and a focused
  state that both look intentional and premium in a screenshot — without staging
  fake data.

---

## 6. Non-goals / guardrails

Explicitly out of scope for this refinement wave. These are rejected up front so
34B stays narrow and safe:

- **No backend changes.** No endpoint, service, or backend logic change.
- **No API / schema changes.** No contract, request/response-shape, or model
  change.
- **No persistence changes.** No storage, store-shape, or data-writing change.
- **No new graph libraries.** No swapping or adding a graph/rendering engine.
- **No Three.js / React Three Fiber / WebGL.** The 2.5D illusion stays CSS /
  transform / SVG over the existing view model.
- **No D3 / Cytoscape / React Flow.** No layout/graph framework is introduced.
- **No physics simulation.** No force-directed layout, springs-as-physics, or
  simulated dynamics driving positions.
- **No fake data.** No fabricated nodes, edges, metrics, or liveliness.
- **No graph mutation.** The graph stays read-only — no node/edge/data/layout/
  selection writes beyond the existing display-only depth derivation.
- **No dashboard / sidebar / card-grid redesign.** The graph-primary shell is not
  reopened.
- **No broad CSS rewrite unless separately scoped.** Refinement edits existing
  rules in place; a wholesale stylesheet rewrite is not authorized here.
- **No screenshot evidence in this planning phase.** Evidence belongs to 34C, not
  34A.

---

## 7. Phase 34B implementation proposal

**Phase 34B — Spatial Hive Visual Refinement Frontend Pass.** The next likely
implementation pass: a focused, frontend-only wave that implements a chosen subset
of the Section 5 refinement targets against the Section 4 principles and the
Section 6 guardrails.

Scope should likely include:

- **`KnowledgeGraphPanel.tsx` only if needed.** Component changes only where a
  refinement genuinely requires derived depth/material/focus state; prefer CSS
  where possible, and keep any derivation display-only and deterministic.
- **`styles.css`.** The primary surface for material, glow, atmosphere, edge, and
  motion-restraint refinement — edited *in place* against the Phase 33B proposed
  class/state names, not appended to as a fresh cascade pile (see Section 9).
- **No backend.**
- **No package changes.**
- **No graph contract changes.**
- **No new dependencies.**
- **No screenshots / evidence** (those belong to 34C).

34B should pick a *bounded* subset of Section 5 to refine well rather than
attempting every category at once; a smaller, coherent, obviously-premium diff is
worth more than a broad one.

---

## 8. Phase 34C QA / evidence proposal

**Phase 34C — Spatial Hive Visual Refinement QA + Screenshot Evidence Refresh.** A
later QA / screenshot-evidence phase, run **only after 34B looks visually worth
locking**. It would validate the refined surface against the connected local
runtime and refresh the Spatial Hive screenshot set (superseding
`phase-33e-spatial-hive-*` while preserving history), following the same honest
evidence discipline as Phase 33E.

**34C is not automatic.** If the frontend visual quality is still unsettled after
34B — if the refinement needs another tuning pass — evidence capture should wait.
Screenshots lock a visual state; they should only be refreshed once that state is
worth locking. The webcam / live hand-motion limitation from Section 2 continues
to apply: no motion-control liveness is claimed until separately verified under
the Phase 32K camera-blocked evidence policy.

---

## 9. CSS cleanup relationship

Future CSS work should avoid endless cascade-winning append blocks where
practical. The Phase 31G consolidation already had to clean up an accumulated
aura/overlay cascade where successive phases stacked declarations at the same
specificity; the 2.5D depth/material/motion work is exactly the kind of change
that can rebuild that debt if it is appended rather than edited in place.

Guidance:

- **Prefer editing existing rules in place** against the authoritative Phase 33B
  proposed class/state names, rather than appending new override blocks that win
  by source order.
- **If a CSS cleanup / consolidation phase is needed, scope it narrowly and
  separately**, or fold it into 34B **only if it is safe** and clearly bounded —
  never as an open-ended rewrite.
- **Do not perform CSS cleanup in Phase 34A.** This phase changes no CSS at all;
  the cleanup relationship is documented here as guidance for 34B and beyond, not
  as work for this phase.

---

## 10. Acceptance criteria

Phase 34A is complete when:

- **Planning doc exists** — this document is present under
  `docs/planning/phase-34a-spatial-hive-visual-refinement-planning.md`.
- **README and roadmap point to it** — the README current-status and the roadmap
  reference this planning doc.
- **Roadmap reflects 33E complete and 34A current / planning** — the roadmap
  marks Phase 33E completed/merged and Phase 34A as the current planning phase,
  with 34B and 34C listed as the likely next phases.
- **No source / runtime / package files changed** — no frontend, backend, API,
  schema, CSS, package, or dependency change.
- **No screenshots added** — no image or evidence capture in this phase.
- **`git diff` confirms docs-only scope** — the diff touches only
  `docs/planning/phase-34a-spatial-hive-visual-refinement-planning.md`,
  `README.md`, and `docs/roadmap.md`.
- **Tracked files contain no conflict markers** — `git diff --check` is clean and
  no `<<<<<<<` / `=======` / `>>>>>>>` markers exist in tracked text files.

---

## 11. Deferred items

- The concrete numbers, easing curves, and named states for each refinement
  target — deferred to Phase 34B, which turns the chosen subset of Section 5 into
  an implementable spec.
- Any CSS consolidation/cleanup work — deferred to a narrowly scoped separate
  phase or a safe, bounded slice of 34B (Section 9).
- Screenshot / evidence capture — deferred to Phase 34C, and only once 34B is
  visually worth locking (Section 8).
- Live webcam / hand-motion evidence for the orbital graph control — remains
  deferred under the Phase 32K camera-blocked evidence policy; not claimed here.
- Any move toward true 3D / WebGL — out of scope for this refinement wave
  (Section 6); would require its own separate planning.

---

## 12. Next sequence

1. **Phase 34A** *(this phase)* — Spatial Hive Visual Refinement Planning
   (planning / docs only).
2. **Phase 34B** — Spatial Hive Visual Refinement Frontend Pass (frontend-only;
   `KnowledgeGraphPanel.tsx` only if needed + `styles.css`; no backend / package /
   contract / dependency / screenshot change).
3. **Phase 34C** — Spatial Hive Visual Refinement QA + Screenshot Evidence Refresh
   (QA / evidence / docs only), run only after 34B is visually worth locking.
