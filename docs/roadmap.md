# Hive|Mind Roadmap

This roadmap explains what Hive|Mind can do now, what is demo-only, and what
should remain future work. It complements the per-phase summary table in the
[README](../README.md), the [Intelligence Surface Plan](intelligence-surface-plan.md),
the portfolio-facing [Demo Guide](demo-guide.md), the canonical
[Final Demo Script](demo/final-demo-script.md) and
[Portfolio Presentation Lock](demo/portfolio-presentation-lock.md), and the
[Phase 12A Demo Freeze + Release Snapshot](releases/phase-12a-demo-freeze.md),
and the [Phase 14E Dreaming Suggestions E2E Evidence](qa/phase-14e-dreaming-suggestions-e2e-evidence.md), and the [Phase 15E Provenance Chains QA Evidence](qa/phase-15e-provenance-chains-qa-evidence.md), and the [Phase 17A Intelligence Report Cohesion + System Readiness Plan](intelligence-report-cohesion-readiness-plan.md),
and the [Phase 17B Intelligence Report Cohesion Hardening + Readiness QA](phase-17b-intelligence-cohesion-hardening.md),
and the [Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md),
and the [Phase 18C Backend API Security Regression QA + Evidence](security/phase-18c-backend-api-security-regression-qa.md),
and the [Phase 18D API Edge Case Hardening Planning / Deferred Security Scope Triage](security/phase-18d-api-edge-case-hardening-planning.md),
and the [Phase 18E API Edge Case Defensive Validation MVP](security/phase-18e-api-edge-case-defensive-validation.md),
and the [Phase 18F API Edge Case Security Regression QA + Evidence](security/phase-18f-api-edge-case-security-regression-qa.md),
and the [Phase 19A Security Cohesion + Release Readiness Planning](security/phase-19a-security-cohesion-release-readiness-planning.md),
and the [Phase 19B Release Readiness QA + Demo Evidence Pass](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md),
and the [Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](release-readiness/phase-20a-demo-release-candidate-planning.md),
and the [Phase 20B Final README + Portfolio Narrative Hardening](release-readiness/phase-20b-final-readme-portfolio-narrative-hardening.md).

## Current status

**Active phase:** Phase 21C - Connected UI screenshot + runtime evidence refresh
(capture / documentation only). Phase 21C re-runs the local backend
(`npm run dev:backend`, port `8787`) and frontend (`npm run dev:frontend`, port
`5173`) and captures the **connected** UI state after the Phase 21A/21B
runtime-config fixes — the "Connected" status pill, live API health, the rendered
Knowledge Graph (7 nodes / 6 edges), and the backend-derived Intelligence Report —
replacing Phase 20D's honestly-recorded `Failed to fetch` evidence while preserving
that earlier history. It changes no backend, frontend, CSS, source-code, package,
config, API, schema, dependency, or test behavior. See the
[Phase 21C Connected UI Screenshot + Runtime Evidence Refresh](demo/phase-21c-connected-ui-evidence.md).
The preceding **Phase 21A** added the dashboard shell foundation and **Phase 21B**
aligned the frontend API base-URL runtime config (root `envDir`, canonical backend
port `8787`), which together fixed the frontend/backend mismatch that Phase 20D had
documented. Before that, Phase 20D executed the Phase 20A screenshot/evidence plan
against **real, locally running app state**: it verified the backend runtime
directly through `/api/health`, `/api/sources`, `/api/graph`, and
`/api/intelligence/report`, and recorded the captured backend-runtime screenshots
and an evidence doc; its frontend browser state showed a `Failed to fetch` (a
run-configuration mismatch, since fixed), documented honestly as captured runtime
evidence. See the
[Phase 20D Final Demo Screenshot + Evidence Capture Pass](demo/phase-20d-demo-evidence.md).
The preceding Phase 20C packaged the existing project narrative into a canonical
[Final Demo Script](demo/final-demo-script.md) and locked the presentation spine via
a [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md) — the one-line
story, the data-flow surface order, and the honesty boundaries. The next recommended
phase is the **Final Portfolio Packaging / Public Presentation Pass**, drawing on the
locked scope and the captured evidence.

Phase 20A defined the **final demo release-candidate scope** for Hive|Mind before
any final polish, screenshot capture, README narrative hardening, UI tightening,
release tagging, or public-facing writeup. It states the current demo-ready story,
locks the clean portfolio narrative (a local-first, deterministic, read-only
knowledge intelligence dashboard with no AI/LLM), enumerates the demo candidate
surfaces with per-surface evidence and overstatement guards, defines a
portfolio-readiness checklist and a screenshot/evidence plan (no screenshots are
created there), lists the known limitations to disclose and the out-of-scope items,
and recommends a controlled next-phase sequence (20B–20E). It implements no code and
changes no behavior. See the
[Phase 20A Demo Release Candidate Planning + Final Portfolio Readiness Scope](release-readiness/phase-20a-demo-release-candidate-planning.md).

Phase 19B verified and recorded the current
state of Hive|Mind as a controlled, demo-ready, release-readiness *candidate*
without changing application behavior. It documents the readiness posture across
backend API stability, the security hardening sequence, the four Intelligence
Report surfaces, Obsidian import/read-only behavior, the read-only Knowledge
Graph visualization, demo clarity, and documentation cohesion; records the
completed security arc (18A–19A) and intelligence arc (Temporal Decay, Dreaming,
Provenance, Query Trails); and adds a **Demo Evidence Checklist** (what may be
shown honestly, what is backend-derived, what stays read-only/non-mutating, what
is deferred, and what must not be overclaimed) plus explicit **Release Readiness
Boundaries**. It implements no code and changes no behavior. See the
[Phase 19B Release Readiness QA + Demo Evidence Pass](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md).

Phase 19A consolidated the completed Phase 18A–18F security-hardening arc into a
single release-readiness view: it summarizes the arc, states the current security
posture without overclaiming, distinguishes **demo readiness** from **production
security readiness**, assesses the release-readiness categories (API defensive
validation, error safety, request-body edge cases, deferred items, documentation,
test evidence, demo expectations, architecture cohesion, and future
production-hardening boundaries), carries the deferred/blocked scope forward
unchanged, and adds a release-readiness checklist. It implements no code and
changes no behavior. See the
[Phase 19A Security Cohesion + Release Readiness Planning](security/phase-19a-security-cohesion-release-readiness-planning.md).

The preceding security arc: Phase 18A delivered the security threat model +
vulnerability test plan; Phase 18B implemented the §5.1 API defensive-validation /
error-safety cases; Phase 18C verified those behaviors, mapped coverage to the
threat model, and recorded the regression evidence; Phase 18D triaged the API edge
cases 18C deferred (deep nesting / recursion, query-parameter safety, value
normalization, route-level validation) into handled / deferred / not-applicable /
blocked buckets and defined a narrow scope for **Phase 18E — API Edge Case
Defensive Validation MVP**; Phase 18E then implemented the selected subset (bounded
request-body nesting-depth guard + explicit null-like / empty-value decisions) as
additive, per-model guards with 18 regression tests; and Phase 18F verifies that
18E behaves as documented — re-running the suite (18 targeted + 23 Phase 18B
regression + 267 full backend tests passing), mapping the coverage back to the
18A threat model and 18D triage, and confirming the intentionally-deferred scope.
Phase 18F implements no code and changes no behavior.

With Phase 16C merged, all four Intelligence Report surfaces (Temporal Decay,
Dreaming Suggestions, Provenance Chains, Query Trails) are backend-derived and
frontend-visible. Phase 17A was the cohesion/readiness *planning* pass and
Phase 17B was the readiness *hardening* pass that documented, without changing
behavior, the design rationale, explicit Temporal Decay thresholds, edge cases,
evidence expectations, performance considerations, and a future source-adapter
strategy. Phase 18A is the security-readiness pass: a documentation-only threat
model and vulnerability test plan that defines scope/authorization, the system
inventory, trust boundaries, the attack-surface matrix, planned test categories,
pass/fail criteria, and recommended future hardening phases — before any
owner-authorized, local-only defensive testing or hardening begins. It implements
no security fix and changes no behavior. See
[Phase 17B Intelligence Report Cohesion Hardening + Readiness QA](phase-17b-intelligence-cohesion-hardening.md)
and the
[Security Threat Model + Vulnerability Test Plan](security/threat-model-and-vulnerability-test-plan.md).

Phase 16A (planning) and Phase 16B (contract/schema alignment) prepared a stable
`QueryTrailEntry` shape. See
[Phase 16A Query Trails / Query Memory Foundation Planning](phase-16a-query-trails-foundation-planning.md)
and
[Phase 16B Query Trails Contract Types / Schema Alignment](phase-16b-query-trails-contract-schema.md).

Phase 16C made the Query Trails section **backend-derived** from existing
store structure (`app/services/query_trails.py`), replacing the demo fixture as
the report's primary source. Rationale: derivation is backend-owned (not
fixtures, not client capture) so the trail logic stays deterministic, reviewable,
and testable against the same store the rest of the report reads.

Only the categories existing data supports are derived — `source_followup`
(a source with linked nodes), `knowledge_gap` (an unsourced node or uncovered
source), and `related_query_cluster` (2+ nodes sharing a tag). The query-history-
dependent categories `repeated_query` and `unresolved_question` stay **blocked
and deferred** because Hive|Mind has **no persisted query history**; fabricating
query-memory records would be dishonest. Phase 16C adds no query persistence,
storage tables, query logging, browser/localStorage capture, new endpoints,
AI/LLM, dependencies, graph/source mutation, or frontend/dashboard changes — the
derived trails are a read-only projection of structural data, not query memory.

## Implemented foundation

- React/Vite frontend and FastAPI backend app shell.
- Local JSON-backed `HiveStore` and Pydantic API models.
- Safe Hive Console API and frontend panel.
- Source Registry backend, frontend panel, and inspector.
- Obsidian adapter/import pipeline and frontend import action surface.
- Knowledge Graph API and read-only Knowledge Graph panel.
- Deterministic SVG graph visualization with inspector sync and demo polish.
- Intelligence report contracts and `GET /api/intelligence/report`.
- Read-only Intelligence Report panel with every section backend-derived
  (Temporal Decay, Dreaming Suggestions, Provenance Chains, and Query Trails).

## Backend-derived intelligence surface

The Intelligence Report is a **fully backend-derived, read-only surface** as of
Phase 16C. As of Phase 13A the **Temporal Decay** section, as of Phase 14C the
**Dreaming Suggestions** section, as of Phase 15C the **Provenance Chains**
section, and as of Phase 16C the **Query Trails** section are derived
(read-only) from existing store/source state. No section is fixture-backed.

Backend-derived sections (read-only):

- Temporal decay statuses (Phase 13A — deterministic timestamp thresholds).
- Dreaming suggestions (Phase 14C — deterministic `duplicate`/`orphan`/`stale`
  rules over store nodes/edges; conservative, with an explainable
  `metadata.evidence` trail and a clean empty section when nothing is derivable).
- Provenance chains (Phase 15C — deterministic source/import/node/edge chains
  from existing store and source registry data, with backend-owned evidence and a
  clean empty section when no graph data exists).
- Query trails (Phase 16C — deterministic `source_followup` / `knowledge_gap` /
  `related_query_cluster` projections over store source/node/tag structure, with
  backend-owned evidence and a clean empty section when nothing is derivable).
  Query-history-dependent categories stay deferred.

Current non-capabilities:

- No `source_coverage_gap` derivation — deferred/blocked pending a future
  contract-expansion phase (Phase 14B contract decision).
- No `unresolved_query` derivation — blocked until query history is persisted.
- No `repeated_query` / `unresolved_question` Query Trail derivation — blocked
  until real persisted query history exists (Phase 16C defers these).
- No semantic provenance inference engine beyond existing source/node/import/edge
  records.
- No query persistence or query-memory logic.
- No AI/LLM calls.
- No automatic graph/source/store mutation.

## Phase history

| Phase | Status | Notes |
| --- | ---: | --- |
| 0 | Complete | Project initialization and planning foundation. |
| 1 | Complete | React/FastAPI foundation with health/status routes. |
| 2 | Complete | API contract and shared data model planning. |
| 3A-3D | Complete | Store, persistence, search helpers, and backend console. |
| 4A-4B | Complete | Frontend console panel and UX polish. |
| 5A-5C | Complete | Source Registry backend, frontend, inspector, and UX polish. |
| 6A-6E | Complete | Obsidian adapter/import pipeline and registry wiring. |
| 7A-7B | Complete | Frontend Obsidian import action panel and UX hardening. |
| 8A-8C | Complete | Knowledge Graph API, panel, and view-model prep. |
| 9A-9C | Complete | Read-only SVG graph visualization and QA polish. |
| 10A | Complete | Intelligence surface planning. |
| 10B | Complete | Intelligence contract types / read-only schemas. |
| 10C | Complete | Intelligence report endpoint foundation. |
| 10D | Complete | Intelligence Report frontend read-only panel. |
| 10E | Complete | Intelligence Report UX hardening / demo readiness. |
| 11A | Complete | Deterministic intelligence demo/seed fixtures. |
| 11B | Complete | Intelligence fixture UX review and screenshot readiness. |
| 11C | Complete | Repo cohesion, API/docs consistency, and demo documentation. |
| 12A | Complete | Demo freeze and release snapshot planning/status documentation. |
| 12B | Complete | Screenshot and demo script polish. |
| 13A | Complete | Temporal Decay section backend-derived from store timestamps (read-only MVP). |
| 13B | Complete | Intelligence Report frontend visibility for backend-derived Temporal Decay. |
| 13C | Complete | Temporal Decay end-to-end QA + demo evidence and status-language pass. |
| 14A | Complete | Dreaming Suggestion backend-derivation planning documentation. |
| 14B | Complete | Dreaming contract/schema alignment. |
| 14B.5 | Complete | Temporal Decay contract QA and edge-case hardening. |
| 14B.6 | Complete | Dreaming logic implementation readiness / defensive backend scope alignment. |
| 14C | Complete | Dreaming Suggestions backend-derived MVP for `duplicate_signal`, `orphaned_node`, and `stale_knowledge_link`. |
| 14D | Complete | Dreaming Suggestions frontend visibility and demo polish. |
| 14E | Complete | Dreaming Suggestions end-to-end QA and demo evidence pass. |
| 15A | Complete | Provenance Chains backend derivation planning and frontend readiness notes. |
| 15B | Complete | Provenance Chains contract types / schema alignment. |
| 15C | Complete | Provenance Chains backend-derived MVP for existing source/import/node/edge records. |
| 15D | Complete | Provenance Chains frontend visibility and demo polish. |
| 15E | Complete | Provenance Chains end-to-end QA and demo evidence pass. |
| 16A | Complete | Query Trails / Query Memory foundation planning before persistence or APIs. |
| 16B | Complete | Query Trails contract types / schema alignment (read-only contract before persistence/derivation). |
| 16C | Complete | Query Trails backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster`; `repeated_query` / `unresolved_question` deferred until query history is persisted. |
| 17A | Complete | Intelligence Report cohesion + system readiness planning (documentation only); aligns the four backend-derived surfaces and recommends a conservative, foundation-first next phase. |
| 17B | Complete | Intelligence Report cohesion hardening + readiness QA (documentation only); design rationale, explicit Temporal Decay thresholds, edge-case matrix, evidence expectations, performance/readiness notes, and future source-adapter strategy. |
| 18A | Complete | Security threat model + vulnerability test plan (documentation only); scope/authorization, system inventory, trust boundaries, attack-surface matrix, planned test categories, pass/fail criteria, and recommended future hardening phases (18B–18F). |
| 18B | Complete | Backend API defensive validation + error safety; global clean-JSON `500` handler (no traceback/path leak), malformed Obsidian vault-path normalization (→ `400`), and additive upper-bound length guards on client free-text fields (→ `422`), with regression coverage in `test_api_error_safety.py`. |
| 18C | Complete | Backend API security regression QA + evidence pass (QA/documentation only); verifies the Phase 18B §5.1/§5.3 behaviors, maps coverage to the threat model, and records test evidence (23 targeted + 249 full backend tests passing). |
| 18D | Complete | API edge case hardening planning / deferred security scope triage (planning/documentation only); triages the edge cases 18C deferred (deep nesting / uncontrolled recursion, query-parameter safety, value normalization, route-level validation) into handled / deferred / not-applicable / blocked buckets, risk-rates them against the local single-user runtime, and defines a narrow scope + readiness checklist for Phase 18E. Implements no code. |
| 18E | Complete | API edge case defensive validation MVP (backend implementation); implements the selected Phase 18D edges as additive, per-model guards with 18 regression tests and error-shape conformance: a bounded request-body nesting-depth guard (`MAX_REQUEST_NESTING_DEPTH = 32`) on the free-form body models (`HiveImportRequest`, `SourceRecordCreate`, `SourceRecordUpdate`) → clean `422` over-depth / at-limit still accepted, plus locked null-like / empty-whitespace value decisions. The route inventory found zero query-reading routes, so no query-param guard target and no justified global middleware — no middleware rewrite, no auth/rate-limit/persistence/dependency changes. |
| 18F | Complete | API edge case security regression QA + evidence pass (QA/documentation only); independently verifies the Phase 18E nesting-depth guard and value-handling decisions, maps coverage back to the Phase 18A threat model and Phase 18D triage, confirms the intentionally-deferred scope (no global middleware, no broad query-param validation, no auth/rate-limit/persistence/frontend expansion), and records test evidence (18 targeted + 23 Phase 18B regression + 267 full backend tests passing). Implements no code and changes no behavior. |
| 19A | Complete | Security cohesion + release readiness planning (planning/documentation only); consolidates the Phase 18A–18F arc into one release-readiness view, states the current security posture without overclaiming, distinguishes demo readiness from production security readiness, assesses the release-readiness categories, carries the deferred/blocked scope forward unchanged, and adds a release-readiness checklist plus rationale notes. Implements no code and changes no behavior. |
| 19B | Complete | Release readiness QA + demo evidence pass (QA/documentation/evidence only); verifies and records the current readiness posture across backend API stability, the security hardening sequence (18A–19A), the four backend-derived Intelligence Report surfaces, Obsidian import/read-only behavior, the read-only Knowledge Graph visualization, demo clarity, and documentation cohesion; adds a Demo Evidence Checklist and explicit Release Readiness Boundaries; frames Hive&#124;Mind as a controlled, local/dev, demo-ready release-readiness candidate (not production-ready/secure). Implements no code and changes no behavior. |
| 20A | Complete | Demo release candidate planning + final portfolio readiness scope (planning/documentation only); defines the final demo release-candidate scope before any polish/screenshots/release work — states the current demo-ready story, locks the deterministic, read-only, local-first portfolio narrative (no AI/LLM), enumerates the demo candidate surfaces with per-surface evidence and overstatement guards, defines a portfolio-readiness checklist and a screenshot/evidence plan (no screenshots created), lists known limitations to disclose and out-of-scope items, and recommends a controlled 20B–20E sequence. Implements no code and changes no behavior. |
| 20B | Complete | Final README + portfolio narrative hardening (documentation only); aligns the README and landing docs with the locked Phase 20A story — tool-first overview, locked one-line narrative, explicit implemented / intentionally-read-only / planned distinction, design-rationale notes, agent-assisted/human-reviewed workflow (devdevbuilds as merge gate), a guardrails/non-goals section, and the status advance to Phase 20B. Implements no code and changes no behavior. |
| 20C | Complete | Final demo script + portfolio presentation lock (documentation / demo only); packages the existing narrative into a canonical [Final Demo Script](demo/final-demo-script.md) and locks the presentation spine via a [Portfolio Presentation Lock](demo/portfolio-presentation-lock.md) — one-line story, data-flow surface order, and honesty boundaries — before any further UI work. UI work remains intentionally deferred until the presentation spine is locked. Implements no code and changes no behavior. |
| 20D | Complete | Final demo screenshot + evidence capture pass (capture / documentation only); executes the Phase 20A screenshot/evidence plan against real, locally running app state — verifies the backend runtime directly via `/api/health`, `/api/sources`, `/api/graph`, and `/api/intelligence/report` and records the captured backend-runtime screenshots and an [evidence doc](demo/phase-20d-demo-evidence.md). The frontend browser state showed a `Failed to fetch` (a run-configuration mismatch, since fixed in 21A/21B), documented honestly as captured runtime evidence. Implements no code and changes no behavior. |
| 21A | Complete | Dashboard shell foundation (frontend styling/scaffold); adds the dashboard shell layout/styles ahead of connected-UI evidence. |
| 21B | Complete | Frontend API base-URL runtime config alignment; loads env from the repo root (`envDir`), documents the canonical backend port `8787`, and adds `.env.example` guidance — fixing the frontend/backend mismatch Phase 20D recorded. |
| 21C | Active | Connected UI screenshot + runtime evidence refresh (capture / documentation only); re-runs the local backend (`8787`) and frontend (`5173`) and captures the connected UI state — "Connected" status, live API health, the rendered Knowledge Graph (7 nodes / 6 edges), and the backend-derived Intelligence Report — replacing Phase 20D's `Failed to fetch` evidence while preserving that history. Records an [evidence doc](demo/phase-21c-connected-ui-evidence.md) and connected-UI screenshots. Implements no code and changes no behavior. |
| Next: portfolio packaging | Planned | Final portfolio packaging / public presentation pass, drawing on the locked scope and captured evidence. No code or contract changes. |

## Future roadmap

| Future track | Goal | Guardrail |
| --- | --- | --- |
| Intelligence derivation | Dreaming `duplicate_signal` / `orphaned_node` / `stale_knowledge_link` suggestions shipped backend in Phase 14C and frontend-visible in Phase 14D. Remaining: `source_coverage_gap` deferred by the pinned Phase 14B contract/schema state and `unresolved_query_pattern` blocked until query-history persistence exists. | Read-only; no AI/LLM until separately planned. |
| Temporal decay | Backend-derived MVP shipped in Phase 13A, frontend visibility/demo polish shipped in Phase 13B, and end-to-end QA shipped in Phase 13C. Remaining: richer reference/last-seen signals. | No graph mutation; indicators remain advisory. |
| Provenance chains | Backend-derived MVP (Phase 15C), frontend visibility/demo polish (Phase 15D), and QA evidence pass (Phase 15E) complete. Remaining: selected-node inspector extension, per-section error state. | Present existing evidence only; do not invent lineage; read-only. |
| Query trails | Persist and present useful console/search history. Phase 16A defined local/read-only boundaries and relationships; Phase 16B aligned the `QueryTrailEntry` contract; Phase 16C shipped a backend-derived MVP for `source_followup` / `knowledge_gap` / `related_query_cluster` from existing source/node/tag structure and made it frontend-visible. Remaining: local query persistence to unblock `repeated_query` / `unresolved_question`. | Read-only structural projection; no query persistence/logging/capture; `repeated_query` / `unresolved_question` stay blocked until real query history exists. |
| Intelligence cohesion | Keep the four backend-derived surfaces (decay, dreaming, provenance, trails) aligned on terminology, evidence shape, empty-state parity, and readiness before adding a fifth. Phase 17A is the planning pass; Phase 17B is the readiness-hardening pass (rationale, thresholds, edge cases, evidence expectations, performance, adapter strategy). | Documentation/cohesion first; no new intelligence logic until the readiness review justifies it. |
| Agent Ops | Expose governed agent/source registry data in the app. | Start read-only from `docs/agent-lab/` shapes. |
| Security hardening | Owner-authorized, local-only defensive testing and hardening per the [threat model + vulnerability test plan](security/threat-model-and-vulnerability-test-plan.md): API validation/error safety shipped (18B) and regression-verified (18C, [evidence](security/phase-18c-backend-api-security-regression-qa.md)); deferred API edge cases triaged and scoped in 18D ([planning](security/phase-18d-api-edge-case-hardening-planning.md)); the selected edge-case subset (bounded nesting-depth guard + value decisions) shipped in 18E and regression-verified in 18F. Phase 19A ([release-readiness planning](security/phase-19a-security-cohesion-release-readiness-planning.md)) consolidates the arc into a demo-ready (not production-secure) posture and a release-readiness checklist, and Phase 19B ([release-readiness QA + demo evidence](release-readiness/phase-19b-release-readiness-qa-demo-evidence.md)) records the whole-project readiness/demo-evidence posture and boundaries. Remaining: Obsidian import filesystem safety (likely next track), intelligence evidence regression, frontend rendering safety, dependency/static baseline; production-security controls (auth, authorization, rate limiting, deployment hardening, secrets management, audit logging, threat monitoring) stay out of scope until the runtime model changes. | Plan-first; narrow per-route guards over middleware rewrites; demo readiness ≠ production security; no third-party targets; document findings before fixing; preserve read-only intelligence guardrails. |

## Standing guardrails

- Read-only surfaces first.
- Suggestions are advisory and never silently applied.
- Deterministic logic before any AI/LLM integration.
- Additive contracts only.
- No dashboard redesign or branding churn inside backend/API phases.
- Demo fixtures must stay labeled as demo data.
- Human merge gate remains with devdevbuilds.


