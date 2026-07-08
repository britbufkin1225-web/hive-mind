# Phase 35A — Spatial Hive Interaction State Planning

**Phase:** Phase 35A — Spatial Hive Interaction State Planning.
**Status:** Planning / documentation only. **No implementation.**
**Scope:** Documentation only. No frontend, backend, API, schema, package,
dependency, CSS, screenshot, or runtime change. **No interaction state
implemented, no persistence, no graph mutation, no gesture-command change, no new
graph engine, no true 3D, no WebGL, no new dependency.**
**Relationship:** Builds directly on the shipped-and-refined 2.5D Spatial Hive —
the [Phase 33A 2.5D Spatial Knowledge Surface Planning](phase-33a-2-5d-spatial-knowledge-surface-planning.md),
the [Phase 33B 2.5D Spatial Hive Visual Contract + Implementation Readiness](phase-33b-2-5d-spatial-hive-visual-contract-readiness.md)
and its concise reusable [2.5D Spatial Hive Visual Contract](../2-5d-spatial-hive-visual-contract.md),
the Phase 33C foundation (PR #131), Phase 33D UX/motion hardening (PR #132), the
[Phase 33E 2.5D Spatial Hive QA + Screenshot Evidence](demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)
evidence pass, the [Phase 34A Spatial Hive Visual Refinement Planning](phase-34a-spatial-hive-visual-refinement-planning.md),
and the completed **Phase 34B** visual-refinement frontend pass (PR #135).
Complements the [roadmap](../roadmap.md) and the [README](../../README.md) phase
table.

> **One-line framing.** Phases 33C–34B built, verified, and visually refined a
> working 2.5D Spatial Hive. Phase 35A plans the *next capability level* —
> **Level 1 interaction state**: how the Spatial Hive responds to hover,
> selection, focus, overlays, camera/view intent, and motion-control readiness as
> **transient, in-memory, reload-resettable** state — without mutating graph data,
> saving layouts, adding persistence, changing backend/API contracts, or
> implementing any frontend behavior yet. This phase writes the direction; it
> changes no runtime behavior.

---

## 1. Executive summary

Phase 35A plans the **first interaction-state layer** for the Spatial Hive. The
2.5D surface exists, is verified, and has been visually refined: deterministic
near/mid/far depth tiers, a selected-node lift to the near tier, ambient
living-hive motion, and a Phase 34B premium refinement pass, all preserving
overlays / inspector / keyboard behavior and orbital-control compatibility.

What the surface does *not* yet have is a **designed, named, coherent interaction
state model**. Today's hover/selection/overlay behaviors are real but were grown
incrementally across earlier phases; there is no single contract that says what
states the Spatial Hive can be in, how they compose, how camera/view intent
relates to them, and where the hard line sits between *transient interaction
state* and *persistent memory* or *graph mutation*.

This is the **Level 1** step in the long-term progression (Level 0 presentation
polish → **Level 1 interaction state** → Level 2 persistent view memory → Level 3
semantic visualization → Level 4 gesture commands → Level 5 dreaming preview →
Level 6 confirmed mutation). Level 1 is deliberately the next step because it is
the highest-leverage, lowest-risk capability: it makes the surface feel
responsive and intentional **without** writing any data, persisting anything, or
changing a single backend contract.

Phase 35A is a planning artifact only. It defines the interaction-state model,
the state categories, the camera/view behavior, the overlay behavior, the
motion-control relationship, the strict non-persistence rule, and the boundaries
that keep later levels out of scope — then scopes the **Phase 35B** frontend
implementation pass and its acceptance criteria. Nothing here is implemented. No
React component, CSS rule, dependency, camera behavior, or graph behavior changes
in Phase 35A.

---

## 2. Current baseline after Phase 34B

The current Spatial Hive surface — shipped in Phase 33C, hardened in Phase 33D,
QA-verified in Phase 33E, and visually refined in Phase 34B (PR #135) — is the
starting point this interaction-state work builds on. Its verified state:

- **Deterministic 2.5D depth tiers.** Nodes sit on discrete near/mid/far depth
  tiers with a monotonic scale relationship and bounded opacity/aura falloff.
  Placement is deterministic (degree-ranked plus id-hash spread), so the same
  graph data yields the same depth structure on every reload.
- **Selected-node focus priority.** Selecting a node lifts it to the near tier
  with legible labels and coherent incident edges; related nodes organize around
  it and unrelated nodes recede but stay readable.
- **Living-hive breathing / aura motion.** An ambient, low-amplitude,
  deterministic breathing / pulsing / aura rhythm gives the colony a living feel
  without a random walk, physics, or layout instability.
- **Refined visual surface (Phase 34B).** The 34B pass sharpened depth
  believability, node/edge material and glow hierarchy, focus cinematics, ambient
  motion restraint, and overlay-to-graph spatial relationship — presentation-only,
  over the same read-only view model.
- **Preserved overlays, inspector, keyboard behavior, and orbital-control
  compatibility.** The graph stays the dominant surface with bounded overlays and
  dock (no sidebar / dashboard / card-grid regression); the selection inspector,
  the Escape dismissal order, focus management, and the opt-in orbital graph
  control remain intact and read-only.

**What already behaves like interaction state today** (grown incrementally, not
yet formalized): hover lifts on nodes/edges, click-to-select and
empty-canvas-deselect, the `selected > related > ambient` emphasis tiers, the
summoned overlays and their Escape dismissal order, and the opt-in orbital camera
transform. Phase 35A's job is to *name and organize* this into a coherent model
and define the additive states around it — not to re-invent what works.

**Honest limitation carried forward.** Webcam / live hand-motion evidence is
**still not claimed** unless separately verified. Consistent with the Phase 32K
camera-blocked evidence policy, the opt-in orbital graph control remains
implemented-but-unverified by live hand motion; no motion-control liveness is
claimed by this phase.

---

## 3. Why interaction state comes next

The visual surface is proven and refined (33C–34B). The next highest-leverage
move is **interaction state**, for three reasons:

- **It is the highest value at the lowest risk.** Making the surface feel
  responsive, intentional, and alive-to-attention is what turns a beautiful
  static graph into a tool you want to *use*. And it can be done entirely in
  transient, in-memory view state — no data write, no persistence, no contract
  change — so the blast radius is small and fully reversible on reload.
- **It is the correct rung on the ladder.** The long-term progression puts
  interaction state (Level 1) before persistent view memory (Level 2), semantic
  visualization (Level 3), gesture commands (Level 4), dreaming preview (Level 5),
  and confirmed mutation (Level 6). You cannot honestly build persistent view
  memory until there is a well-defined transient view state *to* persist; you
  cannot safely add gesture commands until there is an interaction/view-state
  target for them to drive. Level 1 is the foundation the higher levels stand on.
- **It formalizes what already exists before it accretes debt.** Hover, select,
  and overlay behaviors already exist but were grown phase-by-phase. Defining a
  single interaction-state model now — before Level 3 semantic signals or Level 4
  gestures start pushing on it — prevents the same append-only cascade debt the
  Phase 31G CSS consolidation had to clean up, this time in state logic.

---

## 4. Definition: Spatial Hive Interaction State

**Spatial Hive Interaction State** is the set of **transient, in-memory,
user-session view state** that determines how the Spatial Hive *presents itself in
response to user attention and intent* — hover, selection, focus, overlay
context, camera/view pose, command-rail activity, and motion-control readiness —
**without changing any graph data, without persisting anything, and without
surviving a reload.**

It is a projection layer, not a data layer. It reads the existing read-only graph
view model and the current user attention/intent, and it decides emphasis, focus,
camera pose, and overlay context. It never writes back to the graph, the store,
the API, or any storage.

### 4.1 The four-way distinction (the load-bearing definition)

The whole phase hinges on keeping these four categories strictly separate:

| Category | What it is | Lifetime | Writes data? | In scope for Level 1? |
| --- | --- | --- | --- | --- |
| **Presentation-only visual polish** | How the surface *looks* at rest, independent of user attention — depth tiers, material, glow, ambient motion, atmosphere. | Constant per graph data | No | Already done (Level 0 / 33C–34B); **not** re-opened here |
| **Transient interaction state** | How the surface *responds* to attention/intent — hover, selection, focus, related-neighborhood emphasis, overlay context, camera pose, rail/motion-armed status. | User session, in-memory, **resets on reload** | No | **Yes — this is Level 1** |
| **Persistent view memory** | Remembering interaction/view state *across reloads* — last camera pose, last selection, saved focus, pinned overlays. | Survives reload (storage/backend) | Writes view state (not graph) | **No — Level 2, deferred** |
| **Graph data mutation** | Changing the actual graph — adding/removing/editing nodes, edges, layouts, or provenance. | Permanent (store/API) | Writes graph data | **No — Level 6, far future, confirmation-gated** |

Level 1 lives entirely in the second row. Anything that would write to storage
(row 3) or to graph data (row 4) is explicitly out of scope. Row 1 is settled and
is not re-designed here.

---

## 5. Proposed interaction-state model

A single, small, deterministic, **in-memory** view-state model owns interaction
state. It is a projection over the existing read-only view model; it does not
replace or fork it.

**Shape (conceptual, not yet typed — 35B types it):**

- **Attention inputs (read):** current pointer target (node / edge / empty
  canvas), current keyboard focus target, current selection, active overlay,
  active rail control, motion-control armed flag, `prefers-reduced-motion`.
- **Derived view state (computed):** per-node emphasis tier
  (`selected` / `related` / `ambient` / `receded`), per-edge emphasis, active
  focus target, camera/view pose (orbit/yaw/pitch/zoom/recenter intent), overlay
  context (which overlay, bound to which focus target), and the composite
  interaction state (Section 6 categories).
- **Nothing written back.** The model never mutates the graph view model, the
  store, the API, or any storage. Reload rebuilds it from scratch at the
  resting/default state.

**Composition rules (how states combine):**

- States compose predictably rather than fighting: e.g. *hover over a related
  node while a selection is active* layers a hover lift on top of the related
  tier; it does not clobber the selection.
- Exactly one **selected** node at a time (matching today's behavior); hover is
  independent of and additive to selection.
- Focus follows selection by default (Section 7); overlays bind to the current
  focus/selection context (Section 8).
- Reduced-motion is a global modifier that flattens motion in every state without
  removing the state's legibility (Section 6, reduced-motion state).

**Determinism.** Given the same graph data and the same attention inputs, the
derived view state is identical every time — no randomness, no time-dependent
divergence beyond the already-deterministic ambient motion. This keeps the
surface debuggable and screenshot-stable.

---

## 6. State categories

The interaction states the Spatial Hive can be in. These are *additive and
composable*, not a strict finite-state machine — several can hold at once (e.g.
selected + overlay-open + reduced-motion). Each is a **planning definition**; 35B
turns the chosen subset into named states and numbers.

- **Resting / default state.** No hover, no selection, no overlay, no armed
  motion control. The colony breathes at its ambient baseline; all depth tiers are
  present and legible; nothing is emphasized. This is the reload state and the
  screenshot "hero at rest" state.
- **Hover state.** Pointer (or keyboard focus) is over a node or edge with no
  commitment. A restrained, additive lift/illumination of the hovered element and
  a light hint of its direct neighbors. Fully reversible on pointer-out; never
  changes selection; never writes anything.
- **Selected node state.** Exactly one node is committed as selected. It lifts to
  the near tier with a cinematic-but-controlled focus moment, its incident edges
  read as active, and the inspector is available in context. Selecting a different
  node switches in place (no flicker); empty-canvas click deselects.
- **Related-neighborhood state.** Derived from the selection: the selected node's
  direct neighbors form one illuminated local cluster (the `related` tier), while
  unrelated nodes recede but stay readable (the `ambient` / `receded` tiers). This
  is a *derived* state, not a separately-triggered one.
- **Overlay-open state.** A summoned overlay (Vault, Sources, Intelligence,
  Console, explorer/legend, inspector) is open over the graph. The overlay is
  bounded, translucent, and bound to the current focus/selection context; the
  graph stays dominant beneath it (Section 8).
- **Command / rail active state.** The command rail (or a rail control) is
  hovered/focused/engaged. Rail labels reveal within the narrow-viewport
  containment rules already established (Phase 30B); the active control reads as
  active without stealing graph dominance.
- **Motion-control armed state.** The opt-in "Motion controls graph" affordance is
  switched on and the surface is *ready* to accept orbital camera intent — a
  distinct, visible "armed" readiness state — **without** implementing or changing
  any webcam/MediaPipe behavior (Section 9). Armed is a view-state flag plus a
  clear readout; it never implies live-motion verification.
- **Reduced-motion state.** A global modifier honoring `prefers-reduced-motion`:
  ambient and transition motion flatten, but every other state's *legibility and
  clarity survive* — selection, focus, related-neighborhood, and overlay context
  all remain obvious with motion removed. No state may rely on motion alone to
  convey itself.

---

## 7. Camera / view behavior planning

Camera/view state is **transient view pose only** — a display transform over the
existing SVG view model, exactly like the current opt-in orbital transform. It
never moves data, never changes layout, never persists.

- **Focus target.** The interaction state carries a single current *focus target*
  (typically the selected node, otherwise none). Focus is what camera behavior and
  overlays orient around. Focus is derived, in-memory, and reset on reload.
- **Orbit / yaw / pitch state.** The view pose (orbit / yaw / pitch) is a bounded,
  clamped, in-memory transform — the same read-only orbital camera already wired in
  Phase 32G/32H. Level 1 formalizes it as part of interaction state; it does not
  change the orbital math or gains.
- **Zoom state.** A bounded, in-memory zoom/scale of the view (not a data-level or
  layout-level change). Clamped to a legible range; resets on reload.
- **Recenter behavior.** An explicit recenter action (already present as
  "Recenter camera" from Phase 32H) snaps the view pose back to face-on/neutral.
  Recenter is a view-only action — never selection, never data.
- **Selected-node focus behavior.** Selecting a node *may* gently bias the view
  toward the selected node's neighborhood as a focus behavior — planned as
  **optional, restrained, and reduced-motion-safe**, and always subordinate to
  legibility. This is planning-level intent; 35B decides whether/how much
  camera-follow-on-select ships, and it must never fight the user's manual pose or
  cause motion sickness.

**Boundary:** all camera/view state is transient. Reload returns the camera to the
resting/default pose. No last-pose memory in Level 1 (that is Level 2).

---

## 8. Overlay behavior planning

Overlays are already summoned, bounded, and translucent. Level 1 formalizes how
they *relate to interaction state*:

- **Overlays respond to selected / focused context.** An open overlay should
  reflect the current focus/selection context where meaningful (e.g. the inspector
  bound to the selected node), rather than being context-free. The binding is
  read-only — the overlay reads focus state; it never writes back to it or to the
  graph.
- **Overlays must not steal graph dominance.** The graph remains the primary
  surface beneath every overlay. Overlays stay bounded, translucent, and
  non-occluding of the whole field; no overlay may become permanent framing, a
  sidebar, or a dashboard column (Phase 28A contract preserved).
- **Overlay state stays transient.** Which overlay is open, and its focus binding,
  are in-memory interaction state that resets on reload. No pinned/remembered
  overlays in Level 1 (that is Level 2 persistent view memory). The existing
  one-tertiary-overlay-at-a-time exclusivity and the Escape dismissal order stay
  intact.

---

## 9. Motion-control relationship

The Phase 32 webcam/motion-control investment is preserved but **not touched** by
Level 1:

- **Phase 35A / 35B do not implement webcam or MediaPipe changes.** No change to
  camera startup, hand-landmark detection, the `MotionCommand` contract, the
  orbital mapping helper, or the gains. The camera-blocked evidence posture (Phase
  32K) is unchanged, and no live-motion liveness is claimed.
- **Existing motion-control investment must remain compatible.** The
  interaction-state model must treat the opt-in orbital camera as *one input into
  view state* (the motion-control armed state, Section 6) so that when motion
  *is* eventually verified, it already has a well-defined interaction/view-state
  target to drive. Level 1 defines the socket; it does not plug in new motion
  behavior.
- **Future gesture control feeds interaction/view state, not graph mutation.**
  This is the durable boundary: gesture commands (the future Level 4) must drive
  **camera/focus/overlay interaction state**, never graph data mutation. Level 1
  establishes that target so Level 4 has somewhere safe to point. Motion moves the
  *view*, not the *data*.

---

## 10. Non-persistence rule (hard boundary)

Level 1 interaction state is **strictly transient**. This is a hard, testable
rule, not a preference:

- **No `localStorage`.**
- **No `sessionStorage`.**
- **No IndexedDB or any other browser storage.**
- **No backend persistence** — no endpoint, request, or store write to save view
  state.
- **No cookies or URL-encoded view state.**
- **Reload resets interaction state.** After a reload, the Spatial Hive returns to
  the resting/default state (Section 6): no remembered selection, no remembered
  camera pose, no remembered open overlay, no remembered focus. Every session
  starts clean.

If a proposed behavior would need to *remember* anything across a reload, it is
Level 2 (persistent view memory) and is **out of scope** for 35A/35B.

---

## 11. Future persistence boundary (Level 2, deferred)

**Persistent view memory is Level 2 and must be planned later, not here.** Once
Level 1 defines a clean transient view state, Level 2 can plan how (and whether) to
remember pieces of it across reloads — last camera pose, last selection, saved
focus arrangements, pinned overlays — with an explicit storage decision (local vs.
backend), a clear user-facing model (opt-in, resettable), and its own guardrails.

Level 2 is called out here only to **draw the boundary**: nothing in 35A or 35B may
implement persistence, and the transient model must be designed so that a *future*
Level 2 could layer persistence on top **without** having to re-architect Level 1.
Design for future persistence; implement none.

---

## 12. Future semantic boundary (Level 3, deferred)

**Semantic visualization is Level 3 and must not drive visual state in this
phase.** The backend-derived intelligence signals — **Temporal Decay**,
**Provenance Chains**, **Query Trails**, and **Dreaming Suggestions** — must
**not** feed the Spatial Hive's node/edge/emphasis/depth state in Level 1.

Level 1 interaction state responds to *user attention and intent* (hover, select,
focus, camera, overlays), not to *intelligence/semantic signals*. Wiring decay,
provenance, query trails, or dreaming into the visual state is a distinct, later
capability (Level 3 semantic visualization) with its own honesty requirements
(real backend-derived data only, no fabricated liveliness). Keeping the two
separate now prevents Level 1 from accidentally implying the graph is reacting to
intelligence when it is only reacting to the pointer.

---

## 13. Phase 35B implementation proposal

**Phase 35B — Spatial Hive Interaction State Frontend Pass.** The next likely
implementation pass: a focused, frontend-only wave that implements a chosen subset
of the Section 6 state categories and Section 7–8 camera/overlay behaviors against
this model and its guardrails.

Scope should likely include:

- **A small, typed, in-memory interaction-state model** — likely in
  `KnowledgeGraphPanel.tsx` and/or a small dedicated frontend view-state helper
  module — that formalizes the existing hover/select/related/overlay behaviors and
  adds the additive states (focus target, camera/view pose as interaction state,
  motion-control armed state, reduced-motion modifier). Deterministic and
  display-only.
- **`styles.css`** — interaction-state styling edited **in place** against the
  Phase 33B proposed class/state names (`graph-focus-state`,
  `graph-node-focus-anchor/related`, `graph-node-receded`, `graph-hive-state`,
  `graph-reduced-motion`, etc.), not appended as a fresh cascade pile (Phase 34A
  §9 CSS-cleanup relationship).
- **`App.tsx` only where focus/overlay/rail wiring genuinely requires it** — e.g.
  binding overlay context to focus state — kept minimal.
- **No backend.**
- **No persistence** (Section 10) — no storage of any kind.
- **No webcam / MediaPipe change** (Section 9).
- **No graph data mutation** — the graph stays read-only.
- **No new dependency, no new graph library, no Three.js / R3F / WebGL / D3 /
  Cytoscape / React Flow, no physics.**
- **No screenshots / evidence** (those belong to a later QA/evidence phase, and
  the Phase 34C-style evidence refresh remains deferred, not next-active).

35B should pick a **bounded** subset of Section 6 to implement well rather than
every state at once; a smaller, coherent, obviously-responsive diff is worth more
than a broad one.

---

## 14. Acceptance criteria for Phase 35B

Phase 35B (the future implementation pass, **not** this phase) would be complete
when:

- **A named, in-memory interaction-state model exists** that formalizes the
  resting, hover, selected, related-neighborhood, overlay-open, rail-active,
  motion-armed, and reduced-motion states as a coherent composable set.
- **States compose predictably** — hover layers on selection, overlays bind to
  focus, reduced-motion flattens motion without losing legibility — with exactly
  one selected node at a time and flicker-free in-place selection switching.
- **Camera/view state is transient view pose only** — orbit/yaw/pitch/zoom/recenter
  behave as bounded, clamped, read-only view transforms; selecting a node's
  optional focus-bias (if shipped) is restrained and reduced-motion-safe.
- **Overlays respond to focus context, stay bounded, and stay transient** — no
  overlay steals graph dominance; the Escape order and exclusivity are intact.
- **The non-persistence rule holds** — no `localStorage` / `sessionStorage` /
  IndexedDB / cookie / backend write; **a reload returns the surface to the
  resting/default state** with no remembered selection, camera pose, or overlay.
- **No graph mutation** — the graph view model, store, and API are untouched; the
  graph stays read-only.
- **No webcam/MediaPipe/motion behavior change** — the motion-control armed state
  is a view flag + readout only; no live-motion liveness is claimed.
- **Reduced-motion and responsive behavior hold** — every state degrades cleanly
  under `prefers-reduced-motion` and across viewport sizes.
- **`npm run check:frontend` passes**, with no new dependency and no console/network
  errors introduced.

(These are targets for the future 35B pass; Phase 35A asserts none of them as
done.)

---

## 15. Non-goals and guardrails

Explicitly out of scope for Phase 35A (and, where noted, for 35B):

- **No interaction-state implementation in 35A.** This phase writes the plan; it
  changes no code.
- **No persistence** (35A or 35B) — no `localStorage` / `sessionStorage` /
  IndexedDB / cookie / backend view-state write (Section 10). Level 2 only.
- **No graph data mutation** — the graph stays read-only at every level of this
  plan; mutation is Level 6, far future, confirmation-gated.
- **No gesture-command changes** — no webcam / MediaPipe / `MotionCommand` /
  orbital-mapping change (Section 9). Level 4 only.
- **No semantic/intelligence signals driving visual state** — decay, provenance,
  query trails, dreaming stay out of the visual state (Section 12). Level 3 only.
- **No backend / API / schema / contract change.**
- **No new dependency, no new graph library** — no Three.js / React Three Fiber /
  WebGL / D3 / Cytoscape / React Flow / physics.
- **No dashboard / sidebar / card-grid regression** — the graph-primary shell
  (Phase 28A) is not re-opened.
- **No fake data or fabricated liveliness** — no invented nodes/edges/metrics, no
  "hacker" cosplay, no implied capability the app lacks.
- **No broad CSS rewrite unless separately scoped** — 35B edits existing rules in
  place.
- **No screenshot / evidence pass** — the Phase 34C-style evidence refresh remains
  **deferred, not next-active**; 35A adds no screenshots.

---

## 16. Risks and mitigations

- **Risk: interaction state quietly grows into persistence.** A "remember the last
  selection" convenience is a Level 2 feature in disguise.
  **Mitigation:** the hard non-persistence rule (Section 10) and the reload-resets
  acceptance criterion (Section 14) — any cross-reload memory fails review.
- **Risk: camera-follow-on-select causes motion sickness or fights the user.** An
  over-eager auto-camera on selection can feel nauseating or wrest control away.
  **Mitigation:** camera-follow is planned as *optional, restrained,
  reduced-motion-safe, and subordinate to the user's manual pose* (Section 7);
  35B may ship it minimally or not at all.
- **Risk: state append-only debt (a repeat of the 31G CSS cascade problem), now in
  logic.** Bolting states on ad hoc recreates tangled, unpredictable composition.
  **Mitigation:** one small composable model with explicit composition rules
  (Section 5) and in-place CSS against the Phase 33B names (Section 13).
- **Risk: overlays creep back toward permanent framing.** Binding overlays to
  focus could tempt "keep it open" behavior.
  **Mitigation:** overlays stay bounded, transient, exclusive, and Escape-dismissed
  (Section 8); graph dominance is a review gate.
- **Risk: motion-armed state implies live-motion works.** An "armed" readout could
  be read as "verified working."
  **Mitigation:** armed is a *readiness* flag with honest copy; the Phase 32K
  camera-blocked posture and "no liveness claimed" language are preserved
  (Section 9).
- **Risk: scope creep into semantic reactions.** It is tempting to let decay or
  provenance tint nodes "while we're in here."
  **Mitigation:** the Level 3 semantic boundary (Section 12) keeps intelligence
  signals out of Level 1 visual state entirely.

---

## 17. Recommended next sequence

1. **Phase 35A** *(this phase)* — Spatial Hive Interaction State Planning
   (planning / docs only).
2. **Phase 35B** — Spatial Hive Interaction State Frontend Pass (frontend-only;
   a bounded subset of the Section 6 states + Section 7–8 camera/overlay behaviors;
   in-memory only; `KnowledgeGraphPanel.tsx` / small view-state helper / `styles.css`
   / minimal `App.tsx`; **no persistence, no graph mutation, no webcam/MediaPipe
   change, no new dependency, no screenshots**).
3. **Later — Spatial Hive Interaction State QA + Evidence** — a Phase 34C-style
   QA/screenshot-evidence refresh, **deferred and not next-active**, run only once
   the interaction surface is visually and behaviorally worth locking, still under
   the Phase 32K camera-blocked evidence policy.
4. **Future — Level 2** (persistent view memory), then **Level 3** (semantic
   visualization), **Level 4** (gesture commands feeding view state), **Level 5**
   (dreaming preview without mutation), and **Level 6** (graph mutation only with
   explicit human confirmation) — each its own separately-planned phase.

---

## 18. Acceptance criteria for Phase 35A (this planning phase)

Phase 35A is complete when:

- **Planning doc exists** — this document is present under
  `docs/planning/phase-35a-spatial-hive-interaction-state-planning.md`.
- **README and roadmap point to it** — the README current-status marks Phase 35A
  as docs/planning-only with screenshot/evidence deferred and links this doc; the
  roadmap references it.
- **Roadmap reflects the ladder** — Phase 34B marked complete, Phase 35A the
  current planning phase, a proposed Phase 35B row (not complete), and Phase 34C
  evidence preserved as **deferred, not next-active**.
- **No source / runtime / package files changed** — no frontend, backend, API,
  schema, CSS, package, dependency, or screenshot change.
- **`git diff` confirms docs-only scope** — the diff touches only
  `docs/planning/phase-35a-spatial-hive-interaction-state-planning.md`,
  `README.md`, and `docs/roadmap.md`.
- **Tracked files contain no conflict markers** — `git diff --check` is clean and
  no `<<<<<<<` / `=======` / `>>>>>>>` markers exist in tracked text files.
