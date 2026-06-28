# Phase 18C — Backend API Security Regression QA + Evidence Pass

Parent label: **devdevbuilds**

**Status: complete (QA / evidence only).** Phase 18C is a verification-and-evidence
pass over the Phase 18B backend API defensive-validation and error-safety work. It
adds **no** backend feature, endpoint, frontend code, dependency, persistence,
auth, AI/LLM, or graph/source mutation. It runs the existing test suite, confirms
the Phase 18B behaviors hold, maps coverage to the threat model, and records the
evidence below.

This document is the QA companion to the
[Security Threat Model + Vulnerability Test Plan](threat-model-and-vulnerability-test-plan.md)
(Phase 18A) and the Phase 18B implementation it verifies. 18A defined *what to
test* (§5.1 API negative testing, §5.3 Intelligence Report integrity); 18B
*implemented and tested* the §5.1 negative-API cases plus the §5.3 read-only
invariant; 18C *verifies the evidence* that those behaviors are present, correct,
and regression-covered.

> **Status honesty:** Phase 18C does **not** claim Hive|Mind is fully hardened or
> secure. It confirms that the specific Phase 18B defensive behaviors behave as
> documented and are locked by regression tests. The remaining hardening phases
> (18C-filesystem through 18F, per the threat model §7) are still future work.

---

## 1. Why regression QA now (rationale)

- **QA follows 18B before more security work.** Phase 18B added defensive code at
  the highest-traffic trust boundary (frontend request → backend API, threat model
  §3 #1 and #5). Before sequencing the next hardening pass (Obsidian filesystem
  safety, intelligence evidence regression, frontend rendering, dependency
  baseline), the input-boundary defenses already shipped should have a confirmed,
  reviewable evidence trail. Verifying a foundation before building the next layer
  on it matches the contracts-first discipline used across the intelligence phases.
- **This pass stays evidence-focused, not implementation-expanding.** The phase
  goal is a clear evidence trail, not new behavior. Adding endpoints, validation,
  or scanners here would re-open the very boundary 18B just closed and would mix
  unverified new code into a verification pass. The diff is intentionally limited
  to documentation plus (if a gap were found) a tiny test-only assertion. No such
  gap was found — the §5.1/§5.3 categories in scope for 18B are already covered
  (§4), so this pass is documentation/evidence only.
- **Broad vuln automation / auth / rate-limiting stay out of scope.** The threat
  model (§1) scopes this project to owner-authorized, local-only defensive testing
  of a single-user, no-network-exposure, no-auth local app. Standing up a
  vulnerability scanner, an authentication/authorization layer, or rate limiting
  would be new architecture aimed at a threat model (multi-user, network-exposed,
  credential-bearing) that does not apply to the current runtime. Dependency/static
  baseline work is explicitly deferred to a later phase (threat model §5.5 / §7
  18F) where findings are reviewed before any change — not blind-automated here.

---

## 2. Repository / scope verification

- Local repo: `C:\Users\britb\Documents\hive-mind` (not OneDrive; folder is
  `hive-mind`).
- Remote: `https://github.com/britbufkin1225-web/hive-mind.git`.
- Base branch: `main`, in sync with `origin/main`.
- Phase 18B present on main: commit
  `aba8c7c Add Phase 18B backend API defensive validation + error safety (#62)`.
- Phase branch: `phase-18c-backend-api-security-regression-qa`.

---

## 3. What was reviewed

| Artifact | Role in this QA pass |
| --- | --- |
| `docs/security/threat-model-and-vulnerability-test-plan.md` | Source of the §5.1 / §5.3 pass-criteria this QA maps coverage against. |
| `apps/backend/tests/test_api_error_safety.py` | The Phase 18B regression test file (23 tests) verified and mapped here. |
| `apps/backend/app/main.py` | Global unhandled-exception handler returning a clean JSON `500` with no leak. |
| `apps/backend/app/adapters/vault_scanner.py` | `resolve_vault_root` normalizing malformed vault-path strings into a clean `ValueError` (→ `400`). |
| `apps/backend/app/routers/obsidian.py` | Maps the adapter `ValueError` to HTTP `400` (client error, not `500`). |
| `apps/backend/app/models/hive_models.py` | Additive upper-bound length guards on client free-text fields (`command`, `vault_path`, `name`, `root_path`). |

---

## 4. Evidence summary by behavior category

Each category lists the threat-model reference, the safe behavior expected, and the
test(s) in `apps/backend/tests/test_api_error_safety.py` that lock it. All listed
tests **passed** (§5).

| # | Behavior category | Threat-model ref | Expected safe behavior | Covering test(s) | Result |
| - | ----------------- | ---------------- | ---------------------- | ---------------- | ------ |
| 1 | Unknown route | §5.1, §6 (method/route) | Clean `404`, no `500` | `test_unknown_route_returns_404` | ✅ |
| 2 | Wrong method | §5.1, §6 | Clean `405` on POST-only and GET-only routes | `test_wrong_method_on_post_route_returns_405` (×3 paths), `test_wrong_method_on_get_route_returns_405` | ✅ |
| 3 | Malformed JSON | §5.1 | Client `400`/`422`, never `500` | `test_malformed_json_body_is_client_error_not_500` | ✅ |
| 4 | Wrong field types | §5.1 | Structured `422` at contract edge | `test_console_wrong_command_type_is_422`, `test_import_wrong_field_type_is_422` | ✅ |
| 5 | Missing required fields | §5.1 | Structured `422` | `test_console_missing_command_field_is_422`, `test_obsidian_missing_vault_path_is_422` | ✅ |
| 6 | Unsupported enum / blank value | §5.1 | Clean `422` | `test_registry_invalid_enum_value_is_422`, `test_registry_blank_name_is_422` | ✅ |
| 7 | Oversized free-text fields | §5.1 (oversized strings) | Deterministic `422` over bound; at-limit value still `200` | `test_oversized_console_command_is_422`, `test_console_command_at_limit_is_accepted`, `test_oversized_vault_path_is_422`, `test_oversized_registry_root_path_is_422` | ✅ |
| 8 | Invalid object identifiers | §5.1 (invalid IDs) | Clean `404`, no traceback in body | `test_invalid_source_id_is_404`, `test_invalid_registry_source_id_is_404` | ✅ |
| 9 | Malformed vault paths | §5.1 / §5.2 boundary #2 | Null byte / OS-invalid / over-length → `ValueError` → `400`/`422`, no `500`, no traceback | `test_resolve_vault_root_rejects_embedded_null_byte`, `test_resolve_vault_root_wraps_oserror`, `test_api_obsidian_malformed_path_is_client_error_not_500` | ✅ |
| 10 | No traceback / internal-path leakage in `500` | §5.1, §3 #5 | `500` body is `{"detail": "Internal server error"}`; no sentinel, no `Traceback`, no `RuntimeError`, no path | `test_unhandled_exception_returns_clean_json_without_leak` | ✅ |
| 11 | Intelligence Report read-only invariant | §5.3, §3 #4 | Repeated `GET /api/intelligence/report` does not change source/node/edge counts | `test_intelligence_report_does_not_mutate_store` | ✅ |

### Confirmed: defensive validation behaviors
Categories 1–8 above. Malformed, mistyped, missing, bad-enum, blank, and oversized
client input is rejected at the contract boundary with clean `4xx` status codes
before any downstream processing (shlex parsing, filesystem probe, store work).
The upper-bound guards are additive — `test_console_command_at_limit_is_accepted`
confirms a realistic max-length value still returns `200`, so no existing valid
request regressed.

### Confirmed: error-safety behaviors
Categories 3, 9, 10. A malformed body, a malformed vault path, and a forced
unhandled exception all resolve to client-safe responses (`4xx`, or a generic
`500`), never an unhandled crash. The global handler in `main.py` logs the real
error server-side and returns the same `{"detail": ...}` shape as handled errors.

### Confirmed: leakage checks
Categories 8, 9, 10. The `500` body is asserted to exclude the injected sentinel
string, `Traceback`, `RuntimeError`, and the internal path detail; invalid-ID and
malformed-path responses are asserted to exclude `Traceback` / `File "`. No local
filesystem path or internal exception text reaches the client.

### Confirmed: read-only invariants
Category 11. The Intelligence Report surface is exercised twice and store export
counts are unchanged before/after, confirming derivation does not mutate
store/source/graph state (threat model §5.3 central invariant).

---

## 5. Validation results

Environment: Python 3.13.13, pytest 8.4.0, pluggy 1.6.0, anyio 4.13.0 (Windows).
`rootdir: apps/backend`, `configfile: pytest.ini`.

Targeted Phase 18B security / error-safety file:

```text
python -m pytest apps/backend/tests/test_api_error_safety.py
=> 23 passed in 0.60s
```

Full backend suite:

```text
python -m pytest apps/backend
=> 249 passed in 2.12s
```

Frontend build: **not run** (no frontend files touched; per phase guardrail the
frontend build is only run when frontend files change).

---

## 6. Coverage assessment and deferred items

The §5.1 categories in 18B's implemented scope and the §5.3 read-only invariant are
all covered (§4) — no missing regression assertion was found, so this pass adds no
new test. The following remain **deferred** (future-phase work, not Phase 18B
regressions, so intentionally not added here):

- **Deeply nested object / uncontrolled recursion** (threat model §5.1): no
  recursion-depth guard was part of the 18B implementation, so there is no 18B
  behavior to regress against. Candidate for a later API-hardening pass.
- **Unsafe query-parameter handling** (threat model §5.1): not in the 18B
  implemented set; deferred.
- **Obsidian import filesystem safety** — path traversal, absolute-path policy,
  symlink/vault-escape, idempotency (threat model §5.2): deferred to Phase 18C
  (filesystem) per threat model §7. Note: the existing `scan_markdown_files`
  already does not follow symlinks and never returns a path outside the root, but
  the explicit traversal/idempotency test matrix is a separate phase.
- **Intelligence evidence regression** beyond the read-only invariant — timestamp
  honesty, deferred-type blocking (threat model §5.3): deferred to Phase 18D.
- **Frontend rendering safety** (threat model §5.4): deferred to Phase 18E.
- **Dependency / static / secret-grep baseline** (threat model §5.5): deferred to
  Phase 18F; findings to be reviewed before any change, never blind-auto-fixed.

---

## 7. Scope confirmation

Phase 18C did **not**:

- add backend features, endpoints, or frontend code;
- redesign the dashboard / UI or touch branding/assets;
- add AI/LLM behavior or embeddings;
- add authentication, authorization, or rate limiting;
- add a vulnerability scanner or automated scanning;
- add new dependencies, package files, or lockfiles;
- add database tables, persistence, or query history;
- mutate source / graph / intelligence behavior or rewrite the Obsidian importer;
- expand architecture or perform destructive security testing.

The change set is documentation/evidence only: this QA evidence document plus a
narrow roadmap status update.
