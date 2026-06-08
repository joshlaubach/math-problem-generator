export interface BoundingBox {
  x: number
  y: number
  w: number
  h: number
}

const COLLISION_MARGIN = 8

export class WhiteboardLayoutManager {
  private registry: BoundingBox[] = []

  /**
   * Find the lowest Y position >= startY where a block of blockHeight px fits
   * without colliding with any registered block (including COLLISION_MARGIN buffer).
   */
  findNextSlot(blockHeight: number, startY: number): number {
    let y = startY
    let changed = true
    while (changed) {
      changed = false
      for (const bb of this.registry) {
        // Does the candidate slot [y, y+blockHeight] overlap with this registered block?
        const overlaps = y < bb.y + bb.h + COLLISION_MARGIN && y + blockHeight + COLLISION_MARGIN > bb.y
        if (overlaps) {
          y = bb.y + bb.h + COLLISION_MARGIN
          changed = true
          break
        }
      }
    }
    return y
  }

  registerBlock(bbox: BoundingBox): void {
    this.registry.push(bbox)
  }

  /** Read bounding boxes of all Fabric.js objects on the student canvas. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getStudentOccupiedRegions(canvas: any): BoundingBox[] {
    if (!canvas) return []
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (canvas.getObjects() as any[]).map((obj) => {
        const r = obj.getBoundingRect?.() ?? { left: 0, top: 0, width: 0, height: 0 }
        return { x: r.left ?? 0, y: r.top ?? 0, w: r.width ?? 0, h: r.height ?? 0 }
      })
    } catch {
      return []
    }
  }

  /**
   * Given a student bounding box, return the best {x, y} to place an annotation.
   * Prefers right-of-student; falls back to left-of-student if near the canvas edge.
   */
  findAdjacentSlot(
    studentBbox: BoundingBox,
    canvasWidth: number,
    annotW = 220,
  ): { x: number; y: number } {
    const GAP = 16
    const rightX = studentBbox.x + studentBbox.w + GAP
    if (rightX + annotW <= canvasWidth - 8) {
      return { x: rightX, y: studentBbox.y }
    }
    // Try left of student work
    const leftX = studentBbox.x - annotW - GAP
    if (leftX >= 8) {
      return { x: leftX, y: studentBbox.y }
    }
    // Last resort: below student work, same x
    return { x: studentBbox.x, y: studentBbox.y + studentBbox.h + GAP }
  }

  clear(): void {
    this.registry = []
  }
}
