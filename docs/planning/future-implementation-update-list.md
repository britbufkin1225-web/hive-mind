# Hive|Mind — Future Implementation Update List

**Purpose**

This document defines **future implementation targets only**. None of the items below should be treated as completed simply because they are listed here.

When planning or implementing work:

* Treat this as a forward-looking roadmap.
* Verify the current repository state before beginning any implementation.
* Do not assume a phase has been merged unless Git confirms it.
* Preserve existing architectural guardrails.
* Avoid expanding scope beyond the phase currently being implemented.

## Implementation Authority

This document is a catalog of approved future feature directions and long-term implementation goals.

It is **not** an implementation contract.

When conflicts exist, implementation authority follows this order:

1. The active phase planning document (currently
   [Phase 36G — Elastic Spatial Hive Manipulation Planning](phase-36g-elastic-spatial-hive-manipulation-planning.md))
2. [`docs/roadmap.md`](../roadmap.md)
3. This document
4. Historical planning documents

Features listed here should only be implemented when explicitly scheduled by a future project phase. Listing an approach below does not authorize it.

---

# Frontend Future Implementation

## 1. Infinite Spatial Graph Navigation

Evolve the current constrained orbit model toward unconstrained, freeform spatial navigation — the graph should feel like a handled object that can be spun without artificial stops.

**Currently approved direction (Phase 36G interaction contract):**

The approved implementation path is **wrapped (unbounded, wrap-normalized) yaw with a controlled pitch clamp** — endless horizontal rotation with a pitch range that keeps the structure from flipping and keeps billboard labels readable, while preserving the intended freeform feel. See the
[Phase 36G planning document](phase-36g-elastic-spatial-hive-manipulation-planning.md) (§6, Option A), which governs implementation.

Long-term objectives (within that direction):

* Infinite graph rotation
* Smooth momentum
* Configurable damping
* Stable reset/recenter
* Motion-control compatibility
* Mouse, touch, and keyboard support

**Possible future evolution (not currently authorized):**

* Arcball/trackball style manipulation
* Quaternion or equivalent full 3D orientation system

These were evaluated and deliberately deferred in Phase 36G (Options B/C). They require a dedicated future planning phase before any implementation, and would only be revisited if the wrapped-yaw model's feel proves insufficient.

Presentation only.

No graph data may be modified.

---

## 2. Elastic Node Manipulation

Allow direct manipulation of graph nodes.

The currently approved contract for this behavior is defined in the
[Phase 36G planning document](phase-36g-elastic-spatial-hive-manipulation-planning.md) (transient, presentation-only, closed-form displacement — no force simulation, no physics engine), which governs implementation.

Behavior:

* Grab individual nodes.
* Connected nodes follow naturally.
* Relationship strength influences displacement.
* Motion propagates through nearby graph regions.
* Nodes return toward home positions after release.

Graph data must remain immutable.

Only the visual presentation changes.

---

## 3. Physics-Based Graph Presentation

Introduce lightweight custom interaction physics.

Candidate behaviors:

* Spring return
* Inertia
* Momentum
* Relationship tension
* Cluster cohesion
* Hub mass
* Soft collision avoidance
* Energy dissipation
* Stable settling

Do not introduce a heavyweight physics engine unless a future phase explicitly authorizes it.

---

## 4. Advanced Interaction States

Expand interaction modes to include:

* Idle
* Hover
* Selected
* Rotating
* Dragging
* Elastic recovery
* Motion-controlled
* Recentering

Each state should provide subtle visual feedback without overwhelming the interface.

---

## 5. Motion-Control Completion

Continue development of webcam interaction.

Remaining work:

* Validate live hand-motion control feel with a human in frame (camera startup itself was live-validated in Phase 36F)
* Improve gesture reliability
* Resolve conflicts between manual and gesture input
* Improve gesture recovery after tracking loss
* Expand gesture vocabulary only after stable testing

Motion control remains opt-in.

---

## 6. Spatial Hive Refinement

Continue improving the 2.5D presentation.

Potential work:

* Better depth readability
* Improved label clarity
* Adaptive edge visibility
* Better particle layering
* Cluster atmosphere
* Focus framing
* Improved selection emphasis
* Depth-aware interaction
* Better dense-graph readability

---

## 7. Screenshot/Evidence Refresh

Perform only after:

* Graph interaction stabilizes
* Motion validation succeeds
* Major visual work is complete

Evidence should accurately reflect the current runtime.

---

# Backend Future Implementation

## 1. Query Trails

Implement persistent query history.

Potential capabilities:

* Query storage
* Result history
* Node references
* Source references
* Evidence tracking
* Unresolved query recording
* Read-only retrieval

---

## 2. Temporal Knowledge Decay

Continue backend intelligence development.

Future work:

* Dedicated decay service
* Evidence metadata
* Timestamp validation
* Unknown-state handling
* Expanded testing
* Stable deterministic output

---

## 3. Dreaming Intelligence

Expand deterministic Dreaming.

Future suggestion types include:

* Source coverage gaps
* Unresolved query patterns
* Additional heuristic recommendations

Dreaming must remain advisory.

No automatic graph mutation.

---

## 4. Provenance Chains

Expand provenance support.

Future goals:

* Complete derivation tracking
* Source lineage
* Import history
* Transformation history
* Provenance diagnostics

---

## 5. Source Registry Evolution

Potential additions:

* Health reporting
* Import metrics
* Warning summaries
* Refresh diagnostics
* Additional source types

---

## 6. Obsidian Import Improvements

Possible future enhancements:

* Metadata improvements
* Alias resolution
* Better markdown parsing
* Import previews
* Better diagnostics
* Improved re-import behavior

---

## 7. Graph API Expansion

Possible additions:

* Neighborhood queries
* Cluster queries
* Provenance-aware graph responses
* Temporal metadata
* Dreaming references
* Query references

Graph presentation remains frontend-owned.

---

## 8. Activity Logging

Possible additions:

* Query activity
* Intelligence events
* Import events
* Provenance events
* Source events
* Decay events

---

## 9. Security Hardening

Potential future work:

* Authentication
* Authorization
* Rate limiting
* Import validation
* Additional security testing
* Audit improvements

---

# Shared Frontend/Backend Goals

Future integration work should create seamless navigation between:

* Graph
* Intelligence Report
* Provenance
* Dreaming
* Temporal Decay
* Query Trails
* Activity Log

Every intelligence result should expose consistent evidence metadata.

---

# Long-Term Features

Potential future work:

* Session snapshots
* Intent-driven graph layouts
* Uncertainty tagging
* CLI ambient capture
* Optional local AI assistance
* Explainable intelligence summaries

These remain future roadmap items.

---

# Deferred Work

The following are intentionally deferred:

* Full WebGL migration
* Three.js / React Three Fiber
* Persistent manual graph layouts
* Full force-directed simulation
* Multi-camera gesture fusion

These require dedicated planning before implementation.

---

# Implementation Guardrails

Claude should preserve the following principles during every future phase:

* Thin routers
* Service-owned logic
* Deterministic behavior
* Read-only intelligence
* No silent graph mutation
* Stable API contracts
* Presentation separated from knowledge
* Incremental implementation
* Comprehensive regression testing
* Portfolio-quality documentation

Future implementation should prioritize polish, architectural consistency, deterministic behavior, and maintainability over rapid feature expansion.
