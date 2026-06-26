# Hive|Mind — Phase 13C Temporal Decay QA + Demo Evidence

Parent label: **devdevbuilds**

## Purpose

This note records the end-to-end QA pass for the Temporal Knowledge Decay
feature after it became backend-derived (Phase 13A) and demo-visible (Phase
13B). It is **verification and evidence only** — no feature, contract,
persistence, or graph-mutation changes were made in Phase 13C. The only code
change is documentation/status-language updates (including a router docstring);
all behavior is unchanged.

For context, see the [Roadmap](../roadmap.md),
[Intelligence Surface Plan](../intelligence-surface-plan.md),
[API Contract](../api-contract.md), and [Demo Guide](../demo-guide.md).

## What was verified

- **Backend-derived, not fixture.** `GET /api/intelligence/report` returns
  `decay_statuses` produced by `app.services.temporal_decay.derive_decay_statuses`
  (`app/services/intelligence.py`). Every decay row carries
  `metadata.derived = true` and a human-readable `reason`; none carry
  `metadata.fixture`. Verified live against the seeded store: 7 decay rows, all
  `derived`, none `fixture`.
- **Other sections remain honest fixtures.** Dreaming suggestions, provenance
  chains, and query-trail entries are all still `metadata.fixture = true`
  (deterministic demo data) pending their own phases.
- **Read-only.** The report carries `read_only = true`; the builder and the
  derivation are pure projections over store state. `derive_decay_statuses` only
  reads `store.get_nodes()` / `store.get_sources()` and never mutates nodes,
  sources, edges, imports, or persisted knowledge. Repeated calls are
  byte-for-byte identical (covered by
  `test_derivation_is_repeatable_and_read_only`).
- **Frontend labelling.** The Intelligence Report panel
  (`apps/frontend/src/components/IntelligenceReportPanel.tsx`) tags the Temporal
  Decay section **"Backend-derived"** (via `isDerivedRecord`) and the remaining
  sections **"Demo data"** (via `isFixtureRecord`), surfacing each row's bucket,
  `reason`, `age_days`, review flag, and source-reliability hint.

## Bucket coverage

The four status paths — **fresh / aging / stale / unknown** — are fully exercised
by deterministic unit tests in `apps/backend/tests/test_temporal_decay.py`
(boundary cases at the inclusive 30-day and 90-day thresholds, the
no-usable-timestamp `unknown` path, most-recent-signal selection, source
reliability hints, and stable ordering).

In the **live seeded demo**, all nodes share `MOCK_NOW = 2026-06-23`
(`apps/backend/app/mock/mock_data.py`), so against a near-current wall clock they
currently classify as **fresh** (age ~2 days). As real time advances past the
thresholds the same seed nodes age into **aging** (after 30 days) and **stale**
(after 90 days) with no code change — the derivation is purely timestamp-driven.
For a screenshot showing non-fresh buckets, capture after those windows or seed a
node with an older timestamp; the unit tests already prove all four paths.

## Validation

- `npm run build --workspace apps/frontend` — succeeds (clean `tsc -b` + Vite
  build).
- `python -m pytest apps/backend/tests` — 179 passed.

## Guardrails confirmed

No new backend intelligence logic, no new frontend feature systems, no API
contract changes, no persistence changes, no graph-mutation behavior, no
Dreaming/Provenance/Query-Trail implementation, no new dependencies, no dashboard
redesign, and no branding/asset changes. Phase 13C is QA plus documentation
status-language only.
