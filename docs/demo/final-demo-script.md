# Hive|Mind — Final Demo Script

Parent label: **devdevbuilds**

This is the **canonical, final demo walkthrough** for Hive|Mind. It packages the
existing project narrative into one clean, calm script you can read aloud in a
portfolio review, follow while recording a demo, or hand to someone reading the
repo cold. It is the presentation spine the project locks **before** returning to
UI work.

It pairs with the locked release-candidate scope in the
[Phase 20A Demo Release Candidate Planning](../release-readiness/phase-20a-demo-release-candidate-planning.md),
the [Roadmap](../roadmap.md), and the
[Portfolio Presentation Lock](portfolio-presentation-lock.md). Every claim here
matches the deterministic, read-only state described in those documents.

> **Supersedes earlier framing.** This script reflects the **current** state in
> which **all four** Intelligence Report sections — Temporal Decay, Dreaming
> Suggestions, Provenance Chains, and Query Trails — are backend-derived and
> read-only (Query Trails became backend-derived in Phase 16C). Where the older
> [docs/demo-script.md](../demo-script.md) still describes Query Trails as a "demo
> fixture," prefer this document. Use the accurate framing in
> [section 8](#8-how-to-explain-the-intelligence-report-surfaces) and
> [section 12](#12-what-not-to-claim-during-a-demo).

> **Honesty rule (read this first).** Hive|Mind is a **local-first, deterministic,
> demo-grade developer tool**. There is no AI/LLM, no live vault watcher, no graph
> mutation from the UI, and no persisted query history. Say the deferred parts out
> loud — disclosed limitations are a credibility signal, not a weakness.

Estimated length: ~5–7 minutes spoken, or a written walkthrough of roughly ten
beats.

---

## 1. Opening explanation / elevator pitch

> "This is Hive|Mind, built under my devdevbuilds label. It's a **local-first
> developer knowledge intelligence dashboard**: it organizes imported knowledge
> sources, visualizes how they relate, and derives deterministic, read-only
> intelligence signals — temporal decay, dreaming suggestions, provenance chains,
> and query trails — from existing structure rather than from any AI/LLM call."

Keep the opener to two or three sentences. The frame to set is simple: **source
material in, structured and inspectable knowledge out** — computed by reviewable
rules, not a black box.

## 2. Problem statement

> "Personal knowledge tools like Obsidian are excellent for writing and thinking,
> but the structure stays locked inside markdown files. There's no governed data
> model, no API, and no way to reason over the whole corpus. As a project grows,
> you lose track of where knowledge came from, what's gone stale, and how pieces
> connect."

The contrast to land:

- **Obsidian is where you think.** Notes, links, and ideas are authored there.
- **Hive|Mind is the layer above it.** The registry, normalization, graph, and
  analysis surface that turns that writing into structured, queryable knowledge.

## 3. Why Hive|Mind exists as a dev-tool

Frame it as a real product concept first, portfolio piece second.

> "Hive|Mind exists to give developers one place where knowledge organization,
> data provenance, query memory, and intelligence reporting come together — so the
> tooling improves organization, knowledge consistency, source tracking, workflow
> speed, and coordination instead of scattering them across files and tools."

Why it's designed the way it is:

- **Deterministic, backend-derived intelligence over hidden AI behavior.** Every
  signal is computed by reviewable rules over the store. The same state always
  produces the same report, which is what keeps the intelligence layer testable,
  auditable, and honest as it grows.
- **Stability and contracts before cleverness.** New surfaces land as additive,
  documented API contracts first, so the system evolves against a known shape.
- **Traceability before automation.** The system tracks where knowledge came from
  before it ever tries to act on it. Provenance is shown, never invented.

## 4. How the system is organized

> "The backend is FastAPI with Pydantic contracts over a local JSON-backed store I
> call `HiveStore`. Source content is normalized into a shared node/edge model
> rather than stored as raw markdown. The frontend is Vite, React, and TypeScript
> talking to that API. There's no database server, no auth layer, and no AI calls
> — it's a clean, inspectable, contract-first foundation."

The pipeline, stated as stages (each is implemented today unless noted):

1. **Source intake** — read content from a connected source (Obsidian today).
2. **Normalization** — map content into the shared node/edge model.
3. **Source Registry** — track each source, its status, and import metadata.
4. **Knowledge Graph** — project normalized records into a deterministic graph.
5. **Console / query layer** — run read-only commands against the store.
6. **Intelligence Report** — derive read-only signals over that structure.

If the backend is running, point at `/docs` (the FastAPI interactive docs) here —
it makes the contract-first design concrete.

## 5. Demo walkthrough order

Walk the surfaces in the order the data flows, so each panel builds on the last:

1. **README / repo landing** — set the one-paragraph story and the phase status.
2. **Backend health + API docs** — establish the FastAPI surface (`/api/health`,
   `/docs`).
3. **Source Registry** — show source governance: where knowledge entered.
4. **Obsidian Import** — show the concrete "bring your own knowledge" entry point.
5. **Knowledge Graph** — show the normalized structure, read-only.
6. **Intelligence Report** — the four backend-derived signals (the core of the
   story).
7. **Hive Console** — a safe app-command surface, not a shell.
8. **Agent Lab docs** — the coordination layer for the agent-assisted build.

## 6. What to show first in the app

Open on the **assembled dashboard** over a populated demo/import state — console,
registry, graph, and Intelligence Report visible together. The first impression
to create is *one coherent tool*, not a folder of prototypes. Then narrate the
backend connection indicator showing **Connected**, so the audience knows the
frontend is talking to a live API, not a mockup.

## 7. What each major surface demonstrates

- **Source Registry** — *governance.* Each connected source is tracked with its
  status and import metadata; selecting one opens an inspector. This is the
  foundation every downstream signal derives from. Do not overstate: sources are
  local records; there is **no live sync or remote catalog**.
- **Obsidian Import** — *intake.* The import flow reads markdown and normalizes it
  into the node/edge model, then records import metadata on the source. Do not
  overstate: it is a **one-shot read** — no filesystem watcher, no write-back.
- **Knowledge Graph** — *legibility.* A deterministic, read-only SVG projection of
  the normalized records, with a legend, summary stats, and a node/edge inspector;
  selecting a node highlights its connections and dims the rest. Do not overstate:
  **no physics simulation, no editing, no mutation** from the UI.
- **Intelligence Report** — *the differentiator.* Four backend-derived, read-only
  signals in one report, each with a visible evidence trail and an honest empty
  state. See section 8.
- **Hive Console** — *controlled query.* A safe app-command interface (`help`,
  `status`, `list nodes`) — not arbitrary code execution; unsafe shell-style
  commands are rejected.

## 8. How to explain the Intelligence Report surfaces

This is the part to frame most carefully. **All four sections are backend-derived
and read-only.** None is fixture-backed; none runs AI/LLM; none mutates anything.

- **Temporal Knowledge Decay** *(Phase 13A).*
  > "Each row is computed read-only from a node's actual store timestamps using
  > fixed thresholds — fresh ≤ 30 days, aging ≤ 90 days, then stale — with a
  > plain-language reason for every classification and no AI or scoring model."

  Indicators are advisory; nothing is mutated. Still ahead: richer
  last-referenced / last-seen signals beyond import and update times.

- **Dreaming Suggestions** *(Phase 14C).*
  > "These are conservative `duplicate` / `orphan` / `stale-link` suggestions
  > derived from the actual graph nodes and edges, each carrying an explainable
  > evidence trail."

  Suggestions are **advisory and never auto-applied**. `source_coverage_gap` is a
  deferred contract decision; `unresolved_query` stays blocked until query history
  is persisted.

- **Provenance Chains** *(Phase 15C).*
  > "These are deterministic source / import / node / edge lineage chains derived
  > from existing records, with backend-owned evidence. Where source metadata is
  > missing, it's shown honestly as partial or unknown — never invented."

- **Query Trails** *(Phase 16C).*
  > "These are deterministic `source_followup` / `knowledge_gap` /
  > `related_query_cluster` projections over existing source, node, and tag
  > structure — a read-only structural projection, with backend-owned evidence and
  > a clean empty section when nothing is derivable."

  Be explicit about the boundary: **Query Trails do not include persisted user
  query history.** The query-history-dependent categories (`repeated_query` /
  `unresolved_question`) stay **deferred** until local query persistence exists —
  fabricating query-memory records would be dishonest.

## 9. How to explain security hardening and release readiness

> "Security was reasoned about and evidenced, not decorated. The Phase 18 arc
> delivered a threat model, defensive API validation and error safety, an
> edge-case triage, an edge-case validation MVP, and two regression/evidence
> passes. Phase 19 consolidated that into a release-readiness posture with a demo
> evidence checklist and explicit boundaries."

State the boundary plainly:

> "This is a **demo-grade defensive posture for a local, single-user dev-tool — it
> is not production-hardened security.** There are no users, sessions, roles, or
> permissions; only the defensive request → API boundary from the Phase 18 work.
> Production controls — auth, rate limiting, deployment hardening, secrets, audit
> logging, monitoring — are deliberately out of scope until the runtime model
> changes."

See the
[Security Threat Model + Vulnerability Test Plan](../security/threat-model-and-vulnerability-test-plan.md),
the
[Phase 19A Security Cohesion + Release Readiness Planning](../security/phase-19a-security-cohesion-release-readiness-planning.md),
and the
[Phase 19B Release Readiness QA + Demo Evidence Pass](../release-readiness/phase-19b-release-readiness-qa-demo-evidence.md).

## 10. What is intentionally read-only / non-mutating

- The **Knowledge Graph** projects existing structure; it never edits the store.
- The **Intelligence Report** derives signals read-only; repeated reads are
  side-effect-free.
- **Dreaming Suggestions** are advisory and never auto-applied.
- The **Hive Console** runs read-only commands; unsafe commands are rejected.
- **Obsidian import** is a one-shot read with **no write-back** to the vault.

The point to make: inspecting Hive|Mind can never damage it. Read-only-first is a
deliberate design choice, not a missing feature.

## 11. What is intentionally deferred

Name these out loud — they are chosen constraints, not gaps to hide:

- **Persisted query history** (unblocks `repeated_query` / `unresolved_question`
  and Dreaming's `unresolved_query` pattern).
- **Richer temporal-decay signals** beyond import/update timestamps.
- **A live Obsidian watcher / write-back.**
- **Graph or intelligence mutation workflows** (wait until a human-reviewed
  workflow exists to gate them).
- **AI/LLM integration, embeddings, vector search** (only after a separate plan
  and guardrail review).
- **Auth, multi-user, cloud sync, production deployment.**
- **UI expansion / dashboard redesign** — intentionally deferred until this
  presentation spine is locked.

## 12. What not to claim during a demo

Do **not** say:

- "The app uses AI to find connections." *(There is no AI/LLM.)*
- "Temporal decay uses AI or a scoring model." *(It's plain timestamp thresholds.)*
- "The provenance engine traces every fact." *(It shows existing lineage only.)*
- "Query trails are persisted query history." *(They're a structural projection;
  history persistence is deferred.)*
- "It watches my vault live." *(Import is a one-shot read.)*
- "It's production-ready / secure / a SaaS." *(Local, single-user, demo-grade.)*

Use instead:

> "The Intelligence Report is read-only and fully backend-derived. Every signal is
> deterministic — timestamp thresholds, graph duplicate/orphan/stale rules,
> existing source/import/node/edge lineage, and structural query-trail projections
> — with no AI. Where a capability isn't built yet, like persisted query history,
> I say so."

## 13. Closing portfolio explanation

> "So that's Hive|Mind: a local-first developer knowledge intelligence dashboard
> that normalizes Obsidian notes into a governed, inspectable data model behind a
> clean FastAPI/React stack, then derives four deterministic, read-only
> intelligence signals from that structure. It was built in tightly scoped,
> reviewable phases — contracts first, deterministic read-only surfaces second,
> UI third — each with a guardrail doc and recorded QA evidence."

For a reviewer, it demonstrates:

- **End-to-end ownership** — data model, import pipeline, graph visualization, and
  a derived intelligence layer, designed, built, documented, and QA'd across a
  recorded phase history.
- **Engineering judgment over feature count** — a bounded scope done well, with
  deferred work named explicitly.
- **Security reasoning, evidenced** — a threat model, a hardening arc, and
  regression evidence.
- **Honesty as a feature** — the deterministic, read-only, local-first framing is
  precise about what the tool does and does not do.

> **Agent-assisted, human-reviewed.** Hive|Mind's development is agent-assisted but
> human-reviewed. Agents may propose, organize, draft, or review project work;
> **devdevbuilds remains the human decision-maker, reviewer, validator, and merge
> gate.** The coordination model lives in [docs/agent-lab/](../agent-lab/).

## 14. Future roadmap summary

The next wave keeps the intelligence layer honest and reviewable — contracts
first, deterministic read-only derivation second, frontend surfaces third:

- **Demo evidence capture** — execute the screenshot/evidence plan against real
  app state (see the
  [Phase 20A screenshot/evidence plan](../release-readiness/phase-20a-demo-release-candidate-planning.md#screenshot--demo-evidence-plan)).
- **Query memory persistence** — local persistence and review surfaces, which
  would unblock the deferred query-history categories.
- **Richer intelligence signals** — last-referenced/last-seen decay inputs and
  selected-node provenance extension.
- **Security hardening continuation** — Obsidian import filesystem safety,
  intelligence-evidence regression, frontend rendering safety, and a
  dependency/static baseline; production-security controls stay out of scope until
  the runtime model changes.
- **UI expansion** — deliberately deferred until the demo narrative and this
  presentation spine are locked.

See the full [Roadmap](../roadmap.md) and the
[Intelligence Surface Plan](../intelligence-surface-plan.md) for detail.

---

## Pre-demo checklist

Run before presenting:

```bash
npm run check:frontend
npm run check:backend
npm run dev:backend
npm run dev:frontend
```

Then confirm:

- Backend connection shows **Connected**.
- Source Registry renders records and inspector details.
- Knowledge Graph renders nodes/edges, the legend, and selected-item details.
- Intelligence Report renders all four backend-derived sections — Temporal Decay,
  Dreaming Suggestions, Provenance Chains, and Query Trails — each read-only.
- Console accepts `help` / `status` and rejects unsafe commands.
