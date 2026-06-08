/**
 * All custom Fabric object subclasses.
 *
 * Exported as a factory `registerAllShapes(F)` that:
 *  1. Defines every class over the live Fabric module (avoids SSR import of fabric)
 *  2. Registers each class with classRegistry so loadFromJSON works
 *  3. Returns a map of constructors for use by MathWhiteboard drawing handlers
 */
import { evaluate as mjsEvaluate } from 'mathjs'
import { variableStore } from '../VariableStore'

// ── helpers ───────────────────────────────────────────────────────────────────

function toObj(base: Record<string, any>, extra: Record<string, any>) {
  return { ...base, ...extra }
}

// ── factory ───────────────────────────────────────────────────────────────────

export function registerAllShapes(F: any) {
  const { FabricObject, classRegistry } = F

  // ── 1. FabricFreeTriangle ─────────────────────────────────────────────────
  class FabricFreeTriangle extends FabricObject {
    static type = 'FabricFreeTriangle'
    relativeVertices: Array<{ x: number; y: number }> = [
      { x: 0,   y: -50 },
      { x: -50, y:  50 },
      { x: 50,  y:  50 },
    ]
    constructor(opts: any = {}) {
      super(opts)
      if (opts.relativeVertices) this.relativeVertices = opts.relativeVertices
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const [v0, v1, v2] = this.relativeVertices
      ctx.beginPath()
      ctx.moveTo(v0.x, v0.y)
      ctx.lineTo(v1.x, v1.y)
      ctx.lineTo(v2.x, v2.y)
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { relativeVertices: this.relativeVertices })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricFreeTriangle(data)) }
  }
  classRegistry.setClass(FabricFreeTriangle, 'FabricFreeTriangle')

  // ── 2. FabricRightTriangle ────────────────────────────────────────────────
  class FabricRightTriangle extends FabricObject {
    static type = 'FabricRightTriangle'
    constructor(opts: any = {}) {
      super(opts)
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height
      const x0 = -w / 2; const y0 = h / 2   // right-angle corner (bottom-left)
      ctx.beginPath()
      ctx.moveTo(x0,      y0)    // bottom-left (right angle)
      ctx.lineTo(x0 + w,  y0)    // bottom-right
      ctx.lineTo(x0,      y0 - h)// top-left
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
      // Right-angle marker (small square, 10×10)
      const ms = 10
      ctx.beginPath()
      ctx.moveTo(x0 + ms, y0)
      ctx.lineTo(x0 + ms, y0 - ms)
      ctx.lineTo(x0,      y0 - ms)
      ctx.strokeStyle = this.stroke as string || '#333'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricRightTriangle(data)) }
  }
  classRegistry.setClass(FabricRightTriangle, 'FabricRightTriangle')

  // ── 3. FabricIsoTriangle ─────────────────────────────────────────────────
  class FabricIsoTriangle extends FabricObject {
    static type = 'FabricIsoTriangle'
    constructor(opts: any = {}) {
      super(opts)
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height
      ctx.beginPath()
      ctx.moveTo(0,      -h / 2) // apex
      ctx.lineTo(-w / 2,  h / 2) // bottom-left
      ctx.lineTo( w / 2,  h / 2) // bottom-right
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricIsoTriangle(data)) }
  }
  classRegistry.setClass(FabricIsoTriangle, 'FabricIsoTriangle')

  // ── 4. FabricRegularPolygon ──────────────────────────────────────────────
  class FabricRegularPolygon extends FabricObject {
    static type = 'FabricRegularPolygon'
    sides = 6
    constructor(opts: any = {}) {
      super(opts)
      this.sides  = opts.sides  ?? 6
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = Math.min(this.width, this.height) / 2
      const n = Math.max(3, this.sides)
      const offset = -Math.PI / 2  // first vertex at top
      ctx.beginPath()
      for (let i = 0; i < n; i++) {
        const a = offset + (2 * Math.PI * i) / n
        const x = r * Math.cos(a); const y = r * Math.sin(a)
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
      }
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return toObj(super.toObject(inc), { sides: this.sides }) }
    static fromObject(data: any) { return Promise.resolve(new FabricRegularPolygon(data)) }
  }
  classRegistry.setClass(FabricRegularPolygon, 'FabricRegularPolygon')

  // ── 5. FabricAngleMarker ─────────────────────────────────────────────────
  class FabricAngleMarker extends FabricObject {
    static type = 'FabricAngleMarker'
    arcCount: 1 | 2 | 3 = 1
    angleDeg = 60
    showLabel = true
    constructor(opts: any = {}) {
      super(opts)
      this.arcCount  = opts.arcCount  ?? 1
      this.angleDeg  = opts.angleDeg  ?? 60
      this.showLabel = opts.showLabel ?? true
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = Math.min(this.width, this.height) / 2
      const rad = (this.angleDeg * Math.PI) / 180
      const sw = this.strokeWidth ?? 2
      const col = this.stroke as string || '#4a9eff'
      // Vertex at origin; first ray goes right (+x), second ray at angleDeg
      ctx.strokeStyle = col; ctx.lineWidth = sw; ctx.globalAlpha = this.opacity ?? 1
      // Ray 1 (→)
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(r, 0); ctx.stroke()
      // Ray 2 (at angleDeg above ray1)
      ctx.beginPath(); ctx.moveTo(0, 0)
      ctx.lineTo(r * Math.cos(-rad), r * Math.sin(-rad)); ctx.stroke()
      // Arcs
      const arcR = r * 0.35
      for (let i = 0; i < this.arcCount; i++) {
        const ar = arcR + i * 6
        ctx.beginPath(); ctx.arc(0, 0, ar, -rad, 0); ctx.stroke()
      }
      // Degree label
      if (this.showLabel) {
        const midA = -rad / 2
        const lx = (arcR + this.arcCount * 6 + 10) * Math.cos(midA)
        const ly = (arcR + this.arcCount * 6 + 10) * Math.sin(midA)
        ctx.fillStyle = col; ctx.font = `${Math.max(10, sw * 4)}px sans-serif`
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
        ctx.fillText(`${this.angleDeg}°`, lx, ly)
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { arcCount: this.arcCount, angleDeg: this.angleDeg, showLabel: this.showLabel })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricAngleMarker(data)) }
  }
  classRegistry.setClass(FabricAngleMarker, 'FabricAngleMarker')

  // ── 6. FabricRightAngleMarker ─────────────────────────────────────────────
  class FabricRightAngleMarker extends FabricObject {
    static type = 'FabricRightAngleMarker'
    constructor(opts: any = {}) {
      super(opts)
      this.width = opts.width ?? 20; this.height = opts.height ?? 20
    }
    _render(ctx: CanvasRenderingContext2D) {
      const s = Math.min(this.width, this.height)
      ctx.strokeStyle = this.stroke as string || '#4a9eff'
      ctx.lineWidth = this.strokeWidth ?? 2
      ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath()
      ctx.moveTo(0, 0); ctx.lineTo(s / 2, 0); ctx.lineTo(s / 2, -s / 2); ctx.lineTo(0, -s / 2)
      ctx.stroke()
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricRightAngleMarker(data)) }
  }
  classRegistry.setClass(FabricRightAngleMarker, 'FabricRightAngleMarker')

  // ── 7. FabricNumberLine ───────────────────────────────────────────────────
  class FabricNumberLine extends FabricObject {
    static type = 'FabricNumberLine'
    numStart = -5; numEnd = 5; step = 1; showLabels = true
    constructor(opts: any = {}) {
      super(opts)
      this.numStart   = opts.numStart   ?? -5
      this.numEnd     = opts.numEnd     ?? 5
      this.step       = opts.step       ?? 1
      this.showLabels = opts.showLabels ?? true
      this.width  = opts.width  ?? 200
      this.height = opts.height ?? 40
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height
      const col = this.stroke as string || '#4a9eff'
      ctx.strokeStyle = col; ctx.lineWidth = this.strokeWidth ?? 2
      ctx.globalAlpha = this.opacity ?? 1
      const range = this.numEnd - this.numStart
      const toX = (n: number) => ((n - this.numStart) / range) * w - w / 2
      // Main line
      ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2, 0); ctx.stroke()
      // Arrowheads
      const ah = 6
      ctx.beginPath()
      ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2 - ah, -ah / 2); ctx.lineTo(w / 2 - ah, ah / 2); ctx.closePath()
      ctx.fillStyle = col; ctx.fill()
      ctx.beginPath()
      ctx.moveTo(-w / 2, 0); ctx.lineTo(-w / 2 + ah, -ah / 2); ctx.lineTo(-w / 2 + ah, ah / 2); ctx.closePath()
      ctx.fill()
      // Ticks and labels
      const tickH = 8
      if (this.showLabels) {
        ctx.font = `${Math.max(8, Math.min(14, (w / range) * 0.3))}px sans-serif`
        ctx.fillStyle = col; ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      }
      for (let n = this.numStart; n <= this.numEnd; n += this.step) {
        const x = toX(n)
        ctx.beginPath(); ctx.moveTo(x, -tickH / 2); ctx.lineTo(x, tickH / 2); ctx.stroke()
        if (this.showLabels) ctx.fillText(String(n), x, tickH / 2 + 2)
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), {
        numStart: this.numStart, numEnd: this.numEnd, step: this.step, showLabels: this.showLabels,
      })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricNumberLine(data)) }
  }
  classRegistry.setClass(FabricNumberLine, 'FabricNumberLine')

  // ── 8. FabricBrace ───────────────────────────────────────────────────────
  class FabricBrace extends FabricObject {
    static type = 'FabricBrace'
    label = ''; direction: 'horizontal' | 'vertical' = 'horizontal'
    constructor(opts: any = {}) {
      super(opts)
      this.label     = opts.label     ?? ''
      this.direction = opts.direction ?? 'horizontal'
      this.width  = opts.width  ?? 150
      this.height = opts.height ?? 40
    }
    _render(ctx: CanvasRenderingContext2D) {
      const col = this.stroke as string || '#4a9eff'
      const sw = this.strokeWidth ?? 2
      ctx.strokeStyle = col; ctx.lineWidth = sw
      ctx.globalAlpha = this.opacity ?? 1
      const w = this.width; const h = this.height
      // Draw a simple curly brace pointing upward (from -w/2 to w/2, apex at 0, -h/2)
      const cx = 0; const cy = h / 4
      const r = h / 4
      ctx.beginPath()
      // Left half
      ctx.moveTo(-w / 2, cy + r)
      ctx.quadraticCurveTo(-w / 2, cy, -w / 2 + r, cy)
      ctx.lineTo(-r, cy)
      ctx.quadraticCurveTo(0, cy, 0, cy - r)
      // Right half (mirrored)
      ctx.moveTo(w / 2, cy + r)
      ctx.quadraticCurveTo(w / 2, cy, w / 2 - r, cy)
      ctx.lineTo(r, cy)
      ctx.quadraticCurveTo(0, cy, 0, cy - r)
      ctx.stroke()
      if (this.label) {
        ctx.fillStyle = col
        ctx.font = `${Math.max(11, sw * 5)}px sans-serif`
        ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
        ctx.fillText(this.label, 0, cy - r - 4)
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { label: this.label, direction: this.direction })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricBrace(data)) }
  }
  classRegistry.setClass(FabricBrace, 'FabricBrace')

  // ── 9. FabricDot ─────────────────────────────────────────────────────────
  class FabricDot extends FabricObject {
    static type = 'FabricDot'
    label = ''; dotRadius = 6
    constructor(opts: any = {}) {
      super(opts)
      this.label     = opts.label     ?? ''
      this.dotRadius = opts.dotRadius ?? 6
      this.width = opts.width ?? this.dotRadius * 2
      this.height = opts.height ?? this.dotRadius * 2
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = this.dotRadius
      const col = this.stroke as string || '#4a9eff'
      ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2)
      ctx.fillStyle = this.fill && this.fill !== 'transparent' ? this.fill as string : col
      ctx.fill()
      ctx.strokeStyle = col; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke()
      if (this.label) {
        ctx.fillStyle = col; ctx.font = `bold ${r + 6}px sans-serif`
        ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
        ctx.fillText(this.label, 0, -r - 2)
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { label: this.label, dotRadius: this.dotRadius })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricDot(data)) }
  }
  classRegistry.setClass(FabricDot, 'FabricDot')

  // ── 10. FabricVenn ───────────────────────────────────────────────────────
  class FabricVenn extends FabricObject {
    static type = 'FabricVenn'
    count: 2 | 3 = 2; vennLabels: string[] = ['A', 'B']
    constructor(opts: any = {}) {
      super(opts)
      this.count      = opts.count      ?? 2
      this.vennLabels = opts.vennLabels ?? (opts.count === 3 ? ['A','B','C'] : ['A','B'])
      this.width  = opts.width  ?? 200
      this.height = opts.height ?? 140
    }
    _render(ctx: CanvasRenderingContext2D) {
      const col = this.stroke as string || '#4a9eff'
      const sw = this.strokeWidth ?? 2
      ctx.globalAlpha = this.opacity ?? 0.5
      ctx.strokeStyle = col; ctx.lineWidth = sw
      const fill = this.fill && this.fill !== 'transparent' ? this.fill as string : 'rgba(74,158,255,0.15)'
      const w = this.width; const h = this.height
      const r = Math.min(w / 3, h / 2) * 0.9
      if (this.count === 2) {
        const cx1 = -r * 0.5; const cx2 = r * 0.5
        ctx.beginPath(); ctx.arc(cx1, 0, r, 0, Math.PI * 2)
        ctx.fillStyle = fill; ctx.fill(); ctx.stroke()
        ctx.beginPath(); ctx.arc(cx2, 0, r, 0, Math.PI * 2)
        ctx.fillStyle = fill; ctx.fill(); ctx.stroke()
        ctx.globalAlpha = this.opacity ?? 1
        ctx.fillStyle = col; ctx.font = `bold ${r * 0.3}px sans-serif`; ctx.textAlign = 'center'
        ctx.fillText(this.vennLabels[0] ?? 'A', cx1 - r * 0.5, 0)
        ctx.fillText(this.vennLabels[1] ?? 'B', cx2 + r * 0.5, 0)
      } else {
        // 3-circle Venn
        const triR = r * 0.55
        const angles = [-Math.PI / 2, Math.PI / 6, (5 * Math.PI) / 6]
        const cx = angles.map(a => triR * Math.cos(a))
        const cy = angles.map(a => triR * Math.sin(a))
        for (let i = 0; i < 3; i++) {
          ctx.beginPath(); ctx.arc(cx[i], cy[i], r, 0, Math.PI * 2)
          ctx.fillStyle = fill; ctx.fill(); ctx.stroke()
        }
        ctx.globalAlpha = this.opacity ?? 1
        ctx.fillStyle = col; ctx.font = `bold ${r * 0.3}px sans-serif`; ctx.textAlign = 'center'
        for (let i = 0; i < 3; i++) {
          const lx = cx[i] + r * 0.5 * Math.cos(angles[i])
          const ly = cy[i] + r * 0.5 * Math.sin(angles[i])
          ctx.fillText(this.vennLabels[i] ?? String.fromCharCode(65 + i), lx, ly)
        }
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { count: this.count, vennLabels: this.vennLabels })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricVenn(data)) }
  }
  classRegistry.setClass(FabricVenn, 'FabricVenn')

  // ── 11. FabricMatrix ─────────────────────────────────────────────────────
  class FabricMatrix extends FabricObject {
    static type = 'FabricMatrix'
    rows = 3; cols = 3; cells: string[][] = []
    constructor(opts: any = {}) {
      super(opts)
      this.rows  = opts.rows  ?? 3
      this.cols  = opts.cols  ?? 3
      this.cells = opts.cells ?? Array.from({ length: this.rows }, () => Array(this.cols).fill(''))
      this.width  = opts.width  ?? this.cols * 48
      this.height = opts.height ?? this.rows * 36
    }
    _render(ctx: CanvasRenderingContext2D) {
      const cw = this.width / this.cols
      const ch = this.height / this.rows
      const col = this.stroke as string || '#4a9eff'
      ctx.strokeStyle = col; ctx.lineWidth = this.strokeWidth ?? 1
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') {
        ctx.fillStyle = this.fill as string
        ctx.fillRect(-this.width / 2, -this.height / 2, this.width, this.height)
      }
      // Grid lines
      for (let r = 0; r <= this.rows; r++) {
        const y = -this.height / 2 + r * ch
        ctx.beginPath(); ctx.moveTo(-this.width / 2, y); ctx.lineTo(this.width / 2, y); ctx.stroke()
      }
      for (let c = 0; c <= this.cols; c++) {
        const x = -this.width / 2 + c * cw
        ctx.beginPath(); ctx.moveTo(x, -this.height / 2); ctx.lineTo(x, this.height / 2); ctx.stroke()
      }
      // Cell text
      ctx.fillStyle = col; ctx.font = `${Math.min(14, ch * 0.5)}px sans-serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      for (let r = 0; r < this.rows; r++) {
        for (let c = 0; c < this.cols; c++) {
          const tx = -this.width / 2 + (c + 0.5) * cw
          const ty = -this.height / 2 + (r + 0.5) * ch
          ctx.fillText((this.cells[r]?.[c]) ?? '', tx, ty)
        }
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { rows: this.rows, cols: this.cols, cells: this.cells })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricMatrix(data)) }
  }
  classRegistry.setClass(FabricMatrix, 'FabricMatrix')

  // ── 12. FabricVector ─────────────────────────────────────────────────────
  class FabricVector extends FabricObject {
    static type = 'FabricVector'
    constructor(opts: any = {}) {
      super(opts)
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 6
    }
    _render(ctx: CanvasRenderingContext2D) {
      const col = this.stroke as string || '#4a9eff'
      const sw = Math.max(3, this.strokeWidth ?? 3)
      const w = this.width; const ah = sw * 3
      ctx.strokeStyle = col; ctx.fillStyle = col
      ctx.lineWidth = sw; ctx.globalAlpha = this.opacity ?? 1
      ctx.lineCap = 'round'
      ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2 - ah, 0); ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(w / 2, 0)
      ctx.lineTo(w / 2 - ah, -ah * 0.6)
      ctx.lineTo(w / 2 - ah, ah * 0.6)
      ctx.closePath(); ctx.fill()
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricVector(data)) }
  }
  classRegistry.setClass(FabricVector, 'FabricVector')

  // ── 13. FabricLineSegment ────────────────────────────────────────────────
  class FabricLineSegment extends FabricObject {
    static type = 'FabricLineSegment'
    tickCount: 0 | 1 | 2 | 3 = 0
    constructor(opts: any = {}) {
      super(opts)
      this.tickCount = opts.tickCount ?? 0
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 4
    }
    _render(ctx: CanvasRenderingContext2D) {
      const col = this.stroke as string || '#4a9eff'
      const sw = this.strokeWidth ?? 2
      const w = this.width; const th = 12
      ctx.strokeStyle = col; ctx.lineWidth = sw; ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2, 0); ctx.stroke()
      // Tick marks at midpoint
      for (let i = 0; i < this.tickCount; i++) {
        const offset = (i - (this.tickCount - 1) / 2) * 5
        ctx.beginPath(); ctx.moveTo(offset, -th / 2); ctx.lineTo(offset, th / 2); ctx.stroke()
      }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { tickCount: this.tickCount })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricLineSegment(data)) }
  }
  classRegistry.setClass(FabricLineSegment, 'FabricLineSegment')

  // ── 14. FabricParallelogram ──────────────────────────────────────────────
  class FabricParallelogram extends FabricObject {
    static type = 'FabricParallelogram'
    skew = 0.3
    constructor(opts: any = {}) {
      super(opts)
      this.skew  = opts.skew  ?? 0.3
      this.width  = opts.width  ?? 120
      this.height = opts.height ?? 70
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height; const dx = w * this.skew
      ctx.beginPath()
      ctx.moveTo(-w / 2 + dx, -h / 2)
      ctx.lineTo( w / 2,       -h / 2)
      ctx.lineTo( w / 2 - dx,  h / 2)
      ctx.lineTo(-w / 2,        h / 2)
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return toObj(super.toObject(inc), { skew: this.skew }) }
    static fromObject(data: any) { return Promise.resolve(new FabricParallelogram(data)) }
  }
  classRegistry.setClass(FabricParallelogram, 'FabricParallelogram')

  // ── 15. FabricRhombus ────────────────────────────────────────────────────
  class FabricRhombus extends FabricObject {
    static type = 'FabricRhombus'
    constructor(opts: any = {}) {
      super(opts)
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width / 2; const h = this.height / 2
      ctx.beginPath()
      ctx.moveTo(0, -h); ctx.lineTo(w, 0); ctx.lineTo(0, h); ctx.lineTo(-w, 0)
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricRhombus(data)) }
  }
  classRegistry.setClass(FabricRhombus, 'FabricRhombus')

  // ── 16. FabricTrapezoid ──────────────────────────────────────────────────
  class FabricTrapezoid extends FabricObject {
    static type = 'FabricTrapezoid'
    topRatio = 0.6
    constructor(opts: any = {}) {
      super(opts)
      this.topRatio = opts.topRatio ?? 0.6
      this.width  = opts.width  ?? 120
      this.height = opts.height ?? 70
    }
    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height; const tw = w * this.topRatio
      ctx.beginPath()
      ctx.moveTo(-tw / 2, -h / 2)
      ctx.lineTo( tw / 2, -h / 2)
      ctx.lineTo( w  / 2,  h / 2)
      ctx.lineTo(-w  / 2,  h / 2)
      ctx.closePath()
      ctx.globalAlpha = this.opacity ?? 1
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return toObj(super.toObject(inc), { topRatio: this.topRatio }) }
    static fromObject(data: any) { return Promise.resolve(new FabricTrapezoid(data)) }
  }
  classRegistry.setClass(FabricTrapezoid, 'FabricTrapezoid')

  // ── 17. FabricArc ────────────────────────────────────────────────────────
  class FabricArc extends FabricObject {
    static type = 'FabricArc'
    startAngleDeg = 0; endAngleDeg = 90
    constructor(opts: any = {}) {
      super(opts)
      this.startAngleDeg = opts.startAngleDeg ?? 0
      this.endAngleDeg   = opts.endAngleDeg   ?? 90
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = Math.min(this.width, this.height) / 2
      const s = (this.startAngleDeg * Math.PI) / 180
      const e = (this.endAngleDeg   * Math.PI) / 180
      ctx.strokeStyle = this.stroke as string || '#4a9eff'
      ctx.lineWidth = this.strokeWidth ?? 2; ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath(); ctx.arc(0, 0, r, s, e); ctx.stroke()
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { startAngleDeg: this.startAngleDeg, endAngleDeg: this.endAngleDeg })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricArc(data)) }
  }
  classRegistry.setClass(FabricArc, 'FabricArc')

  // ── 18. FabricSector ─────────────────────────────────────────────────────
  class FabricSector extends FabricObject {
    static type = 'FabricSector'
    startAngleDeg = 0; endAngleDeg = 90
    constructor(opts: any = {}) {
      super(opts)
      this.startAngleDeg = opts.startAngleDeg ?? 0
      this.endAngleDeg   = opts.endAngleDeg   ?? 90
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = Math.min(this.width, this.height) / 2
      const s = (this.startAngleDeg * Math.PI) / 180
      const e = (this.endAngleDeg   * Math.PI) / 180
      ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, r, s, e); ctx.closePath()
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill() }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), { startAngleDeg: this.startAngleDeg, endAngleDeg: this.endAngleDeg })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricSector(data)) }
  }
  classRegistry.setClass(FabricSector, 'FabricSector')

  // ── 19. FabricAnnulus ────────────────────────────────────────────────────
  class FabricAnnulus extends FabricObject {
    static type = 'FabricAnnulus'
    innerRatio = 0.5
    constructor(opts: any = {}) {
      super(opts)
      this.innerRatio = opts.innerRatio ?? 0.5
      this.width  = opts.width  ?? 100
      this.height = opts.height ?? 100
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = Math.min(this.width, this.height) / 2
      const ir = r * Math.max(0.05, Math.min(0.95, this.innerRatio))
      ctx.globalAlpha = this.opacity ?? 1
      ctx.beginPath()
      ctx.arc(0, 0, r, 0, Math.PI * 2)
      ctx.arc(0, 0, ir, 0, Math.PI * 2, true)
      if (this.fill && this.fill !== 'transparent') { ctx.fillStyle = this.fill as string; ctx.fill('evenodd') }
      if (this.stroke) { ctx.strokeStyle = this.stroke as string; ctx.lineWidth = this.strokeWidth ?? 2; ctx.stroke() }
    }
    toObject(inc: string[] = []) { return toObj(super.toObject(inc), { innerRatio: this.innerRatio }) }
    static fromObject(data: any) { return Promise.resolve(new FabricAnnulus(data)) }
  }
  classRegistry.setClass(FabricAnnulus, 'FabricAnnulus')

  // ── 20. FabricProtractor ─────────────────────────────────────────────────
  class FabricProtractor extends FabricObject {
    static type = 'FabricProtractor'
    constructor(opts: any = {}) {
      super(opts)
      this.width  = opts.width  ?? 160
      this.height = opts.height ?? 80
    }
    _render(ctx: CanvasRenderingContext2D) {
      const r = this.width / 2
      const col = this.stroke as string || '#c4976a'
      ctx.strokeStyle = col; ctx.lineWidth = this.strokeWidth ?? 1.5
      ctx.globalAlpha = this.opacity ?? 0.85
      // Outer arc (semicircle on top half)
      ctx.beginPath(); ctx.arc(0, 0, r, Math.PI, 0); ctx.stroke()
      // Baseline
      ctx.beginPath(); ctx.moveTo(-r, 0); ctx.lineTo(r, 0); ctx.stroke()
      // Degree markings
      ctx.font = `${Math.max(7, r * 0.09)}px sans-serif`
      ctx.fillStyle = col; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
      for (let deg = 0; deg <= 180; deg += 10) {
        const rad = (deg * Math.PI) / 180
        const c = Math.cos(Math.PI - rad); const s = Math.sin(Math.PI - rad)
        const long = deg % 30 === 0
        const tickLen = long ? r * 0.12 : r * 0.07
        ctx.beginPath()
        ctx.moveTo(c * r, -s * r)
        ctx.lineTo(c * (r - tickLen), -s * (r - tickLen))
        ctx.stroke()
        if (long) {
          const lr = r - tickLen - 6
          ctx.fillText(String(deg), c * lr, -s * lr - 1)
        }
      }
      // Center dot
      ctx.beginPath(); ctx.arc(0, 0, 3, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill()
    }
    toObject(inc: string[] = []) { return super.toObject(inc) }
    static fromObject(data: any) { return Promise.resolve(new FabricProtractor(data)) }
  }
  classRegistry.setClass(FabricProtractor, 'FabricProtractor')

  // ── 21. FabricAxes ───────────────────────────────────────────────────────
  class FabricAxes extends FabricObject {
    static type = 'FabricAxes'
    xMin = -10; xMax = 10; yMin = -10; yMax = 10
    tickSpacing = 1
    variant: 'cartesian' | 'polar' | 'complex' | 'numberplane' = 'cartesian'
    axisFunctions: Array<{ expr: string; color: string; label: string }> = []
    axisPoints: Array<{ x: number; y: number; label: string }> = []
    labelX = 'x'; labelY = 'y'

    constructor(opts: any = {}) {
      super(opts)
      this.xMin          = opts.xMin          ?? -10
      this.xMax          = opts.xMax          ?? 10
      this.yMin          = opts.yMin          ?? -10
      this.yMax          = opts.yMax          ?? 10
      this.tickSpacing   = opts.tickSpacing   ?? 1
      this.variant       = opts.variant       ?? 'cartesian'
      this.axisFunctions = opts.axisFunctions ?? []
      this.axisPoints    = opts.axisPoints    ?? []
      this.labelX        = opts.labelX        ?? 'x'
      this.labelY        = opts.labelY        ?? 'y'
      this.width  = opts.width  ?? 300
      this.height = opts.height ?? 240
    }

    _toSX(mx: number): number {
      return ((mx - this.xMin) / (this.xMax - this.xMin)) * this.width - this.width / 2
    }
    _toSY(my: number): number {
      return -(((my - this.yMin) / (this.yMax - this.yMin)) * this.height - this.height / 2)
    }

    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height
      ctx.globalAlpha = this.opacity ?? 1

      // Background
      ctx.fillStyle = 'rgba(15,22,35,0.04)'; ctx.fillRect(-w / 2, -h / 2, w, h)
      ctx.strokeStyle = '#888'; ctx.lineWidth = 0.5
      ctx.strokeRect(-w / 2, -h / 2, w, h)

      const ox = this._toSX(0); const oy = this._toSY(0)
      const col = this.stroke as string || '#4a9eff'
      const clampX = (x: number) => Math.max(-w / 2, Math.min(w / 2, x))
      const clampY = (y: number) => Math.max(-h / 2, Math.min(h / 2, y))

      // Grid lines (light)
      ctx.strokeStyle = 'rgba(150,150,150,0.25)'; ctx.lineWidth = 0.5
      const xRange = this.xMax - this.xMin; const yRange = this.yMax - this.yMin
      for (let n = Math.ceil(this.xMin / this.tickSpacing); n <= this.xMax / this.tickSpacing; n++) {
        const sx = this._toSX(n * this.tickSpacing)
        ctx.beginPath(); ctx.moveTo(sx, -h / 2); ctx.lineTo(sx, h / 2); ctx.stroke()
      }
      for (let n = Math.ceil(this.yMin / this.tickSpacing); n <= this.yMax / this.tickSpacing; n++) {
        const sy = this._toSY(n * this.tickSpacing)
        ctx.beginPath(); ctx.moveTo(-w / 2, sy); ctx.lineTo(w / 2, sy); ctx.stroke()
      }

      // Axes
      ctx.strokeStyle = '#555'; ctx.lineWidth = 1.5
      // X axis
      ctx.beginPath(); ctx.moveTo(-w / 2, clampY(oy)); ctx.lineTo(w / 2, clampY(oy)); ctx.stroke()
      // Y axis
      ctx.beginPath(); ctx.moveTo(clampX(ox), -h / 2); ctx.lineTo(clampX(ox), h / 2); ctx.stroke()

      // Ticks + labels
      ctx.fillStyle = '#555'; ctx.font = `${Math.max(8, Math.min(11, w / xRange * 0.35))}px sans-serif`
      ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      for (let n = Math.ceil(this.xMin / this.tickSpacing); n <= this.xMax / this.tickSpacing; n++) {
        if (n === 0) continue
        const sx = this._toSX(n * this.tickSpacing)
        ctx.beginPath(); ctx.moveTo(sx, clampY(oy) - 4); ctx.lineTo(sx, clampY(oy) + 4)
        ctx.strokeStyle = '#555'; ctx.lineWidth = 1; ctx.stroke()
        ctx.fillText(String(n * this.tickSpacing), sx, clampY(oy) + 5)
      }
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle'
      for (let n = Math.ceil(this.yMin / this.tickSpacing); n <= this.yMax / this.tickSpacing; n++) {
        if (n === 0) continue
        const sy = this._toSY(n * this.tickSpacing)
        ctx.beginPath(); ctx.moveTo(clampX(ox) - 4, sy); ctx.lineTo(clampX(ox) + 4, sy)
        ctx.strokeStyle = '#555'; ctx.lineWidth = 1; ctx.stroke()
        ctx.fillText(String(n * this.tickSpacing), clampX(ox) - 5, sy)
      }

      // Axis labels
      ctx.font = `italic bold ${Math.max(10, 13)}px sans-serif`
      ctx.fillStyle = '#333'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
      ctx.fillText(this.labelX, w / 2 - 14, clampY(oy) - 12)
      ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
      ctx.fillText(this.labelY, clampX(ox) + 12, -h / 2 + 12)

      // Function plots
      if (this.axisFunctions.length > 0) {
        for (const fn of this.axisFunctions) {
          if (!fn.expr.trim()) continue
          ctx.strokeStyle = fn.color || col; ctx.lineWidth = 2
          ctx.beginPath()
          let first = true
          for (let px = 0; px <= w; px += 1.5) {
            const mx = this.xMin + (px / w) * (this.xMax - this.xMin)
            try {
              const vars = { x: mx, ...variableStore.all() }
              const my = mjsEvaluate(fn.expr, vars)
              if (typeof my !== 'number' || !isFinite(my)) { first = true; continue }
              const sy = this._toSY(my)
              if (sy < -h / 2 - 20 || sy > h / 2 + 20) { first = true; continue }
              first ? ctx.moveTo(px - w / 2, sy) : ctx.lineTo(px - w / 2, sy)
              first = false
            } catch { first = true }
          }
          ctx.stroke()
          // Function label at right edge
          if (fn.label) {
            try {
              const my = mjsEvaluate(fn.expr, { x: this.xMax * 0.9, ...variableStore.all() })
              const sy = this._toSY(my)
              if (isFinite(sy) && sy > -h / 2 && sy < h / 2) {
                ctx.fillStyle = fn.color || col; ctx.font = '11px sans-serif'
                ctx.textAlign = 'right'; ctx.textBaseline = 'middle'
                ctx.fillText(fn.label, w / 2 - 4, sy)
              }
            } catch {}
          }
        }
      }

      // Points
      for (const pt of this.axisPoints) {
        const sx = this._toSX(pt.x); const sy = this._toSY(pt.y)
        if (sx < -w / 2 || sx > w / 2 || sy < -h / 2 || sy > h / 2) continue
        ctx.beginPath(); ctx.arc(sx, sy, 4, 0, Math.PI * 2)
        ctx.fillStyle = col; ctx.fill()
        if (pt.label) {
          ctx.fillStyle = col; ctx.font = '11px sans-serif'
          ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
          ctx.fillText(pt.label, sx, sy - 6)
        }
      }
    }

    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), {
        xMin: this.xMin, xMax: this.xMax, yMin: this.yMin, yMax: this.yMax,
        tickSpacing: this.tickSpacing, variant: this.variant,
        axisFunctions: this.axisFunctions, axisPoints: this.axisPoints,
        labelX: this.labelX, labelY: this.labelY,
      })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricAxes(data)) }
  }
  classRegistry.setClass(FabricAxes, 'FabricAxes')

  // ── 22. FabricSlider ─────────────────────────────────────────────────────
  class FabricSlider extends FabricObject {
    static type = 'FabricSlider'
    varName = 'a'; sliderMin = 0; sliderMax = 10; sliderStep = 0.1; sliderValue = 5
    // Track where the handle is being dragged (local x offset from track start)
    private _dragging = false
    private _unsub: (() => void) | null = null

    constructor(opts: any = {}) {
      super(opts)
      this.varName     = opts.varName     ?? 'a'
      this.sliderMin   = opts.sliderMin   ?? 0
      this.sliderMax   = opts.sliderMax   ?? 10
      this.sliderStep  = opts.sliderStep  ?? 0.1
      this.sliderValue = opts.sliderValue ?? 5
      this.width  = opts.width  ?? 200
      this.height = opts.height ?? 40
      // Emit initial value
      variableStore.set(this.varName, this.sliderValue)
      // Subscribe to external changes (e.g. if another slider drives this)
      this._unsub = variableStore.subscribe(this.varName, () => {
        this.sliderValue = variableStore.get(this.varName)
      })
    }

    _handleX(): number {
      const t = (this.sliderValue - this.sliderMin) / (this.sliderMax - this.sliderMin)
      return -this.width / 2 + t * this.width
    }

    _render(ctx: CanvasRenderingContext2D) {
      const w = this.width; const h = this.height
      const col = this.stroke as string || '#c4976a'
      const hx = this._handleX()
      ctx.globalAlpha = this.opacity ?? 1

      // Track
      ctx.strokeStyle = col; ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2, 0); ctx.stroke()

      // Filled portion
      ctx.strokeStyle = col; ctx.lineWidth = 4
      ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(hx, 0); ctx.stroke()

      // Handle
      ctx.beginPath(); ctx.arc(hx, 0, 8, 0, Math.PI * 2)
      ctx.fillStyle = col; ctx.fill()
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke()

      // Variable name and value
      ctx.fillStyle = col; ctx.font = 'bold 12px sans-serif'
      ctx.textAlign = 'left'; ctx.textBaseline = 'bottom'
      ctx.fillText(`${this.varName} = ${this.sliderValue.toFixed(2)}`, -w / 2, -8)

      // Min/Max labels
      ctx.fillStyle = '#888'; ctx.font = '10px sans-serif'
      ctx.textAlign = 'left'; ctx.textBaseline = 'top'
      ctx.fillText(String(this.sliderMin), -w / 2, 10)
      ctx.textAlign = 'right'
      ctx.fillText(String(this.sliderMax), w / 2, 10)
    }

    /** Called by MathWhiteboard when a mousedown lands on this slider's handle area */
    hitTestHandle(localX: number): boolean {
      const hx = this._handleX()
      return Math.abs(localX - hx) < 12
    }

    /** Update value from a local x position (in object coordinates) */
    updateFromLocalX(localX: number, canvas: any) {
      const w = this.width
      const t = Math.max(0, Math.min(1, (localX + w / 2) / w))
      let v = this.sliderMin + t * (this.sliderMax - this.sliderMin)
      // Round to step
      v = Math.round(v / this.sliderStep) * this.sliderStep
      v = Math.max(this.sliderMin, Math.min(this.sliderMax, v))
      this.sliderValue = v
      variableStore.set(this.varName, v)
      canvas.requestRenderAll()
    }

    dispose() {
      this._unsub?.()
      super.dispose?.()
    }

    toObject(inc: string[] = []) {
      return toObj(super.toObject(inc), {
        varName: this.varName, sliderMin: this.sliderMin, sliderMax: this.sliderMax,
        sliderStep: this.sliderStep, sliderValue: this.sliderValue,
      })
    }
    static fromObject(data: any) { return Promise.resolve(new FabricSlider(data)) }
  }
  classRegistry.setClass(FabricSlider, 'FabricSlider')

  return {
    FabricFreeTriangle,
    FabricRightTriangle,
    FabricIsoTriangle,
    FabricRegularPolygon,
    FabricAngleMarker,
    FabricRightAngleMarker,
    FabricNumberLine,
    FabricBrace,
    FabricDot,
    FabricVenn,
    FabricMatrix,
    FabricVector,
    FabricLineSegment,
    FabricParallelogram,
    FabricRhombus,
    FabricTrapezoid,
    FabricArc,
    FabricSector,
    FabricAnnulus,
    FabricProtractor,
    FabricAxes,
    FabricSlider,
  }
}
