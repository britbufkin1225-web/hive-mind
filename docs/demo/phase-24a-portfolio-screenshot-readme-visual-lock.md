# Phase 24A — Portfolio Screenshot Selection + README Visual Lock

Parent label: **devdevbuilds**

**Status: active (docs / README / demo presentation only).** Phase 24A selects the
strongest existing Phase 23B connected screenshots for the README/demo landing flow,
improves their presentation and captions, and records why these visuals represent the
project well. It is the presentation successor to the
[Phase 23B UI Surface Readability QA + Screenshot Evidence Refresh](phase-23b-ui-readability-qa-screenshot-evidence.md):
it **reuses that phase's real captured screenshots** and adds no new ones. Phase 24A
makes **no** UI, CSS, frontend, backend, API, schema, package, dependency, or runtime
behavior change, and **fabricates no screenshots**.

- **Phase name:** Phase 24A — Portfolio Screenshot Selection + README Visual Lock
- **Date:** 2026-06-28
- **Branch:** `phase-24a-portfolio-screenshot-readme-visual-lock`
- **Repo:** `hive-mind` (Hive&#124;Mind under devdevbuilds)

---

## Why this pass exists

Phase 23B produced a fresh, honest `phase-23b-connected-*` screenshot set after the
Phase 23A readability/panel-hierarchy polish. Before any further UI polish or
walkthrough writing, the project needs a **locked, deliberate** answer to one
question: *which visuals best represent Hive&#124;Mind on the README landing page?*

Dumping all six surfaces into the README would bury the story. Phase 24A picks the
three that, in order, prove the app is real, show the core product, and show the
differentiator — and documents the choice so future phases don't relitigate it.

All visuals are drawn **only** from the existing Phase 23B capture session; no new
runtime was started to produce images for this phase.

## Selected screenshots (README landing set)

These three were added to the README **Visual evidence** section, in this order:

| # | File | README role | Why chosen | What it proves about the connected app |
| --- | --- | --- | --- | --- |
| 1 | `phase-23b-connected-ui-top.png` | Hero / "it's real" | The cleanest single frame that shows the app *connected*: header band, green **Connected** pill, live API health, and the Vault summary metric grid, all above the fold. | The frontend and backend are actually wired together (live health `hivemind-backend` `0.1.0`), not a static page or mockup. |
| 2 | `phase-23b-connected-knowledge-graph.png` | Core product surface | The graph is the central, most visually distinctive product surface — summary band, full legend, and the deterministic SVG graph map with named nodes in one readable frame. | A read-only, deterministic graph (7 nodes / 6 edges, 7 connected / 0 isolated) is derived from sources and rendered with a custom SVG visualization — no physics, no mutation. |
| 3 | `phase-23b-connected-intelligence-report.png` | Differentiator | The Intelligence Report is what sets the project apart, and this frame shows the read-only summary band, `Mode Read-only`, the `BACKEND-DERIVED` badge, and an honest empty-state. | All four sections are deterministic, backend-derived, read-only signals — **no AI/LLM** — with honest empty-states (Dreaming `0`), which is what makes the layer auditable. |

The README also links the full-page capture and the remaining surfaces via
[`docs/demo/screenshots/`](screenshots/) and this note, so nothing is hidden — the
omitted images are one click away, just not on the landing page.

## Screenshots intentionally omitted from the README

| File | Why left out of the README landing page |
| --- | --- |
| `phase-23b-connected-sources.png` | The Source Registry is in its honest **connected empty state** ("No sources registered yet"). It's valid evidence, but a mostly-empty panel weakens a landing-page hero set. Kept in `screenshots/` and described in the Phase 23B evidence doc. |
| `phase-23b-connected-console.png` | Shows the tail of Query Trails flowing into the Console **baseline** ("Nothing has run yet"). Useful as part of the full evidence trail, but visually busy and low-signal as a standalone landing image. |
| `phase-23b-connected-ui-full.png` | The full end-to-end page capture (1280 × 9824) is excellent as a reference artifact but far too tall to embed inline without dominating the README. Linked from the **Visual evidence** section instead. |

No omitted screenshot was deleted; the entire Phase 23B set (and the prior
`phase-22c-*` / `phase-21f-*` / `phase-21c-*` / `phase-20d-*` history) is preserved.

## How the README presentation was improved

- Added a dedicated **Visual evidence** section high on the README (right after the
  Overview, before Current status) so a reviewer sees connected proof immediately.
- Used a deliberate three-beat narrative — *it's real → core product → differentiator*
  — instead of an unordered screenshot dump.
- Wrote captions and descriptive alt text that state what each frame demonstrates in
  honest, connected-runtime language (no marketing inflation, no "AI" claims).
- Linked the full-page capture, the remaining surfaces, and the Phase 23B capture
  session so the landing page stays clean while the full evidence remains reachable.

## Honesty / authenticity confirmation

- **No screenshots were fabricated.** Every image referenced is a pre-existing,
  real headless-browser capture from the Phase 23B connected session (frontend `5173`
  → backend `8787`). Phase 24A created **zero** new images.
- **No runtime, UI, CSS, frontend, or backend behavior changed.** This pass edited
  only Markdown: this note, the README **Visual evidence** section, the README status
  line / phase table / documentation links, and the roadmap status. No application
  code, config, contract, schema, package, or dependency was touched.
- **No app polish hid inside this docs pass.** No "one tiny layout tweak"; the visuals
  reflect the app exactly as Phase 23A shipped and Phase 23B captured it.

## Validation performed

- Re-read each selected screenshot file to confirm it exists, renders, and matches the
  caption written for it (connected dashboard top, Knowledge Graph, Intelligence
  Report).
- Verified all README image paths resolve to real files under
  `docs/demo/screenshots/` and that the new doc/cross-links are correct.
- Confirmed the changed Markdown files are readable and well-formed.
- No app runtime was started or modified for this phase.

## Confirmation

Phase 24A is a documentation/presentation pass. Its entire change set is Markdown:
this evidence note, the README **Visual evidence** section and status/table/link
updates, and the roadmap status update. **No UI / CSS / frontend / backend / API /
schema / package / dependency / runtime behavior changed, and no screenshots were
fabricated.**
