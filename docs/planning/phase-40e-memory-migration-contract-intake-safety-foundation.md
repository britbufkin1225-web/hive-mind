# Phase 40E — Memory Migration Contract + Intake Safety Foundation

**Status:** backend-only, implemented locally / pending independent audit and the
devdevbuilds human merge gate.
**Type:** backend contract + deterministic read-only service phase (no endpoint,
router, frontend, store, graph, Source Registry, parser, persistence, dependency,
or asset change).
**Depends on:** [Phase 40D.5](phase-40d-5-roadmap-reconciliation-memory-migration-pivot.md)
being merged on `main` — the decision record that sequences the memory-migration
track ahead of Grounded Synthesis production and establishes the authoritative
Phase 40D.5–40K ordering.
**Baseline:** `f71a894968868a54fe803e0a88cc2df1e4202515`.

## 1. What this phase is

Phase 40E is the **intake boundary** of the memory-migration track. It answers one
question and stops:

> Given only what has been **declared** about a migration bundle, may Phase 40F
> attempt to parse it — and if not, precisely why?

It introduces the versioned `memory-migration.v1` contract family and a
deterministic, pure, read-only assessment over declared metadata. It parses
nothing, extracts nothing, reads no artifact byte, projects no candidate,
persists nothing, and imports nothing.

## 2. What was added

| File | Role |
| --- | --- |
| `apps/backend/app/models/memory_migration.py` | The `memory-migration.v1` declaration contracts: lifecycle, custody, format, container, entry-kind and digest vocabularies; declared digest; migration provenance; artifact descriptor; bundle; candidate-memory policy; deterministic identity/fingerprint derivation. |
| `apps/backend/app/models/memory_migration_assessment.py` | The assessment **result** contracts: closed diagnostic taxonomy, severity fixed per code, bounded diagnostic record, and the intake assessment report with its derived status. |
| `apps/backend/app/services/memory_migration_intake.py` | `MemoryMigrationIntakeAssessor` — the deterministic, read-only assessment, its named policy bounds, and its fail-closed allowlists. |
| `apps/backend/tests/test_memory_migration_contracts.py` | Contract coverage, including the deliberate *absences*. |
| `apps/backend/tests/test_memory_migration_intake.py` | Assessment coverage: every diagnostic code, escalation, determinism, purity, and value-safety. |
| `docs/planning/phase-40e-memory-migration-contract-intake-safety-foundation.md` | This record. |

`README.md` and `docs/roadmap.md` were updated narrowly to move Phase 40E from
*planned* to *implemented locally* and to describe what now exists.

## 3. The load-bearing decisions, and why

### 3.1 Declared, never verified

Every field in the family is a **declaration**. Phase 40E opens no artifact, so it
cannot confirm a size, a digest, a path, an entry type, or a format. Two
structural consequences:

- `DeclaredArtifactDigest.verified` is pinned `False` and rejects being turned on.
  Verifying a digest requires reading bytes and recomputing the hash; a later
  phase that actually does that may record a verified digest under its own
  contract, not by flipping a flag on a declaration.
- `MemoryMigrationIntakeAssessment.artifacts_read` is pinned `False`. It is the
  single most important claim the report makes about itself: a report asserting
  otherwise would misrepresent the strength of its own verdict to every consumer
  downstream.

The standing `declared_digest_unverified` advisory is emitted for **every** clean
bundle carrying accepted digests. It is not a defect — it is the phase telling the
truth about itself, so that "a digest is present" can never be read as "the digest
checked out".

### 3.2 Raw migration artifacts are not memory and not evidence

`MemoryMigrationBundle` pins `is_memory` and `is_verified_evidence` to `False` and
rejects both being turned on. A bundle is a bounded description of material the
user handed over: not a claim, not a record, not proof of anything.

The permissive Active Memory *record* models (`MemoryRecord`, `EvidenceRecord`)
are deliberately **not** reused. A `MemoryRecord` can be constructed as `active`
and `human_confirmed`, which is precisely the standing migration material must be
structurally incapable of holding. The stable Active Memory *semantic* enums are
reused (`MemorySource`, `MemoryScope`, `LifecycleState`, `VerificationState`,
`MemorySourceType`) so "inactive" and "unverified" mean exactly what they already
mean everywhere else in the system.

### 3.3 The lifecycle stops at the parsing boundary

`MigrationIntakeStatus` has exactly four members:

```text
declared → ready_for_parsing | blocked | quarantined
```

There is deliberately no `parsed`, `projected`, `reviewed`, `approved`,
`persisted`, `verified`, `imported`, or `active` state. Those describe work Phase
40F and Phase 40G do, and a vocabulary able to express them here would let a
declaration claim an outcome no code in this phase produces. A test asserts each
of those literals raises.

`blocked` and `quarantined` are distinguished on a specific operational axis:

- **`blocked`** — the declaration is at fault. Re-declaring it correctly fixes it
  (a missing digest, an unsupported format, a mis-stated total).
- **`quarantined`** — the described material is at fault. No re-declaration fixes
  it (a traversing path, a symlink entry, a refused custody).

That distinction is why the severity axis has three values rather than Phase 40D's
two: a two-valued severity could not express which of the two a finding implies,
and collapsing them would either quarantine recoverable declarations or let unsafe
material be re-declared past the boundary.

### 3.4 A bundle cannot declare its own readiness

`MemoryMigrationBundle.intake_status` is pinned to `declared`, and the assessor
ignores it as an input to the decision — it recomputes the status from the
bundle's actual contents and reports any disagreement as
`unsupported_intake_status`. This is the migration-track form of the Phase 40D
rule that readiness is computed and never read off the record being checked. A
bundle that could declare itself ready would make the whole boundary advisory.

### 3.5 Migration provenance is its own strict contract

`MigrationProvenance` deliberately does **not** reuse
`ProvenanceChain` (`app.models.hive_models`). That structure is a derived,
advisory *graph* view: node/edge shaped, tolerant of partial derivation, and
computed by `app.services.provenance` from records Hive|Mind already holds.
Pre-ingestion custody is the opposite in every respect — it describes material
Hive|Mind does **not** hold, it must be complete rather than partial, it is
asserted rather than derived, and it is load-bearing for a trust decision.
Stretching the graph contract to carry custody would make an advisory structure
into a security boundary and would leave custody with nowhere to live.

`user_provided` is pinned `True` and rejects being turned off. Hive|Mind claims no
direct, account-to-account access to a provider's private system memory, so there
is no legitimate intake path in which the material was not handed over by the
user.

`MigrationCustodyKind` represents `third_party_transfer` and
`automated_account_link` **on purpose**, so the boundary can *name* the custody it
refuses and quarantine it with a typed diagnostic — rather than omitting the
concept and silently accepting whatever arrives wearing an approved label.

### 3.6 Deterministic identity: canonical UTF-8 JSON + SHA-256

`derive_migration_id`, `derive_artifact_fingerprint`, and
`derive_bundle_fingerprint` fold canonical JSON material through SHA-256 with a
**narrow, documented** normalization: NFC on the readable prefix and on each
supplied identifier part, plus surrounding-whitespace stripping on those parts.
Nothing else is touched — no case folding, no separator rewriting, no NFKC —
because each of those would map two materially different declarations onto one
identity. Canonical JSON array material (rather than a delimiter join) means a
part *containing* the delimiter cannot forge a different part boundary.

Two deliberate exclusions and one deliberate inversion:

- `artifact_id` is excluded from the artifact fingerprint, and `bundle_id` from
  the bundle fingerprint: the fingerprint answers "is this the same declared
  material?", which must not depend on the label a caller chose. Excluding it is
  what makes the redundant-declaration check possible at all.
- `label` and `metadata` are excluded: annotation, not identity.
- Artifact fingerprints are folded into the bundle fingerprint **sorted**.
  Reordering the same declared artifacts does not change what the user handed
  over. This is the deliberate opposite of `derive_context_packet_identity`, where
  evidence order encodes assembler *ranking* and is therefore material.

The assessment carries `bundle_fingerprint`, and
`MemoryMigrationIntakeAssessment.permits_parsing(bundle_fingerprint=...)` returns
`True` only when the verdict was `ready_for_parsing` **and** it was made about
exactly the declaration being presented. That is the check Phase 40F is required
to perform before reading a byte; providing it on the report means a parser cannot
re-implement it and get it wrong.

### 3.7 Contract shape versus intake safety — a deliberate split

The models enforce only **representability**: is this value bounded, non-empty,
and recordable at all? They do **not** judge safety.

A declared path is preserved **byte-for-byte**. It is identity-bearing — it is how
a future parser finds the entry and how a candidate traces back to its origin — so
stripping whitespace, collapsing separators, or normalizing case would silently
change what the user declared and could make two materially different entries
collide. `declared_byte_size` and `declared_digest` are optional in the contract
even though the policy requires both, because making absence *representable* is
what lets the assessment emit a typed `missing_declared_size` /
`missing_declared_digest` diagnostic; a contract-mandatory field would surface the
same condition as an untyped `ValidationError` with no diagnostic and no
assessment record.

Rejecting unsafe material at the model edge would destroy exactly the diagnostics
the intake boundary exists to produce.

### 3.8 Nothing is repaired, clipped, or dropped

A traversing path is reported as traversing, not sanitized. An oversized bundle is
reported as oversized, not trimmed. Making an unsafe declaration *look* acceptable
by editing it is the failure mode the layer exists to prevent, and a rewritten path
would additionally destroy the provenance link a migrated candidate must carry back
to its origin. Tests assert the declaration is byte-identical before and after
assessment.

### 3.9 Fail-closed by construction

Every policy set in the service is an **allowlist**, and every check falls through
to a typed blocking or quarantining diagnostic. Anything outside the list —
including a value a later contract revision adds that this service has never seen —
fails closed rather than arriving as an accepted value nobody reviewed. Notably:

- an unrecognized **custody** kind lands in the same branch as the two explicitly
  refused ones, so a future vocabulary addition quarantines rather than passes;
- an entry kind that is neither explicitly safe nor explicitly unsafe blocks.

### 3.10 Diagnostics carry no declared values

Messages contain counts, closed-enum literals, and declaration-local identifiers
only. A declared path, media type, digest value, origin label, or filename is
**never** echoed, even when the value is precisely what the boundary rejected. The
values this phase inspects are the ones most likely to be hostile (a traversal
payload) or sensitive (a filename or export label carrying personal information),
and copying one into the report would move the problem from the declaration into
the record of the declaration. A test probes every message against a set of
planted sensitive values.

Metadata bags additionally refuse credential-shaped keys and **byte-bearing** keys
(`content`, `body`, `raw`, `payload`, `file_bytes`): those would put the artifact's
actual contents inside a declaration, turning a description into an unparsed
payload and defeating the entire declared-metadata boundary.

### 3.11 Candidate Memory cannot represent approved Active Memory

Phase 40E defines **no candidate record** — producing candidates requires parsing,
which is Phase 40F. What it defines is the ceiling those candidates may never
exceed, stated as a validated contract (`CandidateMemoryPolicy`, exposed as the
single canonical `CANDIDATE_MEMORY_POLICY`) rather than as prose, so a later phase
cannot quietly widen it:

| Field | Pinned value | Meaning |
| --- | --- | --- |
| `lifecycle_state` | `inactive` | never part of the active baseline |
| `verification_state` | `unverified` | imported material is never verified truth |
| `represents_active_memory` | `False` | cannot stand in for an approved record |
| `human_review_required` | `True` | review is not optional |
| `persistable` | `False` | Phase 40G is the exclusive persistence boundary |

## 4. The initial assessment-policy bounds

Named constants in `app.services.memory_migration_intake`, deliberately
**declared-size** bounds — nothing has been measured, so exceeding one is a
statement about the declaration, never about the artifact's real size.

| Constant | Value | Rationale |
| --- | --- | --- |
| `MAX_DECLARED_ARTIFACT_BYTES` | 1 GiB | Comfortably exceeds a large ChatGPT `conversations.json` or full export archive, so a legitimate single artifact never approaches it. A declaration above it is far more likely to be a mis-declared size or a decompression-bomb-shaped claim than a real export. |
| `MAX_DECLARED_BUNDLE_BYTES` | 2 GiB | Only *twice* the per-artifact bound rather than a multiple of the artifact count: a migration bundle is one person's own history, not a bulk corpus, and a total far above a couple of large artifacts indicates the bundle is being used as a data dump. |
| `MAX_DECLARED_ARTIFACTS` | 512 | Bounds per-artifact assessment work and keeps a bundle reviewable by a human in Phase 40G. Sits well below the `memory-migration.v1` contract ceiling of `MAX_MIGRATION_BUNDLE_ARTIFACTS` (2048) so policy can tighten or relax without a contract change. |

Repository evidence surfaced no reason to adjust the proposed 1 GiB / 2 GiB
figures during implementation, so they were kept as specified. `MAX_DECLARED_ARTIFACTS`
is validated against the contract ceiling, and `max_artifact_bytes` may not exceed
`max_bundle_bytes` — a single artifact cannot be permitted to be larger than the
whole bundle.

## 5. Notable policy choices with repository grounding

- **`obsidian_vault_export` is recognized but not parseable.** Hive|Mind already
  has a dedicated Obsidian import path (`app.services.obsidian_import`); routing
  vault material through the migration track as well would create two competing
  import paths with different safety rules over the same source. It blocks with
  `unsupported_artifact_format` rather than being silently treated as a generic
  Markdown bundle — which is the whole reason *recognition* and *support* are kept
  separate.
- **`directory_tree` containers block.** A single descriptor for a whole tree
  declares a size and digest for material whose individual entries — their paths,
  entry kinds, and count — are simply not stated, so none of the per-entry safety
  rules can be applied to any of them. Accepting it would mean passing an
  unbounded, unenumerated set of unknown entries as "assessed".
- **A missing digest blocks.** Phase 40E cannot verify a digest, but without one
  *declared*, no later phase could either: there would be nothing to recompute
  against, so substituted bytes would remain undetectable for the whole life of the
  migrated record.
- **`sha1`/`md5` block.** A later phase recomputing them could be satisfied by
  substituted bytes, making the verification step ceremonial rather than real.
- **Internal source types block.** `repository_observer`, `ci_system` and
  `cli_report` are Hive|Mind's *own* producers; a user bundle declaring one as its
  origin would launder that internal authority onto unread bytes. `unknown` blocks
  because unattributable material cannot preserve provenance, which is the entire
  purpose of this track.
- **Reserved Windows device names are checked on every platform.** A declared path
  is portable data, and a bundle assessed on Linux may well be parsed on the
  Windows host this project targets.

## 6. Bounded report, without softening the verdict

The diagnostic list is bounded at `MAX_MIGRATION_DIAGNOSTICS` (256). On overflow,
findings are retained **most-severe-first** and only then re-sorted canonically,
which guarantees the retained set still contains the most severe severity present
in the full set — so the derived status cannot be softened by the act of
truncating. The truncation notice itself is blocking: a declaration that produced
more findings than a report can carry has not been fully described, and reporting
it as ready would be a claim the assessment cannot support.

## 7. Scope and explicit non-goals

**In scope:** the `memory-migration.v1` declaration contracts; the assessment
result contracts; the deterministic read-only intake assessment and its policy;
focused tests; this record; narrow README/roadmap reconciliation.

**Explicit non-goals — none of these were done:**

- Parse a ChatGPT export or any other artifact; extract an archive; read a byte;
  touch the filesystem, network, or Git.
- Verify a declared digest, size, path, entry type, or format.
- Project candidate memory records (Phase 40F).
- Persist anything or perform verified import (Phase 40G).
- Add a router, endpoint, API contract entry, frontend, store, graph, Source
  Registry, dependency, package, or asset change.
- Claim direct access to private ChatGPT system memory or automatic
  account-to-account migration.
- Describe any planned capability as working today.
- Touch Phase 36K.

## 8. Validation

- `python -m pytest apps/backend` — **1111 passed**, of which **199** are the new
  Phase 40E tests (912 pre-existing tests unchanged and passing).
- Every member of `MigrationDiagnosticCode` is proven reachable from a real
  declaration; a taxonomy member no declaration can produce would be a rule nobody
  enforces.
- Purity is enforced structurally by AST scan over both the contract module and
  the intake service: no clock, randomness, `os`/`pathlib`/`subprocess`/`socket`/
  `urllib`, and no `zipfile`/`tarfile`/`open`/`extractall`. The boundary that
  decides whether untrusted material may be touched must itself not touch it.
- Determinism is proven, not assumed: identical declarations yield byte-identical
  reports, the assessor is stateless between calls, and artifact declaration order
  does not change the verdict.
- The assessor is proven not to mutate the declaration it reads.
- No declared value appears in any diagnostic message.

## 9. What Phase 40F and Phase 40G must do

- **Phase 40F** must require a matching `ready_for_parsing` assessment before
  parsing anything — specifically, `assessment.permits_parsing(bundle_fingerprint=
  bundle.fingerprint())` must be `True`. An assessment of a since-edited
  declaration permits nothing, however favourable its verdict. Candidates it
  produces must be constructed under `CANDIDATE_MEMORY_POLICY`.
- **Phase 40G** remains the exclusive reviewed-persistence boundary. Nothing
  before it may write a candidate anywhere, and verified import stays human-gated.

## 10. Data-flow position

```text
User-controlled ChatGPT export or curated bundle   (user provides; no direct
                |                                    private-memory access)
                v
   Phase 40E — declared metadata only, fail-closed, no bytes read   ← this phase
                |   declared → ready_for_parsing / blocked / quarantined
                v
   Phase 40F — Export Parser + Candidate Projection            (planned)
                |   requires a matching ready_for_parsing assessment
                v
   Phase 40G — Reviewed Persistence + Verified Import          (planned)
```

Everything downstream of this phase remains **planned**. No migration capability
works today: nothing is parsed, projected, persisted, or imported, and Hive|Mind
still cannot and does not access private ChatGPT system memory.
