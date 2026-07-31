# Phase 40G — Migration Candidate Assessment (Dry-Run)

Status: implemented locally / pending independent audit.
Baseline: `origin/main` at commit `acfd833` (Phase 40E.7).
Branch: `phase-40g-migration-candidate-assessment-dry-run`.
Scope: backend-only. Deterministic, pure, read-only, non-mutating, non-persisting.

## Human decision this phase implements

Option A was approved for Phase 40G and must not be reopened:

- Phase 40G is **Migration Candidate Assessment (Dry-Run)**.
- The previously planned **Reviewed Persistence + Verified Import** phase is
  renumbered to **Phase 40H**, and the rest of the previously planned tail shifts
  down one letter (see the [roadmap](../roadmap.md)).
- Phase 40G remains deterministic, pure, read-only, non-mutating, and free of
  persistence.
- The durable persistence medium remains deliberately **undecided and outside
  this phase**.

## Product problem

Phase 40F parses migration-export artifacts and projects them into typed
`MemoryMigrationCandidate` records, each carrying its own per-item projection
diagnostics. But Phase 40F reasons **one artifact at a time**: it never looks at
the *complete* candidate set assembled across artifacts (and potentially across
bundles) and asks whether that set, as a whole, is coherent enough for a human to
review.

That set-level gate was missing. Two candidates can duplicate one another, the
same source slot can resolve to two different contents, two entries can claim the
same source position, a candidate can be technically valid yet carry nothing
reviewable, and a Phase 40F error can remain unresolved — and none of those
conditions is visible from a single candidate. Phase 40G adds the missing gate: a
deterministic **dry-run report** over the whole candidate set that identifies
exactly those conditions and derives a review-readiness verdict, **without
persisting, verifying, approving, activating, ranking, deleting, or mutating any
candidate**.

## Phase 40F → 40G → future 40H flow

```
Phase 40F  parser + pure projector
             -> bounded, provenance-linked MemoryMigrationCandidate records
                + per-item MigrationProjectionDiagnostic findings
                        |
Phase 40G  pure candidate-set assessor (this phase)
             -> MigrationCandidateAssessmentReport
                (duplicates grouped, conflicts flagged, ambiguity/degeneracy noted,
                 Phase 40F findings carried, coverage aggregated,
                 review-readiness derived)  --- READ-ONLY, NON-MUTATING
                        |
Phase 40H  Reviewed Persistence + Verified Import (PLANNED, NOT IMPLEMENTED)
             -> blocked on an explicit persistence-medium decision and later
                authorization. No durable medium is selected here.
```

Phase 40G is a **dry run**: it prepares candidates for later human review and
stops. It writes nothing, and it makes no decision about *how* reviewed candidates
would eventually be stored.

## Contracts added

New module `apps/backend/app/models/memory_migration_candidate_assessment.py`
(result contracts only; a separate module, mirroring the 40B/40D/40E/40F split;
the Phase 40F candidate/provenance/diagnostic shapes are reused unchanged):

- `MEMORY_MIGRATION_CANDIDATE_ASSESSMENT_VERSION = "memory-migration-candidate-assessment.v1"`
  — the ruleset version, separate from the wire contract version.
- `MigrationCandidateAssessmentSeverity` — closed `advisory` / `blocking`.
- `MigrationCandidateAssessmentDiagnosticCode` — the closed dry-run taxonomy
  (below).
- `MigrationReviewReadiness` — closed `ready_for_review` / `review_with_warnings`
  / `blocked`.
- `MigrationCandidateAssessmentDiagnostic` — one bounded, content-free finding;
  severity fixed by code; a carried Phase 40F finding is preserved verbatim in
  `carried`.
- `MigrationCandidateDuplicateGroup` — one candidate id occurring N≥2 times, with
  its shared source identity and content digest.
- `MigrationSourceIdentityConflict` — one source identity resolving to ≥2 distinct
  contents, listing the involved candidate ids.
- `MigrationCandidateCoverage` — bounded aggregates keyed only by the closed role
  and source-type vocabularies.
- `MigrationCandidateAssessmentReport` — the passive, content-addressed result.

New service `apps/backend/app/services/memory_migration_candidate_assessment.py`:

- `MemoryMigrationCandidateAssessor.assess(candidates=…, projection_diagnostics=…)`
  — the pure entry point.
- `assess_memory_migration_candidates(...)` — module-level convenience wrapper,
  mirroring the Phase 40E/40C/40D entry-point convention.

## Identity and normalization policy

All identities are pure functions of canonical typed fields folded through the
repository's canonical-JSON + SHA-256 convention
(`derive_migration_id`), with explicit NFC normalization and surrounding-whitespace
stripping on every string part. Nothing reads a clock, randomness, filesystem,
environment, Git, network, or process state.

- **Candidate identity** is the Phase 40F `candidate_id`, reused unchanged.
- **Source identity** (`derive_candidate_source_identity`) folds everything that
  locates a candidate back to origin **except its content**: `bundle_fingerprint`,
  `source_artifact_fingerprint`, `source_local_id`, `source_role`,
  `source_sequence_index`, `chunk_index`. Because a Phase 40F `candidate_id` is a
  pure function of exactly those components *plus* the content digest, two
  candidates that share a source identity and a content digest necessarily share a
  `candidate_id`.

The established Phase 40D "family + NFC-normalized identifier" identity intuition
is applied only where it is semantically valid for migration candidates: the
source-identity rule is defined over candidate/provenance fields directly, not
transplanted from an evidence identity rule. Identities are deterministic, stable
across input ordering, based only on canonical typed fields, explicit about
Unicode normalization, and free of any external state.

## Duplicate-versus-conflict semantics

Both are set-level and input-order independent; nothing is removed.

- **Duplicate** (`DUPLICATE_CANDIDATE`, advisory): candidates sharing a source
  identity **and** a content digest — the same `candidate_id` occurring more than
  once. Grouped and counted (`occurrence_count`), never collapsed. Deterministic
  group id (`derive_duplicate_group_id`) and canonical ordering.
- **Conflict** (`CONFLICTING_SOURCE_IDENTITY`, blocking): a source identity that
  resolves to two or more **distinct** content digests. All involved candidate ids
  stay visible; `distinct_content_digest_count` records how many contents collided
  without reproducing any. A true duplicate is never misreported as a conflict, and
  a conflict is never softened into a harmless duplicate.

## Diagnostic taxonomy and severity

Severity is fixed per code (`MIGRATION_CANDIDATE_ASSESSMENT_SEVERITY`) and a
supplied severity that disagrees is rejected; callers cannot downgrade a finding.

| Code | Severity | Meaning |
| --- | --- | --- |
| `duplicate_candidate` | advisory | Identical candidate occurs N≥2 times; grouped, never removed. |
| `conflicting_source_identity` | blocking | One source slot resolves to materially different content. |
| `ambiguous_source_order` | advisory | ≥2 distinct source entries claim one source-sequence position within one bundle+artifact scope. Missing/optional sequence values do not create false collisions; distinct scopes never collide. |
| `empty_or_degenerate_candidate` | advisory | Contract-valid candidate whose content is whitespace-only after NFC normalization — nothing to review. The canonical candidate model is not weakened to manufacture this. |
| `unresolved_projection_error` | blocking | A carried Phase 40F **error**-severity finding, preserved verbatim in `carried`. |
| `projection_truncation_warning` | advisory | A carried Phase 40F **info**-severity (bounded-skip / overflow / truncation) finding, preserved verbatim with its original severity intact. |
| `diagnostics_truncated` | blocking | The diagnostic list exceeded its bound; the set is not fully described and cannot be treated as ready. |

Carried Phase 40F findings reuse the original typed `MigrationProjectionDiagnostic`
rather than re-encoding it, so no severity or identity is lost. The assessment code
classifies the carried finding by its original severity and cross-checks the
mapping: an `error` must map to `unresolved_projection_error` and an `info` to
`projection_truncation_warning`, so a carried error can never be downgraded.

## Readiness derivation

`review_readiness` is derived by the report from its diagnostics and can never be
asserted by a caller (`resolve_review_readiness`):

- any blocking diagnostic → `blocked`;
- no blocking, ≥1 advisory → `review_with_warnings`;
- no diagnostics requiring attention → `ready_for_review`.

Unknown, unsupported, or internally inconsistent severity (a `None` or unrecognized
value) **fails closed** to `blocked` rather than producing a ready verdict. The
report recomputes readiness and rejects a stored value that disagrees.

## Purity and data-safety guarantees

- **Pure / read-only**: no filesystem, environment, subprocess, Git, network,
  database, clock, randomness/UUID, mutable global state, persistence service,
  Active Memory store, Grounded Synthesis execution, or AI/LLM call. Enforced by an
  AST purity test over the service module, consistent with the Phase 40F projector
  test.
- **Input-order independent** and **serialization-stable**: identical input yields
  a byte-equivalent report; reordered input yields the same canonical report.
- **Non-mutating**: inputs are never modified, reordered, deduplicated-by-removal,
  or repaired. `read_only` is pinned true; `candidates_mutated` and `persisted` are
  pinned false and reject being turned on.
- **Tamper-evident**: `report_id`, every duplicate `group_id`, and every
  `conflict_id` are recomputed and cross-checked at construction; coverage,
  diagnostic counts, and readiness must be recomputable from the report's own
  contents.
- **No raw content**: a report carries closed-enum literals, counts, stable
  candidate-local identifiers, and content **digests** (non-reversible hashes)
  only. No candidate body, export byte, conversation text, or arbitrary exception
  string appears anywhere. Coverage is grouped only by the closed role and
  source-type vocabularies.
- **Bounded**: the diagnostic list is bounded and overflow is represented by an
  explicit blocking `diagnostics_truncated` finding (never a silent drop); a
  candidate set beyond `MAX_ASSESSED_CANDIDATES` (the Phase 40F per-result ceiling)
  is refused loudly rather than assessed partially.

## Test coverage

`apps/backend/tests/test_memory_migration_candidate_assessment.py` (41 tests):
empty and clean input; advisory-only vs blocking verdicts; byte-stable and
order-independent reports; duplicate grouping (never dropping) and deterministic
group ordering/identity; conflict detection and duplicate-vs-conflict separation;
ambiguous source order with no false cross-scope or cross-chunk collisions;
degenerate-candidate detection; carried Phase 40F error (blocking) and carried info
(advisory, severity preserved and non-downgradable); fail-closed readiness;
no-raw-content safety; aggregate coverage; stable content-addressed identity and
forged-identity rejection; `CANDIDATE_MEMORY_POLICY` pinned; input immutability;
AST purity; bounded-collection behavior (at-bound assessed, beyond-bound refused,
diagnostic truncation); Unicode (NFC) normalization; and canonical
serialization/round-trip.

## Non-goals (explicitly out of scope)

Persistence; database writes; durable-medium selection; Active Memory insertion or
mutation; candidate approval, verification, activation, or human-confirmation
state; automatic import; endpoints or routers; frontend work; screenshots or demo
evidence; AI/LLM inference; graph or source mutation; Git mutation services;
candidate deletion; deduplication that removes records; candidate re-ranking or
mutation; rollback execution; auth changes; new dependencies; broad refactors; and
Phase 36K gesture-control work.

## Persistence remains undecided and unimplemented

Phase 40G persists nothing. **Reviewed Persistence + Verified Import is Phase 40H,
which remains planned and blocked on an explicit persistence-medium decision and
later authorization.** No candidate is imported, no memory is migrated, no
persistence exists, no human review has occurred, nothing is verified or activated,
the durable medium has not been selected, and the migration pipeline is not
production-ready.
