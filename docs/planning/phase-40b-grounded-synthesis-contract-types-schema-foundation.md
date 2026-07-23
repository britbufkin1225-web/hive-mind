# Phase 40B — Grounded Synthesis Contract Types + Schema Foundation

**Type:** Backend contract and schema phase. **Runtime behavior added:** none.
**Status:** implemented, Codex-hardened, and locally test-covered; pending final
independent audit (Jules) and the devdevbuilds human merge gate.

**Parent label:** devdevbuilds (human decision-maker and merge gate).
**Composition mode:** `sequential-isolated`.

---

## 1. Purpose

Translate the Phase 40A [Grounded Synthesis Layer architecture](../create-layer-architecture.md)
into a bounded, deterministic, versionable backend contract foundation.

Phase 40B establishes the structural vocabulary that future Grounded Synthesis
capabilities require. It **implements no synthesis behavior**. It is the same
contract-first move that anchored the Active Memory track (Phase 37B,
`active-memory.v1`) and the Repository Observer track (Phase 37I,
`repo-observer.v1`): settle the typed, versioned shapes before any service
consumes them.

*Musings* and *The Loom* appear only as capabilities **within** the Grounded
Synthesis Layer — a synthesis mode and, for Musings, an artifact category. They
are not top-level architectural layers.

## 2. What was added

One backend contract module and one focused test module:

- `apps/backend/app/models/grounded_synthesis.py` — the `grounded-synthesis.v1`
  contract family.
- `apps/backend/tests/test_grounded_synthesis_contracts.py` — 58 focused
  contract, validation, determinism, and boundary-separation tests.

Documentation updates are narrow: this plan, the roadmap, the README, and two
bounded notes in the Phase 40A architecture document.

### 2.1 Contract family

| Contract | Responsibility |
| --- | --- |
| `GROUNDED_SYNTHESIS_CONTRACT_VERSION` | The fixed wire version `grounded-synthesis.v1`. Every top-level record carries it and rejects any other value. |
| `GroundedSynthesisMode` | The bounded mode vocabulary: `musings`, `loom`. Unsupported values fail validation. |
| `SynthesisArtifactCategory` | Closed catalog of proposed output categories from the Phase 40A §1.1 target list, plus `musing`. |
| `GroundingEvidenceKind` | Which existing Hive|Mind subsystem holds a piece of grounding (repository observation, drift finding, Active Memory record/evidence record, contradiction record, context-packet entry, knowledge-graph node, source-registry entry, query trail). |
| `SynthesisReadinessStatus` | Bounded readiness vocabulary: `draft`, `context_required`, `ready`, `insufficient_evidence`, `blocked`, `proposed`, `validation_failed`, `human_review_required`. |
| `SynthesisGenerationMethod` | Single-member enum (`deterministic`). |
| `SynthesisConstraints` | Declared limits plus safety flags a future service must honor. |
| `GroundingEvidenceReference` | A normalized, bounded pointer at one existing piece of evidence. |
| `SynthesisContextSummary`, `SynthesisEvidenceConflict`, `SynthesisMissingContext`, `SynthesisSourceCoverage`, `SynthesisWarning` | The bounded parts of a context packet. |
| `SynthesisContextPacket` | The passive input boundary assembling already-produced grounding. |
| `GroundedSynthesisRequest` | The typed, versioned synthesis request. |
| `SynthesisProvenance` | How a proposed artifact is grounded — mandatory, never optional. |
| `GroundedSynthesisArtifactSection`, `GroundedSynthesisArtifact` | The **proposed** output, explicitly distinct from accepted state. |
| `SynthesisValidationIssue`, `SynthesisValidationResult` | An explicit, non-coercing validation verdict. |
| `derive_grounded_synthesis_id` | A pure identifier helper (SHA-256 over normalized inputs), following the existing `_stable_id` convention. |

## 3. Design decisions and rationale

### 3.1 Follow the existing contract style; add no dependency

The module uses `StrEnum` wire vocabularies, Pydantic `BaseModel`, `Field`
bounds, `field_validator`/`model_validator` checks, and named `MAX_SYNTHESIS_*`
limits — identical to `active_memory.py` and `repository_workspace.py`. It
introduces no new modeling style and no new dependency.

Placement is `app/models/`, the repository's canonical location for contract
families, rather than a new top-level package. Keeping the family in one cohesive
module (rather than splitting contracts and validation across files) matches how
`active_memory.py` and `repository_observer.py` are organized.

### 3.2 Reuse existing vocabularies rather than duplicating them

`EvidenceType`, `EvidenceReference`, `MemorySource`, `MemoryScope`,
`ConfidenceBand`, and `ContradictionSeverity` are imported from
`active-memory.v1`. Re-declaring them would create two vocabularies that could
drift apart, and Phase 40A §3.4 explicitly makes the Grounded Synthesis Layer a
consumer of the same evidence discipline rather than a parallel one. The only new
vocabulary is `GroundingEvidenceKind`, which names the *producing subsystem* — a
distinction no existing enum captures.

Metadata nesting reuses the Phase 18E `assert_within_nesting_depth` guard rather
than a second depth checker.

### 3.3 Proposed, never accepted — enforced structurally

The distinction is enforced by the schema, not by convention:

- `SynthesisReadinessStatus` contains **no** accepted/approved/canonical/
  committed/merged/applied/published value, and a test asserts those strings
  never appear in the vocabulary.
- `GroundedSynthesisArtifact.status` is restricted to the proposal-only subset
  (`PROPOSED_ARTIFACT_STATUSES`); request-lifecycle states are rejected on an
  artifact.
- `human_review_required` and `read_only` default to `True` and **reject** being
  set to `False`, on both the artifact and the constraints. Together with
  `prohibit_repository_writes` and `prohibit_graph_mutation`, these are not
  tunables — a request cannot declare itself exempt from the Phase 40A §8
  boundary.

### 3.4 Provenance is mandatory, and citations cannot outrun it

`GroundedSynthesisArtifact.provenance` is a **required** field. Beyond presence,
cross-field validation requires that:

- `provenance.request_id` matches the artifact's `request_id`;
- every artifact citation and every section evidence id appears in
  `provenance.used_evidence_ids`;
- a `proposed` artifact has non-empty provenance evidence and non-empty
  citations;
- an evidence id is never both used and excluded.

This is the contract-level expression of "evidence before synthesis"
(Phase 40A §6): an artifact cannot claim grounding its audit trail does not
support.

### 3.5 Insufficient evidence is data, not an empty collection

An empty or gap-bearing `SynthesisContextPacket` cannot declare itself `ready`,
and an ungrounded `GroundedSynthesisRequest` cannot declare a grounded status. A
packet's summaries and conflicts must reference evidence the packet actually
carries — a dangling reference is a malformed packet, not a warning.
`SynthesisMissingContext` makes a gap an explicit, named record rather than an
inference from absence.

`SynthesisValidationResult` holds the invariant `status == valid` **iff**
`issues == []`. There is no "valid with problems" state, so a degraded result can
never be read as a passing one, and malformed input is never coerced into a valid
state.

### 3.6 Determinism by construction

Nothing in the module reads a clock, generates a random identifier, touches the
filesystem, runs Git, queries a store or database, or calls a network or model
provider. Every timestamp (`submitted_at`, `assembled_at`, `observed_at`,
`created_at`) and every identifier is caller-supplied and defaults to `None`.
`derive_grounded_synthesis_id` is a pure function of explicitly normalized
inputs. It hashes canonical JSON array material rather than a delimiter-joined
string, so input boundaries remain unambiguous even when content contains a
separator; NFC normalization makes Unicode-equivalent inputs stable.

Collection ordering is caller-preserved, with an explicit
`SynthesisContextPacket.normalized()` returning the canonical ordering — the same
pattern as `RepositoryWorkspaceConfig.normalized()`. Normalization is idempotent
and does not mutate the original.

### 3.7 No provider-specific configuration can enter the contracts

Every model sets `model_config = ConfigDict(extra="forbid")`. That is the
load-bearing setting: no model name, provider, temperature, `top_p`, token
budget, prompt template, credential, or agent execution directive exists as a
field, and none can ride in on an unknown key or a nested metadata key.
`SynthesisGenerationMethod` has a
single member (`deterministic`), so a model-backed producer cannot be recorded as
legitimate provenance without a deliberate, reviewable contract change
(Phase 40A §11).

### 3.8 Bounded input at every edge

Named limits cover identifier length, objective length, summary length, section
heading/body length, total artifact content length, evidence-reference count,
context-summary count, conflict count, missing-context count, warning count,
citation count, artifact-section count, unresolved-claim count, validation-issue
count, metadata entry count, nested metadata container width and total nodes,
metadata key/value length, and metadata nesting depth. Non-finite and non-JSON
metadata values are rejected. Collection bounds are deliberately smaller than
the Active Memory ceiling:
a grounding packet is a curated, human-reviewable selection, not a dump.

Defensive coercion is blocked in both directions — a `bool` supplied where an
integer limit is expected is rejected, and an `int` supplied where a safety flag
is expected is rejected.

## 4. Validation performed

- Focused suite: `python -m pytest tests -k "grounded_synthesis or synthesis_contract" -q`
  — **58 passed**.
- Neighboring regressions (contracts, Active Memory, context packets, provenance,
  Repository Observer, repository evidence projection, workspaces):
  `python -m pytest tests -k "contract or active_memory or context_packet or provenance or repository_observer or repository_evidence or workspace" -q`
  — **486 passed**.
- Full backend suite: `python -m pytest -q` — **772 passed** (714 before this
  phase), no failures or skips. The environment emits one Starlette/httpx
  deprecation warning and one permission warning for the untracked
  `.pytest_cache`; neither affects results.
- `git diff --check` — clean. Conflict-marker scan — none.

Test coverage spans valid construction for both modes and every top-level
contract; invalid construction (unsupported mode, unsupported schema version,
blank/whitespace identifiers and objective, missing provenance, ungrounded
`ready`/`proposed` claims, dangling references, duplicate identifiers,
conflicting identifiers, over-long content, oversized/deeply-nested metadata,
invalid artifact status, malformed evidence type, non-hex digest, negative
limits, booleans as integers, disabled safety flags, unknown extra fields,
mutable default leakage); determinism (stable enum wire values, byte-stable
serialization, deterministic `normalized()` ordering, round-trip equality, pure
identifier derivation, no auto-populated clock or identifier); and boundary
separation (an AST-level assertion that the module imports no I/O or
nondeterminism module and calls no I/O or clock function, a runtime assertion
that every contract constructs with `open`/`subprocess`/`socket` poisoned, and an
assertion that the family exposes no persist/apply/synthesize/export/approve
surface).

## 5. Explicit non-scope

Phase 40B adds **none** of the following: synthesis behavior, a producer,
grounding assembly, evidence lookup or resolution, a policy engine, an API
endpoint, a frontend component or style, persistence, a database schema or
migration, a repository write, a Git write operation, a graph mutation, an Active
Memory insertion, source ingestion, Repository Observer behavior change, Query
Trail persistence, an autonomous agent, orchestration, a background worker, a
scheduled job, authentication, authorization, a dependency change, a lockfile
change, build or deployment configuration, a screenshot, or a design asset. No
AI or LLM provider is integrated. Phase 36K remains paused and untouched.

## 6. Deviation from the Phase 40A proposal

Phase 40A §6 proposed 40B as backend contracts **plus** a mirrored frontend
TypeScript type set and a parity test. The Phase 40B brief scopes this phase to
the backend and prohibits frontend changes, so no frontend mirror or parity test
was added. This is recorded rather than silently absorbed: the mirror remains a
legitimate, still-open item for a later phase, and the backend contract is the
authority in the meantime.

Naming also settled differently from the Phase 40A conceptual vocabulary — the
implemented grounding boundary is `SynthesisContextPacket` (40A's
`GroundingPacket`) and the implemented output is `GroundedSynthesisArtifact`
(40A's `SynthesisResult`). Phase 40A §12.4 explicitly delegated exact schema
names to 40B. `LoomContext`, `ArtifactExport`, and `ReviewRecord` remain
unimplemented; export and review records belong to Phase 40F.

## 7. Multi-agent composition

Composition mode: `sequential-isolated`. Agents must not perform overlapping
repository writes simultaneously.

| Order | Agent | Role |
| --- | --- | --- |
| 1 | Claude Code | Primary implementer (this commit). |
| 2 | Codex | Architecture and schema reviewer. |
| 3 | Jules | Final independent auditor and bounded hardener. |
| — | Antigravity | Offline and unassigned; not participating in this phase. |
| 4 | devdevbuilds | Human merge gate. |

Auditing agents must not amend, squash, or rewrite the primary implementation
commit. Any justified hardening lands as a separate commit identifying the
reviewing agent. No agent may push, open a PR, merge, delete branches, or modify
`main` unless explicitly instructed by devdevbuilds.

## 8. Known limitations

- The contracts are shapes only; nothing validates a *request against a specific
  workspace*, resolves evidence, or checks freshness — those are 40C/40D.
- `SynthesisSourceCoverage.referenced_count` is caller-supplied and is not
  cross-checked against the packet's own reference list; deriving coverage is an
  assembly-service concern.
- No frontend mirror exists yet, so there is no backend/frontend parity test for
  this family (see §6).
- Phase 40A's richer failure vocabulary (§9) is only partially represented:
  40B covers the contract-edge failures (invalid request, insufficient evidence,
  unsupported mode/category, conflicting evidence, constraint violation,
  malformed reference, missing provenance, duplicate reference, bounds
  exceeded). Runtime failure states such as `workspace_unavailable`,
  `stale_baseline`, `producer_failed`, `export_failed`, and `result_stale`
  belong to the phases that can actually produce them.

## 9. Recommended next phase

**Phase 40C — Grounding Context Assembly Service MVP.** A backend-only,
deterministic, read-only service that assembles a `SynthesisContextPacket` from
already-observed evidence over the Phase 40B contracts. No persistence, no
mutation, no AI/LLM, no endpoint expansion beyond a thin boundary.

Phase 40C is **not started**.

## 10. Reference documents

- [Grounded Synthesis Layer architecture](../create-layer-architecture.md)
- [Phase 40A plan](phase-40a-create-layer-foundation-project-cohesion.md)
- [Roadmap](../roadmap.md)
- [Active Agent Memory + Verification Layer reference](../active-agent-memory-verification-layer.md)
- [Repository Observer operator workflow](../operator-repository-observer.md)
- [Agent Lab contribution governance](../agent-lab/README.md)
- [README](../../README.md)
