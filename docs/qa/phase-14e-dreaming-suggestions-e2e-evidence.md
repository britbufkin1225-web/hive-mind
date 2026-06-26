# Phase 14E - Dreaming Suggestions E2E Evidence

## Purpose

Phase 14E is a QA, documentation, and demo-evidence lock pass for the completed
Phase 14C -> Phase 14D Dreaming Suggestions flow. It does not add product logic.
It records that Dreaming Suggestions are now backend-derived, deterministic,
read-only, non-mutating, and visible in the Intelligence Report panel.

## Confirmed repo state

- Repo path: `C:\Users\britb\codex-hivemind-fresh\hive-mind`
- Branch: `phase-14e-dreaming-qa-evidence-v2`
- Base branch refreshed from GitHub `origin/main` before Phase 14E work.
- Phase 14C confirmed: `ce2df8f Add backend-derived Dreaming suggestions MVP (#44)`
- Phase 14D confirmed locally: `de2ab9c Polish Dreaming Suggestions frontend visibility (#45)`

## Phase 14C backend derivation

Phase 14C moved Dreaming Suggestions out of fixture-only demo content for the
supported MVP types. The backend derives suggestions from current store
nodes/edges using deterministic service logic and returns them through the
read-only intelligence report path.

Backend source-of-truth areas verified during orientation:

- `apps/backend/app/services/dreaming.py` derives Dreaming Suggestions as a pure,
  read-only projection over already-persisted store state.
- `apps/backend/app/services/intelligence.py` assembles Dreaming Suggestions into
  `GET /api/intelligence/report` without mutating store state.
- `apps/backend/app/models/hive_models.py` keeps `DreamingSuggestion`,
  `DreamingSuggestionType`, and `confidence_hint` in the read-only intelligence
  contract model.
- `apps/backend/tests/test_dreaming.py` covers derivation, evidence, ordering,
  supported types, and the non-mutating guarantee.
- `apps/backend/tests/test_intelligence_report.py` covers report integration for
  backend-derived Dreaming Suggestions.

## Phase 14D frontend visibility

Phase 14D made backend-derived Dreaming Suggestions visible and readable in the
existing Intelligence Report panel. The frontend does not need to hard-code raw
wire enum strings in the component for this to be valid; it renders through the
shared `DreamingSuggestion` fields, label helpers, backend-provided reason and
rationale fields, evidence metadata, origin/derived markers, and confidence
hints.

Frontend visibility areas verified during orientation:

- `apps/frontend/src/components/IntelligenceReportPanel.tsx` imports and renders
  `DreamingSuggestion` rows.
- The panel surfaces `confidence_hint` and read-only/backend-derived language.
- The panel renders backend-provided title/summary/evidence-style fields without
  adding mutation actions.
- `apps/frontend/src/styles.css` includes Phase 14D styling for Dreaming
  Suggestions visibility.
- `git show --stat de2ab9c` shows Phase 14D touched the Intelligence Report
  component and frontend styles only.

## Repo-wide verification notes

Repo-wide verification confirmed the supported backend-derived suggestion types
exist in backend Dreaming tests:

- `duplicate_signal`
- `stale_knowledge_link`
- `orphaned_node`

Repo-wide verification also confirmed Dreaming Suggestion visibility and contract
language across backend contracts/models/services/tests, frontend types and the
Intelligence Report panel, README, and docs:

- `confidence_hint`
- `DreamingSuggestion`
- `Dreaming Suggestions`
- `backend-derived`
- `read-only`
- non-mutating/no-mutation language

The frontend component uses generic typed suggestion rendering and label helpers,
so the absence of raw backend enum strings inside
`apps/frontend/src/components/IntelligenceReportPanel.tsx` is not a Phase 14D
failure.

## Supported suggestion types

Phase 14C/14D supports these backend-derived Dreaming Suggestions:

| Wire type | Meaning | Phase 14E status |
| --- | --- | --- |
| `duplicate_signal` | Similar or duplicate knowledge nodes based on normalized labels. | Supported and backend-derived. |
| `stale_knowledge_link` | Stale links where linked knowledge changed after the edge was created. | Supported and backend-derived. |
| `orphaned_node` | Nodes with weak or missing graph/source relationships. | Supported and backend-derived. |

## Deferred and blocked types

- `source_coverage_gap` remains deferred because the pinned Phase 14B
  contract/schema state does not include that wire value.
- `unresolved_query_pattern` remains blocked until query history persistence
  exists.

These are explicit future-work boundaries, not Phase 14E failures.

## Read-only and non-mutating behavior

Dreaming Suggestions are advisory. They are generated from existing store data
and displayed for review only.

Phase 14E preserves these guarantees:

- No suggestion is automatically applied.
- No graph, source, or store record is mutated.
- No endpoint changes were made.
- No persistence behavior was added or changed.
- No AI/LLM integration exists in this flow.

## Validation results

Recorded validation for the Phase 14C -> Phase 14D flow:

- Backend tests passed: `169 passed, 1 warning`.
- Frontend build/check passed after an approved run outside the sandbox
  limitation.
- Sandbox/runtime limitations are environment notes only and are not app
  failures.

## Screenshot and demo readiness notes

Phase 14E does not invent or add screenshots. The evidence lock records that the
existing Intelligence Report panel is demo-ready for the completed Dreaming
Suggestions MVP because it can show backend-derived, read-only suggestions with
confidence and evidence context when the backend emits them.

Demo language should say:

- Dreaming Suggestions are backend-derived and deterministic for the supported
  MVP types.
- Dreaming Suggestions are read-only and non-mutating.
- No AI/LLM calls run.
- Source coverage gaps and unresolved query patterns remain future work for the
  reasons documented above.

## Guardrails preserved

Phase 14E is documentation/QA evidence only. This pass intentionally does not
change:

- Backend logic.
- Frontend features.
- API contracts.
- Endpoints.
- Persistence.
- Dependencies.
- `.gitignore`.
- AI/LLM integration.
- Graph/source mutation behavior.
- Dashboard layout or visual system.
