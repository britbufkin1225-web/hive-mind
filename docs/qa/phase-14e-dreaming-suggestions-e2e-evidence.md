# Phase 14E Dreaming Suggestions E2E Evidence

Date: 2026-06-26
Parent label: devdevbuilds
Local branch checked: `phase-11c-repo-cohesion-demo-docs`

## Purpose

Phase 14E is intended to be the QA, documentation, and demo-evidence lock pass
for the Phase 14C -> 14D Dreaming Suggestions flow. The requested target state
is a completed end-to-end flow where backend-derived Dreaming Suggestions are
visible in the frontend Intelligence Report while remaining read-only,
deterministic, non-mutating, and free of AI/LLM integration.

## QA Result

This checkout cannot honestly be locked as the completed Phase 14C -> 14D
Dreaming Suggestions flow.

The local repository history and implementation are still at the Phase 11C
fixture-backed Intelligence Report state:

- Current branch: `phase-11c-repo-cohesion-demo-docs`.
- Available branches: `main`, Phase 1/2 branches, `phase-11b-*`, and
  `phase-11c-*`; no local or remote Phase 14 branch was present.
- `apps/backend/app/services/intelligence.py` still builds the report from
  deterministic demo fixtures in `intelligence_fixtures.py`.
- `README.md`, `docs/roadmap.md`, `docs/demo-guide.md`,
  `docs/screenshot-checklist.md`, and `docs/intelligence-surface-plan.md`
  all describe the Intelligence Report as fixture-backed demo content.

This evidence pass therefore records validation of the current checkout and the
gap to the requested Phase 14E target. It does not claim backend-derived Phase
14 Dreaming behavior that is not present in this workspace.

## What Was Verified

- Documentation mentions of Dreaming Suggestions, Intelligence Report,
  intelligence fixtures, demo readiness, and planned intelligence features.
- Backend Intelligence Report source of truth.
- Frontend Intelligence Report visibility and read-only presentation path.
- Validation scripts declared in `package.json`.
- Guardrails against mutation, persistence changes, new endpoints, new
  dependencies in the repo, and AI/LLM integration.

## Backend Source Of Truth

Current checkout source of truth:

- `apps/backend/app/services/intelligence.py`
- `apps/backend/app/services/intelligence_fixtures.py`
- `apps/backend/app/models/hive_models.py`
- `apps/backend/tests/test_intelligence_report.py`
- `apps/backend/tests/test_intelligence_contracts.py`

Observed behavior in this checkout:

- `GET /api/intelligence/report` is read-only.
- The report is populated with deterministic demo/seed fixtures.
- Fixture entries are tagged with `metadata.fixture == true`.
- The report builder does not mutate store state.
- The report builder does not run real Dreaming heuristics.
- The report builder does not perform temporal decay calculation, provenance
  inference, query persistence, or AI/LLM calls.

## Frontend Visibility

Current checkout frontend surface:

- `apps/frontend/src/components/IntelligenceReportPanel.tsx`
- `apps/frontend/src/types/api.ts`

Observed behavior in this checkout:

- The Intelligence Report panel renders the backend report sections.
- The Dreaming Suggestions section is visible as part of the report.
- Suggestions are rendered as advisory rows/cards.
- The panel has no apply/mutate workflow.
- The UI remains read-only and demo-oriented in the current docs.

## Requested Phase 14 Suggestion Types

The requested Phase 14C/14D target says these backend-derived suggestion types
should be supported:

- `duplicate_signal`
- `stale_knowledge_link`
- `orphaned_node`

Evidence in this checkout:

- These exact Phase 14 type names are not present in the local codebase.
- The current contract enum uses older names such as `duplicate`, `stale`, and
  `orphan`.
- The current populated Dreaming fixtures include `duplicate` and
  `related_nodes`, not the requested Phase 14 backend-derived set.

Result: Phase 14 supported-type coverage is not demonstrable from this checkout.

## Deferred And Blocked Types

Requested Phase 14 target status:

- `source_coverage_gap` remains deferred due to the pinned Phase 14B
  contract/schema decision.
- `unresolved_query_pattern` remains blocked until query history is persisted.

Evidence in this checkout:

- `source_coverage_gap` is not implemented.
- Query trail entries are fixture-backed; query history persistence does not
  exist.
- No implementation of an unresolved-query-derived Dreaming suggestion was
  found.

Result: the requested deferred/blocked status is consistent with the current
checkout's lack of source coverage and query-history derivation, but the Phase
14 naming/contracts are not present locally.

## Read-Only And Non-Mutating Behavior

Validated guardrails in the current checkout:

- No graph/source mutation is performed by the Intelligence Report builder.
- No persistence changes are made by report generation.
- No new endpoints were added in this pass.
- No backend Dreaming logic was added in this pass.
- No frontend features were added in this pass.
- No API contracts were changed in this pass.
- No AI/LLM integration exists or was added.
- No repo dependency files were changed.

Backend tests include `test_intelligence_report_does_not_mutate_store`, which
passed during validation.

## Validation Commands And Results

Frontend:

```powershell
npm run check:frontend
```

Initial sandboxed result: failed before app build due to Vite/esbuild access
denial while loading `apps/frontend/vite.config.ts`.

Approved rerun outside the sandbox:

```powershell
npm run check:frontend
```

Result: passed. Vite built 36 modules and produced `dist/` assets.

Backend:

```powershell
npm run check:backend
```

Initial result: failed before tests because `python` was not on PATH in this
session.

Bundled Python dependency preparation:

```powershell
& 'C:\Users\britb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install -r apps/backend/requirements-dev.txt
```

Result: passed; installed the repo's existing backend dev requirements into the
bundled runtime. No repo dependency files were changed.

Backend test command with writable pytest temp directory:

```powershell
$env:TMP='C:\Users\britb\OneDrive\Documents\hive mind\.pytest-tmp'
$env:TEMP='C:\Users\britb\OneDrive\Documents\hive mind\.pytest-tmp'
& 'C:\Users\britb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest apps/backend --basetemp 'C:\Users\britb\OneDrive\Documents\hive mind\.pytest-tmp\basetemp'
```

Result: passed.

Summary:

- `169 passed`
- `1 warning`
- Runtime: `2.31s`

Warning:

- `StarletteDeprecationWarning` from `fastapi.testclient` importing
  `starlette.testclient`; not related to Dreaming Suggestions behavior.

## Demo Evidence Notes

Current checkout is demo-ready only for the Phase 11 fixture-backed Intelligence
Report story. It should not be demoed as a completed Phase 14C -> 14D
backend-derived Dreaming Suggestions flow.

Safe demo wording for this checkout:

> The current Intelligence Report is read-only and fixture-backed. It shows the
> planned intelligence surface, but real backend-derived Phase 14 Dreaming
> Suggestions are not present in this local checkout.

Do not claim in demos from this checkout:

- Backend-derived `duplicate_signal`, `stale_knowledge_link`, or
  `orphaned_node` suggestions.
- Implemented `source_coverage_gap`.
- Implemented `unresolved_query_pattern`.
- Query-history persistence.
- AI/LLM reasoning.
- Automatic graph/source mutation.

## Screenshot Readiness

No new screenshots were found or created during this pass.

Screenshot checklist for a later Phase 14-ready checkout:

- Intelligence Report panel visible in the frontend.
- Dreaming Suggestions section visible.
- At least one backend-derived `duplicate_signal` suggestion visible.
- At least one backend-derived `stale_knowledge_link` suggestion visible.
- At least one backend-derived `orphaned_node` suggestion visible.
- Read-only/non-mutating language or affordance visible.
- No apply/mutate action shown.
- API response or test evidence showing suggestions are backend-derived.
- Captions explicitly note `source_coverage_gap` as deferred and
  `unresolved_query_pattern` as blocked.

## Phase 14E Conclusion

Validation commands can pass in this environment after using the bundled Python
runtime and a workspace-local pytest temp directory. The current checkout's
Intelligence Report remains stable, read-only, deterministic, and non-mutating.

However, the requested Phase 14C -> 14D Dreaming Suggestions implementation is
not present in this local repository state, so Phase 14E cannot honestly be
marked complete for backend-derived Dreaming Suggestions here. A true Phase 14E
lock pass should be rerun on the branch or commit that contains the Phase 14C
and Phase 14D implementation.
