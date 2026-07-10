/* Phase 36F — Spatial Hive deterministic point-cloud particle field.

   Gives each node a small shell of orbiting dust — a point-cloud presence that
   makes clusters read as volumetric organisms suspended in depth rather than
   flat circles on a panel. Everything is derived from stable graph identity:

   - Particle counts scale with node degree (busier hubs carry denser clouds),
     capped globally so a large graph can never snowball the canvas work.
   - Every offset, size, and twinkle phase comes from FNV-1a hashes of
     `${nodeId}::p${index}` seeds — no Math.random(), no time seeding, so the
     identical graph renders the identical cloud on every reload.
   - Particles carry no data of their own and are drawn on a pointer-events:
     none canvas *behind* the SVG — pure atmosphere, never a click target,
     never a fake graph record.

   Rendering is plain Canvas 2D (no WebGL, no dependency): the caller owns the
   canvas transform (viewBox fitting + devicePixelRatio) and per-node energy
   styling, so this module stays a pure geometry + paint helper. */

import type { OrbitalGraphCameraTransform } from "./orbitalGraphControl";
import {
  hashUnit,
  projectSpatialPoint,
  spatialDepthGlow,
  type SpatialHiveNode,
} from "./spatialHiveProjection";

/** One deterministic dust particle anchored to a node's spatial position. */
export interface SpatialHiveParticle {
  nodeId: string;
  type: string;
  /** World position in viewBox units (shares the node coordinate space). */
  x: number;
  y: number;
  z: number;
  /** Base draw radius in viewBox units, before perspective scale. */
  size: number;
  /** Stable 0..1 twinkle phase so shimmer is per-particle, never synchronized. */
  phase: number;
}

/** Per-node styling the caller resolves from live Hive state: the node type's
    accent color plus an energy multiplier (selected/related/hover brighten
    their cluster; unrelated clusters recede while a selection is active). */
export interface SpatialParticleEnergy {
  color: string;
  energy: number;
}

/** Global particle budget: keeps the per-frame canvas pass trivially cheap
    even for a much larger graph than the current field. */
export const SPATIAL_HIVE_PARTICLE_CAP = 520;

/** Shell thickness: particles live between the node's rim and rim + spread.
    Deep enough that a cluster reads as a volume, not a rim decoration. */
export const SPATIAL_HIVE_PARTICLE_SPREAD = 46;

/** Particles per node: a base presence plus a degree bonus (cluster energy —
    hubs read as denser organisms), bounded per node. */
export function particleCountForDegree(degree: number): number {
  return 8 + Math.min(14, Math.round(degree * 3));
}

/**
 * Build the deterministic particle field for the spatial node cloud. Each
 * node's particles sit on a hash-seeded spherical shell around its (x, y, z)
 * anchor, slightly squashed vertically so clusters read as drifting swarms
 * rather than perfect bubbles. If the degree-driven total would exceed the
 * global cap, every node's count scales down proportionally (min 2), so the
 * budget holds without ever dropping a cluster entirely.
 */
export function buildSpatialHiveParticleField(
  nodes: SpatialHiveNode[],
): SpatialHiveParticle[] {
  const counts = nodes.map((node) => particleCountForDegree(node.degree));
  const total = counts.reduce((sum, count) => sum + count, 0);
  const budgetScale =
    total > SPATIAL_HIVE_PARTICLE_CAP ? SPATIAL_HIVE_PARTICLE_CAP / total : 1;

  const particles: SpatialHiveParticle[] = [];
  nodes.forEach((node, nodeIndex) => {
    const count = Math.max(2, Math.floor(counts[nodeIndex] * budgetScale));
    for (let i = 0; i < count; i += 1) {
      const seed = `${node.id}::p${i}`;
      // Uniform-ish direction on a sphere from two hashes (angle + cos φ).
      const theta = hashUnit(`${seed}::t`) * Math.PI * 2;
      const u = hashUnit(`${seed}::u`) * 2 - 1;
      const sinPhi = Math.sqrt(Math.max(0, 1 - u * u));
      // Bias the shell outward (pow < 1) so the cloud hugs the node's halo.
      const shell =
        node.radius +
        8 +
        Math.pow(hashUnit(`${seed}::r`), 0.65) * SPATIAL_HIVE_PARTICLE_SPREAD;
      particles.push({
        nodeId: node.id,
        type: node.type,
        x: node.x + shell * sinPhi * Math.cos(theta),
        // Slight vertical squash: swarms drift wide, not tall.
        y: node.y + shell * sinPhi * Math.sin(theta) * 0.85,
        z: node.z + shell * u * 0.9,
        size: 0.8 + hashUnit(`${seed}::s`) * 1.4,
        phase: hashUnit(`${seed}::ph`),
      });
    }
  });

  return particles;
}

/** Fallback tint when a node id has no resolved energy entry (should not
    happen in practice; matches the graph's identity violet). */
const FALLBACK_ENERGY: SpatialParticleEnergy = { color: "#8b7cf0", energy: 1 };

/** Memoized #rrggbb → "r, g, b" channel strings so the per-frame draw never
    re-parses colors. Unknown formats fall back to the identity violet. */
const rgbCache = new Map<string, string>();
function rgbChannels(hex: string): string {
  const cached = rgbCache.get(hex);
  if (cached) return cached;
  let channels = "139, 124, 240";
  if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    channels = `${r}, ${g}, ${b}`;
  }
  rgbCache.set(hex, channels);
  return channels;
}

/**
 * Paint the particle field through the camera pose. The caller has already set
 * the canvas transform so drawing happens in viewBox coordinates, and cleared
 * the frame. Depth drives both alpha (far dust dissolves into atmosphere) and
 * drawn radius (perspective scale); energy multiplies both so selected/related
 * clusters glow as one organism with their node while unrelated clusters calm
 * down during a selection.
 *
 * `timeSec` + `animate` drive an optional, deterministic shimmer (a phase-
 * offset sine — bounded, slow, and per-particle). Callers pass animate: false
 * for still frames and under reduced motion, which freezes the field at full
 * presence with zero movement.
 *
 * `displacementByNode` (Phase 36H, optional): transient presentation-only
 * elastic offsets keyed by anchor node id. A displaced anchor carries its
 * dust shell with it — the shell rides the same offset its node renders at —
 * so a pulled cluster stays one organism. The field itself is never mutated;
 * omitting the map (or an empty map) reproduces the 36F behavior exactly.
 */
export function drawSpatialHiveParticles(
  ctx: CanvasRenderingContext2D,
  particles: SpatialHiveParticle[],
  pose: OrbitalGraphCameraTransform,
  width: number,
  height: number,
  energyByNode: Map<string, SpatialParticleEnergy>,
  timeSec: number,
  animate: boolean,
  displacementByNode?: ReadonlyMap<
    string,
    { dx: number; dy: number; dz: number }
  > | null,
): void {
  for (const particle of particles) {
    const shift = displacementByNode?.get(particle.nodeId);
    const projected = projectSpatialPoint(
      particle.x + (shift?.dx ?? 0),
      particle.y + (shift?.dy ?? 0),
      particle.z + (shift?.dz ?? 0),
      pose,
      width,
      height,
    );
    const style = energyByNode.get(particle.nodeId) ?? FALLBACK_ENERGY;
    const twinkle = animate
      ? 0.72 + 0.28 * Math.sin((timeSec * 0.55 + particle.phase) * Math.PI * 2)
      : 1;
    // Brightness follows the shared projected-depth glow curve so dust and
    // every other depth-lit cue agree: near burns, far dissolves into fog.
    const alpha = Math.min(
      0.9,
      0.42 * spatialDepthGlow(projected.depth) * style.energy * twinkle,
    );
    if (alpha <= 0.01) continue;
    const radius =
      particle.size * projected.scale * (0.85 + 0.35 * style.energy);
    ctx.fillStyle = `rgba(${rgbChannels(style.color)}, ${alpha.toFixed(3)})`;
    ctx.beginPath();
    ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
    ctx.fill();
  }
}
