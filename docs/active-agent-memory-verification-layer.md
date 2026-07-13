# Active Agent Memory + Verification Layer — Reusable Reference

**Status:** Concept / reference only. **No implementation exists.** No runtime,
persistence, ingestion, contradiction engine, context-packet generator,
inspector, or repository observer has been built.
**Purpose:** a durable, contract-facing distillation of the vocabulary, record
types, state axes, evidence hierarchy, and contradiction classes for the Active
Agent Memory + Verification Layer, so later phases can cite a stable reference
without re-deriving concepts. The full rationale, problem framing, trust model,
lifecycle rules, security analysis, and phase sequence live in the
[Phase 37A planning doc](planning/phase-37a-active-agent-memory-verification-layer-planning.md).

> This layer remembers *what is currently true, why we believe it, and when to
> stop believing it* — as evidence-backed, supersedable records, computed into a
> read-only pre-action baseline, with humans keeping authority over decisions and
> mutation. It is **not** chat history, notes, logs, or semantic search.

---

## 1. Two state axes (keep separate)

- **Verification state** — *how strongly a claim is believed given evidence*:
  `unverified` · `partially_verified` · `verified` · `human_confirmed` ·
  `contradicted` · `superseded` · `retracted` · `stale` · `unresolvable`.
- **Lifecycle state** — *where the record sits in its life*: created → validated →
  (evidence attached) → verified → active / inactive (superseded · retracted ·
  stale · contradicted-out) → archived.

Records are **immutable**; change is expressed by **appending** new records and
new state/verification events, plus **supersession/retraction links**. History is
preserved, never overwritten.

## 2. Core distinctions

| Distinction | Short rule |
|---|---|
| Fact vs decision | Fact = verifiable "is" (repo evidence rules). Decision = chosen "ought" (human authority rules). |
| Claim vs verified fact | Storing a claim ≠ endorsing it; verified = evidence checked and sufficient. |
| Superseded vs contradicted | Superseded = orderly replacement (winner known). Contradicted = incompatible, unresolved (needs attention). |
| Stale vs false | Stale = was true, evidence aged out. False = asserted untrue (retract/contradict). |
| Confidence vs verification | Confidence = strength of support. Verification = standing/state. Separate axes. |
| Repo evidence vs human intent | Repo evidence decides facts; human intent decides decisions. Neither resolves the other's category. |
| Active vs original state | Original standing = immutable history. Active = computed, current, changeable. |

## 3. Record types (conceptual)

`ProjectFact` · `ProjectDecision` · `ProjectConstraint` · `PhaseStatusRecord` ·
`RepositoryStateRecord` · `CapabilityRecord` · `EvidenceRecord` ·
`ContradictionRecord` · `VerificationRecord` · `ContextPacket` (derived view).

Common spine: stable **identity** (subject + predicate + scope), a **claim**,
**evidence references**, **verification state** + **lifecycle state** (separate),
**source authority + observer**, **timestamps** (observed-at / recorded-at /
evidence-as-of), optional **supersession/retraction links**, append-only state
history. Perishability is carried by type: decisions/constraints are durable
(retired only by humans); repository-state and many facts are perishable (expire
by freshness). Full per-type fields in the planning doc §4.

## 4. Trust model (domain-aware)

Authority depends on **claim category**, not a global ranking:

- **Repository-state claims** → machine/VCS/CI evidence outranks unsupported prose.
- **Product-intent claims** → explicit human decisions are authoritative; committed
  docs are durable *supporting* evidence, not the authority.
- **Implementation-behavior claims** → code + tests + runtime + committed docs
  weighed together, **scoped** to what each demonstrates.

Trust is a policy over *absent/partial* evidence. Where in-scope evidence exists,
evidence governs. Deterministic and inspectable for the MVP — never LLM judgment.

## 5. Evidence hierarchy (claim-relative, strongest first)

1. Human confirmation (for intent) · 2. Repository command output / VCS queries ·
3. Test / CI output · 4. Runtime API responses · 5. Source-code references ·
6. Source-controlled docs · 7. Structured CLI / agent reports (only as strong as
the evidence they carry) · 8. Screenshots · 9. Video · 10. Conversational
summaries · 11. Inferred/reconstructed context.

**Scope discipline:** a screenshot proves visible UI state, not merge status; a
clean `git status` proves tree state at a moment, not runtime behavior; a commit
hash proves a commit exists, not that it is on `main`; a passing test proves the
tested cases, not "feel." Evidence carries: strength, scope, freshness, source,
timestamp, references, invalidation, aggregation.

## 6. Contradiction classes

**MVP (Phase 37D):** duplicate phase status · pending vs merged · frontend-only vs
backend modifications · current vs superseded decision · clean vs dirty
working-tree reports.

**Later (named, not MVP):** test-passed vs failing CI · capability vs missing code
· dependency-unchanged vs lockfile change · no-persistence vs migration ·
read-only vs mutation · endpoint-unchanged vs contract change · security vs unsafe
impl · evidence-scope mismatch · temporal conflict · identity collision ·
incompatible human decisions.

**Not a contradiction:** orderly temporal replacement · missing evidence (→
unverified) · scope mismatch · ambiguity (→ unresolved) · duplicates (→ dedup) ·
mere staleness · policy violation (→ validation/security). MVP rules are
conservative: prefer "unresolved / needs attention" over a false positive.

## 7. Active-state calculation

Deterministic and pure (same records in → same active set out). Per subject/scope
slot: match identity/scope → exclude superseded/retracted → require
`verified`/`human_confirmed`/scoped `partially_verified` → exclude
stale/contradicted/unresolvable → if unresolved contradiction, return "unresolved"
(do **not** pick a winner) → only then prefer most-recent among still-eligible.
**Never "newest wins."** When nothing is safely active, return an explicit
"no active record / unresolved" and expose the uncertainty.

## 8. Pre-action context packet

A **read-only**, bounded, deterministic bundle read *before* acting: project
identity · repository baseline (freshest, timestamped) · active roadmap position /
phase · verified completed phases · active decisions · active constraints · known
capabilities (and explicit gaps) · unresolved contradictions · stale/superseded
warnings · evidence references · verification summary · prohibited assumptions ·
generation timestamp. Only active records enter the baseline; contradictions and
uncertainty get their own sections; generating a packet never mutates anything.
An agent should honor constraints and **stop and ask a human** on unresolved
contradictions or missing baseline — never paper over uncertainty.

## 9. Boundaries

**Owns:** memory records, evidence references, verification/lifecycle state,
supersession/retraction links, contradiction-detection results, active-state
calculation, read-only context-packet generation.

**Must not become:** a graph database · a replacement for source documents · a
hidden chat-history store · an autonomous project manager · an unrestricted agent
scratchpad · a mutation engine · a vector-search dump · a repository watcher · an
"AI truth oracle." Must not mutate the Knowledge Graph. Human governance for
consequential state; **no command execution from records**; **no auto-trust of
prose**; reject/redact secrets; **no autonomous repository mutation**.

## 10. Phase sequence

`37A` Planning → `37B` Contract types / schema alignment → `37C` Deterministic
memory store MVP → `37D` Contradiction detection MVP → `37E` Pre-action context
packet → `37F` Active-memory frontend inspector → `37G` Agent session ingestion
planning → `37H` Repository observer planning. This is a **Track 2 —
Agent Intelligence Infrastructure** effort, parallel to and independent of
**Track 1 — Spatial Interaction** (active implementation phase: 36K).
