# Phase 18A — Security Threat Model + Vulnerability Test Plan (status)

Parent label: **devdevbuilds**

Phase 18A is a **documentation / planning-only** phase. It introduces the
project's first dedicated security artifact: a threat model and a forward-looking
vulnerability test plan for Hive|Mind. It changes no backend logic, no frontend
behavior, no API contracts, no dependencies, no persistence, and no runtime
behavior.

The substantive content lives in
[Security Threat Model + Vulnerability Test Plan](../security/threat-model-and-vulnerability-test-plan.md).
This note is the lightweight phase-status pointer that matches the repo's
per-phase documentation convention.

## What 18A delivers

- A new `docs/security/` area with the threat model + vulnerability test plan.
- Owner-authorized, local-only defensive-testing scope (in-scope vs out-of-scope
  systems, local dev assumptions, explicit no-third-party-target guardrails).
- A system inventory of the security-relevant Hive|Mind systems.
- Documented trust boundaries (frontend→API, file path→import, vault content→
  records, records→derivation, exceptions→error messages, env/config→outputs).
- An attack-surface matrix (surface → example risk → planned test type → expected
  safe behavior).
- A vulnerability test plan organized into API negative testing, Obsidian import
  safety, Intelligence Report integrity, frontend safety, and dependency/static
  review — all as *planned* categories, none implemented.
- Pass/fail criteria for each test area.
- Future hardening phase recommendations (18B–18F).
- A guardrail-preservation statement.

## What 18A explicitly does not do

It implements no security fix, adds no auth/authorization/rate-limiting/input-
validation code, changes no backend/frontend/contract/dependency/persistence
behavior, alters no Obsidian import behavior, adds no AI/LLM, and mutates no
source/graph/store state. It makes no claim that Hive|Mind is hardened. See the
guardrail-preservation statement (§8) in the main document.

## Why now

Hive|Mind's read-only intelligence/reporting architecture is stable (Source
Registry, Obsidian import, Knowledge Graph, Intelligence Report, Temporal Decay,
Dreaming Suggestions, Provenance Chains, Query Trails). Writing the threat model
before any defensive testing turns later security work into reviewable
engineering with scope, intent, and pass/fail criteria — rather than ad-hoc
poking — and keeps that work owner-authorized and local-only.

## Recommended next phases

`18B` Backend API defensive validation + error safety · `18C` Obsidian import
filesystem safety hardening · `18D` Temporal Decay / intelligence evidence
regression hardening · `18E` Frontend rendering safety + error-state hardening ·
`18F` Dependency / static security baseline. These are recommendations only; see
§7 of the main document.
