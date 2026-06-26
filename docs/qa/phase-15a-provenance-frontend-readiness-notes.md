# Phase 15A — Provenance Chains Frontend Readiness Notes

**Phase:** 15A (parallel, review-only)
**Date:** 2026-06-26
**Author:** Review pass (no implementation)
**Status:** Documentation only — no frontend or backend changes

---

## 1. Current State

Provenance Chains are rendered inside `IntelligenceReportPanel.tsx` using fixture-backed data.
The section is live in the UI and is clearly labelled with a **"Demo data"** badge
(via `isFixtureRecord()` on `metadata.fixture === true`) until backend derivation ships.

**Relevant files:**

| File | Lines | Role |
|---|---|---|
| `apps/frontend/src/components/IntelligenceReportPanel.tsx` | 367–387, 608–624 | Section + row component |
| `apps/frontend/src/types/api.ts` | 231–254, 277–293 | `ProvenanceChain`, `IntelligenceReport` types |
| `apps/frontend/src/api/client.ts` | ~100–101 | `/intelligence/report` GET call |
| `apps/frontend/src/styles.css` | ~1067–1244 | Shared `intel-row` / `intel-tag` styles |

---

## 2. What the Current UI Renders

`ProvenanceRow` (line 367) displays per chain:

- **Node ID** — `chain.node_id` in a `<code>` tag
- **Source type tag** — `chain.source_type` if present (e.g. `obsidian`, `pdf`, `github`)
- **Link summary** — `"{links.length} link(s) · {linked_node_ids.length} linked node(s)"`
- **Origin path** — `chain.origin_path` inline if non-null
- **Last imported** — `formatDate(chain.last_imported_at)` → locale string or `"—"`

The `ReportSection` wrapper handles:

- Count badge from `report.summary.provenance_chain_count`
- Empty state text: *"No provenance chains yet — these appear once sources are imported into the graph."*
- Demo badge when any chain has `metadata.fixture === true`

---

## 3. Labels / Copy That Will Need to Change

When Provenance Chains become backend-derived the following copy should be revisited:

| Current | Needed change | Location |
|---|---|---|
| Empty state: *"No provenance chains yet — these appear once sources are imported into the graph."* | Revise or split — the current text conflates "no data yet" with "feature not shipped". When backend-derived, an empty state means the graph genuinely has no traceable provenance, not that the feature is pending. | `IntelligenceReportPanel.tsx:612` |
| `SectionBadge kind="demo"` | Remove once real derivation ships. Ensure `isDerivedRecord()` path is wired to show a `kind="derived"` badge instead. | `IntelligenceReportPanel.tsx:614–616` |
| Report-level note (line ~519): *"Provenance and query-trail sections remain deterministic demo fixtures…"* | Remove the inline comment/note when provenance becomes real; Query Trails note can remain until that phase ships. | `IntelligenceReportPanel.tsx:~519` |
| `"Last imported:"` label | Keep as-is; `last_imported_at` is already in the type and meaningful. Confirm backend always populates it. | `ProvenanceRow` line 383 |
| Section description: *"A read-only audit trail tracing knowledge back to its origin."* | Copy is accurate — keep it. Explicitly mentions read-only, no change needed. | `IntelligenceReportPanel.tsx:609` |

---

## 4. Missing Display States to Add in Phase 15C/15D

The current `ProvenanceRow` has no handling for these states that backend derivation will expose:

### 4a. Unknown / Untracked State
`chain.source_id === null && chain.origin_path === null` → node exists but provenance is unresolved.
Currently renders silently with a `"—"` date and no origin, which is misleading.
**Recommended:** add a small `"origin unknown"` label or badge in this case.

### 4b. Backend-Down / Error State
The panel already has a top-level error state (`status === "error"`) but there is no per-section
degraded state. If the backend returns a partial report (e.g. provenance_chains is an empty array
due to a derivation error rather than genuinely empty data), the UI silently shows the empty state.
**Recommended:** consider a `metadata.error` or report-level error flag in the contract for Phase 15C.

### 4c. Large Chain / Many Links
`ProvenanceRow` renders all links as a flat count string. If a node has many derived edges (`derived_edge_ids`, `stored_edge_ids`), there is no truncation or expand behavior.
**Recommended:** cap display at e.g. 5 links with a `"+ N more"` affordance for Phase 15D polish.

### 4d. Source Type — Unknown Value
`chain.source_type` is typed as `RegistrySourceType | null`. If the backend emits an unrecognised
source type string the `<span className="intel-tag">` will render it raw. Not a breaking problem
but worth a `formatSourceType()` helper in 15D to normalise display.

### 4e. Derived vs Fixture Badge Distinction
`isDerivedRecord()` (`metadata.derived === true`) is already defined but **not used** in the
Provenance Chains section — only `isFixtureRecord()` is. When real derivation ships the section
should show a `kind="derived"` badge (matching how Dreaming Suggestions and Decay do it) rather
than no badge at all.
**Gap:** wire `isDerivedRecord()` into `ProvenanceRow` or the `ReportSection` badge slot.

---

## 5. Can the Current UI Support Backend-Derived Provenance Without a Redesign?

**Yes.** The panel structure is already sound:

- `IntelligenceReport.provenance_chains: ProvenanceChain[]` is already in the API type.
- `ProvenanceChain` type already carries `source_id`, `source_type`, `origin_path`, `links`,
  `linked_node_ids`, `derived_edge_ids`, `stored_edge_ids`, `last_imported_at`, and `metadata`.
- `ReportSection` / `ProvenanceRow` components can accept real data without structural change.
- Empty state, count badge, and fixture/derived badge slots are all present.

No redesign is needed. The Phase 15C/15D work is a polish pass only:
copy changes, badge wiring, unknown-state label, and optional large-chain truncation.

---

## 6. Type / Display Gaps Summary (for Phase 15C/15D)

| Gap | Severity | File | Action |
|---|---|---|---|
| No `isDerivedRecord` badge in Provenance section | Medium | `IntelligenceReportPanel.tsx:608–624` | Wire `isDerivedRecord()` to badge slot |
| Empty state copy conflates "no data" vs "feature pending" | Low | `IntelligenceReportPanel.tsx:612` | Split into two strings; switch on derivation flag |
| No `"origin unknown"` state when source_id + origin_path both null | Low | `ProvenanceRow` (line 367) | Add conditional label |
| No per-section error/degraded state | Low | `IntelligenceReportPanel.tsx` | Consider contract flag in Phase 15C |
| No truncation for large `links` / `derived_edge_ids` arrays | Low | `ProvenanceRow` | Add `"+ N more"` in Phase 15D |
| Raw `source_type` rendering without normalisation | Low | `ProvenanceRow:374–376` | Add `formatSourceType()` helper |
| Inline fixture comment mixes provenance + query trail note | Informational | `IntelligenceReportPanel.tsx:~519` | Split comment when provenance ships |

---

## 7. Guardrails Confirmation

- No frontend files edited.
- No backend files edited.
- No API contract changes.
- No CSS or component additions.
- No new dependencies.
- No Query Trails implementation scope.
- Documentation-only output.

---

## 8. Next Steps (not in scope for Phase 15A)

- **Phase 15B** (backend): derive real `ProvenanceChain` records from source registry imports.
- **Phase 15C** (frontend): wire `isDerivedRecord` badge, update empty-state copy, add unknown-origin label.
- **Phase 15D** (polish): large-chain truncation, `formatSourceType()`, per-section error state.
