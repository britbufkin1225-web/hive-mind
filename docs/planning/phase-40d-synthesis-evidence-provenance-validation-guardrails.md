# Phase 40D — Synthesis Evidence, Provenance, and Validation Guardrails

**Status:** implemented locally / pending independent audit and the devdevbuilds
human merge gate.
**Type:** backend service phase only.
**Depends on:** [Phase 40B](phase-40b-grounded-synthesis-contract-types-schema-foundation.md)
(the `grounded-synthesis.v1` contracts) and
[Phase 40C](phase-40c-grounding-context-assembly-service-mvp.md) (the grounding
context assembly service).

## 1. What this phase is

Phase 40D adds the deterministic, read-only **guardrail layer** of the Grounded
Synthesis Layer. It answers exactly one question:

> Is this `SynthesisContextPacket` sufficiently grounded, internally consistent,
> and provenance-complete to be passed into a future synthesis capability?

It answers it and stops. Phase 40D is the **trust boundary** between grounding
assembly and any future generation: it is the thing that must be reviewable and
trustworthy *before* anything is ever produced from a packet.

**Hive|Mind still does not generate Grounded Synthesis output.** Deciding that
grounding is trustworthy is not producing anything from it. There is no synthesis
text, no *Musings* output, no *Loom* output, no prompt, no model provider, no
retrieval-augmented generation, and no producer of any kind. (*Musings* and *The
Loom* remain planned **capabilities within** the Grounded Synthesis Layer, not
separate architecture layers.)

## 2. What it adds

| Area | Files |
| --- | --- |
| Validation service | `apps/backend/app/services/grounding_validation.py` |
| Report contracts | `apps/backend/app/models/grounded_synthesis_validation.py` |
| Tests | `apps/backend/tests/test_grounding_validation.py` |

Phase 40D introduces:

- **Deterministic packet validation** — `validate_synthesis_context_packet(packet)`
  (and the `SynthesisContextPacketValidator` service behind it) is a pure
  function from packet to typed report.
- **Evidence identity guardrails** — canonical identity checked with the
  assembler's own rule.
- **Provenance integrity checking** — resolution, completeness, and per-family
  expectations.
- **Packet consistency validation** — every declared total recomputed from the
  packet's actual contents.
- **Explicit synthesis-readiness determination** — computed, never read off the
  packet.
- **Blocking and non-blocking diagnostics** — a closed taxonomy with stable
  codes, severity, ordering, and messages.

## 3. Design decisions and rationale

### 3.1 A separate report contract module, not a Phase 40B change

The Phase 40B contracts are stable and were reused **unchanged**. A validation
report is a *new* shape describing an existing contract, so it lives in its own
module (`grounded_synthesis_validation.py`) — the same split as
`repository_observer` / `repository_observer_api`. Nothing here redefines,
mirrors, or narrows the packet, evidence-reference, provenance, artifact, or
request contracts, and no parallel packet model or second evidence hierarchy was
created.

The report projects onto the canonical Phase 40B `SynthesisValidationResult`
through `to_validation_result()`, so a consumer that already speaks
`grounded-synthesis.v1` needs no new vocabulary to learn whether a packet is
valid. Only *blocking* diagnostics become issues: Phase 40B makes a result valid
if and only if it carries no issues, so filing an advisory finding as an issue
would make every merely-repetitive packet invalid.

### 3.2 Pure and read-only

The validator never mutates the packet, rewrites or removes an evidence record,
repairs a provenance reference, re-ranks evidence, re-assembles context, persists
a verdict, or touches a repository, graph, source, store, or Active Memory. It
reads no clock, generates no random identifier, and performs no filesystem, Git,
or network access — a structural AST test enforces that, mirroring the Phase 40C
purity test. Tests assert byte-identical packet state after both successful and
failing validation.

### 3.3 A packet is never trusted on its own word

The Phase 40C assembler computes every count, coverage total, truncation figure,
readiness reason, and packet identifier a packet carries. Phase 40D **recomputes
them from the packet's actual contents** and compares. An assembler-declared or
tampered packet whose summary fields merely look plausible therefore fails.

The strongest of these is **packet identity re-derivation**. The Phase 40C
identifier is a content-derived hash over the packet's mode, readiness, assembly
time, ordered evidence ids, conflicts, gaps, coverage, and warnings, so editing
any of them changes the derived id. To make the two sides provably fold the same
material, Phase 40C's private `_derive_packet_id` was refactored into a public
`derive_context_packet_identity(...)` that both the assembler and the validator
call. Behavior is unchanged; the derivation now exists once instead of twice.
(Reported below under the 5% efficiency allowance.)

### 3.4 Assembler-declared vs hand-built packets

Some claims only exist for a packet that says it came from the Phase 40C assembly
policy — canonical ordering, coverage completeness, the empty-`context_summaries`
rule, and the derived identifier. Those checks run only when the packet's
metadata declares `assembly_version`. A hand-built packet never made those
claims, so holding it to them would reject legitimate input; it is checked
against the contract alone. An **unrecognized** assembly version is fail-closed:
its eligibility, ranking, and bounds rules are unknown, so none of its derived
claims can be checked against anything.

### 3.5 Two layers, not one

The Phase 40B models already enforce field shape — bounds, enum membership,
metadata safety, identifier uniqueness, dangling cross-references, and the
readiness rules a constructed packet must satisfy. Phase 40D does not
re-implement field parsing. It restates the *semantic* rules a bypassed
construction path could evade (`model_construct`, `model_copy`, a
partially-migrated producer, a future transport that rebuilds a packet
field-by-field) and adds the cross-record and cross-assembler checks Pydantic
cannot express at all. A guardrail that assumes its input was validated elsewhere
guards nothing.

`read_only` is deliberately **not** re-checked: it is pinned by the Phase 40B
model, it says nothing about whether the *evidence* is trustworthy, and adding a
diagnostic code for it would widen the taxonomy without widening the guarantee.

### 3.6 Severity belongs to the code, not to the caller

`DIAGNOSTIC_SEVERITY` maps every diagnostic code to a fixed severity, and
`GroundingValidationDiagnostic` fills it in — rejecting a supplied severity that
disagrees. A blocking condition therefore cannot be filed as advisory by a
producer that would rather not block. This is the Phase 40D form of the Phase 40B
"no silent authority escalation" rule.

Blocking is the default posture. Exactly four codes are advisory, because each
leaves the packet's grounding fully trustworthy and traceable:

| Advisory code | Why it does not block |
| --- | --- |
| `redundant_evidence_identity` | The same evidence recorded twice with identical material — wasteful, but nothing about it is untrue. |
| `unexpected_provenance_reference_kind` | Phase 37A permits every pointer kind on every reference, so this means "may not resolve", not "cannot be trusted". |
| `non_canonical_ordering` | Ordering is presentation. Reordering a packet changes no claim and drops no evidence. |
| `no_grounding_evidence` | An empty packet is a legitimate, honestly declared outcome; Phase 40B already forbids it from claiming `ready`. |

### 3.7 Diagnostics carry no secrets

Messages contain counts, closed-enum literals, and packet-local identifiers only.
A reference *value* — a path, a remote, a command, an excerpt — is never echoed,
**even when the value is exactly what the guardrail rejected**. Phase 40C kept raw
provider material out of packets; Phase 40D must not reintroduce it through a
diagnostic. Tests assert that an absolute path and a credential-bearing URL never
appear in any message.

## 4. Rules implemented

### 4.1 Evidence identity

Canonical identity is `(grounding_kind, NFC-normalized source record id)` — the
assembler's own key, reused unchanged. Including the family is what stops two
genuinely different records collapsing merely because two subsystems use the same
provider id; excluding it would invent an equivalence the assembler explicitly
refuses to make.

- duplicate evidence identifiers → **blocking**
- same canonical identity with conflicting declared sources → **blocking**
  (`conflicting_source_identity`)
- same canonical identity with materially different content → **blocking**
  (`conflicting_evidence_identity`)
- same canonical identity with identical material → **advisory**
- a grounding family with no verified Hive|Mind normalization → **blocking**
- Unicode-equivalent identifiers collide by NFC, exactly as the assembler
  normalizes them
- findings are computed from sorted, string-keyed groupings, so they do not
  depend on the order references appear in

### 4.2 Provenance

Per family, because the canonical contract intentionally distinguishes them:

- no usable pointer value → **blocking** (`malformed_provenance_identifier`)
- no source record identifier → **blocking** (`missing_provenance_reference`)
- repository-family evidence with no declared producing source → **blocking**
  (`missing_provenance_source`)
- conflict or context summary citing evidence the packet does not carry, or a
  conflict resolving fewer than two packet records → **blocking**
  (`dangling_evidence_reference`)
- a context summary attributed to no evidence → **blocking**
  (`ungrounded_context_summary`)
- an assembler-declared packet carrying summaries at all → **blocking**
  (`unexpected_context_summary`; `context_summaries` is the one collection the
  packet identifier does not cover, so this is the check that closes that gap)
- a pointer kind outside the set Hive|Mind's producers emit for that family →
  **advisory**

`active_memory_evidence_record` has no expected pointer-kind set on purpose: the
assembler reuses the `EvidenceRecord`'s own reference verbatim, and such a record
may legitimately point at any of the ten Phase 37A pointer kinds.

### 4.3 Repository and source safety

Fail-closed, exactly as Phase 40C established:

- unsafe repository identity recorded in the packet's own assembly diagnostics →
  **blocking**, packet-scoped. It is deliberately *not* attached to any evidence
  reference, so the safe evidence that survived alongside it is not
  misrepresented as unsafe, and the packet is still fully validated rather than
  discarded.
- a `file_path` pointer that is absolute or contains a traversal segment, or any
  pointer embedding `user:password@` in a URL authority → **blocking**,
  record-scoped, so exactly the offending record is named.

Neither is ever normalized away into a trusted identity.

### 4.4 Packet consistency

Recomputed, never trusted: accepted-evidence totals against the actual reference
count, accepted against inspected, critical-conflict totals against the actual
conflicts, per-family coverage totals and coverage completeness, the readiness
reason against the packet's contents (a blocking reason with a non-blocked
readiness, a ready reason with a non-ready readiness, `ready` alongside warnings,
`ready_with_warnings` with none, `no_eligible_evidence` with evidence,
`missing_requested_context` with no gaps), the Phase 40B `ready` rules, canonical
ordering of conflicts/coverage/warnings, and the re-derived packet identity.

A declared `critical_evidence_truncated` or `unrepresentable_critical_conflict`
reason additionally raises `unknown_critical_evidence`: the packet is not merely
blocked, it is knowingly incomplete about the evidence that mattered most.

### 4.5 Bounds, truncation and overflow

Packet-level and per-family bounds are checked against the same
`GroundingAssemblyLimits` the assembler applies, including lifting the per-family
cap when only one family contributed. Oversized identifiers, labels, summaries,
and metadata bags are reported. Truncation counts must agree with the recorded
bounds-based exclusions, and any truncation must be represented by a
bounds-exceeded warning.

**Nothing is clipped, dropped, or repaired to bring a packet back inside a
bound.** An over-full packet is reported as over-full, and the report still
counts every reference the packet carries. Making an invalid packet *look* valid
by removing records is the exact failure this layer exists to prevent.

### 4.6 Readiness

`assessed_readiness` is computed:

- any blocking diagnostic → `blocked`, whatever the packet claims;
- otherwise the packet's own declaration stands.

A validator that upgraded an honestly `context_required` packet would be
re-assembling it, and one that downgraded a clean `ready` packet over advisory
findings would make "ready with warnings" unreachable — which Phase 40C
deliberately made reachable. `synthesis_ready` is true if and only if the
assessment is `ready`, and the report model rejects any combination that
disagrees. No universal per-family evidence requirement was invented: a family is
required only where the contract or the packet request says so.

### 4.7 Determinism

For identical semantic input the report is byte-identical: fixed codes, fixed
severity, canonical ordering by `(code, grounding_kind, subject_id, message)`,
deduplicated findings, and a readiness result that is a pure function of them.
Ordering and uniqueness are enforced by the report model itself, not only by the
producing service, so an out-of-order or duplicated diagnostic list is a
malformed report rather than a cosmetic difference.

## 5. Explicitly out of scope

No AI/LLM integration, synthesis text generation, *Musings* generation, *The
Loom* generation, prompt construction, model provider integration,
retrieval-augmented generation, Grounded Synthesis API endpoint, frontend panel,
review or approval workflow, export workflow, persistence, database migration,
repository/source/graph/Active Memory mutation, Obsidian importer change,
Repository Observer expansion, authentication change, rate limiting, new
dependency, or broad backend refactor. Phase 36K remained paused and untouched.

## 6. Validation

- focused Phase 40D tests: `apps/backend/tests/test_grounding_validation.py` —
  **64 passed**
- Phase 40C regression: `apps/backend/tests/test_grounding_context.py` and Phase
  40B contracts: `apps/backend/tests/test_grounded_synthesis_contracts.py` —
  **134 passed**
- full backend suite: **912 passed**
- `python -m compileall apps/backend/app` — clean
- `git diff --check` — clean

## 7. Recommended next phase

**Phase 40E — Grounded Synthesis API and Read-Only Workspace.** The grounded
input boundary now exists and is checkable; the natural next step is a thin
read-only surface for inspecting assembled packets and their validation reports,
before any producer is built.
