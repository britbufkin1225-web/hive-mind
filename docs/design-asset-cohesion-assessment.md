# Design-Asset Cohesion Assessment

**Status:** Bounded assessment (Phase 40A). **No binary assets are changed by this
phase.** This document inventories project-facing design assets, screenshots,
diagrams, README imagery, terminology, and visual-identity references, and
classifies each against Hive|Mind's current state (post-Phase 39D) and its next
direction (the planned Create Layer). It records findings and recommendations
only; replacing images, capturing new screenshots, and any branding work are
explicitly out of scope here and deferred.

**Authored under:** Phase 40A — Create Layer Foundation Planning + Project
Cohesion.

---

## 1. Scope and method

Inspected, at the repository level:

- Branding binary assets under `docs/assets/`.
- README imagery references in `README.md`.
- The screenshot corpus under `docs/demo/screenshots/`.
- Text-based / Mermaid diagrams and the "How It Works" pipelines in `README.md`
  and the roadmap.
- Terminology and visual-identity language across README, roadmap, and the Active
  Memory / Repository Observer references.

Classification vocabulary used per asset:

- **Match** — still accurately represents current functionality.
- **Obsolete** — represents a superseded project state; misleading if presented as
  current.
- **Relabel** — should remain but be captioned/dated so its state is clear.
- **Replace (deferred)** — should eventually be re-captured/redrawn; not in this
  phase.

## 2. Branding assets

| Asset | Classification | Notes |
| --- | --- | --- |
| `docs/assets/branding/hivemind-readme-banner.png` (~1.1 MB) | Match / monitor | The single branding binary. The `Hive\|Mind` wordmark and hive/graph motif remain consistent with the product identity. It does not depict any specific obsolete UI state, so it stays valid. Recommendation: keep as-is; revisit only if a deliberate branding-expansion phase is reopened (currently deferred). |

There is exactly one branding binary in the repository; there is no sprawling,
inconsistent asset set to reconcile. This is healthy.

## 3. README imagery (screenshots referenced inline)

The README references three real connected-runtime captures, all from the
graph-primary surface era:

| Referenced image | Classification | Notes |
| --- | --- | --- |
| `docs/demo/screenshots/phase-28c-default-graph-primary-surface.png` | Match | Accurately shows the graph-primary workspace, which remains the current shell. |
| `docs/demo/screenshots/phase-28c-selected-node-inspector.png` | Match | Selected-node inspector behavior is current. |
| `docs/demo/screenshots/phase-28c-intelligence-overlay.png` | Match | Intelligence overlay is current; caption already avoids over-claiming an Active Memory UI. |

The README's captions are careful and honest (they explicitly note these are real
captures, not mockups, and that the Spatial Hive set does not claim live gesture
tuning). No inline README image misrepresents current functionality.

**Gap (not a defect):** none of the referenced imagery depicts the newer
read-only inspector surfaces (Active Memory context-packet inspector, Repository
Observer snapshot/drift inspector). These are real, implemented surfaces with no
screenshot representation in the README. Capturing them is **deferred** (screenshot
work is out of scope for the current priority), but it is the highest-value future
visual addition.

## 4. Screenshot corpus (`docs/demo/screenshots/`)

72 PNG files spanning phases **20d → 33e**. Character of the corpus:

- **Backend/API captures (phase 20d):** `Match (historical)` — still valid as API
  evidence; recommend **relabel** as historical backend evidence so they are not
  read as current UI.
- **Connected-UI captures (21c, 21f, 22c, 23b, 25c, 26c, 27e):** these track the
  UI's evolution from dashboard-with-panels toward the graph-first shell. Earlier
  sets (21c–25c) show **obsolete** pre-graph-primary layouts; they are legitimate
  QA history but should not be presented as the current UI. Recommendation:
  **relabel** as phase-dated QA history (they already live under phase-named QA
  evidence docs, which mitigates this).
- **Graph-primary captures (28c, 29c, 30c):** `Match` — represent the current
  graph-first surface.
- **Spatial Hive captures (33e):** `Match / experimental` — accurately depict the
  implemented 2.5D presentation; correctly *not* presented as live gesture tuning.

The corpus is organized by phase-named QA/evidence documents, which already frames
most captures as point-in-time evidence rather than current-state claims. The main
cohesion risk is any future doc that pulls an early (21c–25c) capture forward as if
it were the current UI. No current doc does this.

## 5. Diagrams and pipelines

| Diagram / pipeline | Location | Classification | Notes |
| --- | --- | --- | --- |
| "Current product pipeline" (text) | `README.md` | Match | Source → import → normalization → store → graph → intelligence → inspection is accurate. |
| "Active Memory and Verification pipeline under development" (text) | `README.md` | Match | Accurately marked as under development; steps reflect implemented + planned split. |
| Repository Observer dependency flow (text) | Active Memory reference §21 | Match | Router → snapshot service → Git adapter → read-only subprocess is current. |
| Create Layer data-flow (Mermaid) | `docs/create-layer-architecture.md` §13 | Match (new, planned) | New in Phase 40A; explicitly shows human-gated, no-autonomous-mutation flow. |

The text-based pipelines are honest about implemented-versus-planned. The new
Create Layer Mermaid diagram is the first diagram to depict the creation
direction and is labeled planned.

## 6. Terminology and visual language

- **Wordmark:** `Hive|Mind` is used consistently. **Match.**
- **Parent label:** `devdevbuilds` is consistently the human decision-maker /
  merge gate across README, roadmap, and now the Create Layer docs. **Match.**
- **Core metaphors:** graph / hive / evidence / provenance / verification are
  consistent and now extended cleanly by *grounded creation* and *agent
  coordination* language. **Match.**
- **Does the visual language reflect intelligence, provenance, creation, and agent
  coordination?** Intelligence, provenance, and verification are well represented
  in text and diagrams. **Creation** and **agent coordination** were previously
  under-represented visually; Phase 40A adds the first creation-direction diagram
  and the Create Layer track, closing part of that gap in text. A dedicated
  creation/coordination *visual* remains **deferred**.
- **Stale framing repaired in Phase 40A:** the README previously framed the
  project partly as a passive demo / portfolio experiment and carried a stale
  roadmap section pinned at Phase 38A. Phase 40A reconciles this to lead with
  real-development-tool framing and the current post-39D state (see the README
  "Project Framing" and "Roadmap" sections).

## 7. README-vs-functionality consistency

README presentation is consistent with current functionality after the Phase 40A
reconciliation:

- Implemented surfaces (graph, intelligence report, Active Memory inspector,
  Repository Observer inspector, drift) are described as implemented.
- The Create Layer is described as **planned**, in a clearly labeled section, and
  never claimed as existing functionality.
- The current-implementation-status table remains the authoritative
  implemented-versus-planned ledger and is not contradicted by the new framing.

## 8. Findings summary

- **Match / healthy:** single consistent branding banner; honest, careful inline
  README imagery; consistent wordmark, parent label, and core metaphors; accurate
  text pipelines; new labeled Create Layer diagram.
- **Relabel (low effort, future):** early backend (20d) and pre-graph-primary UI
  (21c–25c) captures should always be presented as phase-dated history — already
  largely handled by their QA/evidence docs.
- **Replace / add (deferred):** no screenshots yet exist for the Active Memory and
  Repository Observer read-only inspectors, and no visual yet depicts the Create
  Layer / agent-coordination direction. These are the highest-value future visual
  additions but are **out of scope now** (screenshot, branding, and animation work
  are deferred under the current priority).
- **Obsolete-if-misused:** early UI captures are only a risk if a future doc
  presents them as the current UI; no current doc does.

## 9. Boundary

This assessment changed **no binary assets, screenshots, or branding files**, and
recommends none for Phase 40A. All replacement/recapture/branding work is deferred
to an explicitly reopened visual phase. Phase 36K materials were not inspected for
change and remain paused and untouched.

## 10. Reference documents

- [Create Layer architecture](create-layer-architecture.md)
- [Phase 40A planning](planning/phase-40a-create-layer-foundation-project-cohesion.md)
- [Roadmap](roadmap.md)
- [README](../README.md)
- [Phase 28C graph-primary evidence](demo/phase-28c-true-graph-primary-surface-qa-screenshot-evidence.md)
- [Phase 33E Spatial Hive evidence](demo/phase-33e-2-5d-spatial-hive-qa-screenshot-evidence.md)
- [Frontend asset contract](frontend-asset-contract.md)
