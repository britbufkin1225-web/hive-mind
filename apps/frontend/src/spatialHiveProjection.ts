/* Phase 36F — Spatial Hive pseudo-3D projection helpers.

   Pure, deterministic TypeScript that gives the read-only knowledge graph a
   *pseudo-3D point-cloud foundation*: every node receives a stable (x, y, z)
   spatial coordinate derived only from data the graph already has (layout
   position, degree, id hashes), and a small perspective projector maps those
   coordinates through the orbital camera pose (yaw / pitch / zoom) into
   screen-space position + scale + normalized depth.

   Nothing here is a 3D engine: no WebGL, no scene graph, no physics — just a
   closed-form rotate → perspective-divide projection the existing living-Hive
   presentation attaches to. Design constraints (mirroring graphLayout /
   graphViewModel):

   - Deterministic: identical graph data always yields identical spatial
     coordinates. No Math.random(), no time seeding, no per-session state.
   - Read-only: consumes layout output, mutates nothing, and never invents
     graph data — the z axis and the point-cloud drift are *display geometry*
     derived from real node identity/degree, not fake records.
   - Dependency-free: React/DOM are never touched; callers own rendering.

   Rationale for a separate module (vs growing graphLayout): the 2D ring layout
   remains the authoritative, selection-tested node arrangement. This module
   layers a spatial interpretation *underneath* the existing Hive polish, so
   the projection math is auditable in one place and the flat layout stays the
   single source of truth for graph structure. */

import type { GraphLayoutNode } from "./lib/graphLayout";
import type { OrbitalGraphCameraTransform } from "./orbitalGraphControl";

/** A node lifted into the spatial Hive model: the 2D layout position plus a
    stable depth coordinate and a bounded organic drift off the perfect ring.
    All coordinates are in viewBox units, centered like the layout itself. */
export interface SpatialHiveNode {
  id: string;
  type: string;
  degree: number;
  /** Node circle radius from the layout, carried for particle shells. */
  radius: number;
  /** World position: x/y start from the ring layout (plus deterministic
      drift); z is centered on 0, positive toward the viewer. */
  x: number;
  y: number;
  z: number;
  /** The 0..1 depth unit (0 = far, 1 = near) that also drives the discrete
      far/mid/near tiers, so continuous projection and tier styling agree. */
  zUnit: number;
}

/** One projected point: screen position, perspective scale, and normalized
    nearness (0 = deepest, 1 = closest) for fog/width/energy falloff. */
export interface ProjectedSpatialPoint {
  x: number;
  y: number;
  scale: number;
  depth: number;
}

// --- Tuning constants --------------------------------------------------------
//
// All values are in viewBox units (the graph draws in a 760×560 viewBox) and
// chosen so the resting field already reads as occupying depth (~±25% scale
// spread front-to-back) while the bounded orbital camera (yaw ≤ ~32°) can never
// project a node off-screen or through the camera plane.

/** Half-extent of the z axis: nodes live in z ∈ [-range, +range]. */
export const SPATIAL_HIVE_DEPTH_RANGE = 170;

/** Camera distance from the field centre at zoom 1. Zooming in shortens the
    distance (a dolly), so near objects grow faster than far ones — approach,
    not a flat uniform scale. */
export const SPATIAL_HIVE_CAMERA_DISTANCE = 620;

/** Perspective focal length: projected scale = focal / (distance - z). */
export const SPATIAL_HIVE_FOCAL_LENGTH = 560;

/** Floor for the perspective denominator so an extreme zoom-in can never
    divide by ~0 and fling a near node to infinity. */
export const SPATIAL_HIVE_MIN_PROJECTION_DEPTH = 90;

/** Zoom sanitization bounds — wider than the camera's own clamp (0.65..1.7)
    so the projector stays safe even if a caller feeds an unclamped pose. */
export const SPATIAL_HIVE_MIN_ZOOM = 0.4;
export const SPATIAL_HIVE_MAX_ZOOM = 2.2;

/** Max radial drift off the ring per node (toward/away from centre) and max
    tangential drift along it. Together they break the perfect-ring silhouette
    into an organic constellation without ever moving a node far enough to
    confuse its place in the layout. */
export const SPATIAL_HIVE_RADIAL_DRIFT = 30;
export const SPATIAL_HIVE_TANGENT_DRIFT = 18;

const DEG_TO_RAD = Math.PI / 180;

/** Stable string → unit float in [0, 1). A small FNV-1a hash normalized into
    the unit interval. Deterministic and dependency-free: identical ids always
    yield the identical value, so spatial coordinates, cluster phases, and
    particle shells are reproducible with no runtime randomness.
    (Phase 36F: moved here from KnowledgeGraphPanel so the projection, the
    depth tiers, and the particle field all share one hash source.) */
export function hashUnit(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

/** The canonical 0..1 depth unit for a node (0 = far, 1 = near). Structural
    depth brings busy hubs forward (degree-ranked) while a stable id hash
    spreads equal-degree nodes across the range. This is the exact formula the
    Phase 33C tier model used inline — exported so the discrete far/mid/near
    tiers and the continuous projection can never disagree about depth. */
export function computeSpatialDepthUnit(
  id: string,
  degree: number,
  maxDegree: number,
): number {
  if (maxDegree <= 0) {
    return hashUnit(id);
  }
  const degreeNorm = degree / maxDegree;
  return degreeNorm * 0.65 + hashUnit(id) * 0.35;
}

/**
 * Lift the deterministic 2D ring layout into the spatial Hive model. Each node
 * keeps its layout position as the anchor, gains a bounded hash-driven drift
 * (radial + tangential, so the silhouette reads as a suspended constellation
 * rather than a printed ring), and receives a stable z from its depth unit.
 * Pure function of the layout: same nodes in, same cloud out, every reload.
 */
export function buildSpatialHiveNodes(
  nodes: GraphLayoutNode[],
  width: number,
  height: number,
): Map<string, SpatialHiveNode> {
  const centerX = width / 2;
  const centerY = height / 2;
  const maxDegree = nodes.reduce((max, node) => Math.max(max, node.degree), 0);
  const spatial = new Map<string, SpatialHiveNode>();

  for (const node of nodes) {
    const zUnit = computeSpatialDepthUnit(node.id, node.degree, maxDegree);
    const z = (zUnit - 0.5) * 2 * SPATIAL_HIVE_DEPTH_RANGE;

    let x = node.x;
    let y = node.y;
    const dx = node.x - centerX;
    const dy = node.y - centerY;
    const dist = Math.hypot(dx, dy);
    if (dist > 1) {
      // Unit radial direction and its perpendicular, so the drift is expressed
      // relative to the ring: "a bit further out / in" plus "a bit around".
      const ux = dx / dist;
      const uy = dy / dist;
      const radial =
        (hashUnit(`${node.id}::radial`) - 0.5) * 2 * SPATIAL_HIVE_RADIAL_DRIFT;
      const tangent =
        (hashUnit(`${node.id}::tangent`) - 0.5) * 2 * SPATIAL_HIVE_TANGENT_DRIFT;
      x = node.x + ux * radial + -uy * tangent;
      y = node.y + uy * radial + ux * tangent;
    }

    spatial.set(node.id, {
      id: node.id,
      type: node.type,
      degree: node.degree,
      radius: node.radius,
      x,
      y,
      z,
      zUnit,
    });
  }

  return spatial;
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

/**
 * Project one world point through the camera pose into screen space.
 *
 * Order of operations: recentre → yaw (rotate about the vertical axis) →
 * pitch (rotate about the horizontal axis) → perspective divide against a
 * zoom-dollied camera distance. Positive yaw orbits the structure so its
 * right side comes toward the viewer; positive pitch tips the top toward the
 * viewer; zoom > 1 moves the camera closer (near points grow faster than far
 * points — true parallax, not a uniform scale).
 *
 * Pure and total: non-finite inputs are sanitized, the perspective denominator
 * is floored, and the returned depth is clamped to [0, 1].
 */
export function projectSpatialPoint(
  x: number,
  y: number,
  z: number,
  pose: OrbitalGraphCameraTransform,
  width: number,
  height: number,
): ProjectedSpatialPoint {
  const yaw = (Number.isFinite(pose.yaw) ? pose.yaw : 0) * DEG_TO_RAD;
  const pitch = (Number.isFinite(pose.pitch) ? pose.pitch : 0) * DEG_TO_RAD;
  const zoom = clamp(pose.zoom, SPATIAL_HIVE_MIN_ZOOM, SPATIAL_HIVE_MAX_ZOOM);

  const cx = (Number.isFinite(x) ? x : 0) - width / 2;
  const cy = (Number.isFinite(y) ? y : 0) - height / 2;
  const cz = Number.isFinite(z) ? z : 0;

  // Yaw: rotate about the vertical (y) axis.
  const cosY = Math.cos(yaw);
  const sinY = Math.sin(yaw);
  const x1 = cx * cosY + cz * sinY;
  const z1 = cz * cosY - cx * sinY;

  // Pitch: rotate about the horizontal (x) axis.
  const cosP = Math.cos(pitch);
  const sinP = Math.sin(pitch);
  const y2 = cy * cosP - z1 * sinP;
  const z2 = z1 * cosP + cy * sinP;

  // Perspective divide against the dollied camera distance.
  const distance = SPATIAL_HIVE_CAMERA_DISTANCE / zoom;
  const denom = Math.max(SPATIAL_HIVE_MIN_PROJECTION_DEPTH, distance - z2);
  const scale = SPATIAL_HIVE_FOCAL_LENGTH / denom;

  return {
    x: width / 2 + x1 * scale,
    y: height / 2 + y2 * scale,
    scale,
    depth: clamp(0.5 + z2 / (2 * SPATIAL_HIVE_DEPTH_RANGE), 0, 1),
  };
}

// --- Depth-driven atmosphere curves ------------------------------------------
//
// Small pure helpers so the fog/width language lives beside the projection that
// feeds it. All are bounded well away from 0: depth *recedes* elements, it
// never removes them — the existing tier/selection opacity hierarchy multiplies
// on top (the spatial wrapper is a separate element, so opacities compose).

/** Node fog: multiplies the node group's opacity by camera-relative depth.
    Floor 0.7 keeps the deepest node clearly present under the tier fades. */
export function spatialNodeFog(depth: number): number {
  return 0.7 + 0.3 * clamp(depth, 0, 1);
}

/** Edge fog: synapses soften with distance a touch more than nodes do, so far
    links recede into atmosphere while near links stay crisp. */
export function spatialEdgeFog(depth: number): number {
  return 0.55 + 0.45 * clamp(depth, 0, 1);
}

/** Depth-aware synapse width factor (multiplies each state's stroke width in
    CSS via --spatial-edge-w): near edges thicken slightly, far edges thin. */
export function spatialEdgeWidthFactor(depth: number): number {
  return 0.72 + 0.56 * clamp(depth, 0, 1);
}
