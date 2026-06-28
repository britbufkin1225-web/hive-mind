# Phase 18E — API Edge Case Defensive Validation MVP

Parent label: **devdevbuilds**

**Status: complete (backend implementation).** Phase 18E implements the small,
selected subset of API edge-case guards that
[Phase 18D](phase-18d-api-edge-case-hardening-planning.md) triaged and scoped. It
is additive and regression-tested: it adds defensive validation for the
highest-value structural request edge (deep nesting) and locks the explicit
value-handling decisions Phase 18D asked to document, **without** expanding
product behavior, adding endpoints/middleware, or changing any stable contract
for valid requests.

This is the implementation companion to the
[Security Threat Model + Vulnerability Test Plan](threat-model-and-vulnerability-test-plan.md)
(§5.1 API negative testing), building directly on the Phase 18B defensive
validation, the Phase 18C regression evidence, and the Phase 18D scope.

> **Status honesty:** Phase 18E does **not** claim Hive|Mind is fully hardened.
> It implements the *selected* 18E subset (bounded nesting depth + explicit
> value-handling decisions). Items 18D deferred beyond this subset (total-body
> byte ceilings, and the not-applicable/blocked auth/rate-limit/persistence
> tracks) remain future or out-of-scope work, unchanged.

---

## Route inventory (recorded before code changes)

Per the Phase 18D readiness checklist, every route that accepts a POST/PATCH body
and/or reads query parameters:

| Route | Method | Body model | Reads query params? | Free-form nested input? |
| --- | --- | --- | --- | --- |
| `/api/import` | POST | `HiveImportRequest` | No | **Yes** — lists of records, each with `metadata` |
| `/api/console/execute` | POST | `ConsoleExecuteRequest` | No | No — single `command: str` |
| `/api/obsidian/import` | POST | `ObsidianImportRequest` | No | No — `vault_path` / `source_name` strings |
| `/api/registry/sources` | POST | `SourceRecordCreate` | No | **Yes** — free-form `metadata` dict |
| `/api/registry/sources/{id}` | PATCH | `SourceRecordUpdate` | No | **Yes** — free-form `metadata` dict |
| all `GET` routes | GET | — | No | — |

**Query-parameter finding (honest scope note).** The inventory found **zero**
routes that read query parameters — every route is body-driven or path-id-driven.
Phase 18D's recommended query-param work ("on the routes that actually read query
params") therefore has **no target** in the current API. Adding a global
query-string cap would require request-level middleware, which Phase 18D
explicitly cautioned against introducing without an inventory that justifies it
(`Route-Level Validation Boundaries`). With no query-reading route to protect,
that middleware is **not** justified and is intentionally **not** added; the
finding is recorded so a future route that introduces a query parameter knows to
add a narrow per-route guard at that point. This keeps the phase honest and
avoids re-opening trust boundary #1 globally.

---

## Edge cases hardened

### 1. Bounded request-body nesting depth (the 18E headline — Medium risk)

A deeply nested JSON body (`{"a": {"a": {"a": ...}}}`) is a structural attack on
the parser and any recursive traversal, not on a single field. The Phase 18B
field guards (type/length/presence/blank/enum) cannot see request *shape*. Phase
18E adds the missing structural guard:

- **Where:** `app/services/validation.py` — a pure, dependency-free
  `assert_within_nesting_depth(value, max_depth)` with the named constant
  `MAX_REQUEST_NESTING_DEPTH = 32`. The traversal is **iterative, never
  recursive**, and short-circuits on the first over-depth container, so the guard
  itself cannot overflow the stack on the hostile input it defends against.
- **Applied to:** only the body models that accept a free-form nested structure —
  `HiveImportRequest`, `SourceRecordCreate`, `SourceRecordUpdate` — via a small
  additive `_NestingDepthGuardedModel` mixin (`model_validator(mode="before")`),
  so the check runs at the contract edge *before* any downstream processing
  (store import, persistence). Flat models (`ConsoleExecuteRequest`,
  `ObsidianImportRequest`) have no nestable field and are left untouched.
- **Behavior:** over-depth → clean `422` (same structured validation-error shape
  as the existing Phase 18B guards); at-limit body → still accepted (no valid
  request regressed). Never a `500`, traceback, or path leak.
- **Why per-model, not middleware:** matches Phase 18D's `Route-Level Validation
  Boundaries` guidance — narrow, individually testable, additive, no global blast
  radius.

The bound (32) is far above any realistic body — Hive|Mind's deepest legitimate
structure is the snapshot import (request → list → record → `metadata` →
a handful of values), comfortably in single digits — yet low enough to reject
recursion-shaped payloads early.

### 2. Explicit value-handling decisions (Low risk — documented + locked)

Phase 18D asked for explicit, tested decisions on value edges 18B did not target
field-by-field. No new behavior was introduced; these tests pin the existing safe
behavior as intentional so it cannot silently regress:

- **Null-like sentinel strings** (`"null"`, `"None"`, `"undefined"`, `"nil"`,
  `"NaN"`) are **ordinary string values**, not a magic "absent" marker — e.g. a
  source named `"null"` is a valid create (`201`), and a `"null"` console command
  is a graceful unknown-command `200` with `ok: false`.
- **Empty / whitespace-only values** keep their existing clean `4xx` handling — a
  whitespace-only Obsidian `vault_path` stays a clean `400` (never a `500` /
  traceback), consistent with the empty-path behavior; the registry blank-name
  `422` from Phase 18B is unchanged.

---

## Error-response conformance

Every new guard returns the **existing** error contract (Phase 18D "Error
Response Safety"): the depth guard raises a plain `ValueError`, which Pydantic
renders as the same structured `422` (`detail`) that the Phase 18B field
validators already produce — no new error shape is invented. A dedicated test
asserts the rejection body contains no traceback, no source path (`File "`), and
no internal exception class name, so Phase 18C cat. 10 (no-leak) is not regressed.
New guards fail as a clean `4xx` *before* the global `500` backstop, which remains
the backstop and not the primary path.

---

## Tests added (mapped to threat model §5.1)

New file `apps/backend/tests/test_api_edge_case_validation.py` (18 tests):

| Test | Edge case | §5.1 category |
| --- | --- | --- |
| `test_depth_guard_allows_at_limit` | at-limit depth accepted | deeply nested objects |
| `test_depth_guard_rejects_over_limit` | over-limit depth rejected | deeply nested objects |
| `test_depth_guard_counts_list_nesting` | list nesting counted | deeply nested objects |
| `test_depth_guard_allows_flat_and_scalar_values` | shallow/scalar unaffected | deeply nested objects |
| `test_depth_guard_survives_pathologically_deep_input` | guard itself no stack overflow | uncontrolled recursion |
| `test_registry_create_rejects_deeply_nested_metadata` | deep `metadata` → `422` | deeply nested objects |
| `test_registry_create_accepts_at_limit_metadata` | at-limit body still `201` | no valid request regressed |
| `test_import_rejects_deeply_nested_node_metadata` | deep import body → `422` | deeply nested objects |
| `test_import_accepts_shallow_valid_body` | shallow import still `200` | no valid request regressed |
| `test_registry_update_rejects_deeply_nested_metadata` | deep PATCH body → `422` | deeply nested objects |
| `test_deep_nesting_rejection_leaks_nothing` | `422`, no traceback/path/class leak | error-response safety |
| `test_null_like_strings_are_ordinary_values` (×5) | null-like strings are plain strings | ambiguous primitive values |
| `test_console_null_like_command_is_graceful_200` | null-like command graceful | ambiguous primitive values |
| `test_whitespace_only_vault_path_is_clean_client_error` | whitespace path → clean `400` | empty/whitespace values |

The unit tests pin the exact inclusive depth boundary independently of any route;
the API tests prove end-to-end rejection/acceptance and the no-leak contract.

---

## Validation commands run

- Targeted: `python -m pytest apps/backend/tests/test_api_edge_case_validation.py`
  → **18 passed**.
- Phase 18B regression: `python -m pytest apps/backend/tests/test_api_error_safety.py`
  (with registry/endpoints/contract tests) → **passed**.
- Full backend suite: `python -m pytest apps/backend` → **267 passed** (249 prior
  + 18 new), stable across repeated runs.

---

## Guardrails preserved

Phase 18E did **not**: add frontend code or redesign the dashboard; add new
intelligence features or any AI/LLM logic; add new API endpoints; add any
middleware; overhaul auth or add rate limiting; add a vulnerability scanner or
fuzzing automation; add new dependencies, package files, or lockfiles; expand
persistence or the data model; mutate source/graph/intelligence behavior; or
perform a broad refactor. It changed **stable API contracts for valid requests**
in no way — every existing valid request still passes. The change set is: one new
pure validation helper, an additive mixin applied to three free-form body models,
one new test file, and this document.
