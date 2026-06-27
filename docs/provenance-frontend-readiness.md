# Phase 15D Readiness — Provenance Chains Frontend Visibility + Demo Polish

## Status

| Phase | Status | Scope |
|-------|--------|-------|
| 15B | Complete, merged | Contract/schema alignment for Provenance Chains |
| 15C | In progress (Codex) | Backend-derived, deterministic, read-only Provenance Chain generation |
| 15D | Planned | Frontend display of backend-derived Provenance Chains |

This document scopes the Phase 15D UI pass. It is a planning artifact only. No code is modified here.

---

## What Phase 15D Should Accomplish

Make backend-derived Provenance Chains clear, scannable, and demo-honest in the Intelligence Report panel after Phase 15C lands. No new logic, no new endpoints, no graph mutation.

---

## UI Goals

- Label Provenance Chains explicitly as backend-derived and read-only at the panel level — not per-row, not per-card.
- Make source-to-node and node-to-node relationships scannable without requiring a user to expand anything.
- Surface evidence/reason metadata at the card level, not hidden behind tooltips by default.
- Distinguish complete, partial, and unknown provenance states with visible but non-alarming UI treatment.
- Maintain honest demo language throughout — no implication of AI reasoning or autonomous graph editing.
- Avoid color as the only signal for any state (completeness, status, confidence).

---

## Recommended Display Model

Each provenance entry should render as a card or row with the following fields:

### Required Fields (render empty state if absent)

| Field | Source in Contract | Display Label |
|---|---|---|
| Chain title | `chain.title` or derived | "Provenance Chain" |
| Chain summary | `chain.summary` | Displayed as body text below title |
| Source label | `chain.source.label` | "Source:" |
| Node labels | `chain.nodes[].label` | Inline pill list or bulleted |
| Relationship type | `chain.relationship_type` | "Relationship:" |
| Evidence / reason | `chain.evidence` or `chain.reason` | "Evidence:" |

### Optional Fields (render only if present)

| Field | Source in Contract | Display Label |
|---|---|---|
| Confidence | `chain.confidence` | "Confidence:" — render as text, not gauge |
| Completeness | `chain.completeness` | "Completeness:" — text badge only |
| Status | `chain.status` | Status badge: Complete / Partial / Unknown |
| Timestamp | `chain.timestamp` | "Derived:" in muted text below card |

### Empty/Unknown Field State

When a field is present in the contract but returns null, empty string, or is omitted from the backend response:

- Do not hide the row. Render the label with a placeholder.
- Placeholder text: `—` (em dash) for scalar fields; `No nodes recorded` for node lists.
- Never render "null" or "undefined" to the user.

---

## Empty States

Define these explicitly before Phase 15D implementation begins:

| State | UI Copy |
|---|---|
| No provenance chains available | "No provenance chains available for this record." |
| Backend unavailable | "Provenance data is currently unavailable. The backend service may be offline." |
| Partial provenance only | "Partial provenance only. Some source or node metadata is missing from this chain." |
| Unknown source metadata | "Source metadata is not recorded for this chain." |
| Contract-valid but sparse response | "Provenance chain recorded. Detailed metadata is not available for this entry." |

All empty states should render in the panel body, not as a modal or overlay. Use a non-error visual treatment (muted text, not red/warning).

---

## Accessibility and Readability Requirements

- **Keyboard navigation:** All provenance cards must be reachable via Tab. Expand/collapse actions (if used) must be keyboard-triggerable.
- **Semantic headings:** The panel should use an `h2` or `h3` for "Provenance Chains" and not rely on visual size alone to communicate hierarchy.
- **Badge text:** All status/completeness/confidence badges must have visible text labels. Do not use icon-only badges.
- **Mobile layout:** Cards should stack vertically. Node pill lists should wrap. Labels should not truncate at < 375px viewport width.
- **Color independence:** Complete/Partial/Unknown states must use text labels in addition to any color treatment. Do not distinguish these states by color alone.
- **Stable row labels:** Card labels must not change position or content based on which fields are populated. Consistent field order across all cards.

---

## Guardrails for Phase 15D Implementation

The following are out of scope for Phase 15D:

- No backend changes
- No API contract changes
- No new endpoints
- No graph mutation controls in this panel
- No source mutation controls in this panel
- No Query Trails implementation
- No AI/LLM wording anywhere in the UI
- No new frontend dependencies
- No dashboard layout redesign
- No branding or asset changes

If any of the above seem necessary to display a field correctly, raise it as a scoped sub-issue before touching code.

---

## Suggested Validation Checklist for Phase 15D

Run these checks before marking Phase 15D complete:

- [ ] Frontend build passes with no type errors
- [ ] Backend-up smoke check: provenance panel renders with real data
- [ ] Backend-down check: error state renders, no JS exceptions logged
- [ ] Empty provenance check: empty state copy renders correctly
- [ ] Partial metadata check: cards with missing optional fields render cleanly
- [ ] Mobile/responsive check: cards readable at 375px and 768px

---

## Demo Language Guide

### Use These Phrases

- "Backend-derived provenance chain"
- "Read-only evidence trail"
- "Derived from existing source and graph records"
- "No graph or source mutation occurs from this panel"
- "Source-to-node relationship as recorded by the backend"
- "Provenance data is generated server-side from existing records"

### Avoid These Phrases

- "AI-generated provenance"
- "LLM reasoning"
- "autonomous memory editing"
- "self-healing knowledge graph"
- "Claude generated this"
- "inferred by the model"
- "agent-derived"

The distinction matters for portfolio honesty and for avoiding user misunderstanding about what the system does. Provenance Chains in Phase 15C are deterministic backend records — label them as such.

---

## Notes

This document supersedes any informal Phase 15D planning notes from earlier sessions. Phase 15C (Codex) must land and be reviewed before Phase 15D frontend work begins.

Do not begin Phase 15D implementation until the Phase 15C backend API response shape is confirmed in a merged PR.
