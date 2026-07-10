/* Phase 36H — Elastic Spatial Hive manipulation helpers.

   Pure, deterministic TypeScript implementing the Phase 36G elastic contract:
   a grabbed node can be temporarily displaced, the displacement propagates
   along *real graph relationships* with bounded, monotonically decaying
   strength, and everything recovers to the deterministic home positions on
   release. Nothing here is a physics simulation — the model is closed-form:

       displayDisplacement(node) = grabbedDisplacement
                                 × hopAttenuation(graphDistance(node))
                                 × recoveryFactor

   where hopAttenuation is a fixed weight table over BFS hop distance
   (1.0 → 0.45 → 0.18 → 0) and recoveryFactor is an exponential decay applied
   after release. Rationale for closed-form over a force simulation (36G §7):
   given the same graph, the same grab, and the same pointer path, the
   deformation is identical — deterministic like the rest of the spatial
   stack — it needs no integrator, no per-node velocity state, no iterative
   convergence, no physics dependency, its per-frame cost is O(affected
   nodes), and every rule is unit-testable as a pure function in this one
   file. A general force solver would buy organic chaos the read-only Hive
   explicitly does not want, at the price of nondeterminism and tuning drift.

   Design constraints (mirroring spatialHiveProjection / orbitalGraphControl):
   - Deterministic: no Math.random(), no clocks, no hidden state.
   - Presentation-only: displacements are transient offsets applied between
     the deterministic world coordinates and the projector. Nothing here ever
     reads or writes graph data, layout, selection, or persistence.
   - Dependency-free: React/DOM are never touched; callers own rendering. */

// --- Interaction ownership -----------------------------------------------------

/** Who currently owns spatial interaction. Exactly one owner at a time, so
    graph dragging, node grabbing, motion control, and reset can never apply
    competing control simultaneously (Phase 36H input-arbitration contract). */
export type SpatialInteractionOwner =
  | "none"
  | "graph-pointer"
  | "node-grab"
  | "motion-control"
  | "reset";

/** Resolve the single winning interaction owner from the active signals.
    Precedence (36H contract): an active node grab wins over an active graph
    drag, which wins over a reset in flight, which wins over motion control;
    motion control applies only when no pointer interaction owns the graph.
    Pure: same inputs, same owner. */
export function resolveSpatialInteractionOwner(input: {
  nodeGrabActive: boolean;
  graphDragActive: boolean;
  resetActive: boolean;
  motionControlEngaged: boolean;
}): SpatialInteractionOwner {
  if (input.nodeGrabActive) return "node-grab";
  if (input.graphDragActive) return "graph-pointer";
  if (input.resetActive) return "reset";
  if (input.motionControlEngaged) return "motion-control";
  return "none";
}

// --- Displacement vectors --------------------------------------------------------

/** A temporary world-space displacement in viewBox units. Never persisted. */
export interface ElasticVector {
  dx: number;
  dy: number;
  dz: number;
}

export const ELASTIC_VECTOR_ZERO: ElasticVector = Object.freeze({
  dx: 0,
  dy: 0,
  dz: 0,
});

function finite(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

export function elasticVectorMagnitude(v: ElasticVector): number {
  return Math.hypot(finite(v.dx), finite(v.dy), finite(v.dz));
}

// --- Relationship adjacency + bounded hop influence ------------------------------

/** Undirected adjacency (node id → neighbor ids) built once per graph-data
    change, never per frame. Edges are the only structural input — influence
    follows *real relationships*, so pulling a node visibly drags exactly the
    records related to it and nothing else (36G §8: edges are real data;
    spatial proximity in the ring layout is partly cosmetic). */
export function buildElasticAdjacency(
  edges: ReadonlyArray<{ source: string; target: string }>,
): Map<string, string[]> {
  const adjacency = new Map<string, string[]>();
  const link = (a: string, b: string) => {
    const list = adjacency.get(a);
    if (list) {
      if (!list.includes(b)) list.push(b);
    } else {
      adjacency.set(a, [b]);
    }
  };
  for (const edge of edges) {
    if (!edge.source || !edge.target || edge.source === edge.target) continue;
    link(edge.source, edge.target);
    link(edge.target, edge.source);
  }
  return adjacency;
}

/** Influence weight per BFS hop distance from the grabbed node. Index = hops.
    Monotone-decreasing by contract (a second-degree node never moves more
    than a first-degree node); anything beyond the table — three or more hops,
    or disconnected — receives exactly zero, so unrelated nodes stay still and
    the stillness itself shows where relationships end (36G §8). */
export const ELASTIC_HOP_WEIGHTS: readonly number[] = [1, 0.45, 0.18];

/** Maximum relationship distance that receives any influence. */
export const ELASTIC_MAX_HOPS = ELASTIC_HOP_WEIGHTS.length - 1;

/** Bounded breadth-first influence map from the grabbed node: node id →
    displacement weight. Computed once per grab (O(nodes + edges), never per
    frame) and reused for the whole gesture. Deterministic: same graph + same
    grabbed node → same weights. */
export function computeElasticInfluence(
  grabbedId: string,
  adjacency: ReadonlyMap<string, readonly string[]>,
  hopWeights: readonly number[] = ELASTIC_HOP_WEIGHTS,
): Map<string, number> {
  const weights = new Map<string, number>();
  if (!grabbedId || hopWeights.length === 0) return weights;
  weights.set(grabbedId, hopWeights[0]);
  let frontier: string[] = [grabbedId];
  for (let hop = 1; hop < hopWeights.length; hop += 1) {
    const next: string[] = [];
    for (const id of frontier) {
      for (const neighbor of adjacency.get(id) ?? []) {
        if (!weights.has(neighbor)) {
          weights.set(neighbor, hopWeights[hop]);
          next.push(neighbor);
        }
      }
    }
    if (next.length === 0) break;
    frontier = next;
  }
  return weights;
}

// --- Grab displacement: soft cap, easing, recovery -------------------------------

/** Maximum grabbed-node displacement magnitude in world/viewBox units. */
export const ELASTIC_MAX_DISPLACEMENT = 140;

/** Soft-cap a displacement vector: small pulls pass through nearly unchanged,
    and the effective magnitude eases asymptotically toward `max` via tanh —
    approaching the cap *is* the "graph resists stretching" feel (36G §7 soft
    limit), and no input sequence can ever exceed it, so a node can never be
    yanked off-screen or through the camera plane. Pure and total. */
export function softCapElasticDisplacement(
  v: ElasticVector,
  max: number = ELASTIC_MAX_DISPLACEMENT,
): ElasticVector {
  const dx = finite(v.dx);
  const dy = finite(v.dy);
  const dz = finite(v.dz);
  const magnitude = Math.hypot(dx, dy, dz);
  if (magnitude <= 0 || max <= 0) return ELASTIC_VECTOR_ZERO;
  const capped = max * Math.tanh(magnitude / max);
  const scale = capped / magnitude;
  return { dx: dx * scale, dy: dy * scale, dz: dz * scale };
}

/** Per-60fps-frame fraction the grabbed displacement moves toward the pointer
    target: a fast follow that still reads as tension, not teleportation. */
export const ELASTIC_GRAB_EASE = 0.32;

/** Retained fraction of a released displacement per 60fps-equivalent frame —
    the recovery factor's exponential decay toward home. */
export const ELASTIC_RECOVERY_RETAIN = 0.86;

/** Magnitude (world units) below which a displacement snaps to exact zero, so
    recovery provably settles instead of hovering asymptotically near rest. */
export const ELASTIC_SETTLE_EPSILON = 0.05;

const BASE_FRAME_MS = 1000 / 60;

/** Convert an elapsed frame time into a 60fps-equivalent frame count, clamped
    so a tab-throttled frame can never teleport the deformation. */
function framesFromDt(dtMs: number): number {
  const dt = Number.isFinite(dtMs) ? Math.min(Math.max(dtMs, 0), 100) : BASE_FRAME_MS;
  return dt / BASE_FRAME_MS;
}

/** Ease `current` toward `target` by `easePerFrame` per 60fps-equivalent
    frame (frame-rate independent via dt-scaled exponentiation), snapping to
    the target once within the settle epsilon. An ease of 1 follows the target
    exactly — the reduced-motion "position-coupled, no lag" posture. Pure. */
export function easeElasticVector(
  current: ElasticVector,
  target: ElasticVector,
  dtMs: number,
  easePerFrame: number = ELASTIC_GRAB_EASE,
): ElasticVector {
  const ease = Math.min(Math.max(finite(easePerFrame), 0), 1);
  if (ease >= 1) return { dx: finite(target.dx), dy: finite(target.dy), dz: finite(target.dz) };
  const a = 1 - Math.pow(1 - ease, framesFromDt(dtMs));
  const next: ElasticVector = {
    dx: finite(current.dx) + (finite(target.dx) - finite(current.dx)) * a,
    dy: finite(current.dy) + (finite(target.dy) - finite(current.dy)) * a,
    dz: finite(current.dz) + (finite(target.dz) - finite(current.dz)) * a,
  };
  const remaining = Math.hypot(
    next.dx - finite(target.dx),
    next.dy - finite(target.dy),
    next.dz - finite(target.dz),
  );
  return remaining <= ELASTIC_SETTLE_EPSILON
    ? { dx: finite(target.dx), dy: finite(target.dy), dz: finite(target.dz) }
    : next;
}

/** Decay a released displacement toward zero — the recovery factor. Retain 0
    (the reduced-motion profile) snaps home immediately; otherwise the vector
    shrinks by `retainPerFrame` per 60fps-equivalent frame and snaps to exact
    zero below the settle epsilon so the render loop's elastic work ends. */
export function decayElasticVector(
  v: ElasticVector,
  dtMs: number,
  retainPerFrame: number = ELASTIC_RECOVERY_RETAIN,
): ElasticVector {
  const retain = Math.min(Math.max(finite(retainPerFrame), 0), 1);
  if (retain <= 0) return ELASTIC_VECTOR_ZERO;
  const factor = Math.pow(retain, framesFromDt(dtMs));
  const next: ElasticVector = {
    dx: finite(v.dx) * factor,
    dy: finite(v.dy) * factor,
    dz: finite(v.dz) * factor,
  };
  return elasticVectorMagnitude(next) <= ELASTIC_SETTLE_EPSILON
    ? ELASTIC_VECTOR_ZERO
    : next;
}

// --- Screen → world displacement mapping ------------------------------------------

const DEG_TO_RAD = Math.PI / 180;

/** Map a screen-plane pointer displacement (already unscaled by the node's
    projected perspective scale, i.e. in world units at the node's depth) into
    a world-space displacement by inverse-rotating through the current camera
    pitch then yaw — the exact inverse of `projectSpatialPoint`'s rotation
    order. Because the rotations are linear, projecting `home + result`
    reproduces the screen delta exactly, so the grabbed node tracks the
    pointer in its own depth plane at any yaw/pitch (36G §7). Pure. */
export function screenDeltaToWorldDisplacement(
  sdx: number,
  sdy: number,
  yawDeg: number,
  pitchDeg: number,
): ElasticVector {
  const dxc = finite(sdx);
  const dyc = finite(sdy);
  const yaw = finite(yawDeg) * DEG_TO_RAD;
  const pitch = finite(pitchDeg) * DEG_TO_RAD;

  // Inverse pitch (rotate camera-space delta by -pitch about the x axis).
  const cosP = Math.cos(pitch);
  const sinP = Math.sin(pitch);
  const dy1 = dyc * cosP;
  const dz1 = -dyc * sinP;

  // Inverse yaw (rotate by -yaw about the vertical axis).
  const cosY = Math.cos(yaw);
  const sinY = Math.sin(yaw);
  return {
    dx: dxc * cosY - dz1 * sinY,
    dy: dy1,
    dz: dz1 * cosY + dxc * sinY,
  };
}

// --- Reduced-motion parameter selection --------------------------------------------

/** The tuning profile the driver reads for the active motion preference. */
export interface ElasticMotionProfile {
  /** Grab follow ease per frame; 1 = position-coupled, no lag/overshoot. */
  grabEase: number;
  /** Recovery retain per frame; 0 = snap home instantly on release. */
  recoveryRetain: number;
  /** Whether drag-release rotational momentum is allowed at all. */
  momentumEnabled: boolean;
}

/** Pick elastic/momentum parameters for the motion preference. Reduced motion
    keeps direct manipulation usable (a node tracking the user's own hand is
    position-coupled, not autonomous motion — 36G §11 posture (a)) while
    disabling everything autonomous: no momentum coast, no eased follow lag,
    no animated spring-back — release snaps home. */
export function elasticMotionProfile(reducedMotion: boolean): ElasticMotionProfile {
  return reducedMotion
    ? { grabEase: 1, recoveryRetain: 0, momentumEnabled: false }
    : {
        grabEase: ELASTIC_GRAB_EASE,
        recoveryRetain: ELASTIC_RECOVERY_RETAIN,
        momentumEnabled: true,
      };
}
