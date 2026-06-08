import { MINOR_GRID } from './GridRenderer'

interface Point { x: number; y: number }

/** Snap a world-coordinate point to the nearest minor grid lattice. */
export function snapToGrid(p: Point, zoom: number): Point {
  return {
    x: Math.round(p.x / MINOR_GRID) * MINOR_GRID,
    y: Math.round(p.y / MINOR_GRID) * MINOR_GRID,
  }
}

/** Key points of interest on a Fabric object (world coordinates). */
function getObjectSnapPoints(obj: any): Point[] {
  const pts: Point[] = []
  const cx = obj.left + (obj.width ?? 0) * (obj.scaleX ?? 1) / 2
  const cy = obj.top  + (obj.height ?? 0) * (obj.scaleY ?? 1) / 2
  const w2 = (obj.width ?? 0) * (obj.scaleX ?? 1) / 2
  const h2 = (obj.height ?? 0) * (obj.scaleY ?? 1) / 2

  // Center
  pts.push({ x: cx, y: cy })
  // Four corners
  pts.push({ x: cx - w2, y: cy - h2 })
  pts.push({ x: cx + w2, y: cy - h2 })
  pts.push({ x: cx + w2, y: cy + h2 })
  pts.push({ x: cx - w2, y: cy + h2 })
  // Midpoints of edges
  pts.push({ x: cx,       y: cy - h2 })
  pts.push({ x: cx,       y: cy + h2 })
  pts.push({ x: cx - w2, y: cy       })
  pts.push({ x: cx + w2, y: cy       })

  // For line-like objects, endpoints
  if (obj.x1 !== undefined && obj.x2 !== undefined) {
    pts.push({ x: obj.x1, y: obj.y1 })
    pts.push({ x: obj.x2, y: obj.y2 })
  }

  return pts
}

/**
 * Snap a world-coordinate point to nearby object snap points.
 * Returns the snapped point and a snap indicator (world coords), or null if no snap.
 * @param excludeId  Fabric object id to exclude (the object being dragged)
 */
export function snapToObjects(
  p: Point,
  canvas: any,
  zoom: number,
  excludeId?: string,
): { snapped: Point; indicator: Point } | null {
  const THRESHOLD_PX = 12   // screen pixels
  const thresholdWorld = THRESHOLD_PX / zoom

  let best: { dist: number; pt: Point } | null = null

  for (const obj of canvas.getObjects()) {
    if (obj.id === excludeId) continue
    for (const sp of getObjectSnapPoints(obj)) {
      const dx = sp.x - p.x
      const dy = sp.y - p.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < thresholdWorld && (!best || dist < best.dist)) {
        best = { dist, pt: sp }
      }
    }
  }

  if (!best) return null
  return { snapped: best.pt, indicator: best.pt }
}
