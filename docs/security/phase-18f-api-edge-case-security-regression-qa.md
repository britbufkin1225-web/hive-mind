# Phase 18F — API Edge Case Security Regression QA + Evidence Pass

Parent label: **devdevbuilds**

**Status: complete (QA / evidence only).** Phase 18F is a verification-and-evidence
pass over the Phase 18E API edge-case defensive-validation work. It adds **no**
backend feature, endpoint, validation rule, middleware, frontend code, dependency,
persistence, auth, rate limiter, scanner, AI/LLM, or graph/source mutation. It
reviews the existing Phase 18E implementation and tests, runs the existing test
suite, confirms the Phase 18E behaviors hold, maps coverage back to the Phase 18A
threat model and the Phase 18D triage, and records the evidence below.

This document is the QA companion to the
[Phase 18E — API Edge Case Defensive Validation MVP](phase-18e-api-edge-case-defensive-validation.md),
the [Phase 18D — API Edge Case Hardening Planning / Deferred Security Scope Triage](phase-18d-api-edge-case-hardening-planning.md),
and the [Security Threat Model + Vulnerability Test Plan](threat-model-and-vulnerability-test-plan.md)
(Phase 18A, §5.1 API negative testing). The delivered API-hardening track is:

- **18A** — threat model / what to test;
- **18B** — implementation of the in-scope §5.1 field-level cases;
- **18C** — QA / evidence over 18B;
- **18D** — planning / triage of the deferred structural edges;
- **18E** — implementation of the selected 18D subset (bounded nesting depth +
  explicit value-handling decisions);
- **18F** — *this pass*: QA / evidence over 18E.

> **Status honesty:** Phase 18F does **not** claim Hive|Mind is fully hardened or
> secure. It confirms that the specific Phase 18E defensive behaviors behave as
> documented and are locked by regression tests. The items Phase 18D deferred
> beyond the 18E subset (total-body byte ceilings; the not-applicable
> auth/rate-limit and blocked persistence tracks) remain future / out-of-scope
> work, unchanged. No vulnerability was fixed and no defense was added in this
> phase.

---

## 1. Why regression QA now (rationale)

- **QA follows 18E before more security work**, mirroring the 18B → 18C pattern.
  Phase 18E added a new *structural* guard (request-body nesting depth) plus
  explicit value-handling decisions at trust boundary #1 (request → API). Before
  sequencing any further hardening, the newly shipped guard should have a
  confirmed, reviewable evidence trail mapping it back to the planning it came
  from. Verifying a foundation before building on it matches the contracts-first
  discipline used across the intelligence phases.
- **This pass stays evidence-focused, not implementation-expanding.** The goal is
  a clear regression-evidence trail, not new behavior. Adding endpoints,
  validation, middleware, or scanners here would re-open the boundary 18E just
  closed and mix unverified new code into a verification pass. The diff is
  intentionally limited to this document plus a narrow roadmap status update. No
  coverage gap was found (§5), so this pass adds no new test.
- **Auth / rate-limit / broad query-param middleware stay out of scope.** The
  threat model (§1) scopes this project to owner-authorized, local-only defensive
  testing of a single-user, no-network-exposure, no-auth local app. Phase 18E's
  route inventory found **zero** query-reading routes, so there is no per-route
  query-param target and no justified global middleware (Phase 18D
  *Route-Level Validation Boundaries*). Standing those up here would be new
  architecture aimed at a threat model that does not apply today.

---

## 2. Repository / scope verification

- Local repo: `C:\Users\britb\Documents\hive-mind` (not OneDrive; folder is
  `hive-mind`).
- Remote: `https://github.com/britbufkin1225-web/hive-mind.git`.
- Phase branch: `phase-18f-api-edge-case-security-regression-qa`.
- Phase 18E implementation under review: commit
  `2d006ad Add Phase 18E API edge case defensive validation MVP` (present on the
  `phase-18e-api-edge-case-defensive-validation-mvp` branch this QA branch is
  stacked on). At the time of this pass, `origin/main` HEAD is
  `75d85d9 Add Phase 18D API edge case hardening planning + deferred scope triage (#64)`
  — i.e. Phase 18E's PR was **not yet merged into `main`** when 18F began, so this
  QA branch was created from the 18E branch (the only place the 18E code lives)
  rather than from `main`. This is recorded for honesty; it changes no 18E code.
- Working tree clean before changes; the only diff this phase introduces is this
  evidence document plus a narrow roadmap status update.

---

## 3. What was reviewed

| Artifact | Role in this QA pass |
| --- | --- |
| `docs/security/threat-model-and-vulnerability-test-plan.md` | Source of the §5.1 API-negative pass-criteria this QA maps 18E coverage against. |
| `docs/security/phase-18d-api-edge-case-hardening-planning.md` | The triage that selected the 18E scope (deep nesting + value decisions) and set the readiness checklist verified here. |
| `docs/security/phase-18e-api-edge-case-defensive-validation.md` | The 18E implementation companion doc whose claims (route inventory, guard, tests, 267-pass count) this pass independently re-runs and confirms. |
| `apps/backend/app/services/validation.py` | The pure, iterative `assert_within_nesting_depth` guard and the named bound `MAX_REQUEST_NESTING_DEPTH = 32`. |
| `apps/backend/app/models/hive_models.py` | The additive `_NestingDepthGuardedModel` mixin and its application to `HiveImportRequest`, `SourceRecordCreate`, `SourceRecordUpdate`; flat models (`ConsoleExecuteRequest`, `ObsidianImportRequest`) confirmed untouched. |
| `apps/backend/tests/test_api_edge_case_validation.py` | The 18E regression file (18 tests) verified and mapped here. |

---

## 4. Coverage confirmation — edge cases now covered by Phase 18E

Each row lists the threat-model reference, the safe behavior expected, and the
18E test(s) that lock it. All listed tests **passed** (§6).

| # | Edge case | Threat-model ref | Expected safe behavior | Covering test(s) | Result |
| - | --------- | ---------------- | ---------------------- | ---------------- | ------ |
| 1 | Deeply nested body — at-limit accepted | §5.1 (deeply nested objects) | Depth exactly at bound still valid (no valid request regressed) | `test_depth_guard_allows_at_limit`, `test_registry_create_accepts_at_limit_metadata` | ✅ |
| 2 | Deeply nested body — over-limit rejected | §5.1 (deeply nested objects) | Over-depth → clean `422` before downstream processing | `test_depth_guard_rejects_over_limit`, `test_registry_create_rejects_deeply_nested_metadata`, `test_import_rejects_deeply_nested_node_metadata`, `test_registry_update_rejects_deeply_nested_metadata` | ✅ |
| 3 | List nesting counted like dict nesting | §5.1 (deeply nested objects) | Lists contribute to depth; over-depth list → `ValueError` | `test_depth_guard_counts_list_nesting` | ✅ |
| 4 | Shallow / scalar values unaffected | §5.1 (no valid request regressed) | Strings, ints, shallow structures never trip the guard | `test_depth_guard_allows_flat_and_scalar_values`, `test_import_accepts_shallow_valid_body` | ✅ |
| 5 | Guard itself cannot overflow the stack | §5.1 (uncontrolled recursion) | Iterative guard rejects a 50,000-deep payload with a clean `ValueError`, never a `RecursionError`/crash | `test_depth_guard_survives_pathologically_deep_input` | ✅ |
| 6 | Rejection leaks nothing | §5.1 error-response safety / §3 #5 | `422` with `{"detail": ...}`; no `Traceback`, `File "`, or `ValueError` class name in body | `test_deep_nesting_rejection_leaks_nothing` | ✅ |
| 7 | Null-like sentinel strings are ordinary values | §5.1 (ambiguous primitive values) | `"null"`/`"None"`/`"undefined"`/`"nil"`/`"NaN"` are plain strings → `201`; null-like console command → graceful `200` `ok=false` | `test_null_like_strings_are_ordinary_values` (×5), `test_console_null_like_command_is_graceful_200` | ✅ |
| 8 | Empty / whitespace-only values keep clean 4xx | §5.1 (empty/whitespace values) | Whitespace-only vault path → clean `400`, never `500`/traceback | `test_whitespace_only_vault_path_is_clean_client_error` | ✅ |

### Confirmed: structural defensive validation
Rows 1–5. A deeply nested / recursion-shaped body is rejected at the contract edge
with a clean `422` (or a `ValueError` at the helper level) *before* any downstream
traversal, store import, or persistence runs. The bound is inclusive and additive —
`test_depth_guard_allows_at_limit` and `test_registry_create_accepts_at_limit_metadata`
confirm a body whose deepest container sits exactly at `MAX_REQUEST_NESTING_DEPTH`
still succeeds, so no realistic valid request regressed. The traversal is iterative,
so the guard cannot itself overflow the stack on the hostile input it defends
against (row 5).

### Confirmed: error-shape conformance / no leak
Row 6. The depth guard raises a plain `ValueError`, which Pydantic renders as the
**same** structured `422` (`{"detail": ...}`) the Phase 18B field validators
already produce — no new error shape is invented. The rejection body is asserted to
exclude `Traceback`, a source path (`File "`), and the internal exception class
name, so Phase 18C cat. 10 (no-leak) is **not regressed**.

### Confirmed: value-handling decisions locked
Rows 7–8. No new behavior was introduced; these tests pin the existing safe
behavior as an *intentional, documented* decision so it cannot silently regress:
null-like sentinel strings are ordinary string values, and empty / whitespace-only
values keep their existing clean `4xx` handling.

---

## 5. Coverage assessment — confirmed gaps intentionally NOT closed

Phase 18E implemented only the *selected* 18D subset. The following were
**intentionally not added**, consistent with the Phase 18D triage and the threat
model — confirmed still absent in the reviewed code:

- **No global middleware.** The nesting-depth guard is a per-model
  `model_validator(mode="before")` mixin applied to three free-form body models
  only. There is no request-level interceptor. (Phase 18D *Route-Level Validation
  Boundaries*; verified in `hive_models.py`.)
- **No broad query-parameter validation.** The 18E route inventory found **zero**
  query-reading routes, so there is no per-route query target and the global
  query-string cap Phase 18D conditioned on an inventory remains unjustified and
  unadded. A future route that introduces a query parameter must add a narrow
  per-route guard at that point.
- **No auth / rate-limit work.** Not applicable to the single-user, local,
  no-network, no-auth runtime (threat model §1).
- **No frontend / API expansion.** No new endpoint, no new response field, no
  frontend file touched. The guarded models accept exactly the same valid bodies
  as before.
- **No persistence / data-model changes.** No store, schema, or query-history
  change. (Persisted query-history input edges remain **blocked** until
  persistence exists — threat model §5.3.)
- **No total-body byte ceiling.** Deferred by Phase 18D as a possible follow-up;
  out of the 18E subset and not added.
- **No new dependency, scanner, or AI/LLM change.**

No missing 18E regression assertion was found — the selected §5.1 edges and the
explicit value decisions are all covered (§4) — so this pass adds **no** new test.

---

## 6. Validation results

Environment: Python 3.13.13, pytest 8.4.0 (Windows). `rootdir: apps/backend`,
`configfile: pytest.ini`.

Targeted Phase 18E edge-case file:

```text
python -m pytest apps/backend/tests/test_api_edge_case_validation.py
=> 18 passed in 0.54s
```

Phase 18B regression file (confirms the existing field-level guards still hold
alongside the new structural guard):

```text
python -m pytest apps/backend/tests/test_api_error_safety.py
=> 23 passed in 0.52s
```

Full backend suite:

```text
python -m pytest apps/backend
=> 267 passed in 2.22s
```

The 267-pass total matches the Phase 18E doc's recorded count (249 prior + 18
new), independently reproduced here. Frontend build: **not run** (no frontend
files touched; per phase guardrail the frontend build is only run when frontend
files change).

---

## 7. Mapping 18E coverage back to the Phase 18A and 18D planning

| Planning source | What it asked for | How Phase 18E satisfied it | Confirmed here |
| --- | --- | --- | --- |
| **18A** threat model §5.1 — *deeply nested objects → no uncontrolled recursion* | A negative-test category for structural depth attacks | Bounded, iterative nesting-depth guard rejecting over-depth with a clean `422`; guard cannot overflow the stack | §4 rows 1–6 ✅ |
| **18A** threat model §5.1 — *ambiguous / empty / whitespace primitive values* | Deterministic, leak-free handling of odd-but-typed values | Explicit, tested decisions: null-like strings are plain values; empty/whitespace keep clean `4xx` | §4 rows 7–8 ✅ |
| **18A** threat model §5.1 / §3 #5 — *error-response safety* | No new error shape; no traceback/path leak | Depth guard reuses the existing `{"detail": ...}` `422`; no-leak test asserts no class/path/traceback | §4 row 6 ✅ |
| **18D** readiness checklist — *route inventory before code* | Inventory every body-accepting / query-reading route | 18E doc records the full route table; finds zero query-reading routes | §3, §5 ✅ |
| **18D** readiness checklist — *bounded depth guard, named constant, at-limit success* | Depth guard with a documented constant and an at-limit acceptance test | `MAX_REQUEST_NESTING_DEPTH = 32` with rationale; at-limit body still accepted | §4 rows 1, 5 ✅ |
| **18D** *Route-Level Validation Boundaries* — *no global middleware unless justified* | Narrow, per-model, individually testable guards | Per-model mixin on 3 models; no middleware | §5 ✅ |
| **18D** *Error Response Safety* — *conformance, not a new shape* | Same `{"detail": ...}` shape and status conventions | Verified identical to Phase 18B/18C error contract | §4 row 6 ✅ |
| **18D** *Recommended 18E Scope* item 2 — *query-param safety on routes that read query params* | Validate the query-reading routes | No query-reading route exists → no target; recorded, not invented | §5 ✅ (correctly scoped out) |
| **18D** *Not In Scope Yet* — auth / rate-limit / persistence / scanner | Stay out until the runtime model changes | None added | §5 ✅ |

---

## 8. Scope confirmation

Phase 18F did **not**:

- add backend features, endpoints, validation rules, or middleware;
- add or change any test or any application code;
- add frontend code or redesign the dashboard / UI or touch branding/assets;
- add AI/LLM behavior or embeddings;
- add authentication, authorization, or rate limiting;
- add a vulnerability scanner or automated scanning/fuzzing;
- add new dependencies, package files, or lockfiles;
- add database tables, persistence, or query history;
- change any stable API contract for valid requests;
- expand the API surface or any frontend/API behavior;
- mutate source / graph / intelligence behavior or rewrite the Obsidian importer;
- perform a broad refactor or any destructive testing.

The change set is documentation / evidence only: this QA evidence document plus a
narrow roadmap status update. **No application behavior changed** and **no valid
request contract changed** — every existing valid request still passes, confirmed
by the full backend suite (267 passed).

---

## 9. Remaining deferred security scope

Unchanged from the Phase 18D triage; **not** addressed here (and not required for
this evidence pass):

- **Total request-body byte / element-count ceiling** — deferred follow-up beyond
  the per-field and per-depth limits (Medium).
- **Query-parameter safety** — remains a *latent* item with **no current target**
  (zero query-reading routes); to be implemented as a narrow per-route guard if and
  when a route introduces a query parameter (Low–Medium).
- **Obsidian import filesystem path-safety matrix** — distinct future track
  (threat model §5.2).
- **Intelligence evidence regression beyond the read-only invariant** — distinct
  future track (threat model §5.3).
- **Frontend rendering safety** — distinct future track (threat model §5.4).
- **Dependency / static / secret baseline** — distinct future track (threat model
  §5.5); findings reviewed before any change, never blind-auto-fixed.
- **Auth / rate-limit / persisted query-history edges** — **not applicable** /
  **blocked** under the current single-user, local, no-network, no-auth runtime
  (threat model §1, §5.3).

---

## 10. Final status

Phase 18F is **complete as a QA / evidence pass**. The Phase 18E nesting-depth
guard and explicit value-handling decisions are independently confirmed present,
correct, and regression-locked (18 targeted + 23 Phase 18B regression + 267 full
backend tests passing), mapped back to the Phase 18A threat model and the Phase
18D triage, with the intentionally-deferred scope re-confirmed.

No claim is made that Hive|Mind is fully hardened — only that the specific Phase
18E behaviors behave as documented and cannot silently regress. The deferred edges
above remain future / out-of-scope work.
