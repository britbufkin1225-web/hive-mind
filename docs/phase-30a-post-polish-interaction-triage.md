# Phase 30A — Post-Polish Interaction Triage + Next Frontend Direction Planning

## Status

Planning phase. **No implementation.** This document reviews the Phase 29C
QA outcome, triages the remaining interaction rough edges into a prioritized
next wave, and defines a locked implementation contract for Phase 30B before
any frontend code is touched. It changes no frontend, CSS, backend, API,
schema, package, dependency, runtime asset, or screenshot state.

This phase does not "just fix" anything. There is no CSS in this document, no
hover trickery, no quiet one-line patch smuggled in under a planning heading.
The two known limitations are triaged here and *implemented* in Phase 30B —
not before.

This document inherits in full the
[Phase 28A True Graph-Primary Surface + Overlay Contract](phase-28a-true-graph-primary-overlay-contract.md)
(including its Section 6 visual correction lock), the
[Phase 29A Graph Interaction + Overlay Polish Planning](planning/phase-29a-graph-interaction-overlay-polish-planning.md)
contract, and the honest limitations recorded in the
[Phase 29C QA + Screenshot Evidence](demo/phase-29c-graph-interaction-overlay-polish-qa-screenshot-evidence.md).

---

## 1. Phase 29C Review

Phase 29C was the QA / evidence pass immediately after the Phase 29B
interaction implementation. It re-ran the connected local runtime (backend
`8787`, frontend `5173`) and verified the Phase 29A interaction contract
against the real app across 28 scripted checks. What it confirmed:

- **The graph-primary surface exists and holds.** The Knowledge Graph SVG
  canvas fills the viewport edge-to-edge; there is no persistent sidebar,
  dashboard column, or card-grid framing in any observed state (default,
  hover/focus, selection, inspector, overlay-open, tools-overlay, narrow
  viewport).
- **Overlays and tools function as contextual, graph-subordinate surfaces.**
  The explorer (legend/lists) summons as a bounded floating card; the four
  dock tools (Vault, Sources, Intelligence, Console) open as bounded glass
  drawers, one tertiary overlay at a time; the inspector mounts on selection
  and stays a bounded card, never a viewport majority.
- **The interaction model reads correctly.** Additive hover lifts on nodes
  and edges, the three-tier selected > related > ambient/dimmed emphasis,
  flicker-free in-place selection switching, edge selection, empty-canvas
  click-to-deselect (and its correct no-op when nothing is selected), the
  Escape dismissal order (tertiary dock → explorer → selection/inspector,
  one surface per press), one-tool-at-a-time exclusivity, and deliberate
  overlay persistence across deselection all verified.
- **Screenshot evidence was captured** for the default at-rest shell,
  hover/focus, selected node, inspector context (edge selection), overlay
  open (explorer), tools overlay (Intelligence dock), and the narrow (420px)
  viewport — seven connected-runtime captures, each visually re-verified.
- **The frontend check passed.** `npm run check:frontend` (`tsc -b &&
  vite build`) completed with zero errors.
- **The backend was untouched** and therefore not re-tested. The directly
  exercised endpoints returned the same shapes/values as the established
  evidence trail (health `0.1.0`, graph 7 nodes / 6 edges, Intelligence
  Report Dreaming 0 / Decay 7 / Provenance 7 / Query Trails 7).
- **Remaining issues are interaction-polish issues, not foundational
  failures.** The two rough edges Phase 29C recorded (Escape focus scoping
  after dock close; focused-rail label overflow at very narrow widths) are
  small, localized, and honestly documented — the shell, the graph-primary
  contract, the overlay hierarchy, and the interaction model are all sound.

**Assessment:** Phase 29 landed the interaction/overlay contract cleanly.
The surface direction is correct and locked. What is left is a short,
targeted recovery pass on two keyboard/responsive details — exactly the kind
of narrow, contract-bounded wave Phase 30B is scoped to be.

---

## 2. Known Limitations

The two required limitations, each triaged with current behavior, why it
matters, its user-facing effect, a recommended future fix direction, and a
risk level. These are the primary inputs to the Phase 30B scope.

### 2.1 Escape / focus behavior after dock close

- **Current behavior.** The dock (tertiary overlay) layer handles Escape on
  a window-level capture listener, while the explorer and selection layers
  handle Escape via the graph panel's scoped `onKeyDown`. When the dock
  closes, focus is intentionally returned to the rail button that summoned
  it — and that button sits *outside* the graph panel. Because the
  explorer/selection Escape handler is scoped to the panel, the very next
  Escape press lands on an element outside that scope and is ignored until
  focus re-enters the panel.
- **Why it matters.** The Phase 29A contract promises a predictable Escape
  dismissal *stack*: one press peels one surface, repeated presses walk down
  to a bare graph. A press that silently does nothing breaks that promise
  and makes the keyboard model feel unreliable exactly when a keyboard user
  is leaning on it.
- **User-facing effect.** Mouse users never notice — re-entering the graph
  with the pointer restores panel focus before they press Escape again. Pure
  keyboard users hit one "dead" Escape after closing a dock and must Tab (one
  extra level of focus travel) back into the panel before Escape resumes
  peeling the explorer/selection. The dismissal *order itself* is correct
  once focus is in the panel; this is a focus-scoping gap, not an ordering
  bug.
- **Recommended future fix direction.** Unify where Escape is handled so the
  dismissal stack is honored regardless of which element currently holds
  focus — e.g., route dock/explorer/selection Escape through a single
  consistent listener scope, and/or return focus after dock close to a
  target inside the graph panel's Escape scope rather than to a rail button
  outside it. The fix must **not** introduce a focus trap: Tab and Escape
  must keep working, and focus must never be yanked away from where a
  keyboard user reasonably expects it. No new focus-management library.
- **Risk level.** **Low–Medium.** The behavioral target is clear and the
  affected surface is small, but focus/Escape wiring touches several layers
  (dock listener, panel `onKeyDown`, focus-return targets) and is easy to
  regress — a careless fix could trap focus or double-handle Escape (peeling
  two surfaces per press). Requires careful keyboard re-verification in
  Phase 30C.

### 2.2 Focused rail label overflow at 420px

- **Current behavior.** The bottom-docked control rail is icon-only at rest
  and reveals text labels on hover/focus. At 420px width the at-rest
  icon-only rail fits comfortably on screen (confirmed by the Phase 29C
  fresh-load narrow-viewport capture). But when the rail *holds focus* and
  reveals its labels, the expanded labeled rail widens past the viewport
  edge, clipping the `Console` label.
- **Why it matters.** The graph-primary contract requires the utility rail to
  stay reachable and legible on narrow viewports. A label that runs off the
  screen edge undercuts the "compact, intentional, dismissible" utility
  promise and looks unfinished in exactly the responsive state a reviewer is
  likely to test.
- **User-facing effect.** On a ~420px viewport, focusing/expanding the rail
  clips the last label (`Console`) at the right edge. At-rest icon-only
  behavior is unaffected and acceptable; the overflow appears only in the
  focused/expanded state. No functionality is lost (the control is still
  activatable) — it is a visual clipping issue.
- **Recommended future fix direction.** Add a responsive rule for the
  *focused/expanded* rail at narrow widths so revealed labels stay within
  the viewport — candidate approaches include wrapping/stacking the expanded
  rail, constraining/scrolling it within the viewport, revealing only the
  focused item's label rather than all labels at once, or keeping the rail
  icon-only below a breakpoint while still exposing the label to assistive
  tech (e.g., `aria-label`/tooltip) rather than as inline layout width. The
  at-rest icon-only compact rail behavior must be preserved. This must be a
  **narrow responsive rule**, not a rail redesign.
- **Risk level.** **Low.** Contained, presentational, and reversible; the
  main risk is scope creep into a broader rail/nav redesign, which the
  Phase 30B forbidden scope explicitly blocks.

### 2.3 Carried-forward context (not a Phase 30B target)

- The **Vault summary zeroed counts vs. the populated 7-node/6-edge mock
  graph** split (unpopulated vault importer vs. the mock graph fixture) has
  been documented since Phase 27E and is *not* an interaction/polish issue.
  It stays out of Phase 30B scope and is noted here only so it is not
  mistaken for an interaction regression.

---

## 3. Phase 30B Candidate Scope

**Recommended Phase 30B title:**
**Phase 30B — Interaction Recovery + Responsive Rail Frontend Implementation
Pass.**

Phase 30B is a **narrow, interaction-specific frontend implementation pass**
against this document — not an open-ended polish wander and not a redesign.

### 3.1 Direction decision — what the next wave focuses on

Of the candidate frontend directions (keyboard/focus behavior; Escape /
deselect / dock-close behavior; rail/menu responsive behavior; overlay
hierarchy refinement; graph hover/select/deselect interaction cleanup;
inspector context behavior; narrow-viewport polish), Phase 30B focuses on
exactly two, because they are the only two the Phase 29C QA surfaced as real
defects against the locked contract:

1. **Keyboard / Escape / focus recovery after dock close** (Limitation 2.1).
2. **Responsive rail behavior — focused-label overflow at narrow widths**
   (Limitation 2.2).

Everything else in the candidate list — overlay hierarchy refinement, graph
hover/select/deselect cleanup, inspector context behavior, broader
narrow-viewport polish — verified correctly in Phase 29C and is
**explicitly deferred**. There is no defect there to chase, and reopening a
passing surface risks regressing a locked contract for no user benefit.

### 3.2 Phase 30B may touch

- `apps/frontend/src/components/KnowledgeGraphPanel.tsx` — the primary
  interaction surface where the explorer/selection Escape scope and the rail
  live.
- `apps/frontend/src/styles.css` — the responsive rule for the
  focused/expanded rail at narrow widths.
- Existing frontend graph helper / view-model files — **only if truly
  needed** for presentation-safe focus/label state, with no data or contract
  change.
- `apps/frontend/src/App.tsx` (or wherever the shell/overlay wiring lives) —
  **only if** the dock-close focus-return / Escape-scope wiring requires it.
- `README.md` / `docs/roadmap.md` — minimal status updates only.

### 3.3 Phase 30B implementation targets

- **Restore predictable Escape behavior after dock close** — a keyboard user
  who closes a dock and presses Escape again should have that press peel the
  next surface (explorer, then selection/inspector), not hit a dead key.
- **Improve focus return without trapping the user** — dismissing an overlay
  returns focus somewhere sensible and inside the Escape scope, while Tab and
  Escape keep working and focus is never yanked away unexpectedly. No focus
  trap.
- **Prevent focused rail labels from overflowing** on narrow viewports so the
  expanded/focused rail stays within the screen edge (no clipped `Console`
  label at ~420px).
- **Preserve icon-only compact rail behavior** at rest and wherever it is
  already correct; the responsive change targets only the focused/expanded
  narrow-viewport state.
- **Keep overlays contextual and graph-subordinate** — no change to the
  overlay hierarchy, stacking, exclusivity, or bounded-glass treatment that
  Phase 29C verified.
- **Improve keyboard interaction clarity** within the existing patterns and
  ARIA affordances; no new keyboard framework, no command-palette build-out.
- **Avoid broad layout redesign** — this is a recovery pass, not a reshape.

---

## 4. Phase 30B Forbidden Scope

Phase 30B must **not** include:

- No backend changes.
- No API / schema / contract changes.
- No package / dependency changes.
- No new graph libraries (no D3, Cytoscape, React Flow, canvas-force, 3D).
- No fake data, fake states, or fabricated intelligence signals.
- No graph mutation controls of any kind; the graph stays read-only.
- No new dashboard / card-grid shell.
- No persistent sidebar or permanent labeled navigation bar.
- No asset / icon / favicon / image dump; no new runtime assets.
- No broad CSS rewrite — only the narrow responsive rule(s) and the focus
  wiring the two limitations require.
- No unplanned visual redesign; no "while I'm here" restyling of surfaces
  that already passed Phase 29C.
- No screenshot / evidence work — that is Phase 30C's job, if separately
  scoped.
- No new persistence, auth/session work, Obsidian importer changes, or
  AI/LLM integration.
- No reopening of already-passing interaction surfaces (hover, selection,
  inspector, overlay stacking) except where the two named limitations
  genuinely require a touch.

---

## 5. Recommended Phase Sequence

The next clean, controlled sequence:

| Phase | Type | Purpose |
| --- | --- | --- |
| **30A** | Planning / docs only | Post-polish interaction triage + next frontend direction planning (**this phase**). Review Phase 29C, triage the two known limitations, and lock the Phase 30B contract. |
| **30B** | Frontend implementation | Interaction Recovery + Responsive Rail Frontend Implementation Pass. Restore predictable Escape after dock close; improve focus return without trapping; add the narrow-viewport focused-rail responsive rule. Narrow, interaction-specific; `KnowledgeGraphPanel.tsx` / `styles.css` (+ `App.tsx` only if wiring requires). No screenshots. |
| **30C** | QA / evidence / docs only | Interaction Recovery QA + Screenshot Evidence Refresh. Re-run the connected runtime after 30B, re-verify the Escape-after-dock-close stack and the narrow-viewport focused rail (and confirm no regression across the Phase 29C interaction set), and refresh the screenshot evidence trail. Docs/screenshots/evidence only. |

30C runs **only after** 30B and is evidence-only — no implementation, no fixes.

---

## 6. Design Rationale

Brief "why" for each major planning decision:

- **Why focus recovery matters.** The Phase 29A contract sells a predictable
  Escape *stack*: press once, peel one surface; keep pressing, reach a bare
  graph. A dead Escape after dock close quietly breaks that promise for the
  exact audience (keyboard users) the contract is meant to serve. Restoring
  it is a correctness fix, not cosmetic polish — the interaction either keeps
  its word or it doesn't.

- **Why responsive rail behavior matters.** The graph-primary contract
  requires the utility rail to stay compact, reachable, and *legible* on
  narrow viewports. A label clipped at the screen edge is the kind of
  unfinished detail a reviewer notices first on a phone-width capture. The
  at-rest icon-only rail is already right; only the focused/expanded narrow
  state needs a rule, so the fix is small and low-risk.

- **Why Phase 30B should stay narrow.** Phase 29C verified the entire
  interaction/overlay contract at 28/28 with only two rough edges. Reopening
  passing surfaces to "improve" them risks regressing a locked contract for
  no user benefit — the classic CSS-wander failure mode Phase 29A warned
  against. Fixing exactly the two documented defects, and nothing else, keeps
  the change reviewable and the risk contained.

- **Why screenshots/evidence should wait for Phase 30C.** Capturing evidence
  in the same pass as the fix conflates "changed the code" with "verified the
  behavior," and tempts mid-capture tweaks. Keeping 30B implementation-only
  and 30C evidence-only preserves the honest, repeatable
  implement → verify → record cadence the project has used since the 27/28/29
  arcs, and matches this codebase's plan → build → QA discipline.

- **Why the graph-primary contract must remain locked.** The graph *is* the
  application surface; that direction has been re-derived, corrected, and
  re-locked repeatedly (27A–27E, 28A–28D, 29A–29C). Every interaction fix
  from here must stay subordinate to it. Any drift back toward a
  sidebar / dashboard / card-grid / SaaS shell — even accidentally, under
  "responsive rail" or "focus" cover — would undo the most expensive,
  most-revisited decision in the project. It stays locked.

---

## 7. Guardrail Lock

- **Phase 30A is planning only.** This document adds planning/docs
  (`docs/phase-30a-post-polish-interaction-triage.md`, plus minimal
  `docs/roadmap.md` and, if needed, `README.md` status updates) and changes
  **no** frontend, CSS, backend, API, schema, package, dependency, runtime,
  or screenshot state.
- **Phase 30B must be narrow and interaction-specific** — the two documented
  limitations only (Escape/focus recovery after dock close; focused-rail
  label overflow at narrow widths), inside `KnowledgeGraphPanel.tsx` and
  `styles.css` (and `App.tsx` only if the focus/Escape wiring requires it),
  with the Section 4 forbidden list enforced.
- **No implementation happens until Phase 30B.** No fix is smuggled into this
  planning phase. No CSS, no focus wiring, no rail change occurs here.
- **No visual direction may drift back toward dashboard / sidebar /
  card-grid / SaaS-shell layouts.** The graph-primary surface direction
  (28A §1, §6.6 rejection lists; 28D lock) remains in force: the graph is the
  full application surface, menus and panels remain contextual overlays,
  visual energy stays graph-owned (nodes, edges, aura, pulse, selection,
  grouping, active graph states), the shell stays dark black/chrome/metal/
  dev-tool serious, and non-graph color stays minimal.

---

## 8. Statement of Scope

This phase produced planning and documentation only. No application code,
style, configuration, dependency, API, schema, data, or screenshot behavior
was changed. The two Phase 29C limitations are triaged here and scheduled for
implementation in Phase 30B and verification in Phase 30C — not before.
