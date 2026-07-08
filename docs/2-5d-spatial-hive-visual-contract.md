# 2.5D Spatial Hive Visual Contract

**Type:** Reusable frontend visual contract. **Status:** Contract only — no runtime
implementation. **Read this before implementing any 2.5D depth, Hive-State, or
Focus-State behavior.**

This is the concise, self-contained contract a future implementation session can
build against without rereading the whole roadmap. It is the distilled form of the
long-form
[Phase 33B readiness doc](planning/phase-33b-2-5d-spatial-hive-visual-contract-readiness.md),
which in turn derives from the
[Phase 33A planning doc](planning/phase-33a-2-5d-spatial-knowledge-surface-planning.md).
If this doc and the long-form doc disagree, the long-form doc wins.

---

## 1. Purpose

Define how the Hive|Mind knowledge graph becomes a **2.5D spatial hive** — a layered,
orbit-able, living-colony surface — using **frontend-safe depth illusion only** over
the existing read-only SVG view model. The goal: the graph should feel like a
handled spatial knowledge object that is alive but calm, without adopting true 3D, a
graph library, a physics engine, or any new dependency. The depth is a composed
illusion; it is **not** true 3D.

---

## 2. Non-negotiable visual rules

- The **graph dominates** — full-viewport primary surface/viewfinder, never a widget
  in a card grid.
- **No persistent sidebar / dashboard column.** Tools stay contextual overlays.
- **Color lives in the graph** (nodes/edges/aura); the shell stays dark, chrome,
  neutral. No accent color in shell chrome or overlays.
- **Depth feels spatial, not cartoonish** — restrained, believable near/far.
- **Motion feels alive, not random** — coordinated, low-amplitude, deterministic.
- **Focus clarifies, never obscures** — Focus-State makes the selection easier to
  read.
- **Overlays support the graph** — translucent, bounded, non-occluding; opening one
  never flattens the spatial field into a dashboard.
- **Read-only always** — no graph mutation, no layout editing, no data change.

---

## 3. Depth tiers

Every node resolves to one discrete depth tier (primary depth handle):

| Tier | Role | Scale | Opacity | Aura/glow | Labels |
| --- | --- | --- | --- | --- | --- |
| **near** | foreground / selected / anchor | largest | full | strongest | always legible |
| **mid** | related cluster / secondary | medium | high | moderate | readable |
| **far** | unrelated / background | smallest | reduced | soft | may reduce, never noise |

Rules:

- Scale ramp is **monotonic and bounded** (near > mid > far) — enough to read as
  depth, not cartoonish.
- Opacity falloff never drops a node/label below readable.
- Edges inherit tier from endpoints: incident/foreground edges come forward;
  background edges thin and dim. **No glowing hairball.**
- Optional **blur** on the far tier only — minimal, guarded, disabled under
  reduced-motion / low-power; depth must be fully legible with blur off.
- **Selected node always rises** to near. **Related cluster gets secondary lift** to
  near/mid. **Unrelated nodes recede** to mid/far but stay readable — never removed.
- Depth must **improve readability**, not decorate. Test: does depth make the
  selected neighborhood easier to read? If not, dial it back.

Proposed classes: `graph-depth-tier-near`, `graph-depth-tier-mid`,
`graph-depth-tier-far`.

---

## 4. Hive-State (ambient / resting)

The non-selected colony feels alive through subtle, coordinated motion, while staying
fully legible.

- **Deterministic breathing** — slow, low-amplitude scale/opacity oscillation.
- **Phase-organized pulsing** — glow pulse organized by cluster phase so a cluster
  reads as one organism; clusters sit at reproducible offset phases.
- **Aura / ring oscillation** — halos expand/settle within a tight clamp.
- **Spring-to-home micro-movement** — barely-perceptible bounded drift around each
  node's deterministic home; always springs back, never wanders.
- **No random walk, no physics dependency, no layout instability, no data mutation.**
- **Idle graph feels alive without becoming noise** — a user can read it while it
  breathes.

Proposed class: `graph-hive-state`, `graph-colony-cluster`.

---

## 5. Focus-State (selected / inspected)

The colony leans toward attention — same renderer, attentive pose.

- **Selected node = spatial anchor** — promoted to near tier; largest, sharpest,
  strongest glow; legible through orbit.
- **Related nodes = illuminated local cluster** — come to near/mid, organize into a
  calmer, tighter, readable arrangement.
- **Unrelated nodes recede** — to background; dimmer/softer; never removed.
- **Selected edges legible** — incident edges promoted; distant edges recede.
- **Inspector feels connected** to the anchored node, not a detached sidebar;
  overlays stay translucent so the anchor reads through/behind them.
- **Ambient damps, focus energizes** — global rhythm calms while the focused cluster
  gains a slightly livelier attentive rhythm.
- **Keyboard + pointer parity** — identical behavior; focus indicators preserved.
- **Read-only preserved** — selecting only selects; deselect returns to Hive-State
  non-destructively via a short eased, reversible transition.

Proposed classes: `graph-focus-state`, `graph-node-focus-anchor`,
`graph-node-focus-related`, `graph-node-receded`.

---

## 6. Determinism

**Same graph data ⇒ same visual structure every reload.**

- Per-node phase/period/home-offset from a **stable hash of the node id**.
- Cluster rhythm/grouping from a **stable hash of the grouping key** (source / topic
  / type / size).
- Deterministic phase offsets from (cluster key + node id).
- Deterministic depth-tier assignment: relationship-to-selection first, then stable
  structural fallback (id/degree/type hash); resting tiers fall back to a
  deterministic structural default.
- Deterministic aura rhythm and deterministic grouping fallback (defined order, e.g.
  type → source → degree).
- **No `Math.random()`, no time-seeded jitter, no unbounded drift.** If it can't be
  derived deterministically from stable ids/keys or existing relationships, it isn't
  added. Never fabricate a trait to force grouping.

Proposed class: `graph-reduced-motion` (see §7).

---

## 7. Reduced-motion / accessibility

- **Respect `prefers-reduced-motion`** — hard requirement.
- **Flatten colony motion** — ambient breathing/pulsing/drift/parallax clamp toward
  zero; colony becomes still-but-layered; no idle drift.
- **Focus still works** under reduced motion — selection still lifts; emphasis
  carried by depth/opacity/scale; Hive↔Focus becomes a near-instant emphasis change.
- **Preserve keyboard focus indicators** — never painted over or dimmed below
  visibility.
- **Maintain readable labels/contrast** at every tier that matters.
- **Never rely on motion alone** to communicate state — all state (selected /
  related / receded / cluster) readable from static depth/opacity/scale/color.
- **Webcam control stays optional** — full usability by pointer/keyboard without it.

---

## 8. Runtime implementation boundaries

Future implementation **must**:

- Derive all depth/state metadata (`zDepth`, tier, phase, home-offset, cluster key,
  selected/related/receded flags) on the **frontend, at render time, display-only**.
- Layer on top of the existing read-only SVG view model and existing selection
  semantics.
- Ride the existing orbital camera path (`integrateOrbitalCamera` → single shared CSS
  transform) for any depth-intensity coupling.
- Keep the `MotionCommand` → `OrbitalGraphControlCommand` → camera bridge intact and
  separate.
- Prefer compositor-friendly properties (`transform`, `opacity`); compute depth once
  per selection/hover change, not per frame; carry per-frame motion through the
  existing `motionCommandRef` zero-re-render path.

Future implementation **must not**:

- Add any dependency (no graph/camera/gesture/physics/3D library).
- Add Three.js / React Three Fiber / D3 / Cytoscape / React Flow / canvas / WebGL.
- Change backend / API / schema / persistence, or persist/transmit derived display
  state.
- Mutate graph data, add mutation controls, or make the graph writable.
- Reintroduce a persistent sidebar/dashboard grid or splash color into shell chrome.
- Rebuild CSS cascade debt — edit authoritative rules in place, don't append
  same-specificity overrides.
- Use randomness or fabricate data/traits/evidence.

---

## 9. Future implementation checklist

Before an implementation pass (33C+) is considered done:

- [ ] Depth reads as spatial (believable near/far) **without** true 3D.
- [ ] Selected node visually lifts to the near tier as the spatial anchor.
- [ ] Related cluster organizes into one readable illuminated cluster.
- [ ] Unrelated nodes recede but remain readable (never removed).
- [ ] Ambient Hive-State feels alive but calm and stays legible while breathing.
- [ ] All motion is low-amplitude, deterministic, and reproducible across reloads.
- [ ] `prefers-reduced-motion` yields a still-but-layered, fully usable surface with
      focus indicators intact.
- [ ] Keyboard and pointer selection reach Focus-State identically.
- [ ] Graph stays read-only; selection/inspector semantics unchanged.
- [ ] No new dependency; no backend/API/schema change; no fake data.
- [ ] Proposed class/state names (or documented extensions following the same
      `graph-` prefix + tier/state orthogonality) are used; no ad-hoc cascade
      appends.
- [ ] `npm run check:frontend` passes with no bundle/dependency regression.
- [ ] Evidence/screenshots remain deferred per the Phase 32K camera-blocked evidence
      policy — nothing fabricated or simulated.
