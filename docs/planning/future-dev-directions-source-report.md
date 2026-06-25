# Hive|Mind — Future Development Directions Source Report

> **Status:** Planning source document — documentation only.
> **Purpose:** Capture future Hive|Mind development directions across all major product areas so later implementation phases can draw from a single, governed source of intent.

---

## How to Use This Document

This report is a **planning source**, not an implementation spec. It organizes the major
product sections, innovative feature directions, implementation timing, risk notes, and a
recommended phase order. Treat each section as a backlog of intent that downstream phase
plans (Phase 10A onward) refine into concrete tickets.

Nothing here authorizes app, backend, frontend, or dependency changes. Implementation is
gated behind the phase order at the end of this document.

---

## Product Angle

Hive|Mind is a **local intelligence workbench** for sources, Obsidian vaults, knowledge
graphs, agent-assisted development, and human-confirmed insight.

It should **not** become a generic dashboard or an AI chatbot wrapper. The intended
direction is a **hacker-tool / analyst-console interface** with strong source tracking,
graph intelligence, and governed AI-assisted workflows. Every surface should make
provenance, connection, and confidence legible to a human operator.

---

## 1. Source Registry

**Current role:** Tracks project/source inputs such as Obsidian imports, local data,
future external data, and agent/model sources.

**Future features:**

- Source trust profile
- Source health badge
- Source timeline
- Verification status
- Provenance depth
- Source-to-node relationship summary
- Import quality summary
- Source conflict detection

**Signature feature:** Source trust profile.

**Implementation timing:** After intelligence planning, before Dreaming. Source trust
should support provenance, decay, and confidence logic.

---

## 2. Obsidian Integration

**Current role:** Obsidian adapter/import foundation exists and is visible in the Source
Registry.

**Future features:**

- Vault intelligence summary
- Note cluster detection
- Orphan note detection
- Highly connected note detection
- Tag intelligence
- Unresolved wiki-link report
- Duplicate note/title candidates
- Backlink quality classification

**Signature feature:** Obsidian vault intelligence summary.

**Implementation timing:** After graph/source registry contracts are stable. Avoid live
sync until import behavior and data models are mature.

---

## 3. Knowledge Graph

**Current role:** Read-only graph API and custom read-only SVG graph visualization exist,
including node/edge selection and inspector sync.

**Future features:**

- Graph focus mode
- Graph path tracing
- Source overlay
- Confidence overlay
- Temporal decay overlay
- Dream suggestion overlay
- Query trail overlay
- Mini graph summary
- Cluster preview
- Node neighborhood isolation

**Signature feature:** Graph focus mode plus graph intelligence overlays.

**Implementation timing:** Graph focus mode should come before advanced Dreaming or
Temporal Decay UI.

---

## 4. Console / Hacker-Tool Surface

**Current role:** Frontend console panel exists and is connected to backend console/search
behavior.

**Future features:**

- Command history
- Suggested commands
- Structured result cards
- Copy result action
- Run last command
- Clear output
- Command examples
- Command grammar
- Console metadata
- Keyboard-first command flow

**Example future commands:**

```
search "FastAPI"
show sources
show graph stats
trace node "API Contracts"
show stale nodes
show dream suggestions
explain source obsidian-vault
```

**Signature feature:** Console Power UX.

**Implementation timing:** High-priority next UI feature track after current planning.
Supports hacker-tool identity.

---

## 5. Command Palette

**Current role:** Not implemented.

**Future features:**

- Ctrl+K command launcher
- Focus console
- Refresh graph
- Refresh sources
- Clear graph selection
- Open Agent Lab
- Toggle graph overlays
- Run previous command
- Jump to source registry
- Jump to selected node/edge

**Signature feature:** Keyboard-first command palette.

**Implementation timing:** After Console Power UX.

---

## 6. Inspector / Dossier Panel

**Current role:** Inspector syncs with selected graph node or edge.

**Future features:**

- Node dossier
- Edge dossier
- Source evidence stack
- Related nodes section
- Relationship evidence section
- Confidence and decay badges
- Provenance chain preview
- Activity involving selected object
- Suggested actions

**Signature feature:** Knowledge dossier panel.

**Implementation timing:** After command palette or directly after console polish.

---

## 7. Intelligence Layer

**Current role:** Planned but not implemented.

**Future features:**

- Provenance chains
- Query trails
- Temporal Knowledge Decay
- Confidence/uncertainty states
- Conflict detection
- Duplicate candidates
- Dream suggestions
- Human confirmation workflow

**Important rule:** Dreaming should suggest soft links, duplicates, stale nodes, and
unresolved patterns. It **must not mutate stored knowledge without explicit user
confirmation.**

**Signature feature:** Human-confirmed intelligence overlays.

**Implementation timing (recommended order):**

1. Intelligence Surface Planning
2. Provenance Chain Surface
3. Query Trails
4. Temporal Decay Read-Only UI
5. Dream Mode Read-Only Overlay
6. Confirmation workflow (later)

---

## 8. Agent Ops / Agent Lab

**Current role:** `docs/agent-lab` is being established as a source registry and workflow
governance layer for AI coding/planning/review agents.

**Future features:**

- Agent registry
- Agent role definitions
- Agent session ledger
- Prompt pack browser
- Source link verification tracker
- Agent scoring rubric
- Human decision log
- Context pack generator
- Agent performance dashboard
- Read-only Agent Registry API
- Agent Lab frontend panel

**Signature feature:** Agent session ledger plus context pack generator.

**Implementation timing:** Documentation/data now. App implementation later after source
shapes stabilize.

---

## 9. Activity Feed / System Log

**Current role:** Planned dashboard surface.

**Future features:**

- Typed intelligence events
- Source imported event
- Node created event
- Edge resolved event
- Query executed event
- Agent run completed event
- Human decision recorded event
- Dream suggestion generated event
- Stale node detected event
- Expandable event details
- Event filters

**Signature feature:** Typed intelligence event feed.

**Implementation timing:** After console/palette work or alongside Agent Ops read-only API.

---

## 10. Reports / Exports

**Current role:** Not implemented.

**Future features:**

- Knowledge Health Report
- Source Import Report
- Agent Run Report
- Graph Summary Report
- Stale Knowledge Report
- Dream Suggestion Report
- Portfolio Demo Report
- Markdown export
- JSON export
- README-ready summary export

**Signature feature:** Knowledge health and demo-readiness reports.

**Implementation timing:** After Query Trails, Agent Ops, and source/graph state provide
enough meaningful data.

---

## 11. Backend / Data Model

**Current role:** FastAPI foundation, store, source registry, Obsidian import, and graph
API exist.

**Future features:**

- Unified knowledge object model
- Evidence-first records
- Human confirmation fields
- Source-backed agent sessions
- Read-only APIs before mutation APIs
- Event model
- Report model
- Query trail model
- Provenance model
- Decay state model

**Suggested normalized objects:**

- Source
- Import
- Node
- Edge
- Query
- Agent Session
- Decision
- Event
- Report

**Evidence-first fields:**

- `created_by`
- `source_id`
- `confidence`
- `provenance`
- `human_confirmed`
- `created_at`
- `updated_at`

**Signature feature:** Evidence-first backend contracts.

**Implementation timing:** After planning docs and before advanced intelligence UI.

---

## 12. Frontend / Visual System

**Current role:** Functional dashboard with graph, source registry, console, and panels.

**Future features:**

- Hacker workbench layout
- Left nav
- Main graph/workspace
- Right inspector dossier
- Bottom console
- Activity/system log
- UI modes
- Semantic badge system
- Design tokens
- Graph overlay styling
- Confidence/decay visual states
- Agent role visual states

**Future UI modes:**

- Explore Mode
- Console Mode
- Source Mode
- Agent Ops Mode
- Dream Mode
- Decay Mode
- Report Mode

**Signature feature:** Dark intelligence workbench layout.

**Implementation timing:** Do not do a giant redesign immediately. Build through controlled
UI phases.

---

## 13. Testing / QA / Governance

**Current role:** Manual phase validation is already part of workflow.

**Future features:**

- Phase validation checklist
- Guardrail audit
- Demo readiness score
- Changed-file scope checker
- Forbidden dependency checker
- Session note required check
- Backend-touched warning
- README/status consistency check

**Demo readiness score:**

| Score | Meaning |
| ----- | --------------- |
| 0 | Broken |
| 1 | Compiles |
| 2 | Usable |
| 3 | Demo-safe |
| 4 | Screenshot-ready |
| 5 | Portfolio-grade |

**Signature feature:** Demo readiness scoring.

**Implementation timing:** Start through Agent Ops docs. Add scripts later.

---

## Recommended Phase Order

### Immediate docs / data

1. Commit Agent Lab docs foundation.
2. Add Agent Ops workflow direction docs.
3. Add machine-readable YAML registry.
4. Add prompt packs.
5. Add this future development directions source report.

### Next app phases

1. Phase 10A — Intelligence Surface Planning
2. Phase 10B — Console Power UX
3. Phase 10C — Command Palette
4. Phase 10D — Inspector Dossier Upgrade

### Then intelligence surfaces

1. Phase 11A — Provenance Chain Surface
2. Phase 11B — Query Trails
3. Phase 11C — Temporal Decay Read-Only UI
4. Phase 11D — Dream Mode Read-Only Overlay

### Then Agent Ops app layer

1. Agent Ops API — read-only registry/session/source endpoints
2. Agent Lab UI — frontend panel
3. Agent Performance Dashboard
4. Context Pack Generator

### Then demo / product flex

1. Reports / Exports
2. Workbench Layout Polish
3. Graph Overlay Modes
4. Portfolio Demo Mode

---

## Core Product Principle

Each project area should answer a clear question:

- **Source Registry:** Where did this knowledge come from?
- **Graph:** How is this knowledge connected?
- **Inspector:** What does this object mean?
- **Console:** How do I operate the system?
- **Intelligence:** What deserves attention?
- **Agent Ops:** How is AI-assisted development governed?
- **Activity Feed:** What changed?
- **Reports:** What matters enough to export or present?
- **Backend:** What evidence supports this record?
- **Frontend:** Can the user understand and control the system quickly?

---

## Guardrails

This document is **documentation-only**. It does not authorize implementation work. The
following are explicitly out of scope for any task that produces or consumes this report
as its sole deliverable:

- No app code.
- No backend changes.
- No frontend changes.
- No dependencies.
- No Phase 10 implementation.
- No Dreaming implementation.
- No Temporal Decay implementation.
- No graph mutation controls.
- No dashboard redesign.
