# Phase 40F — Export Parser + Candidate Projection

**Status:** Implemented locally / pending independent audit.
**Track:** Grounded Synthesis + Memory Migration (Phase 40D.5–40K sequence).
**Dependency:** Phase 40E — Memory Migration Contract + Intake Safety Foundation
(merged, `b1dda05`, PR #189).
**Boundary:** Phase 40F reads user-controlled artifact bytes and produces
**candidates**. It persists nothing and imports nothing — reviewed persistence and
verified import are the exclusive Phase 40G boundary.

Phase 40F is the first memory-migration phase permitted to open a user-controlled
artifact and read its bytes. Everything before it judged *declarations*: Phase 40E
decided, from declared metadata alone, whether a bundle is safe enough for a parser
to attempt. Phase 40F is that parser. It reads the declared bytes only after the
Phase 40E gate authorizes it, proves the bytes are the bytes the user declared,
interprets the supported export and curated formats deterministically, and projects
their user-visible content into bounded, provenance-linked candidate memory
records that are structurally incapable of being active, verified, or persisted.

## Components

| File | Role |
| --- | --- |
| `apps/backend/app/models/memory_migration_projection.py` | Pure contracts: the candidate record, its provenance, the measured-integrity result, the curated-input shape, the parsed-item intermediate, the projection diagnostic taxonomy, and the projection result. No I/O. |
| `apps/backend/app/services/memory_migration_parser.py` | The **only** Phase 40F component permitted filesystem/archive/byte I/O. Byte sources, the reused authorization gate, integrity verification, defensive archive handling, format dispatch, and the run orchestrator. |
| `apps/backend/app/services/memory_migration_projection.py` | The **pure** projector: parsed items → candidates. Deterministic, no I/O, no clock, no randomness. |
| `apps/backend/tests/test_memory_migration_parser.py` | Gate, integrity, archive-safety, ChatGPT parsing, curated/plain-text parsing, determinism, value-safety. |
| `apps/backend/tests/test_memory_migration_projection.py` | Candidate-standing ceiling, deterministic identity/ordering, chunking/overflow, provenance, projector purity. |

## Why parsing is gated by the exact Phase 40E bundle fingerprint

The one rule Phase 40F must never weaken is the authorization boundary. It does not
merely check `assessment.assessed_status == READY_FOR_PARSING`; it calls the Phase
40E contract method

```python
assessment.permits_parsing(bundle_fingerprint=bundle.fingerprint())
```

which returns `True` only when the assessment reached `ready_for_parsing` **and**
was made about exactly the declaration being presented. An assessment for an older
or since-modified declaration produces a different content-derived
`bundle_fingerprint`, so it authorizes nothing — the parser reports a
`stale_assessment` finding and reads zero bytes. This is the same rule Phase 40E
shipped, reused rather than re-implemented: a second, weaker readiness check inside
the parser would be a second thing that can get it wrong. No artifact byte is
touched before this gate passes, which the tests prove by driving a rejected gate
through a spying byte source and asserting zero read calls.

## Why byte-integrity verification is different from factual verification

Phase 40E digests were **declarations** — the user (or their export tool) said the
bytes hash to a value, and Phase 40E, reading no bytes, could not confirm it and
pinned `DeclaredArtifactDigest.verified` to `False`. Phase 40F reads bytes, so it
can and does recompute the accepted digest and compare it, and compares the actual
size to the declared size. On any mismatch it fails closed: that artifact produces
**no candidates**.

But integrity verification answers only one question:

> *Are these bytes the bytes the user declared?*

It says nothing about whether the statements inside those bytes are true. The two
concepts are kept in separate shapes so no consumer can conflate them. Phase 40F
never mutates the Phase 40E `verified` flag; instead it records a confirmed result
in the dedicated `VerifiedArtifactIntegrity` model (`integrity_verified=True`,
observed digest equal to declared). Meanwhile every candidate remains
`verification_state = unverified`, no matter how cleanly its source hashed. A
verified byte stream is not a verified claim.

## Why candidates use a dedicated contract instead of `MemoryRecord`

Phase 40E deliberately did not reuse the permissive Active Memory `MemoryRecord`,
because a `MemoryRecord` can be constructed `active` and `human_confirmed` — the
exact standing migrated material must never hold. Phase 40F preserves that decision.
`MemoryMigrationCandidate` is a distinct contract that pins the five
candidate-standing fields and cross-checks them against the canonical
`CANDIDATE_MEMORY_POLICY` fixed in Phase 40E:

```
lifecycle_state          = inactive
verification_state       = unverified
represents_active_memory = false
human_review_required    = true
persistable              = false
```

No caller can override these — the model rejects any other value, and it fails
closed if the candidate's standing and the policy it carries ever disagree. A
candidate is emphatically **not** a `MemoryRecord`: it carries no record kind, no
evidence, and no confidence, and cannot be built active or confirmed. Candidate
construction additionally verifies its own deterministic identity (content digest
and candidate id), so a forged or stale candidate cannot be constructed at all.

## Supported artifact formats

Phase 40F parses exactly the five formats Phase 40E marked parseable, dispatched
explicitly and fail-closed:

| Format | Container | Handling |
| --- | --- | --- |
| `chatgpt_export_archive` | `zip_archive` | Defensive in-memory ZIP; locate and read only the `conversations.json` member; parse conversations. |
| `chatgpt_conversations_json` | `single_file` | Parse the conversations array directly. |
| `curated_json_bundle` | `single_file` | Versioned, `extra="forbid"` curated document → one candidate per entry. |
| `curated_markdown_bundle` | `single_file` | Treated conservatively as a document; no semantic heading extraction. |
| `plain_text_document` | `single_file` | One document candidate. |

`obsidian_vault_export` is excluded on purpose — Hive|Mind already has a dedicated
Obsidian import pipeline, and a second competing path would apply different safety
rules to the same source. Any unsupported `(format, container)` pair yields a typed
`unsupported_format` / `unsupported_container` diagnostic and reads nothing.

## ChatGPT export safety boundary

Hive|Mind has **no direct access to private ChatGPT system memory**. Phase 40F
processes only material the user explicitly supplied. From a ChatGPT export it
extracts visible conversational content conservatively:

- only `user` and `assistant` text messages become candidates;
- `system`, `tool`, and `developer` material is skipped with a counted diagnostic
  and never imported — an exported message is never treated as equivalent to
  private system memory, and hidden/system/developer instructions never become
  candidate memories;
- conversation and message identifiers and timestamps are preserved when present;
- missing message ancestry is never fabricated; malformed or incomplete records are
  skipped with bounded diagnostics, never repaired.

## Archive safety policy

`chatgpt_export_archive` requires ZIP handling, done with the Python standard
library (no new dependency) and read-only:

- the archive is opened in memory from its verified bytes and is **never**
  extracted to disk; `extractall`/`extract` are never called;
- every member is screened and the whole artifact fails closed on the first
  violation — absolute paths, `..` traversal, control characters, encrypted
  members, and symlink/device/socket/FIFO entries are all refused;
- explicit member-count, per-member uncompressed-size, total-uncompressed-size, and
  compression-ratio bounds reject decompression-bomb-shaped input;
- only the intended `conversations.json` member is read, through a bounded stream,
  selected deterministically by sorted path;
- nothing from an archive is ever executed or followed.

The per-member safety screen is a pure function (`_member_safety_violation`) so it
can be unit-tested against crafted members — an encrypted flag, a symlink mode — that
the standard library cannot easily be made to write.

## Deterministic identity

Candidate identity is content-derived and reproducible, reusing the repository's
canonical-JSON + SHA-256 convention (`derive_migration_id`). A candidate id folds
in the bundle fingerprint, artifact fingerprint, source-local identifier, role,
chunk index, and content digest; the content digest is a SHA-256 over the chunk's
UTF-8 bytes. Nothing reads a clock, a random source, object identity, or filesystem
ordering. Identical bytes and configuration always yield byte-equivalent candidates.

## Deterministic ordering

Output order is canonical and independent of hostile input order. Conversations are
read in export (array) order; messages within a conversation are ordered by a stable
traversal of the mapping tree keyed on `(create_time, node_id)` — never JSON object
insertion order — and each parsed item carries an explicit sequence index. The final
candidate list is sorted by `(artifact_id, source_sequence_index, chunk_index,
candidate_id)`. Repeated parsing of identical bytes yields identical ordering.

## Bounds and overflow policy

Bounds are honest, never silent:

- candidate content is bounded (`MAX_CANDIDATE_CONTENT_CHARS`); a longer parsed item
  is split into deterministically-ordered chunks carrying `chunk_index`/`chunk_count`
  metadata, and reassembling the chunks reproduces the bounded content exactly;
- content the parser had to cap (`MAX_PARSED_ITEM_CHARS`) is flagged
  (`content_truncated`) and reported with a `candidate_content_overflow` diagnostic
  — never quietly clipped to look complete;
- candidate-count overflow against the run budget (`MAX_MIGRATION_CANDIDATES`) is
  represented with a `candidate_count_overflow` diagnostic carrying the exact number
  of candidates that were not created, rather than dropping records to fit.

## Provenance model

Every candidate traces back to the exact material that produced it. Its provenance
answers, for a Phase 40G reviewer: which user-provided bundle, which artifact, which
artifact fingerprint, which **verified** byte stream (observed digest), which
conversation/document/entry, which source role, which source timestamp (when one
existed), and which parser/projection policy version. Distinct source entries are
never collapsed into one candidate merely because their text matches — identity is
provenance-aware.

## Diagnostic taxonomy

Diagnostics are a closed vocabulary (`MigrationProjectionDiagnosticCode`) with
severity fixed per code (`info` for a bounded skip that left the run usable, `error`
for an artifact or run that produced nothing). Severity is derived from the code,
never caller-controlled. Messages carry counts, closed-enum literals, and
declaration-local identifiers only — **never** raw exported conversation text, a
declared path, or a digest value, for the same reason Phase 40E refused to echo
declared values. The list is deduplicated, canonically ordered, and bounded, with an
error-first truncation notice that can never soften what failed.

## Parser / projection separation

The pipeline is:

```
unsafe external bytes → parser → bounded parsed items → pure projector → candidates
```

All filesystem, archive, and byte access lives in the parser (behind a
`MigrationArtifactByteSource` abstraction). The projector is pure and deterministic:
it opens no file, reads no clock, generates no random value, makes no network or Git
call, and mutates no input. That purity is enforced structurally by an AST check in
the projection tests, not merely promised.

## Why no AI/LLM semantic extraction is used

Phase 40F performs no AI/LLM parsing, classification, summarization, fact
extraction, embedding, or semantic search. Imported prose is a **candidate**, not
truth. Manufacturing project facts, decisions, phase states, or repository facts
from free-form conversation text would be exactly the silent authority escalation
the whole migration track forbids. The parser interprets structure deterministically
and stops; a human decides what any candidate means in Phase 40G.

## Explicit Phase 40G boundary

Phase 40F ends at candidates returned to the caller. It does not persist a
candidate, insert one into any store, mark one reviewed/approved/verified/
human-confirmed, activate one, run contradiction or active-state calculation over
one, or mutate the Source Registry, Knowledge Graph, repository, or Git. The
projection result pins `persisted` and `imported` to `False` and rejects being
turned on. Reviewed persistence and verified import are the exclusive Phase 40G
boundary.

## Validation performed

- **Phase 40F focused:** 66 passed (`test_memory_migration_projection.py` 23 +
  `test_memory_migration_parser.py` 43).
- **Phase 40E regression:** 223 passed (`test_memory_migration_contracts.py`,
  `test_memory_migration_intake.py`), unchanged.
- **Neighboring Active Memory / grounding regression:** 367 passed.
- **Full backend:** 1201 passed (prior baseline 1135 + 66 new; no regressions).
- Compile validation over the new/changed Python files, `git diff --check`, and a
  merge-conflict-marker scan all clean.

## Known limitations

- Curated Markdown and plain-text artifacts are treated as whole documents;
  Phase 40F does not split Markdown by heading or otherwise interpret its structure,
  by design (conservative — no semantic extraction).
- Curated JSON and other curated formats are supported only as `single_file`
  artifacts in this phase; a curated bundle declared as a ZIP fails closed with an
  `unsupported_container` diagnostic.
- Candidate content chunking is a fixed-width character split, not word- or
  sentence-aware, chosen for trivial determinism.
- Phase 40F produces candidates in memory and returns them; it provides no storage,
  review UI, API, or import path — those follow in later phases.
