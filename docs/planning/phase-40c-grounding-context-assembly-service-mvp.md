# Phase 40C — Grounding Context Assembly Service MVP

Backend-only, deterministic, read-only assembly of existing Hive|Mind evidence
into valid Phase 40B `SynthesisContextPacket` records.

- Service: [`apps/backend/app/services/grounding_context.py`](../../apps/backend/app/services/grounding_context.py)
- Tests: [`apps/backend/tests/test_grounding_context.py`](../../apps/backend/tests/test_grounding_context.py)
- Contracts reused: [`apps/backend/app/models/grounded_synthesis.py`](../../apps/backend/app/models/grounded_synthesis.py) (Phase 40B, unchanged)

## 1. Purpose

Phase 40C answers exactly one question:

> Given an eligible grounding request and the evidence Hive|Mind already holds,
> what bounded, traceable context packet should a future synthesis process
> receive?

It establishes the **grounded input boundary** for the Grounded Synthesis Layer.
The packet is the deliverable. Nothing is generated from it in this phase.

**Rationale — why assembly is separated from synthesis.** Collecting, filtering,
ranking, bounding and packaging evidence is a deterministic, auditable
transformation; producing prose from that evidence is not. Splitting them means
the grounded input boundary can be reviewed, tested and trusted *before*
anything is ever generated from it — and a later generative stage cannot quietly
widen its own grounding, because it does not assemble it.

## 2. What was added

A single service module exposing a small explicit interface:

```python
class GroundingContextAssemblyService:
    def assemble(
        self,
        request: GroundedSynthesisRequest,
        *,
        evidence: GroundingEvidenceSources,
        assembled_at: datetime | None = None,
    ) -> SynthesisContextPacket: ...
```

plus `assemble_grounding_context(...)`, mirroring the existing
`project_repository_evidence` / `build_context_packet` entry-point convention.

No endpoint, persistence, cache, packet history, background worker, dependency,
frontend surface, or contract change was added. The Phase 40B models are reused
exactly as published; **no Phase 40B compatibility correction was required.**

**Rationale — why the core is pure.** `assemble` takes the request, an explicit
`GroundingEvidenceSources` bundle the caller has already obtained from the
existing read-only providers, and an explicit `assembled_at`. Provider *access*
stays with the caller; provider *interpretation* lives in the service and is
independently testable from fixtures. A service that reached into stores itself
could not be proven deterministic, and would couple the grounded input boundary
to store availability.

**Rationale — why the service is read-only and non-persistent.** It holds no
state between calls, caches no packet, and writes nothing. A cached or persisted
packet would become a second source of truth about grounding that could drift
from the evidence, and packet history is a Phase 40F/40E concern with its own
review semantics.

## 3. Deterministic pipeline

```text
existing provider records (caller-supplied)
      ↓  collection
normalization into GroundingEvidenceReference
      ↓  eligibility filtering
deterministic deduplication
      ↓  stable ranking
bounded selection (per-family, then packet)
      ↓  conflict / gap / coverage construction
readiness evaluation
      ↓
SynthesisContextPacket
```

Nothing in the module reads a clock, generates a random identifier, calls a
network or model provider, runs Git, touches the filesystem, enumerates a
directory, queries a store, or mutates anything. A structural test parses the
module's AST and fails on any `os`/`random`/`uuid`/`time`/`subprocess`/`socket`/
`urllib`/`pathlib` import or any `now`/`utcnow`/`uuid4`/`random`/`open`/`getenv`
call.

## 4. Evidence sources

### Implemented in the MVP

| `GroundingEvidenceKind` | Source record | Why it is included |
| --- | --- | --- |
| `active_memory_evidence_record` | `EvidenceRecord` | Already *is* a typed evidence reference (`EvidenceType` + bounded `EvidenceReference` + scope + source + capture time); normalizes one-to-one. |
| `repository_observation` | `RepositorySnapshot.evidence` | Bounded, deterministic, digest-bearing observations carrying a declared `EvidenceAuthority` — a real authority axis rather than a guessed one. |
| `repository_drift_finding` | `RepositoryDriftAnalysis.evidence` | Same shape, derived against a baseline. |
| `contradiction_record` | `ContradictionRecord` | The only family that can make a packet *unsafe* to synthesize from. Excluding it would let a packet look cleaner than the evidence is. |
| `active_memory_record` | `MemoryRecord` | The project's own claims: weakest as grounding, indispensable as context. |

**Rationale — why this set is appropriate for the MVP.** Every one of these five
already carries the Phase 37A/40B grounding vocabulary — evidence type, bounded
evidence reference, source identity, scope, confidence band, contradiction
severity — so each normalizes without inventing anything. Together they cover the
repository (observed state and drift), the project's asserted knowledge, its
supporting evidence, and its known conflicts: the full span a synthesis stage
would need, with no fabricated coverage.

### Deliberately deferred

| Family | Why deferred |
| --- | --- |
| `context_packet_entry` | The Phase 37E `ContextPacket` is an aggregate of the memory and contradiction records already covered. Admitting it would enter the same underlying records twice under a second canonical identity, which deduplication cannot collapse and which would inflate coverage counts. |
| `knowledge_graph_node` | `HiveGraphNode` carries no evidence type, no bounded evidence reference, no scope, no confidence band, and no verification standing. |
| `source_registry_entry` | `SourceRecord` likewise carries none of the grounding vocabulary. |
| `query_trail` | `QueryTrailEntry` is explicitly contract-only over query history that is not persisted. |
| Dreaming suggestions, decay statuses, provenance chains | Derived *advisory views* over graph records rather than observations, and `GroundingEvidenceKind` has no member for them — adding one would be a Phase 40B contract expansion, not a Phase 40C assembly concern. |

Normalizing any of these would require inventing evidence type, reference kind,
scope, and confidence mappings — precisely the fabricated-grounding failure the
Grounded Synthesis Layer exists to prevent. They remain available to a later
phase that first gives them evidence semantics.

A caller-supplied `request.evidence_references` entry is admitted as a candidate
in its own right (it is already a valid Phase 40B grounding reference) but ranks
below every provider family, so a provider-held copy always wins the duplicate
contest.

## 5. Normalization policy

Each candidate becomes one `GroundingEvidenceReference` retaining a stable
evidence id, grounding kind, originating provider source, source record id,
scope, bounded label and summary, freshness, confidence where the record
declares one, content digest where one is available, and a small closed-enum
metadata bag.

**Rationale — why raw provider payloads are never copied.** Bounded excerpts,
absolute repository roots, remote URLs, command output, and free-form provider
metadata bags stay where they are. Packet metadata carries only closed-enum
scalars and counts, so a credential, token, or machine-specific path has no route
into a packet. A caller's own metadata bag is likewise not passed through: it has
already satisfied Phase 40B bounds, but copying it would make packet metadata a
pass-through channel rather than assembly-controlled diagnostics.

Two normalization choices are deliberately conservative:

- A `MemoryRecord` gets `evidence_type=None`. A claim is not evidence of itself,
  and choosing any `EvidenceType` for it would assert proof the record does not
  carry.
- Repository evidence gets `confidence=None`. No confidence is *calculated*
  anywhere in Hive|Mind (Phase 37A §6.3, Phase 39A); inventing one here would be
  a computed trust score.

Repository observer evidence categories map to the Active Memory hierarchy
through one explicit table; categories with no honest counterpart
(`exclusion_record`, `externally_supplied_claim`, `unsupported_data`) map to
`None` rather than to a plausible-looking neighbour — an unknown evidence type is
better than a wrong one.

Pointer selection prefers a repository-relative path, then the commit hash, then
the branch, then the snapshot/drift artifact id. Absolute roots and remote URLs
are never used: they are machine-specific and can carry credentials.

## 6. Eligibility and filtering

| Rule | Exclusion reason |
| --- | --- |
| Evidence family outside `SUPPORTED_GROUNDING_KINDS` | `unsupported_evidence_kind` |
| Candidate declares a scope different from the request's | `out_of_scope` |
| No stable source identity or no usable reference value | `missing_grounding_fields` |
| Memory record lifecycle is not `active` | `not_active_lifecycle` |
| Memory record verification is `unresolvable` | `unresolvable_verification` |
| Repository identity is `unsafe_location` / `mismatched_root` / `mismatched_remote` | `unsafe_repository_identity` |
| Observer authority is `unsupported_assumption` / `unavailable_information` | `ungrounded_authority` |
| Observer evidence truncation state is `omitted` | `omitted_content` |
| Loses a duplicate contest | `duplicate_evidence` |
| Removed by a packet or per-family bound | `bounds_exceeded` |

Three of these carry rationale worth stating explicitly:

- **Absence of scope is not evidence of being out of scope.** Only a candidate
  declaring a *different* scope is excluded. Contradiction records carry no scope
  at all; excluding them under a scoped request would hide exactly the conflicts
  a scoped packet most needs to surface.
- **`contradicted` records are kept; only `unresolvable` is dropped.** Dropping a
  contradicted record would remove one side of a conflict the packet is required
  to surface. `unresolvable` means no evidence can settle the claim, so it can
  ground nothing.
- **Non-`active` lifecycle states are excluded.** Superseded, stale, retracted
  and inactive records are explicitly not the current baseline, and Phase 39A
  projects every repository-derived candidate as `inactive` — grounding on those
  would treat an unactivated projection as accepted project truth.
- **Lifecycle and verification are read from the candidate's own normalized
  metadata**, never from a shared index, so a caller-supplied reference reusing a
  provider record id cannot inherit that record's standing.

## 7. Deduplication

Key: `(grounding_kind, NFC-normalized source record id)` — the provider's own
stable identity. Never Python object identity, never `hash()`, never set
iteration order, never a serialized blob whose representation could shift.

Winner precedence, in order:

1. participation in an open **critical** contradiction;
2. declared **provider authority** (§8);
3. **confidence** band;
4. **freshness**, newest first;
5. the candidate's canonical hash material as a stable lexical tie-break.

Cross-family collapsing is deliberately *not* attempted: two families referring
to the same underlying fact do so under different evidence semantics, and merging
them would be an invented equivalence. The deduplicated set is emitted in sorted
canonical-key order so dict insertion order — the only place input order could
otherwise leak — cannot influence the result.

## 8. Ranking and tie-breaks

Sort key, ascending:

1. participation in an open critical contradiction;
2. whether the request named the evidence directly;
3. declared provider authority = `family_base + within_family_offset`;
4. confidence band (`high` < `medium` < `low` < none);
5. freshness, newest first, undated last;
6. canonical evidence family;
7. the derived evidence identifier.

Family bases are spaced by 20 so a family's own offsets can never cross into the
next family's band:

| Family | Base | Offset source |
| --- | --- | --- |
| `active_memory_evidence_record` | 0 | `EvidenceType` declaration index |
| `repository_observation` | 20 | `EvidenceAuthority` |
| `repository_drift_finding` | 40 | `EvidenceAuthority` |
| `contradiction_record` | 60 | `ContradictionSeverity` |
| `active_memory_record` | 80 | `VerificationState` |
| caller-supplied request reference | 160 | `EvidenceType` or "untyped" |

**Rationale — why these ranks are deterministic.** Every input is a *declared
field on a real record*: never a computed score, never a heuristic, never a
clock- or environment-derived value, never an LLM judgement. Evidence records
lead because `EvidenceType` **is** the repository's canonical claim-relative
strength hierarchy (Phase 37A §6.1) and reusing it avoids inventing a second,
competing one. Repository observations follow as direct, re-verifiable,
digest-bearing evidence; drift findings after them because drift is derived
*from* an observation; contradiction records next as structural signals *about*
other evidence; memory records last among providers because a claim is context,
not proof of itself. Criticality is evaluated ahead of authority, so a critical
conflict still leads the packet regardless of family.

The final tie-break is the derived evidence id — a pure function of the
candidate's canonical material — so ordering is stable across processes and never
depends on `hash()` randomization or input order.

## 9. Bounds and truncation

`GroundingAssemblyLimits` is validated at construction and every default sits at
or below its Phase 40B counterpart, so a packet built with the defaults can never
be rejected for exceeding a contract bound.

| Limit | Default | Purpose |
| --- | --- | --- |
| `max_raw_candidates` | 1024 | Total collection guard |
| `max_evidence_items` | 128 | Packet items (`MAX_SYNTHESIS_EVIDENCE_REFERENCES`) |
| `max_items_per_kind` | 48 | Per-family contribution |
| `max_conflicts` | 64 | Packet conflicts |
| `max_missing_context` | 64 | Packet gaps |
| `max_warnings` | 64 | Packet warnings |
| `max_label_length` / `max_summary_length` | 512 / 2048 | Bounded text |

The request's own `constraints.max_evidence_references` always wins when it is
stricter: a caller may narrow the packet, never widen it past the contract.

**Rationale — why a per-family cap exists.** A packet of 128 repository
observations is not grounded context, it is a repository dump, and it would push
every contradiction and every project claim out of the packet on count alone. The
cap is **lifted when only one family produced eligible evidence**, because there
is then nothing for it to crowd out — that is the single-provider scoping case,
expressed through the evidence actually available rather than through a request
field the Phase 40B contract does not define.

**Rationale — why raw candidate overflow fails closed.** Discarding raw
candidates *before* eligibility and criticality are known could silently remove a
critical conflict. `GroundingCandidateOverflowError` tells the caller to narrow
the request instead — the same choice Phase 37E made in
`ContextPacketTruncationUnsupportedError`.

Every truncation is represented, never silent: a `bounds_exceeded`
`SynthesisWarning` per packet-level and per-family omission, an aggregated
warning for text truncation, and counts in packet metadata. Text truncation keeps
the leading characters and marks the cut with a single ellipsis so the result is
stable and visibly incomplete. Warning overflow keeps the first N in canonical
order and replaces the tail with one explicit "N additional warning(s) omitted"
notice.

**Critical evidence is never silently lost.** Critical-conflict participants rank
first, so bounds remove them last; if a bound removes one anyway, readiness
becomes `blocked` and a `bounds_exceeded` warning names the count.

## 10. Packet construction and identity

The packet is constructed in ranking order — `normalized()` is deliberately *not*
called, because it re-sorts by evidence id and would destroy the meaningful,
deterministic ranking. Conflicts, gaps, coverage and warnings are each emitted in
their own canonical order.

`packet_id` is derived through the Phase 40B
`derive_grounded_synthesis_id("gs-packet", …)` helper over canonical JSON of:
assembly version, schema version, request id, correlation id, mode, readiness,
`assembled_at`, the **ordered** evidence ids, conflicts, gap ids, coverage, and
warnings.

**Rationale.** Folding the *ordered* evidence ids in means a reordered packet is
a different packet. Folding the assembly version in means a packet built under
different assembly rules can never collide with one built under these. Folding
`assembled_at` in means two assemblies of identical evidence at different
declared times do not share an id. Nothing random, clock-read, or
environment-derived participates, so identical material always yields the same
id.

If `request.context_packet_id` is set and does not equal the derived id, the
service raises `GroundingPacketIdentityError`: returning a differently-identified
packet under the caller's declaration would misrepresent what the request was
grounded on.

`context_summaries` is always empty. A summary spanning several evidence records
is synthesis, and an unattributed narrative has no place inside the grounded
input boundary.

## 11. Readiness

First-match rules, strongest failure first:

| Order | Outcome | Condition |
| --- | --- | --- |
| 1 | `blocked` | unsafe repository identity, unrepresentable critical conflict, or truncated critical evidence |
| 2 | `blocked` | a represented conflict with `critical` severity |
| 3 | `insufficient_evidence` | no eligible evidence |
| 4 | `context_required` | requested evidence is missing from the packet |
| 5 | `ready` | evidence present, no gaps, no critical conflict |

Warnings never downgrade `ready` — "ready with warnings" is exactly a ready
packet carrying warnings — but they are always carried, and
`metadata.readiness_reason` distinguishes `ready` from `ready_with_warnings`.

**Rationale — why these rules protect a future synthesis stage.** The ordering is
the point: a blocker outranks emptiness, emptiness outranks a gap, and only a
packet with evidence, no gaps, and no critical conflict may call itself `ready`.
A downstream producer can therefore branch on one field and never has to
re-derive whether its grounding was trustworthy. This matches the Phase 40B
contract exactly — an ungrounded, gap-bearing, or critically-conflicted packet
cannot be `ready` — so the service can never produce a packet the contract would
reject.

## 12. Critical-conflict behavior

Conflicts are **surfaced, never resolved**: no winner is chosen and no
participant is dropped. Only `open` contradictions count — a resolved or archived
contradiction is history, and treating it as a live blocker would permanently
block every packet once any conflict had ever existed.

A contradiction whose participants are not both present cannot be expressed as a
packet conflict (the Phase 40B contract requires at least two known evidence
ids), so it becomes an explicit `conflicting_evidence` warning and, when
critical, a readiness blocker. That is the difference between "we could not
represent this" and silently losing it.

Representable conflicts exceeding `max_conflicts` raise rather than clip.

## 13. Diagnostics

Carried in packet metadata — bounded, ordered, and secret-free:

`assembly_version`, `request_mode`, `candidates_inspected`,
`candidates_accepted`, `candidates_excluded`, `duplicates_removed`,
`items_truncated`, `text_truncations`, `critical_conflict_count`,
`readiness_reason`, `exclusion_reasons` (counts keyed by closed reason code), and
`unsupported_evidence_kinds`.

`SynthesisSourceCoverage` records one entry per family that *offered* a
candidate, with the count it actually contributed. Zero-count entries are kept
deliberately: a family that offered evidence and contributed none is materially
different from a family that was never consulted, and only the explicit zero
makes that visible.

Every metadata value is a count, a closed-enum literal, or a fixed slug. No path,
remote, credential, environment value, excerpt, or provider payload can reach the
bag, and the shallow shape stays well inside the Phase 40B metadata entry,
container, depth and node bounds. No forbidden provider/runtime key
(`model`, `prompt`, `api_key`, `temperature`, `provider`, …) is ever produced.

## 14. Tests

71 focused tests in `apps/backend/tests/test_grounding_context.py` covering basic
assembly and contract validity, determinism (identical input, shuffled input,
packet-id stability and change, lexical tie-breaks, Unicode-equivalent
identifiers), request validation, filtering (scope, lifecycle, verification,
unsupported families, ungrounded authorities, omitted content, unsafe repository
identity), deduplication (winner precedence, order independence, provider vs.
caller), bounds (raw-candidate guard, packet limit, per-family limit and its
lift, deterministic truncation, oversized text, critical evidence retention,
limit validation), readiness and conflicts, diagnostics and coverage, security
and metadata protections, and structural determinism.

## 15. Deliberate exclusions

No AI or LLM integration, model-provider client, prompt construction or template,
synthesis generation, cross-record summary, recommendation, content drafting,
frontend surface, TypeScript mirror, React component, CSS, persistence, database
table, migration, packet cache or history, repository/graph/source/active-memory/
contradiction mutation, export or review workflow, API endpoint, background
worker, task queue, scheduler, webhook, external network call, or new dependency.
Phase 36K remains untouched.

## 16. Next recommended phase

**Phase 40D — Synthesis Evidence, Provenance, and Validation Guardrails**, as the
roadmap sequences it: deterministic policy and validation over the packet this
phase produces (`SynthesisValidationResult`), scope exclusions,
prohibited-assumption enforcement, and fail-closed bounds — still with no
generative step.
