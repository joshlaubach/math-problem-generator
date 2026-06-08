'use client'
import React, {
  forwardRef, useCallback, useEffect, useImperativeHandle,
  useRef, useState,
} from 'react'
import dynamic from 'next/dynamic'
import katex from 'katex'
import { MathInput } from '@/components/MathInput'
import { drawGrid, MINOR_GRID } from './whiteboard/GridRenderer'
import { HistoryManager } from './whiteboard/HistoryManager'
import { snapToGrid, snapToObjects } from './whiteboard/SnapEngine'
import { registerAllShapes } from './whiteboard/shapes'
import { variableStore } from './whiteboard/VariableStore'
import type { DrawTool, GridType, MathWhiteboardProps, ShapeClasses } from './whiteboard/types'
import { SESSION_TOOLS } from './whiteboard/types'

const PropertiesPanel = dynamic(
  () => import('./whiteboard/PropertiesPanel').then(m => m.PropertiesPanel),
  { ssr: false },
)

// ── Constants ─────────────────────────────────────────────────────────────────

const COLORS = [
  '#e8e4dc', '#0f1623',
  '#4a9eff', '#c4976a', '#f87171',
  '#4ade80', '#facc15', '#a78bfa',
  '#94a3b8', '#fb923c', '#f472b6', '#34d399',
] as const

const DEFAULT_STROKE = '#4a9eff'
const ZOOM_MIN = 0.05
const ZOOM_MAX = 30
const SAVE_DEBOUNCE = 2000
const SNAP_DEBOUNCE = 1500

type Point = { x: number; y: number }

interface DrawState {
  active: boolean
  shape: any
  x0: number; y0: number
}

interface MultiClickState {
  pts: Point[]
  preview: any[]   // fabric objects shown as guides
}

export interface MathWhiteboardHandle {
  exportPng(): string | null
  getCanvas(): any
}

// ── Sub-components (outside MathWhiteboard to avoid remount on parent re-render) ──

const SIZE_PRESETS = [1, 4, 10, 20] as const
const SIZE_LABELS  = ['Thin', 'Med', 'Thick', 'XL'] as const

// Extended palette for the color picker popup (6 columns × 6 rows)
const PICKER_COLORS = [
  '#ffffff','#e8e4dc','#94a3b8','#4a5472','#0f1623','#000000',
  '#bfdbfe','#93c5fd','#4a9eff','#2563eb','#1d4ed8','#1e3a8a',
  '#fecaca','#f87171','#ef4444','#dc2626','#f472b6','#ec4899',
  '#bbf7d0','#4ade80','#22c55e','#16a34a','#34d399','#059669',
  '#fef08a','#facc15','#f59e0b','#fb923c','#f97316','#ea580c',
  '#e9d5ff','#a78bfa','#8b5cf6','#7c3aed','#c4976a','#92400e',
] as const

const DASH_PRESETS: Array<{ label: string; dash: number[] }> = [
  { label: 'Solid',    dash: [] },
  { label: 'Dotted',   dash: [2, 6] },
  { label: 'Dashed',   dash: [10, 6] },
  { label: 'Long',     dash: [20, 8] },
]

interface LaTeXPreset { display: string; latex: string; atomic: boolean }
const LATEX_PRESETS: LaTeXPreset[] = [
  // Structures
  { display: 'a/b',  latex: '\\frac{a}{b}',       atomic: false },
  { display: '√x',   latex: '\\sqrt{x}',           atomic: false },
  { display: 'ⁿ√x',  latex: '\\sqrt[n]{x}',        atomic: false },
  { display: 'xⁿ',   latex: 'x^{n}',              atomic: false },
  { display: 'xₙ',   latex: 'x_{n}',              atomic: false },
  { display: 'd/dx', latex: '\\frac{d}{dx}',       atomic: false },
  // Calculus
  { display: 'Σ',    latex: '\\sum_{i=1}^{n}',    atomic: false },
  { display: '∫',    latex: '\\int_{a}^{b}',       atomic: false },
  { display: 'lim',  latex: '\\lim_{x \\to a}',   atomic: false },
  // Relations
  { display: '≤', latex: '\\leq',       atomic: true },
  { display: '≥', latex: '\\geq',       atomic: true },
  { display: '≠', latex: '\\neq',       atomic: true },
  { display: '≈', latex: '\\approx',    atomic: true },
  { display: '∞', latex: '\\infty',     atomic: true },
  { display: '±', latex: '\\pm',        atomic: true },
  // Greek
  { display: 'π', latex: '\\pi',        atomic: true },
  { display: 'θ', latex: '\\theta',     atomic: true },
  { display: 'α', latex: '\\alpha',     atomic: true },
  { display: 'β', latex: '\\beta',      atomic: true },
  { display: 'γ', latex: '\\gamma',     atomic: true },
  { display: 'λ', latex: '\\lambda',    atomic: true },
  { display: 'μ', latex: '\\mu',        atomic: true },
  { display: 'σ', latex: '\\sigma',     atomic: true },
  { display: 'Δ', latex: '\\Delta',     atomic: true },
  { display: 'Ω', latex: '\\Omega',     atomic: true },
  { display: 'φ', latex: '\\varphi',    atomic: true },
  { display: 'ε', latex: '\\varepsilon',atomic: true },
  // Trig / Log
  { display: 'sin', latex: '\\sin', atomic: true },
  { display: 'cos', latex: '\\cos', atomic: true },
  { display: 'tan', latex: '\\tan', atomic: true },
  { display: 'log', latex: '\\log', atomic: true },
  { display: 'ln',  latex: '\\ln',  atomic: true },
  // Sets / Logic
  { display: '∈', latex: '\\in',             atomic: true },
  { display: '⊂', latex: '\\subset',         atomic: true },
  { display: '∪', latex: '\\cup',            atomic: true },
  { display: '∩', latex: '\\cap',            atomic: true },
  { display: '→', latex: '\\rightarrow',     atomic: true },
  { display: '⇒', latex: '\\Rightarrow',     atomic: true },
  { display: '⟺', latex: '\\Leftrightarrow', atomic: true },
  // Operators
  { display: '×', latex: '\\times', atomic: true },
  { display: '÷', latex: '\\div',   atomic: true },
  { display: '·', latex: '\\cdot',  atomic: true },
]

interface ThemeColors {
  tbBg: string; tbBorder: string; tbMuted: string; tbText: string
  caramel: string; caramelDim: string; d: boolean
}

function ColorPickerPopup({ color, onChange, onClose, theme: t }: {
  color: string; onChange: (c: string) => void; onClose: () => void; theme: ThemeColors
}) {
  const [hexInput, setHexInput] = useState(color)
  const nativeRef = useRef<HTMLInputElement>(null)
  const eyedropperSupported = typeof window !== 'undefined' && 'EyeDropper' in window

  useEffect(() => { setHexInput(color) }, [color])

  const handleHex = (val: string) => {
    setHexInput(val)
    if (/^#[0-9a-fA-F]{6}$/.test(val)) onChange(val)
  }

  const pickEyedropper = async () => {
    try {
      const dropper = new (window as any).EyeDropper()
      const result = await dropper.open()
      onChange(result.sRGBHex); setHexInput(result.sRGBHex)
    } catch {}
    onClose()
  }

  return (
    <div onMouseDown={e => e.stopPropagation()} style={{
      position: 'absolute', top: '100%', left: 0, zIndex: 200, marginTop: 4,
      background: t.tbBg, border: `1px solid ${t.tbBorder}`,
      borderRadius: 8, padding: 10, width: 196,
      boxShadow: '0 6px 24px rgba(0,0,0,0.3)',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 3 }}>
        {PICKER_COLORS.map(c => (
          <button key={c} onClick={() => { onChange(c); setHexInput(c); onClose() }} style={{
            width: 24, height: 24, borderRadius: 4, background: c, cursor: 'pointer',
            border: `2px solid ${c === color ? t.tbText : 'transparent'}`,
            outline: c === color ? `1px solid ${t.tbBorder}` : 'none', outlineOffset: 1,
          }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <input value={hexInput} onChange={e => handleHex(e.target.value)} placeholder="#000000"
          style={{
            flex: 1, padding: '4px 6px', borderRadius: 5, fontSize: 11,
            border: `1px solid ${t.tbBorder}`, background: 'transparent',
            color: t.tbText, fontFamily: 'monospace',
          }} />
        <div style={{ position: 'relative', width: 24, height: 24, flexShrink: 0 }}>
          <input ref={nativeRef} type="color" value={color.startsWith('#') && color.length === 7 ? color : '#000000'}
            onChange={e => { onChange(e.target.value); setHexInput(e.target.value) }}
            style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }} />
          <div style={{ width: 24, height: 24, borderRadius: 4, background: color, border: `1px solid ${t.tbBorder}`, pointerEvents: 'none' }} />
        </div>
        <button onClick={pickEyedropper} disabled={!eyedropperSupported}
          title={eyedropperSupported ? 'Pick from screen' : 'Not supported in this browser'} style={{
            width: 24, height: 24, borderRadius: 4, border: `1px solid ${t.tbBorder}`,
            background: 'transparent', cursor: eyedropperSupported ? 'pointer' : 'not-allowed',
            color: eyedropperSupported ? t.tbText : t.tbMuted, fontSize: 12, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>⊙</button>
      </div>
    </div>
  )
}

function ColorRow({ color, onChange, label, theme: t }: {
  color: string; onChange: (c: string) => void; label?: string; theme: ThemeColors
}) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  return (
    <div>
      {label && <div style={{ fontSize: 10, fontWeight: 600, color: t.tbMuted, marginBottom: 4 }}>{label}</div>}
      <div style={{ position: 'relative' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {COLORS.map(c => (
            <button key={c} onClick={() => onChange(c)} style={{
              width: 20, height: 20, borderRadius: '50%', background: c, cursor: 'pointer', flexShrink: 0,
              border: `2px solid ${c === color ? t.tbText : 'transparent'}`,
              outline: c === color ? `1px solid ${t.tbBorder}` : 'none', outlineOffset: 1,
            }} />
          ))}
          <button onMouseDown={e => { e.stopPropagation(); setOpen(s => !s) }}
            title="More colors" style={{
              width: 20, height: 20, borderRadius: 4, background: color,
              border: `1px solid ${t.tbBorder}`, cursor: 'pointer', fontSize: 10,
              color: t.d ? '#000' : '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>+</button>
        </div>
        {open && <ColorPickerPopup color={color} onChange={onChange} onClose={() => setOpen(false)} theme={t} />}
      </div>
    </div>
  )
}

function StrokeControls({ size, setSize, mode: previewMode, color, theme: t }: {
  size: number; setSize: (n: number) => void
  mode: 'pen' | 'highlight' | 'eraser' | 'line'; color: string; theme: ThemeColors
}) {
  const previewRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const cv = previewRef.current; if (!cv) return
    const ctx = cv.getContext('2d'); if (!ctx) return
    ctx.clearRect(0, 0, cv.width, cv.height)
    ctx.strokeStyle = previewMode === 'highlight' ? 'rgba(250,204,21,0.5)'
      : previewMode === 'eraser' ? (t.d ? '#e6edf3' : '#0f1623') : color
    ctx.lineWidth = Math.min(size, cv.height - 4)
    ctx.lineCap = 'round'; ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(10, cv.height / 2 + 6)
    ctx.bezierCurveTo(cv.width * 0.3, cv.height / 2 - 10, cv.width * 0.65, cv.height / 2 + 10, cv.width - 10, cv.height / 2 - 4)
    ctx.stroke()
  }, [size, previewMode, color, t.d])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: t.tbMuted }}>Stroke width</div>
      <canvas ref={previewRef} width={176} height={34}
        style={{ borderRadius: 5, background: t.d ? '#0d1117' : '#ffffff', display: 'block' }} />
      <input type="range" min={1} max={40} step={0.5} value={size}
        onChange={e => setSize(Number(e.target.value))} style={{ width: '100%', cursor: 'pointer' }} />
      <div style={{ display: 'flex', gap: 3 }}>
        {SIZE_PRESETS.map((p, i) => (
          <button key={p} onClick={() => setSize(p)} style={{
            flex: 1, padding: '3px 0', borderRadius: 4, fontSize: 9, cursor: 'pointer',
            fontWeight: size === p ? 700 : 400,
            border: `1px solid ${size === p ? t.caramel : t.tbBorder}`,
            background: size === p ? t.caramelDim : 'transparent',
            color: size === p ? t.caramel : t.tbMuted,
          }}>{SIZE_LABELS[i]}</button>
        ))}
      </div>
      <div style={{ fontSize: 9, color: t.tbMuted, textAlign: 'right' }}>{size}px</div>
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export const MathWhiteboard = forwardRef<MathWhiteboardHandle, MathWhiteboardProps>(
  function MathWhiteboard({ mode = 'full', theme = 'light', userId, onSnapshot }, ref) {

    // ── Refs ──────────────────────────────────────────────────────────────────
    const containerRef    = useRef<HTMLDivElement>(null)
    const gridCanvasRef   = useRef<HTMLCanvasElement>(null)
    const canvasElRef     = useRef<HTMLCanvasElement>(null)
    const fabricRef       = useRef<any>(null)
    const FRef            = useRef<any>(null)
    const shapesRef       = useRef<ShapeClasses | null>(null)
    const historyRef      = useRef(new HistoryManager(50))
    const saveTimer       = useRef<ReturnType<typeof setTimeout> | null>(null)
    const snapTimer       = useRef<ReturnType<typeof setTimeout> | null>(null)

    // Tool state refs (always current inside event handlers)
    const toolRef         = useRef<DrawTool>('pen')
    const colorRef        = useRef(DEFAULT_STROKE)
    const fillRef         = useRef('transparent')
    const strokeWRef      = useRef(2)
    const gridSnapRef     = useRef(true)
    const gridTypeRef     = useRef<GridType>('square')
    const showGridRef     = useRef(true)
    const themeRef        = useRef(theme)

    // Drawing state
    const drawState       = useRef<DrawState>({ active: false, shape: null, x0: 0, y0: 0 })
    const multiClick      = useRef<MultiClickState>({ pts: [], preview: [] })
    const sliderDrag      = useRef<{ obj: any; startX: number } | null>(null)
    const isEraserDown    = useRef(false)

    // Pan/zoom state
    const isPanning       = useRef(false)
    const panStart        = useRef<Point>({ x: 0, y: 0 })
    const panVptStart     = useRef<number[]>([1,0,0,1,0,0])
    const spaceHeld       = useRef(false)
    const activePointers  = useRef<Map<number, { x: number; y: number; type: string }>>(new Map())
    const lastPinchDist   = useRef<number | null>(null)
    const penLastSeen     = useRef(0)  // for palm rejection
    const isTouchDevice   = useRef(
      typeof navigator !== 'undefined' &&
      (/iPad/.test(navigator.userAgent) ||
       (navigator.userAgent.includes('Mac') && navigator.maxTouchPoints > 1) ||
       navigator.maxTouchPoints > 1)
    )

    // Snap indicator
    const snapIndicatorRef = useRef<HTMLDivElement>(null)
    const snapWorldPt      = useRef<Point | null>(null)

    // ── React State ───────────────────────────────────────────────────────────
    const [tool,             setTool]             = useState<DrawTool>('pen')
    const [strokeW,          setStrokeW]          = useState(2)
    // Per-tool colors
    const [penColor,         setPenColor]         = useState(DEFAULT_STROKE)
    const [highlightColor,   setHighlightColor]   = useState('#facc15')
    const [lineColor,        setLineColor]        = useState(DEFAULT_STROKE)
    const [shapeStroke,      setShapeStroke]      = useState(DEFAULT_STROKE)
    const [shapeFill,        setShapeFill]        = useState('transparent')
    // Per-tool sizes
    const [penSize,          setPenSize]          = useState(4)
    const [highlightSize,    setHighlightSize]    = useState(16)
    const [pixelEraserSize,  setPixelEraserSize]  = useState(26)
    const [eraserMode,       setEraserMode]       = useState<'stroke' | 'pixel'>('stroke')
    // Line arrowhead
    const [arrowhead,        setArrowhead]        = useState<'none'|'end'|'start'|'both'>('end')
    const [lineSize,         setLineSize]         = useState(2)
    const [lineDash,         setLineDash]         = useState<number[]>([])
    // Grid / canvas
    const [gridSnap,         setGridSnap]         = useState(true)
    const [gridType,         setGridType]         = useState<GridType>('square')
    const [showGrid,         setShowGrid]         = useState(true)
    const [selectedObj,      setSelectedObj]      = useState<any>(null)
    const [showLatex,        setShowLatex]        = useState(false)
    const [latexVal,         setLatexVal]         = useState('')
    const [canUndo,          setCanUndo]          = useState(false)
    const [canRedo,          setCanRedo]          = useState(false)

    // Refs for event handlers
    const penSizeRef          = useRef(4)
    const highlightSizeRef    = useRef(16)
    const pixelEraserSizeRef  = useRef(26)
    const eraserModeRef       = useRef<'stroke' | 'pixel'>('stroke')
    const arrowheadRef        = useRef<'none'|'end'|'start'|'both'>('end')
    const lineSizeRef         = useRef(2)
    const lineDashRef         = useRef<number[]>([])
    const penColorRef         = useRef(DEFAULT_STROKE)
    const highlightColorRef   = useRef('#facc15')
    const lineColorRef        = useRef(DEFAULT_STROKE)
    const shapeStrokeRef      = useRef(DEFAULT_STROKE)
    const shapeFillRef        = useRef('transparent')

    // Sync refs → state
    useEffect(() => { toolRef.current            = tool },          [tool])
    useEffect(() => { strokeWRef.current         = strokeW },       [strokeW])
    useEffect(() => { penSizeRef.current         = penSize },       [penSize])
    useEffect(() => { highlightSizeRef.current   = highlightSize }, [highlightSize])
    useEffect(() => { pixelEraserSizeRef.current = pixelEraserSize },[pixelEraserSize])
    useEffect(() => { eraserModeRef.current      = eraserMode },    [eraserMode])
    useEffect(() => { arrowheadRef.current       = arrowhead },     [arrowhead])
    useEffect(() => { lineSizeRef.current        = lineSize },      [lineSize])
    useEffect(() => { lineDashRef.current        = lineDash },      [lineDash])
    useEffect(() => { penColorRef.current        = penColor },      [penColor])
    useEffect(() => { highlightColorRef.current  = highlightColor },[highlightColor])
    useEffect(() => { lineColorRef.current       = lineColor },     [lineColor])
    useEffect(() => { shapeStrokeRef.current     = shapeStroke },   [shapeStroke])
    useEffect(() => { shapeFillRef.current       = shapeFill },     [shapeFill])
    useEffect(() => { gridSnapRef.current        = gridSnap },      [gridSnap])
    useEffect(() => { gridTypeRef.current        = gridType },      [gridType])
    useEffect(() => { showGridRef.current        = showGrid },      [showGrid])
    useEffect(() => { themeRef.current           = theme },         [theme])

    // Keep colorRef + fillRef in sync with the active tool's color (for event handlers)
    useEffect(() => {
      if (tool === 'pen')        colorRef.current = penColorRef.current
      else if (tool === 'highlight') colorRef.current = highlightColorRef.current
      else if (tool === 'line')  colorRef.current = lineColorRef.current
      else                       colorRef.current = shapeStrokeRef.current
      fillRef.current = shapeFillRef.current
    }, [tool, penColor, highlightColor, lineColor, shapeStroke, shapeFill])

    // ── Theme colours ─────────────────────────────────────────────────────────
    const d         = theme === 'dark'
    const tbBg      = d ? '#161b22' : '#f6f7fb'
    const tbBorder  = d ? '#30363d' : '#dce0ee'
    const tbText    = d ? '#e6edf3' : '#0f1623'
    const tbMuted   = d ? '#8b949e' : '#4a5472'
    const caramel   = d ? '#d29922' : '#b8860b'
    const caramelDim = d ? 'rgba(210,153,34,0.14)' : 'rgba(184,134,11,0.1)'

    // ── Grid canvas redraw ────────────────────────────────────────────────────
    const redrawGrid = useCallback(() => {
      const gc = gridCanvasRef.current
      const canvas = fabricRef.current
      if (!gc || !canvas) return
      const ctx = gc.getContext('2d')
      if (!ctx) return
      const vpt: number[] = [...canvas.viewportTransform]
      drawGrid(ctx, vpt, gc.width, gc.height, gridTypeRef.current, themeRef.current)
      // Snap indicator
      const ind = snapIndicatorRef.current
      if (ind) {
        const sp = snapWorldPt.current
        if (sp) {
          const sx = sp.x * vpt[0] + vpt[4]
          const sy = sp.y * vpt[3] + vpt[5]
          ind.style.transform = `translate(${sx - 6}px, ${sy - 6}px)`
          ind.style.display = 'block'
        } else {
          ind.style.display = 'none'
        }
      }
    }, [])

    // ── History helpers ───────────────────────────────────────────────────────
    const pushHistory = useCallback(() => {
      const canvas = fabricRef.current
      if (!canvas) return
      const props = [
        'type','relativeVertices','sides','arcCount','angleDeg','showLabel',
        'numStart','numEnd','step','showLabels','tickCount','label','direction',
        'dotRadius','count','vennLabels','rows','cols','cells','innerRatio',
        'skew','topRatio','startAngleDeg','endAngleDeg','varName','sliderMin',
        'sliderMax','sliderStep','sliderValue','xMin','xMax','yMin','yMax',
        'tickSpacing','variant','axisFunctions','axisPoints','labelX','labelY',
      ]
      historyRef.current.push(canvas.toJSON(props))
      setCanUndo(historyRef.current.canUndo())
      setCanRedo(historyRef.current.canRedo())
    }, [])

    const doUndo = useCallback(() => {
      const canvas = fabricRef.current
      if (!canvas) return
      const s = historyRef.current.undo()
      if (s) canvas.loadFromJSON(JSON.parse(s)).then(() => canvas.requestRenderAll())
      setCanUndo(historyRef.current.canUndo())
      setCanRedo(historyRef.current.canRedo())
    }, [])

    const doRedo = useCallback(() => {
      const canvas = fabricRef.current
      if (!canvas) return
      const s = historyRef.current.redo()
      if (s) canvas.loadFromJSON(JSON.parse(s)).then(() => canvas.requestRenderAll())
      setCanUndo(historyRef.current.canUndo())
      setCanRedo(historyRef.current.canRedo())
    }, [])

    // ── Persistence ───────────────────────────────────────────────────────────
    const scheduleSave = useCallback(() => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        const canvas = fabricRef.current
        if (!canvas) return
        const props = [
          'type','relativeVertices','sides','arcCount','angleDeg','showLabel',
          'numStart','numEnd','step','showLabels','tickCount','label','direction',
          'dotRadius','count','vennLabels','rows','cols','cells','innerRatio',
          'skew','topRatio','startAngleDeg','endAngleDeg','varName','sliderMin',
          'sliderMax','sliderStep','sliderValue','xMin','xMax','yMin','yMax',
          'tickSpacing','variant','axisFunctions','axisPoints','labelX','labelY',
        ]
        try {
          const json = JSON.stringify({
            canvas: canvas.toJSON(props),
            vpt: canvas.viewportTransform,
          })
          localStorage.setItem(`wb_${userId ?? 'anon'}`, json)
        } catch {}
      }, SAVE_DEBOUNCE)
    }, [userId])

    // ── Snap helper ───────────────────────────────────────────────────────────
    const getSnappedScenePoint = useCallback((e: any): Point => {
      const canvas = fabricRef.current
      if (!canvas) return { x: e.scenePoint?.x ?? 0, y: e.scenePoint?.y ?? 0 }
      const raw: Point = canvas.getScenePoint(e.e ?? e)
      if (!gridSnapRef.current) {
        snapWorldPt.current = null
        return raw
      }
      const zoom = canvas.viewportTransform[0]
      // Try object snap first
      const objSnap = snapToObjects(raw, canvas, zoom)
      if (objSnap) {
        snapWorldPt.current = objSnap.snapped
        return objSnap.snapped
      }
      // Then grid snap
      const gsnap = snapToGrid(raw, zoom)
      snapWorldPt.current = gsnap
      return gsnap
    }, [])

    // ── Shape placement helpers ───────────────────────────────────────────────
    const placeShapeAt = useCallback((x0: number, y0: number, x1: number, y1: number) => {
      const canvas = fabricRef.current
      const F = FRef.current
      const S = shapesRef.current
      if (!canvas || !F || !S) return

      const t = toolRef.current
      const left   = Math.min(x0, x1)
      const top    = Math.min(y0, y1)
      const width  = Math.max(Math.abs(x1 - x0), 4)
      const height = Math.max(Math.abs(y1 - y0), 4)
      const cx     = (x0 + x1) / 2
      const cy     = (y0 + y1) / 2
      const col    = colorRef.current
      const fill   = fillRef.current
      const sw     = strokeWRef.current

      const base = { left, top, width, height, stroke: col, strokeWidth: sw, fill, selectable: true }
      const baseC = { left: cx - width/2, top: cy - height/2, width, height, stroke: col, strokeWidth: sw, fill, selectable: true }

      let obj: any = null

      switch (t) {
        case 'rect':
          obj = new F.Rect({ ...base })
          break
        case 'circle':
          obj = new F.Circle({ left: cx - width/2, top: cy - height/2, radius: Math.min(width, height)/2, stroke: col, strokeWidth: sw, fill, selectable: true })
          break
        case 'ellipse':
          obj = new F.Ellipse({ ...baseC, rx: width/2, ry: height/2 })
          break
        case 'triangle-free':
          obj = new S.FabricFreeTriangle({ ...base,
            relativeVertices: [{ x: 0, y: -height/2 }, { x: -width/2, y: height/2 }, { x: width/2, y: height/2 }],
          })
          break
        case 'triangle-right':
          obj = new S.FabricRightTriangle({ ...base })
          break
        case 'triangle-iso':
          obj = new S.FabricIsoTriangle({ ...base })
          break
        case 'parallelogram':
          obj = new S.FabricParallelogram({ ...base })
          break
        case 'rhombus':
          obj = new S.FabricRhombus({ ...base })
          break
        case 'trapezoid':
          obj = new S.FabricTrapezoid({ ...base })
          break
        case 'polygon-regular':
          obj = new S.FabricRegularPolygon({ ...base, sides: 6 })
          break
        case 'arc':
          obj = new S.FabricArc({ ...base })
          break
        case 'sector':
          obj = new S.FabricSector({ ...base, fill })
          break
        case 'annulus':
          obj = new S.FabricAnnulus({ ...base, fill })
          break
        case 'venn':
          obj = new S.FabricVenn({ ...base, count: 2 })
          break
        case 'matrix':
          obj = new S.FabricMatrix({ ...base })
          break
        case 'number-line':
          obj = new S.FabricNumberLine({ left, top: cy - 20, width: Math.max(width, 100), height: 40, stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'brace':
          obj = new S.FabricBrace({ left, top, width: Math.max(width, 60), height: Math.max(height, 40), stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'axes':
          obj = new S.FabricAxes({ left, top, width: Math.max(width, 200), height: Math.max(height, 160), stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'slider':
          obj = new S.FabricSlider({ left, top: cy - 20, width: Math.max(width, 120), height: 40, stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'protractor':
          obj = new S.FabricProtractor({ left, top, width: Math.max(width, 120), height: Math.max(height/2, 60), stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'angle-marker':
          obj = new S.FabricAngleMarker({ left, top, width: Math.max(width, 80), height: Math.max(height, 80), stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'right-angle-marker':
          obj = new S.FabricRightAngleMarker({ left, top, width: 24, height: 24, stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'dot':
          obj = new S.FabricDot({ left: cx - 10, top: cy - 10, width: 20, height: 20, stroke: col, strokeWidth: sw, fill: col, selectable: true })
          break
        case 'vector':
          obj = new S.FabricVector({ left, top: cy - 4, width: Math.max(width, 60), height: 8, stroke: col, strokeWidth: sw, selectable: true })
          break
        case 'line-segment':
          obj = new S.FabricLineSegment({ left, top: cy - 4, width: Math.max(width, 40), height: 8, stroke: col, strokeWidth: sw, selectable: true })
          break
      }

      if (obj) {
        canvas.add(obj)
        canvas.setActiveObject(obj)
        canvas.requestRenderAll()
        pushHistory()
        scheduleSave()
        setSelectedObj(obj)
      }
    }, [pushHistory, scheduleSave])

    // ── LaTeX placement ───────────────────────────────────────────────────────
    const handleAddLatex = useCallback(async (overrideLaTeX?: string) => {
      const canvas = fabricRef.current; const F = FRef.current
      const val = overrideLaTeX ?? latexVal
      if (!canvas || !F || !val.trim()) { setShowLatex(false); setLatexVal(''); return }

      try {
        const div = document.createElement('div')
        div.style.cssText = 'position:absolute;top:-9999px;left:-9999px;font-size:20px;line-height:1.5;padding:4px 8px;'
        document.body.appendChild(div)
        katex.render(val, div, { throwOnError: false, displayMode: false })
        await new Promise(r => requestAnimationFrame(r))
        const w = Math.max(div.offsetWidth + 16, 80)
        const h = Math.max(div.offsetHeight + 8, 36)
        const html = div.innerHTML
        document.body.removeChild(div)

        const col = colorRef.current
        const svgStr = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><foreignObject x="0" y="0" width="${w}" height="${h}"><div xmlns="http://www.w3.org/1999/xhtml" style="color:${col};font-size:20px;line-height:1.5;padding:4px 8px;">${html}</div></foreignObject></svg>`
        const dataUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)))

        const vpt = canvas.viewportTransform
        const cx = (canvas.width  / 2 - vpt[4]) / vpt[0]
        const cy = (canvas.height / 2 - vpt[5]) / vpt[3]

        F.Image.fromURL(dataUrl, (img: any) => {
          img.set({ left: cx - w/2, top: cy - h/2, selectable: true })
          canvas.add(img); canvas.setActiveObject(img); canvas.requestRenderAll()
          pushHistory(); scheduleSave()
        })
      } catch (err) { console.warn('LaTeX render error:', err) }

      setShowLatex(false); setLatexVal(''); setTool('select')
    }, [latexVal, pushHistory, scheduleSave])

    // ── Keyboard shortcuts ────────────────────────────────────────────────────
    useEffect(() => {
      const onKey = (e: KeyboardEvent) => {
        const el = e.target as HTMLElement
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable) return

        const ctrl = e.ctrlKey || e.metaKey
        if (ctrl && e.key === 'z') { e.preventDefault(); doUndo(); return }
        if (ctrl && (e.key === 'y' || (e.shiftKey && e.key === 'Z'))) { e.preventDefault(); doRedo(); return }
        if (ctrl && e.key === 'g') { e.preventDefault(); setGridSnap(s => !s); return }
        if (ctrl && e.key === 'd') {
          e.preventDefault()
          const canvas = fabricRef.current
          const ao = canvas?.getActiveObject()
          if (ao) ao.clone().then((cl: any) => { cl.left += 20; cl.top += 20; canvas.add(cl); canvas.setActiveObject(cl); canvas.requestRenderAll(); pushHistory(); scheduleSave() })
          return
        }
        if (ctrl) return

        if (e.key === ' ') { spaceHeld.current = true; return }
        if (e.key === 'Escape' || e.key === 'v' || e.key === 'V') { setTool('select'); return }
        if (e.key === 'h' || e.key === 'H') { setTool('hand'); return }
        if (e.key === 'p' || e.key === 'P') { setTool('pen'); return }
        if (e.key === 'y' || e.key === 'Y') { setTool('highlight'); return }
        if (e.key === 'e' || e.key === 'E') { setTool('eraser'); return }
        if (e.key === 'l' || e.key === 'L') { setTool('line'); return }
        if (e.key === 't' || e.key === 'T') { setTool('text'); return }
        if (e.key === 'f' || e.key === 'F') { setTool('latex'); setShowLatex(true); return }
        if (e.key === 's' || e.key === 'S') { setTool('rect'); return }
        if (e.key === 'm' || e.key === 'M') { setTool('axes'); return }
        if (e.key === 'Delete' || e.key === 'Backspace') {
          const canvas = fabricRef.current
          const ao = canvas?.getActiveObject()
          if (ao) { canvas.remove(ao); canvas.discardActiveObject(); canvas.requestRenderAll(); setSelectedObj(null); pushHistory(); scheduleSave() }
        }
      }
      const onKeyUp = (e: KeyboardEvent) => { if (e.key === ' ') spaceHeld.current = false }
      window.addEventListener('keydown', onKey)
      window.addEventListener('keyup', onKeyUp)
      return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('keyup', onKeyUp) }
    }, [doUndo, doRedo, pushHistory, scheduleSave])

    // ── Fabric initialization ─────────────────────────────────────────────────
    useEffect(() => {
      const canvasEl = canvasElRef.current
      if (!canvasEl || fabricRef.current) return
      let gone = false

      ;(async () => {
        const F = await import('fabric')
        if (gone) return
        FRef.current = F

        // Register all custom shapes before creating the canvas
        shapesRef.current = registerAllShapes(F) as ShapeClasses

        const container = containerRef.current
        const W = container?.clientWidth  ?? window.innerWidth
        const H = container?.clientHeight ?? window.innerHeight

        // Size the grid canvas
        if (gridCanvasRef.current) {
          gridCanvasRef.current.width  = W
          gridCanvasRef.current.height = H
        }

        const canvas = new F.Canvas(canvasEl, {
          width: W, height: H,
          selection: true,
          preserveObjectStacking: true,
        })
        // No background fill — grid canvas behind handles that
        canvas.backgroundColor = ''
        fabricRef.current = canvas

        // Set initial drawing mode — the tool-sync useEffect runs before Fabric is ready,
        // so we apply the default pen mode here immediately after init.
        const initBrush = new F.PencilBrush(canvas)
        initBrush.color = colorRef.current
        initBrush.width = strokeWRef.current
        initBrush.decimate = 3
        canvas.freeDrawingBrush = initBrush
        canvas.isDrawingMode    = true
        canvas.selection        = false
        canvas.defaultCursor    = 'crosshair'

        // Position Fabric's .canvas-container to fill the parent
        const fc = canvasEl.parentElement as HTMLElement | null
        if (fc) {
          fc.style.position = 'absolute'
          fc.style.inset    = '0'
        }

        // Restore saved state
        try {
          const saved = localStorage.getItem(`wb_${userId ?? 'anon'}`)
          if (saved) {
            const { canvas: json, vpt } = JSON.parse(saved)
            await canvas.loadFromJSON(json)
            if (vpt) canvas.setViewportTransform(vpt)
          }
        } catch {}

        // ── Canvas event handlers ─────────────────────────────────────────────

        // Grid redraws on any viewport change
        const onVpt = () => redrawGrid()
        canvas.on('after:render', onVpt)

        // Selection
        canvas.on('selection:created', (e: any) => setSelectedObj(e.selected?.[0] ?? null))
        canvas.on('selection:updated', (e: any) => setSelectedObj(e.selected?.[0] ?? null))
        canvas.on('selection:cleared',  ()       => setSelectedObj(null))

        // Object modification → history + save
        canvas.on('object:modified', () => { pushHistory(); scheduleSave() })

        // Grid snap on move
        canvas.on('object:moving', (opt: any) => {
          if (!gridSnapRef.current || !opt.target) return
          const t = opt.target
          const snapped = snapToGrid({ x: t.left ?? 0, y: t.top ?? 0 }, canvas.viewportTransform[0])
          t.set({ left: snapped.x, top: snapped.y })
        })

        // path:created (pen/highlight/pixel-eraser)
        canvas.on('path:created', (opt: any) => {
          if (toolRef.current === 'highlight' && opt.path) {
            opt.path.set({ opacity: 0.32 })
          }
          if (toolRef.current === 'eraser' && eraserModeRef.current === 'pixel' && opt.path) {
            opt.path.set({ globalCompositeOperation: 'destination-out', selectable: false, evented: false })
          }
          canvas.requestRenderAll()
          pushHistory(); scheduleSave()
          if (onSnapshot) {
            if (snapTimer.current) clearTimeout(snapTimer.current)
            snapTimer.current = setTimeout(() => {
              const url = canvas.toDataURL({ format: 'png', multiplier: 1 })
              onSnapshot(url.split(',')[1])
            }, SNAP_DEBOUNCE)
          }
        })

        // ── Mouse / pointer handlers ──────────────────────────────────────────

        canvas.on('mouse:down', (opt: any) => {
          const t  = toolRef.current
          const p  = getSnappedScenePoint(opt)
          const F2 = FRef.current
          const S  = shapesRef.current
          if (!F2) return
          const ds = drawState.current
          const mc = multiClick.current

          // Slider drag
          if (t === 'select' || t === 'hand') {
            const ao = opt.target
            if (ao?.type?.toLowerCase() === 'fabricslider') {
              // Convert click to local object coords
              const m = canvas.viewportTransform
              const sx = (opt.e.clientX - (canvasEl.parentElement?.getBoundingClientRect().left ?? 0) - m[4]) / m[0]
              const sy = (opt.e.clientY - (canvasEl.parentElement?.getBoundingClientRect().top  ?? 0) - m[5]) / m[3]
              const lx = sx - (ao.left ?? 0) - (ao.width ?? 0) / 2
              if (ao.hitTestHandle(lx)) {
                sliderDrag.current = { obj: ao, startX: lx }
                canvas.isDrawingMode = false
                canvas.discardActiveObject()
                canvas.requestRenderAll()
                return
              }
            }
          }

          // Eraser — delete object under cursor
          if (t === 'eraser') {
            isEraserDown.current = true
            const target = canvas.findTarget(opt.e) as any
            if (target) { canvas.remove(target); canvas.requestRenderAll() }
            return
          }

          // Line (with optional arrowheads + dash pattern)
          if (t === 'line') {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
            const dash = lineDashRef.current
            ds.shape  = new F2.Line([p.x, p.y, p.x, p.y], {
              stroke: lineColorRef.current, strokeWidth: lineSizeRef.current,
              strokeDashArray: dash.length ? dash : undefined,
              selectable: false, strokeLineCap: 'round',
            })
            canvas.add(ds.shape)
          }

          // Click-drag shapes
          if (['rect','circle','ellipse','triangle-right','triangle-iso',
               'parallelogram','rhombus','trapezoid','polygon-regular',
               'arc','sector','annulus','venn','matrix','number-line',
               'brace','axes','slider','protractor','angle-marker',
               'right-angle-marker','vector','line-segment'].includes(t)) {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
          }

          // Multi-click shapes (triangle-free)
          if (t === 'triangle-free') {
            ds.active = false
            mc.pts.push(p)
            // Preview dot
            const dot = new F2.Circle({ left: p.x - 4, top: p.y - 4, radius: 4, fill: colorRef.current, selectable: false, evented: false })
            canvas.add(dot); mc.preview.push(dot)
            if (mc.pts.length === 2) {
              const ln = new F2.Line([mc.pts[0].x, mc.pts[0].y, p.x, p.y], { stroke: colorRef.current, strokeWidth: 1, selectable: false, evented: false, strokeDashArray: [4, 4] })
              canvas.add(ln); mc.preview.push(ln)
            }
            if (mc.pts.length === 3) {
              // Complete
              const [v0, v1, v2] = mc.pts
              const minX = Math.min(v0.x, v1.x, v2.x); const maxX = Math.max(v0.x, v1.x, v2.x)
              const minY = Math.min(v0.y, v1.y, v2.y); const maxY = Math.max(v0.y, v1.y, v2.y)
              const cx = (minX + maxX) / 2; const cy = (minY + maxY) / 2
              const w = Math.max(maxX - minX, 4); const h = Math.max(maxY - minY, 4)
              const relV = [
                { x: v0.x - cx, y: v0.y - cy },
                { x: v1.x - cx, y: v1.y - cy },
                { x: v2.x - cx, y: v2.y - cy },
              ]
              if (S) {
                const obj = new S.FabricFreeTriangle({ left: minX, top: minY, width: w, height: h, relativeVertices: relV, stroke: colorRef.current, strokeWidth: strokeWRef.current, fill: fillRef.current, selectable: true })
                canvas.add(obj); canvas.setActiveObject(obj)
              }
              // Remove previews
              mc.preview.forEach((o: any) => canvas.remove(o))
              mc.pts = []; mc.preview = []
              canvas.requestRenderAll(); pushHistory(); scheduleSave()
            } else { canvas.requestRenderAll() }
            return
          }

          // Text
          if (t === 'text') {
            const it = new F2.IText('', { left: p.x, top: p.y, fill: colorRef.current, fontSize: 18, fontFamily: 'system-ui,sans-serif' })
            canvas.add(it); canvas.setActiveObject(it); it.enterEditing(); canvas.requestRenderAll()
            pushHistory(); scheduleSave()
          }

          // Dot (single click)
          if (t === 'dot') {
            if (!S) return
            const obj = new S.FabricDot({ left: p.x - 10, top: p.y - 10, width: 20, height: 20, stroke: colorRef.current, strokeWidth: strokeWRef.current, fill: colorRef.current, selectable: true })
            canvas.add(obj); canvas.setActiveObject(obj); canvas.requestRenderAll()
            pushHistory(); scheduleSave(); setSelectedObj(obj)
          }
        })

        canvas.on('mouse:move', (opt: any) => {
          const t  = toolRef.current
          const ds = drawState.current

          // Eraser — continuously delete objects under cursor while mouse held
          if (t === 'eraser' && isEraserDown.current) {
            const target = canvas.findTarget(opt.e) as any
            if (target) { canvas.remove(target); canvas.requestRenderAll() }
            return
          }

          if (!ds.active && t !== 'triangle-free') { snapWorldPt.current = null; return }

          const p = getSnappedScenePoint(opt)

          if (t === 'line') {
            ds.shape?.set({ x2: p.x, y2: p.y })
            canvas.requestRenderAll()
          }

          // Live preview for click-drag shapes — just update a transient rect
          if (ds.active && ['rect','circle','ellipse','triangle-right','triangle-iso',
                'parallelogram','rhombus','trapezoid','polygon-regular','arc','sector',
                'annulus','venn','matrix','number-line','brace','axes','slider',
                'protractor','angle-marker','right-angle-marker','vector','line-segment'].includes(t)) {
            // Show a ghost rect
            if (!ds.shape) {
              ds.shape = new FRef.current.Rect({
                left: ds.x0, top: ds.y0, width: 0, height: 0,
                stroke: colorRef.current, strokeWidth: 1, strokeDashArray: [4, 4],
                fill: 'transparent', selectable: false, evented: false,
              })
              canvas.add(ds.shape)
            }
            ds.shape.set({
              left: Math.min(p.x, ds.x0), top: Math.min(p.y, ds.y0),
              width: Math.abs(p.x - ds.x0), height: Math.abs(p.y - ds.y0),
            })
            canvas.requestRenderAll()
          }

          // Slider drag
          if (sliderDrag.current) {
            const sd = sliderDrag.current
            const m  = canvas.viewportTransform
            const sx = (opt.e.clientX - (canvasEl.parentElement?.getBoundingClientRect().left ?? 0) - m[4]) / m[0]
            const lx = sx - (sd.obj.left ?? 0) - (sd.obj.width ?? 0) / 2
            sd.obj.updateFromLocalX(lx, canvas)
          }
        })

        canvas.on('mouse:up', (opt: any) => {
          const t  = toolRef.current
          const ds = drawState.current

          // Slider drag end
          if (sliderDrag.current) {
            sliderDrag.current = null
            pushHistory(); scheduleSave(); return
          }

          // Eraser — commit history on release
          if (t === 'eraser' && isEraserDown.current) {
            isEraserDown.current = false
            pushHistory(); scheduleSave(); return
          }

          if (t === 'line' && ds.shape) {
            const p = getSnappedScenePoint(opt)
            const ah = arrowheadRef.current
            const col = lineColorRef.current
            const sw  = lineSizeRef.current
            const addTip = (x: number, y: number, angle: number) => {
              const tip = new FRef.current.Triangle({
                left: x, top: y, width: 10 + sw * 1.5, height: 12 + sw * 1.5,
                fill: col, stroke: col,
                angle: (angle * 180 / Math.PI) + 90,
                originX: 'center', originY: 'center', selectable: false,
              })
              canvas.add(tip)
            }
            const fwdAngle = Math.atan2(p.y - ds.y0, p.x - ds.x0)
            const bkAngle  = Math.atan2(ds.y0 - p.y, ds.x0 - p.x)
            if (ah === 'end'   || ah === 'both') addTip(p.x,   p.y,   fwdAngle)
            if (ah === 'start' || ah === 'both') addTip(ds.x0, ds.y0, bkAngle)
          }

          if (ds.active) {
            // Remove ghost rect preview
            if (ds.shape && ['rect','circle','ellipse','triangle-right','triangle-iso',
                  'parallelogram','rhombus','trapezoid','polygon-regular','arc','sector',
                  'annulus','venn','matrix','number-line','brace','axes','slider',
                  'protractor','angle-marker','right-angle-marker','vector','line-segment'].includes(t)) {
              canvas.remove(ds.shape)
            }
            // Place final shape
            const p = getSnappedScenePoint(opt)
            if (t !== 'line') {
              placeShapeAt(ds.x0, ds.y0, p.x, p.y)
            } else {
              // Line is already on canvas; make it selectable
              ds.shape?.set({ selectable: true })
              pushHistory(); scheduleSave()
            }
            ds.active = false; ds.shape = null
            canvas.requestRenderAll()
          }

          snapWorldPt.current = null
        })

        // ── Zoom & Pan — pointer events ───────────────────────────────────────

        const fabricUpper = canvas.upperCanvasEl as HTMLCanvasElement

        const onPD = (e: PointerEvent) => {
          activePointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY, type: e.pointerType })

          // Palm rejection: if a pen was seen within 2s, ignore touch
          if (e.pointerType === 'pen') penLastSeen.current = Date.now()
          if (e.pointerType === 'touch' && Date.now() - penLastSeen.current < 2000) return

          // Middle mouse or Space+drag → start pan
          if (e.button === 1 || spaceHeld.current || toolRef.current === 'hand') {
            isPanning.current  = true
            panStart.current   = { x: e.clientX, y: e.clientY }
            panVptStart.current = [...canvas.viewportTransform]
            fabricUpper.style.cursor = 'grabbing'
            e.preventDefault()
          }
        }

        const onPM = (e: PointerEvent) => {
          activePointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY, type: e.pointerType })

          // Pinch zoom — touch devices only, and only when both pointers are touch/pen
          const ptrs = [...activePointers.current.values()]
          const touchPtrs = ptrs.filter(p => p.type !== 'mouse')
          if (isTouchDevice.current && touchPtrs.length === 2) {
            const dx = touchPtrs[0].x - touchPtrs[1].x; const dy = touchPtrs[0].y - touchPtrs[1].y
            const dist = Math.sqrt(dx*dx + dy*dy)
            if (lastPinchDist.current !== null) {
              const ratio = dist / lastPinchDist.current
              const cx    = (touchPtrs[0].x + touchPtrs[1].x) / 2
              const cy    = (touchPtrs[0].y + touchPtrs[1].y) / 2
              const rect  = fabricUpper.getBoundingClientRect()
              const px    = cx - rect.left; const py = cy - rect.top
              const vpt   = canvas.viewportTransform
              const oldZ  = vpt[0]
              const newZ  = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldZ * ratio))
              const r     = newZ / oldZ
              canvas.setViewportTransform([newZ, 0, 0, newZ, px - (px - vpt[4]) * r, py - (py - vpt[5]) * r] as [number,number,number,number,number,number])
              redrawGrid()
            }
            lastPinchDist.current = dist
            return
          }
          lastPinchDist.current = null

          // Pan
          if (!isPanning.current) return
          const dx = e.clientX - panStart.current.x
          const dy = e.clientY - panStart.current.y
          const vpt = [...panVptStart.current] as [number,number,number,number,number,number]
          vpt[4] += dx; vpt[5] += dy
          canvas.setViewportTransform(vpt)
          redrawGrid()
        }

        const onPU = (e: PointerEvent) => {
          activePointers.current.delete(e.pointerId)
          lastPinchDist.current = null
          if (isPanning.current) {
            isPanning.current = false
            fabricUpper.style.cursor = toolRef.current === 'hand' ? 'grab' : 'crosshair'
          }
        }

        // Scroll wheel zoom
        const onWheel = (e: WheelEvent) => {
          if (!e.ctrlKey && !e.metaKey) return
          e.preventDefault()
          const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08
          const rect   = fabricUpper.getBoundingClientRect()
          const px     = e.clientX - rect.left; const py = e.clientY - rect.top
          const vpt    = canvas.viewportTransform
          const oldZ   = vpt[0]
          const newZ   = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, oldZ * factor))
          const r      = newZ / oldZ
          canvas.setViewportTransform([newZ, 0, 0, newZ, px - (px - vpt[4]) * r, py - (py - vpt[5]) * r])
          redrawGrid()
        }

        const onPLeave = (e: PointerEvent) => {
          activePointers.current.delete(e.pointerId)
          lastPinchDist.current = null
        }
        fabricUpper.addEventListener('pointerdown',  onPD, { passive: false })
        fabricUpper.addEventListener('pointermove',  onPM, { passive: true  })
        fabricUpper.addEventListener('pointerup',    onPU)
        fabricUpper.addEventListener('pointercancel',onPU)
        fabricUpper.addEventListener('pointerleave', onPLeave)
        fabricUpper.addEventListener('wheel', onWheel, { passive: false })
        fabricUpper.style.touchAction = 'none'

        // ── Resize observer ───────────────────────────────────────────────────
        const ro = new ResizeObserver(() => {
          const el = containerRef.current
          if (!el) return
          const W = el.clientWidth; const H = el.clientHeight
          canvas.setDimensions({ width: W, height: H })
          if (gridCanvasRef.current) {
            gridCanvasRef.current.width  = W
            gridCanvasRef.current.height = H
          }
          canvas.requestRenderAll()
        })
        if (container) ro.observe(container)

        // Initial history entry
        pushHistory()
        // Initial grid draw
        redrawGrid()

        return () => {
          gone = true
          ro.disconnect()
          fabricUpper.removeEventListener('pointerdown',   onPD)
          fabricUpper.removeEventListener('pointermove',   onPM)
          fabricUpper.removeEventListener('pointerup',     onPU)
          fabricUpper.removeEventListener('pointercancel', onPU)
          fabricUpper.removeEventListener('pointerleave',  onPLeave)
          fabricUpper.removeEventListener('wheel', onWheel)
          try { canvas.dispose() } catch {}
          fabricRef.current  = null
          FRef.current       = null
          shapesRef.current  = null
        }
      })()

      return () => { gone = true }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // ── Sync tool → canvas mode ───────────────────────────────────────────────
    useEffect(() => {
      const canvas = fabricRef.current; const F = FRef.current
      if (!canvas || !F) return

      canvas.isDrawingMode = false
      canvas.selection     = false
      canvas.defaultCursor = 'crosshair'

      if (tool === 'select') {
        canvas.selection = true; canvas.defaultCursor = 'default'
        canvas.getObjects().forEach((o: any) => { o.selectable = true; o.evented = true })
        canvas.requestRenderAll(); return
      }
      if (tool === 'hand') { canvas.defaultCursor = 'grab'; return }
      if (tool === 'pen') {
        const b = new F.PencilBrush(canvas)
        b.color = penColorRef.current; b.width = penSizeRef.current; b.decimate = 3
        canvas.freeDrawingBrush = b; canvas.isDrawingMode = true; return
      }
      if (tool === 'highlight') {
        const b = new F.PencilBrush(canvas)
        b.color = highlightColorRef.current; b.width = highlightSizeRef.current; b.decimate = 3
        canvas.freeDrawingBrush = b; canvas.isDrawingMode = true; return
      }
      if (tool === 'eraser') {
        if (eraserModeRef.current === 'pixel') {
          const b = new F.PencilBrush(canvas)
          b.color = 'rgba(0,0,0,1)'; b.width = pixelEraserSizeRef.current
          canvas.freeDrawingBrush = b; canvas.isDrawingMode = true
        } else {
          canvas.isDrawingMode = false; canvas.selection = false
          canvas.defaultCursor = 'cell'
        }
        return
      }
    }, [tool, eraserMode, d])

    // Sync brush color/width live when per-tool settings change
    useEffect(() => {
      const canvas = fabricRef.current
      if (!canvas?.freeDrawingBrush) return
      if (tool === 'pen')      { canvas.freeDrawingBrush.color = penColor;       canvas.freeDrawingBrush.width = penSize }
      if (tool === 'highlight'){ canvas.freeDrawingBrush.color = highlightColor; canvas.freeDrawingBrush.width = highlightSize }
      if (tool === 'eraser' && eraserMode === 'pixel') { canvas.freeDrawingBrush.width = pixelEraserSize }
    }, [penColor, penSize, highlightColor, highlightSize, pixelEraserSize, tool, eraserMode])

    // Redraw grid when settings change
    useEffect(() => { redrawGrid() }, [showGrid, gridType, theme, redrawGrid])

    // Expose handle
    useImperativeHandle(ref, () => ({
      exportPng: () => fabricRef.current?.toDataURL({ format: 'png', multiplier: 1 }) ?? null,
      getCanvas: () => fabricRef.current,
    }), [])

    // ── Toolbar helpers ───────────────────────────────────────────────────────

    const SHAPES: Array<{ id: DrawTool; icon: string; label: string }> = [
      { id: 'rect',           icon: '▭', label: 'Rectangle'         },
      { id: 'circle',         icon: '○', label: 'Circle'            },
      { id: 'ellipse',        icon: '⬭', label: 'Ellipse'           },
      { id: 'triangle-free',  icon: '△', label: 'Free Triangle'     },
      { id: 'triangle-right', icon: '◺', label: 'Right Triangle'    },
      { id: 'triangle-iso',   icon: '▲', label: 'Isosceles Triangle'},
      { id: 'parallelogram',  icon: '▱', label: 'Parallelogram'     },
      { id: 'rhombus',        icon: '◇', label: 'Rhombus'           },
      { id: 'trapezoid',      icon: '⌂', label: 'Trapezoid'         },
      { id: 'polygon-regular',icon: '⬡', label: 'Regular Polygon'   },
      { id: 'arc',            icon: '⌒', label: 'Arc'               },
      { id: 'sector',         icon: '◔', label: 'Sector'            },
      { id: 'annulus',        icon: '◎', label: 'Annulus'           },
      { id: 'venn',           icon: '⊙', label: 'Venn Diagram'      },
    ]

    const MATH_OBJS: Array<{ id: DrawTool; icon: string; label: string }> = [
      { id: 'axes',              icon: '⊹', label: 'Axes'              },
      { id: 'number-line',       icon: '↔', label: 'Number Line'       },
      { id: 'vector',            icon: '⇒', label: 'Vector Arrow'      },
      { id: 'angle-marker',      icon: '∠', label: 'Angle Marker'      },
      { id: 'right-angle-marker',icon: '⌐', label: 'Right Angle Marker'},
      { id: 'line-segment',      icon: '—', label: 'Line Segment'      },
      { id: 'brace',             icon: '⌣', label: 'Brace'             },
      { id: 'dot',               icon: '•', label: 'Dot / Point'        },
      { id: 'matrix',            icon: '⊞', label: 'Matrix / Table'    },
      { id: 'slider',            icon: '⊨', label: 'Slider'            },
      { id: 'protractor',        icon: '⌓', label: 'Protractor'        },
    ]

    // Session mode shows a curated subset in each group
    const SESSION_SHAPES  = SHAPES.filter(s => ['rect','circle','triangle-free'].includes(s.id))
    const SESSION_MATH    = MATH_OBJS.filter(m => ['axes','number-line','vector','angle-marker','right-angle-marker','dot'].includes(m.id))
    const visibleShapes   = mode === 'session' ? SESSION_SHAPES : SHAPES
    const visibleMath     = mode === 'session' ? SESSION_MATH   : MATH_OBJS

    const isShapeTool  = SHAPES.some(s => s.id === tool)
    const isMathTool   = MATH_OBJS.some(m => m.id === tool)
    const hasPanel     = !['select','hand'].includes(tool)

    const tc: ThemeColors = { tbBg, tbBorder, tbMuted, tbText, caramel, caramelDim, d }

    const TBtn = ({ id, icon, label, active, onClick }: {
      id?: DrawTool; icon: string; label: string; active?: boolean; onClick?: () => void
    }) => {
      const isActive = active ?? (id ? tool === id : false)
      return (
        <button title={label} onClick={onClick ?? (() => { if (id) setTool(id) })} style={{
          width: 36, height: 36, borderRadius: 6, fontSize: 16, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          border: `1px solid ${isActive ? caramel : 'transparent'}`,
          background: isActive ? caramelDim : 'transparent',
          color: isActive ? caramel : tbText,
        }}>{icon}</button>
      )
    }

    const Divider = () => <div style={{ width: 28, height: 1, background: tbBorder, margin: '2px auto' }} />
    const PanelDivider = () => <div style={{ height: 1, background: tbBorder, margin: '4px 0' }} />
    const PanelLabel = ({ children }: { children: React.ReactNode }) => (
      <div style={{ fontSize: 10, fontWeight: 600, color: tbMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{children}</div>
    )

    // ── Options panel content per tool ────────────────────────────────────────

    const panelContent = (() => {
      if (tool === 'pen') return (
        <>
          <ColorRow color={penColor} onChange={setPenColor} label="Color" theme={tc} />
          <PanelDivider />
          <StrokeControls size={penSize} setSize={setPenSize} mode="pen" color={penColor} theme={tc} />
        </>
      )
      if (tool === 'highlight') return (
        <>
          <ColorRow color={highlightColor} onChange={setHighlightColor} label="Color" theme={tc} />
          <PanelDivider />
          <StrokeControls size={highlightSize} setSize={setHighlightSize} mode="highlight" color={highlightColor} theme={tc} />
        </>
      )
      if (tool === 'eraser') return (
        <>
          <PanelLabel>Eraser mode</PanelLabel>
          <div style={{ display: 'flex', gap: 4 }}>
            {(['stroke','pixel'] as const).map(m => (
              <button key={m} onClick={() => setEraserMode(m)} style={{
                flex: 1, padding: '6px 0', borderRadius: 5, fontSize: 11, cursor: 'pointer',
                fontWeight: eraserMode === m ? 700 : 400,
                border: `1px solid ${eraserMode === m ? caramel : tbBorder}`,
                background: eraserMode === m ? caramelDim : 'transparent',
                color: eraserMode === m ? caramel : tbText, textTransform: 'capitalize',
              }}>{m}</button>
            ))}
          </div>
          {eraserMode === 'pixel' && (
            <>
              <PanelDivider />
              <StrokeControls size={pixelEraserSize} setSize={setPixelEraserSize} mode="eraser" color={tbText} theme={tc} />
            </>
          )}
        </>
      )
      if (tool === 'line') return (
        <>
          <ColorRow color={lineColor} onChange={setLineColor} label="Color" theme={tc} />
          <PanelDivider />
          <StrokeControls size={lineSize} setSize={setLineSize} mode="line" color={lineColor} theme={tc} />
          <PanelDivider />
          <PanelDivider />
          <PanelLabel>Line style</PanelLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {DASH_PRESETS.map(p => {
              const active = JSON.stringify(lineDash) === JSON.stringify(p.dash)
              return (
                <button key={p.label} onClick={() => setLineDash(p.dash)} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px',
                  borderRadius: 5, cursor: 'pointer',
                  border: `1px solid ${active ? caramel : tbBorder}`,
                  background: active ? caramelDim : 'transparent',
                }}>
                  <svg width="60" height="8" style={{ flexShrink: 0 }}>
                    <line x1="2" y1="4" x2="58" y2="4"
                      stroke={active ? caramel : lineColor || tbText}
                      strokeWidth="2"
                      strokeDasharray={p.dash.join(' ') || undefined}
                      strokeLinecap="round" />
                  </svg>
                  <span style={{ fontSize: 10, color: active ? caramel : tbMuted }}>{p.label}</span>
                </button>
              )
            })}
          </div>
          <PanelDivider />
          <PanelLabel>Arrowhead</PanelLabel>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            {([['none','——'],['end','——›'],['start','‹——'],['both','‹——›']] as const).map(([m, icon]) => (
              <button key={m} onClick={() => setArrowhead(m)} style={{
                padding: '5px 0', borderRadius: 5, fontSize: 12, cursor: 'pointer',
                fontWeight: arrowhead === m ? 700 : 400,
                border: `1px solid ${arrowhead === m ? caramel : tbBorder}`,
                background: arrowhead === m ? caramelDim : 'transparent',
                color: arrowhead === m ? caramel : tbText,
              }}>{icon}</button>
            ))}
          </div>
        </>
      )
      if (tool === 'text') return (
        <>
          <PanelLabel>Font size</PanelLabel>
          <div style={{ display: 'flex', gap: 4 }}>
            {[12, 16, 20, 28].map(sz => (
              <button key={sz} onClick={() => setStrokeW(sz)} style={{
                flex: 1, padding: '5px 0', borderRadius: 5, fontSize: 10, cursor: 'pointer',
                fontWeight: strokeW === sz ? 700 : 400,
                border: `1px solid ${strokeW === sz ? caramel : tbBorder}`,
                background: strokeW === sz ? caramelDim : 'transparent',
                color: strokeW === sz ? caramel : tbText,
              }}>{sz}</button>
            ))}
          </div>
        </>
      )
      if (tool === 'latex') return (
        <>
          <PanelLabel>Insert symbol</PanelLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 3 }}>
            {LATEX_PRESETS.map(p => (
              <button key={p.latex} title={p.latex}
                onClick={() => {
                  if (p.atomic) {
                    setLatexVal(p.latex); handleAddLatex(p.latex)
                  } else {
                    setLatexVal(p.latex); setShowLatex(true)
                  }
                }} style={{
                  padding: '5px 2px', borderRadius: 5, fontSize: 11, cursor: 'pointer',
                  border: `1px solid ${tbBorder}`, background: 'transparent', color: tbText,
                }}>{p.display}</button>
            ))}
          </div>
          <PanelDivider />
          <button onClick={() => setShowLatex(true)} style={{
            width: '100%', padding: '7px 0', borderRadius: 6, fontSize: 12, cursor: 'pointer',
            border: `1px solid ${caramel}`, background: caramelDim, color: caramel, fontWeight: 600,
          }}>Open formula editor</button>
        </>
      )
      if (isShapeTool) return (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 3 }}>
            {visibleShapes.map(s => (
              <button key={s.id} title={s.label} onClick={() => setTool(s.id)} style={{
                padding: '6px 0', borderRadius: 5, fontSize: 14, cursor: 'pointer',
                border: `1px solid ${tool === s.id ? caramel : tbBorder}`,
                background: tool === s.id ? caramelDim : 'transparent',
                color: tool === s.id ? caramel : tbText,
              }}>{s.icon}</button>
            ))}
          </div>
          <PanelDivider />
          <ColorRow color={shapeStroke} onChange={setShapeStroke} label="Stroke" theme={tc} />
          <PanelDivider />
          <ColorRow color={shapeFill === 'transparent' ? '#00000000' : shapeFill}
            onChange={c => setShapeFill(c)} label="Fill" theme={tc} />
          <button onClick={() => setShapeFill('transparent')} style={{
            marginTop: 2, padding: '3px 0', borderRadius: 4, fontSize: 10, cursor: 'pointer',
            border: `1px solid ${shapeFill === 'transparent' ? caramel : tbBorder}`,
            background: shapeFill === 'transparent' ? caramelDim : 'transparent',
            color: shapeFill === 'transparent' ? caramel : tbMuted,
          }}>No fill</button>
        </>
      )
      if (isMathTool) return (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {visibleMath.map(m => (
              <button key={m.id} title={m.label} onClick={() => setTool(m.id)} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                borderRadius: 5, fontSize: 12, cursor: 'pointer',
                border: `1px solid ${tool === m.id ? caramel : 'transparent'}`,
                background: tool === m.id ? caramelDim : 'transparent',
                color: tool === m.id ? caramel : tbText,
              }}>
                <span style={{ fontSize: 14 }}>{m.icon}</span>{m.label}
              </button>
            ))}
          </div>
        </>
      )
      return null
    })()

    // ── Render ────────────────────────────────────────────────────────────────

    return (
      <div style={{ position: 'absolute', inset: 0, display: 'flex', overflow: 'hidden' }}>

        {/* ── Tool rail (52px) ──────────────────────────────────────────────── */}
        <div style={{
          width: 52, flexShrink: 0, zIndex: 10,
          background: tbBg, borderRight: `1px solid ${tbBorder}`,
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: 2, padding: '8px 4px', overflowY: 'auto',
        }}>
          {/* ── Utilities (top) ── */}
          <TBtn icon="↩" label="Undo [Ctrl+Z]" active={false} onClick={doUndo} />
          <TBtn icon="↪" label="Redo [Ctrl+Y]" active={false} onClick={doRedo} />
          <button title="Clear canvas" onClick={() => {
            const canvas = fabricRef.current; if (!canvas) return
            canvas.clear(); canvas.backgroundColor = ''
            canvas.requestRenderAll(); pushHistory(); scheduleSave()
          }} style={{
            width: 36, height: 36, borderRadius: 6, fontSize: 14, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            border: '1px solid transparent', background: 'transparent', color: '#f87171',
          }}>✕</button>
          <TBtn icon={showGrid ? '⊞' : '□'} label="Toggle grid" active={showGrid} onClick={() => setShowGrid(s => !s)} />
          <select value={gridType} onChange={e => setGridType(e.target.value as GridType)} title="Grid type"
            style={{ fontSize: 9, width: 40, background: tbBg, color: tbText, border: `1px solid ${tbBorder}`, borderRadius: 4, padding: '2px 0' }}>
            <option value="square">Grid</option>
            <option value="dotted">Dots</option>
            <option value="isometric">Iso</option>
            <option value="blank">None</option>
          </select>
          <TBtn icon="⊡" label="Snap to grid" active={gridSnap} onClick={() => setGridSnap(s => !s)} />

          <Divider />

          {/* ── Drawing tools ── */}
          <TBtn id="select"    icon="↖"  label="Select [V]"    onClick={() => setTool('select')} />
          <TBtn id="hand"      icon="✋"  label="Hand [H]"      onClick={() => setTool('hand')} />
          <TBtn id="pen"       icon="✒"  label="Pen [P]"       onClick={() => setTool('pen')} />
          <TBtn id="highlight" icon="🖍" label="Highlight [Y]" onClick={() => setTool('highlight')} />
          <TBtn id="eraser"    icon="⌫"  label="Eraser [E]"    onClick={() => setTool('eraser')} />
          <TBtn id="line"      icon="╱"  label="Line [L]"      onClick={() => setTool('line')} />
          <TBtn id="text"      icon="T"  label="Text [T]"      onClick={() => setTool('text')} />
          <TBtn id="latex"     icon="ƒ"  label="LaTeX [F]"     onClick={() => { setTool('latex'); setShowLatex(true) }} />
          <TBtn icon="▭" label="Shapes [S]"      active={isShapeTool}
            onClick={() => { if (!isShapeTool) setTool('rect') }} />
          <TBtn icon="∑" label="Math objects [M]" active={isMathTool}
            onClick={() => { if (!isMathTool) setTool('axes') }} />
        </div>

        {/* ── Options panel (animated 0 → 200px) ───────────────────────────── */}
        <div style={{
          width: hasPanel ? 200 : 0,
          overflow: 'hidden',
          flexShrink: 0,
          transition: 'width 150ms ease-out',
          borderRight: hasPanel ? `1px solid ${tbBorder}` : 'none',
          background: tbBg,
          zIndex: 9,
        }}>
          <div style={{
            width: 200, height: '100%', overflowY: 'auto',
            display: 'flex', flexDirection: 'column', gap: 10,
            padding: '12px 12px',
            boxSizing: 'border-box',
          }}>
            {panelContent}
          </div>
        </div>

        {/* ── Canvas area ───────────────────────────────────────────────────── */}
        <div ref={containerRef} style={{ flex: 1, position: 'relative', overflow: 'hidden', background: d ? '#0d1117' : '#ffffff' }}>
          <canvas ref={gridCanvasRef} style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none', display: showGrid ? 'block' : 'none' }} />
          <div ref={snapIndicatorRef} style={{ display: 'none', position: 'absolute', top: 0, left: 0, zIndex: 2, pointerEvents: 'none', width: 12, height: 12, borderRadius: '50%', border: '2px solid #4a9eff', background: 'rgba(74,158,255,0.25)' }} />
          <canvas ref={canvasElRef} style={{ position: 'absolute', inset: 0, zIndex: 1 }} />
        </div>

        {/* ── Right properties panel (full mode) ───────────────────────────── */}
        {mode === 'full' && (
          <PropertiesPanel selectedObj={selectedObj} canvas={fabricRef.current} theme={theme} />
        )}

        {/* ── LaTeX overlay ─────────────────────────────────────────────────── */}
        {showLatex && (
          <div style={{
            position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
          }}>
            <div style={{
              background: tbBg, border: `1px solid ${tbBorder}`,
              borderRadius: 12, padding: 20, width: 360,
              display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: tbText }}>Insert LaTeX formula</div>
              <MathInput value={latexVal} onChange={setLatexVal} placeholder="Type LaTeX…" />
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => handleAddLatex()} style={{
                  flex: 1, padding: 9, borderRadius: 8, fontSize: 13, fontWeight: 600,
                  background: caramel, color: '#fff', border: 'none', cursor: 'pointer',
                }}>Place on canvas</button>
                <button onClick={() => { setShowLatex(false); setLatexVal('') }} style={{
                  flex: 1, padding: 9, borderRadius: 8, fontSize: 13,
                  background: 'transparent', color: tbMuted,
                  border: `1px solid ${tbBorder}`, cursor: 'pointer',
                }}>Cancel</button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
)
