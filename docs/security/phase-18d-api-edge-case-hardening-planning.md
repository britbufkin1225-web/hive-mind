# Phase 18D — API Edge Case Hardening Planning / Deferred Security Scope Triage

Parent label: **devdevbuilds**

**Status: complete (planning / triage only).** Phase 18D is a documentation-only
pass. It adds **no** backend feature, endpoint, validation code, middleware,
frontend code, test, dependency, persistence, auth, rate limiter, scanner, AI/LLM,
or graph/source mutation. It reviews the existing Phase 18A–18C security work,
triages the API edge-case hardening items those phases explicitly deferred, and
organizes them into a clear, scoped plan for a future implementation phase
(Phase 18E). Nothing here changes behavior.

This document is the planning companion to the
[Security Threat Model + Vulnerability Test Plan](threat-model-and-vulnerability-test-plan.md)
(Phase 18A, §5.1 API negative testing) and the
[Phase 18C Backend API Security Regression QA + Evidence](phase-18c-backend-api-security-regression-qa.md)
(§6 coverage assessment and deferred items). 18A defined *what to test*; 18B
*implemented and tested* the in-scope §5.1 cases; 18C *verified that evidence* and
named the edge cases left out; 18D *triages those leftovers* into handled /
verified / deferred / not-applicable / blocked buckets and writes the readiness
criteria for the next phase.

> **Status honesty:** Phase 18D does **not** claim Hive|Mind is fully hardened or
> that the deferred edge cases are safe today. It claims only that the deferred
> items are now organized, risk-rated, and ready to be implemented deliberately in
> a later phase instead of rushed. No vulnerability was fixed and no defense was
> added in this phase.

---

## Purpose

Phase 18C confirmed that the Phase 18B defensive-validation and error-safety
behaviors hold and are regression-locked (23 targeted + 249 full backend tests
passing). In doing so it explicitly recorded (18C §6) that several deeper API
edge cases were **not** part of the 18B implementation and therefore had no 18B
behavior to regress against — for example deeply nested object / uncontrolled
recursion and unsafe query-parameter handling.

Those items have been mentioned but never organized. The purpose of Phase 18D is
to turn that loose "deferred" list into a reviewable triage artifact:

- Separate what is **already handled** by 18B (and verified by 18C) from what is
  genuinely **deferred**, **not applicable** to the current architecture, or
  **blocked** until a future feature exists.
- Risk-rate each deferred edge case against the actual local, single-user,
  no-network, no-auth runtime described in the threat model (§1), so we do not
  inflate or dismiss risk.
- Define a narrow, testable scope for **Phase 18E — API Edge Case Defensive
  Validation MVP**, with an implementation-readiness checklist, so the next phase
  implements a small, justified set of guards rather than a broad middleware
  rewrite.

This is the seatbelt inspection before driving faster: boring, correct, and far
cheaper than the regret of shipping an unplanned validation rewrite into a
security-facing boundary.

---

## Context from Phase 18A–18C

| Phase | Type | What it established that 18D builds on |
| --- | --- | --- |
| 18A | Planning | The threat model, trust boundaries, and §5.1 API-negative-testing categories — including the two edge cases this phase centers on: *deeply nested objects → no uncontrolled recursion* and *unsafe query parameters → no internal leak*. |
| 18B | Implementation | The shipped defensive behaviors at trust boundary #1 (request → API) and #5 (exception → error message): a global clean-JSON `500` handler with no traceback/path leak, malformed Obsidian vault-path normalization (→ `400`), and additive upper-bound length guards on client free-text fields (→ `422`). |
| 18C | QA / evidence | Independent verification that the 18B behaviors hold and a coverage map to the threat model, **plus** an explicit deferred-items list (18C §6) naming deep nesting and query-parameter safety as future, non-regression work. |

Phase 18D consumes 18C §6 directly: that list is the input to the triage tables
below. 18D does not reopen the 18B boundary or re-run 18C's verification — it
organizes the gaps 18C already named.

### Note on phase re-sequencing (honesty)

The threat model §7 originally sketched a hardening sequence where "18C" was
Obsidian import filesystem safety and later letters covered intelligence,
frontend, and dependency work. Actual delivery diverged: the API track was strong
enough to justify a dedicated regression/evidence pass, so the **delivered**
sequence became 18B (API validation) → 18C (API regression QA). Phase 18D
continues that **delivered API-hardening track** rather than the original §7
lettering. The other §7 tracks (Obsidian filesystem, intelligence evidence
regression, frontend rendering, dependency baseline) are unchanged in intent and
remain future work; only the letters moved. §7 is reconciled to reflect this so
the roadmap and threat model do not contradict each other.

---

## Already Handled Security Areas

These are **in place from Phase 18B and verified by Phase 18C** (18C §4). They are
listed here so the deferred triage cannot accidentally re-scope something that is
already done.

| Area | Handled by | Verified by | Behavior |
| --- | --- | --- | --- |
| Unknown route | 18B | 18C cat. 1 | Clean `404`, no `500`. |
| Wrong method | 18B | 18C cat. 2 | Clean `405` on POST-only / GET-only routes. |
| Malformed JSON body | 18B | 18C cat. 3 | Client `400`/`422`, never `500`. |
| Wrong field types | 18B | 18C cat. 4 | Structured `422` at the contract edge. |
| Missing required fields | 18B | 18C cat. 5 | Structured `422`. |
| Unsupported enum / blank value | 18B | 18C cat. 6 | Clean `422`. |
| Oversized free-text fields | 18B | 18C cat. 7 | Deterministic `422` over bound; at-limit still `200`. |
| Invalid object identifiers | 18B | 18C cat. 8 | Clean `404`, no traceback. |
| Malformed vault paths | 18B | 18C cat. 9 | Null byte / OS-invalid / over-length → `400`/`422`, no `500`. |
| No traceback / path leakage in `500` | 18B | 18C cat. 10 | `500` body is `{"detail": "Internal server error"}`; no internals. |
| Intelligence Report read-only invariant | 18B | 18C cat. 11 | Repeated report `GET` does not mutate store/source/graph. |

**Implication for 18D:** the request-shape, field-type, field-size,
missing/blank/enum, and error-leakage edges are closed. What remains are
*structural* request edges (nesting depth, total body size beyond per-field
length) and *query-string* edges (parameter count/length/repeat/type), plus a
small set of value-normalization edges that 18B did not target field-by-field.

---

## Deferred Edge Case Areas

Status legend:

- **Handled (18B/18C)** — already implemented and verified; listed for completeness.
- **Deferred** — real, in-scope edge that 18B did not implement; candidate for 18E.
- **Not applicable** — does not map to the current architecture/runtime.
- **Blocked** — depends on a feature that does not exist yet (persistence, auth,
  query history); cannot be meaningfully implemented or tested until then.

| Area | Current status | Risk | Suggested future handling | Notes |
| --- | --- | --- | --- | --- |
| Deeply nested object / uncontrolled recursion | Deferred | Medium | Add a bounded recursion-depth / nesting-depth guard on POST bodies; reject over-depth with a clean `422` before deep traversal. | Named in 18C §6 and threat model §5.1. No 18B guard exists, so no regression today. FastAPI/Pydantic parse the whole body before handlers run; depth bound is the targeted defense. |
| Oversized nested request bodies (total size, not per-field) | Deferred | Medium | Add a total request-body size ceiling (count of fields / total bytes), distinct from the existing per-field length guards. | 18B bounds individual free-text fields (`command`, `vault_path`, `name`, `root_path`) but not aggregate body size or array/object element counts. |
| Unsafe / malformed query-parameter handling | Deferred | Low–Medium | Validate query params against expected type/shape; reject malformed values with a clean `422`/`400`, never a `500` or internal leak. | Named in 18C §6 / threat model §5.1. Most current routes are body-driven or path-id-driven; query-param surface is small (see Query Parameter Safety below). |
| Query parameter length / count limits | Deferred | Low | Cap query-string length and parameter count per request; reject excess cleanly. | Defensive only; no current route depends on large query strings. |
| Repeated parameters (`?x=a&x=b`) | Deferred | Low | Define and document an explicit policy (first-wins / reject) for duplicate query keys on the few routes that read query params. | Framework default today is implicit; making it explicit is the hardening. |
| Unexpected parameter types (e.g. string where int expected) | Partially handled / Deferred | Low | Where a typed query/path param exists, confirm `422` on type mismatch; add coverage where a route reads an untyped param. | Path-id type coercion already yields clean `4xx` (18C cat. 8); untyped query reads are the gap. |
| Empty-string / whitespace-only values | Partially handled / Deferred | Low | Extend explicit empty/whitespace rejection (or documented normalization) beyond the fields 18B's blank-name guard already covers. | 18C cat. 6 covers blank `name`; other free-text fields rely on type/length guards, not an explicit whitespace rule. |
| Null-like / sentinel values (`"null"`, `"None"`, `"undefined"` as strings) | Deferred | Low | Decide and document whether these are treated as plain strings (current) or rejected; add coverage to lock the decision. | Currently treated as ordinary strings by Pydantic; low risk but worth an explicit, tested decision. |
| Malformed value normalization (mixed/odd encodings within accepted types) | Deferred | Low | Confirm odd-but-typed values normalize or reject without `500`; add targeted coverage. | Distinct from malformed-JSON (already `400`/`422`, 18C cat. 3) — this is well-formed JSON with hostile-shaped string values. |
| Consistent error-response behavior for edge cases | Partially handled | Medium | Assert that *new* edge-case guards return the **same** `{"detail": ...}` JSON shape and status conventions as existing guards. | The shape contract exists (18C cat. 3/10); 18E must conform to it, not invent a new error shape. |
| Internal exception leakage on edge cases | Handled (18B/18C) | — | Keep the global `500` handler as the backstop; new guards should fail *before* it as clean `4xx`. | 18C cat. 10 already locks no-leak `500`. New guards must not regress this. |
| Route-level defensive validation gaps | Deferred | Low–Medium | Inventory routes that read query/untyped input and add narrow per-route guards where a gap exists, rather than a global middleware. | See Route-Level Validation Boundaries below. |
| Auth / rate-limit edge cases (e.g. token abuse, request flooding) | Not applicable | — | None in current runtime. | Threat model §1: single-user, local, no network exposure, no auth. Out of scope until that model changes. |
| Persisted query-history edge cases | Blocked | — | Revisit when/if query persistence exists. | Threat model §5.3 / roadmap: `repeated_query` / `unresolved_question` stay blocked until persistence exists; their input edges are blocked with them. |

---

## Deep Nesting / Recursive Payload Risk

**Why this deserves its own planning pass.** A deeply nested JSON body
(`{"a":{"a":{"a": ...}}}`) is a structural attack on the *parser and any recursive
traversal*, not on a single field. The existing 18B guards are field-level
(type, length, presence) and cannot see request *shape*. A nesting-depth guard is
a different mechanism — it must run early, be bounded by a constant, and return the
same clean `422` the rest of the boundary uses. Bundling it into 18B would have
mixed a new structural mechanism into a field-validation pass and shipped it
without its own test matrix.

**Why it was not a Phase 18C regression.** 18C verifies behaviors that 18B
*implemented*. There was never a depth guard to regress; calling its absence a
"regression" would be dishonest. 18C correctly logged it as deferred (18C §6) and
left it for a deliberate phase.

**Suggested future handling (for 18E, not now).** A single bounded depth check on
POST bodies, with a small constant limit, rejecting over-depth as a clean `422`
before any deep traversal — plus a test that a body at the limit still succeeds
(mirroring 18B's at-limit acceptance test so no valid request regresses).

---

## Query Parameter Safety

**Why it deserves its own pass.** Query parameters are a separate untrusted
channel from the JSON body. They can be repeated, arrive with unexpected types,
carry injection-shaped strings, or be absurdly long/numerous. The threat model
(§5.1) and 18C (§6) both name them. They were **not** a 18C regression because
18B never added query-param validation — Hive|Mind's current routes are largely
body-driven and path-id-driven, so the query surface is small and was not the
highest-traffic edge 18B targeted.

**Current reality (keeps the risk honest).** The live runtime is local,
single-user, no-auth, no network exposure (threat model §1). A hostile query
string is owner-supplied against the owner's own instance. That makes query-param
risk **low-to-medium**, not critical — but still worth a small, explicit guard so
behavior is deterministic and documented rather than implicit framework default.

**Suggested future handling (for 18E, not now).**

- Inventory the routes that actually read query parameters (likely few).
- For each, validate type/shape and reject malformed values with a clean `422`/`400`.
- Add a request-level cap on query-string length and parameter count.
- Choose and document an explicit duplicate-key policy (first-wins or reject).
- Confirm none of these paths can reach a `500` or leak internals.

---

## Error Response Safety

**Why stable, predictable error responses matter for a security-facing backend.**
An error response is itself an output surface. Inconsistent error shapes leak
information (which guard fired, what the internal field name is, sometimes a
stack), and they make the client harder to write correctly. Hive|Mind already
standardized on `{"detail": ...}` JSON with conventional `4xx`/`5xx` codes, and
18C cat. 3 / 10 lock that the `500` path never leaks a traceback or path.

The 18D requirement on any future edge-case guard is therefore a **conformance**
requirement, not a new design: every new guard (depth, query-param, value
normalization) must return the *same* `{"detail": ...}` shape and the *same*
status conventions already in use, and must fail as a clean `4xx` *before* the
global `500` backstop. This keeps the boundary auditable: a reviewer can predict
the response for any malformed input without reading the handler.

---

## Route-Level Validation Boundaries

**Why future implementation should avoid broad middleware rewrites unless
justified.** The cheapest, most testable place to add a guard is usually the route
or model that owns the input — not a global middleware that intercepts every
request. A global middleware:

- changes behavior for *every* route at once, widening the blast radius of a bug;
- is harder to test in isolation (every test now traverses it);
- tends to grow into a catch-all that hides which route actually needs which guard;
- re-opens trust boundary #1 globally — the exact boundary 18B just closed
  carefully and 18C just verified.

The 18D recommendation is **narrow, per-route or per-model guards** (e.g. a depth
check applied where bodies are accepted, a query-param validator on the specific
routes that read query params), each with its own focused test. A global mechanism
should be introduced only if an inventory shows the same guard is genuinely needed
on enough routes that duplication outweighs the blast-radius cost — and even then,
it should be additive and individually testable, matching the additive-contract
discipline used across the intelligence phases.

**Why backend defensive validation should remain narrow and testable.** Each guard
should map to one named edge case, one clean status code, one test asserting
rejection, and (where a limit exists) one test asserting the at-limit value still
succeeds. This is how 18B stayed safe: additive, bounded, and regression-locked.
18E should inherit that shape exactly.

---

## Not In Scope Yet

The following are explicitly **not** Phase 18D work and **not** recommended for the
immediate next phase, to prevent scope creep:

- **Authentication / authorization edge cases.** No auth layer exists (threat
  model §1); there are no tokens, sessions, or roles to abuse. Not applicable until
  the runtime gains network exposure or multi-user access.
- **Rate limiting / DoS / request flooding.** Single-user local runtime; no
  network adversary in the test model. A rate limiter is new architecture aimed at
  a threat model that does not apply today (consistent with 18C §1 rationale).
- **Persisted query-history input edges.** Blocked until query persistence exists
  (threat model §5.3, roadmap Query Trails track). `repeated_query` /
  `unresolved_question` and their input edges stay blocked together.
- **Vulnerability scanner / automated fuzzing automation.** Out of scope per the
  threat model (§1) and 18C (§1); this track stays owner-authorized and
  hand-reviewed, not blind-automated.
- **Dependency / static / secret baseline.** Separate future track (threat model
  §5.5); findings reviewed before any change, never blind-fixed.
- **Obsidian filesystem path-safety matrix, intelligence evidence regression,
  frontend rendering safety.** Distinct future tracks (threat model §5.2/§5.3/§5.4),
  unchanged by this phase.

---

## Recommended Phase 18E Scope

**Phase 18E — API Edge Case Defensive Validation MVP** is the recommended next
phase. It is a **backend-focused implementation phase** that implements a *small,
selected* subset of the deferred edges above, each additive and regression-tested,
without a broad middleware rewrite.

Recommended 18E scope (narrow on purpose):

1. **Bounded request-body nesting-depth guard** on POST endpoints → clean `422`
   over the limit; at-limit body still accepted.
2. **Query-parameter safety** on the routes that actually read query params:
   type/shape validation, a request-level length/count cap, and an explicit,
   documented duplicate-key policy → clean `422`/`400`, never `500`/leak.
3. **Explicit empty/whitespace and null-like value decisions** for the small set
   of free-text fields not already covered by the 18B blank-name guard → documented
   and tested.
4. **Error-shape conformance** for every new guard: same `{"detail": ...}` JSON
   shape and status conventions; no new error format; no traceback/path leak.

Out of 18E scope: total-body-size byte ceilings beyond field/depth limits (can be
a follow-up if needed), any middleware, any auth/rate-limit/persistence work, and
the non-API tracks listed in *Not In Scope Yet*.

---

## Implementation Readiness Checklist

For **Phase 18E** (the implementing phase) — this is the definition of done 18E
should satisfy. Phase 18D does **not** implement any of it.

- [ ] Inventory of every route that reads query parameters and/or accepts a POST
      body, recorded in the 18E doc before code changes.
- [ ] Bounded nesting-depth guard added at the body-accepting boundary, with a
      named constant limit and a documented rationale for the value.
- [ ] Depth-guard tests: over-limit body → `422`; at-limit body → success (no valid
      request regressed).
- [ ] Query-param validation on the inventoried routes: malformed/oversized/excess
      → clean `422`/`400`; valid → unchanged behavior.
- [ ] Explicit, documented duplicate-query-key policy (first-wins or reject) with a
      test locking it.
- [ ] Query-string length and parameter-count caps with tests for the limit and
      the at-limit boundary.
- [ ] Empty-string / whitespace-only / null-like value decisions documented and
      tested for the targeted fields.
- [ ] Every new guard returns the existing `{"detail": ...}` error shape and
      conventional status code; a test asserts no traceback / path / internal text
      leaks (no regression of 18C cat. 10).
- [ ] No new edge-case path can reach an unhandled `500`; the global handler
      remains the backstop, not the primary path.
- [ ] Guards are per-route / per-model and individually testable; **no** global
      middleware unless an inventory justifies it and it is additive + tested.
- [ ] Full backend test suite passes; new tests added are listed and mapped to the
      threat-model §5.1 categories they cover.
- [ ] No new dependency, persistence, auth, rate limiter, scanner, frontend, or
      AI/LLM change is introduced.

---

## Guardrails Preserved

Phase 18D is documentation and planning only. This phase did **not**:

- add backend features, endpoints, validation code, or middleware;
- add or change any test;
- add frontend code or redesign the dashboard / UI or touch branding/assets;
- add AI/LLM behavior or embeddings;
- add authentication, authorization, or rate limiting;
- add a vulnerability scanner or automated scanning/fuzzing;
- add new dependencies, package files, or lockfiles;
- add database tables, persistence, or query history;
- mutate source / graph / intelligence behavior or rewrite the Obsidian importer;
- expand architecture or perform any security testing (no tests were run against
  the app in this phase; it is planning only).

The change set is documentation/planning only: this triage/planning document plus
narrow status updates to the roadmap and the threat-model future-phase section.

---

## Final Status

Phase 18D is **complete as a planning/triage pass**. The deferred API edge-case
items named by Phase 18C are now triaged into handled / deferred / not-applicable /
blocked buckets, risk-rated against the actual local single-user runtime, and
turned into a narrow, testable scope and readiness checklist for the next phase.

No claim is made that the deferred edge cases are mitigated today — they are
*organized and ready to implement*, not implemented. Security hardening of these
edges remains future work.

**Recommended next phase: Phase 18E — API Edge Case Defensive Validation MVP**
(backend implementation of the selected edges above, additive and regression-tested,
no middleware rewrite).
