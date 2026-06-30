'use client'

/**
 * Whiteboard — persistent scrollable canvas for AI tutor sessions.
 *
 * Layer stack (bottom → top):
 *   0. CSS dot-grid background
 *   1. Tutor layer — Framer Motion-animated KaTeX/geometry blocks + section dividers (z-index 5)
 *   2. Student layer — Fabric.js freehand canvas (z-index 10)
 *
 * Phase-2 constraint system (all 10):
 *   1. Boundary enforcement  — blocks clamped to [PAD_LEFT, canvasWidth - PAD_RIGHT]
 *   2. No self-overlap       — every write goes through WhiteboardLayoutManager.findNextSlot()
 *   3. Margin gutters        — GAP=24px, PAD=32px
 *   4. Step gating           — 400ms cursor pulse before block appears (sequential reveal)
 *   5. Incorrect coloring    — markIncorrect() sets #a03535 on last latex block
 *   6. Student layer aware   — annotateStudentWork() reads Fabric bboxes via layout manager
 *   7. Color constants       — TUTOR_INK / STUDENT_INK / CORRECTION_INK never swapped
 *   8. Cursor presence       — pulsing ◆ at nextY for 400ms before each write
 *   9. Pointer-before-write  — Framer Motion outline flash on referenced block before annotation
 *  10. Write speed           — Framer Motion duration = clamp(charCount * 0.04, 0.3, 2.0) seconds
 */

import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  forwardRef,
  memo,
} from 'react'
import dynamic from 'next/dynamic'
import { WhiteboardLayoutManager } from '../lib/whiteboard-layout-manager'
import type { GeometryElement } from './WhiteboardPlot'

// ── Dynamic imports (no SSR) ─────────────────────────────────────────────────

const MafsPlot = dynamic(() => import('./WhiteboardPlot'), {
  ssr: false,
  loading: () => <div style={{ width: '100%', height: 160, borderRadius: 8 }} />,
})

// ── Color constants (constraint 7) ───────────────────────────────────────────

const TUTOR_INK      = '#e8e4dc'   // tutor block text (on dark) / tutor ink
const STUDENT_INK    = '#4a9eff'   // student drawing color
const CORRECTION_INK = '#c4976a'   // annotation / caramel
const INCORRECT_INK  = '#a03535'   // incorrect answer — dark red

void STUDENT_INK  // referenced by docs; Fabric brush uses it at runtime

const ANNOTATION_INK: Record<string, string> = {
  correction:   CORRECTION_INK,
  confirmation: '#2d6a4f',
  neutral:      '#8b949e',
}

// ── Self-contained theme colors — no CSS var inheritance ──────────────────────

interface WbTC {
  surface: string; surface2: string; border: string
  text: string; textDim: string; textMuted: string
  caramel: string; caramelDim: string; caramelGlow: string
}

function mkTC(theme: 'light' | 'dark'): WbTC {
  const d = theme === 'dark'
  return {
    surface:     d ? '#161b22' : '#ffffff',
    surface2:    d ? '#1c2128' : '#f0f2f8',
    border:      d ? '#30363d' : '#dce0ee',
    text:        d ? '#e6edf3' : '#0f1623',
    textDim:     d ? '#8b949e' : '#4a5472',
    textMuted:   d ? '#6e7681' : '#8a96b4',
    caramel:     d ? '#d29922' : '#b8860b',
    caramelDim:  d ? 'rgba(210,153,34,0.12)' : 'rgba(184,134,11,0.10)',
    caramelGlow: d ? 'rgba(210,153,34,0.28)' : 'rgba(184,134,11,0.25)',
  }
}

// ── Layout constants (constraints 1, 3) ──────────────────────────────────────

const GAP = 28    // vertical gap between blocks (was 14)
const PAD = 32    // left/right padding inside doc (was 12)

// Generous approximate heights — layout manager handles exact overlap
const BLOCK_H: Record<string, number> = {
  latex:      120,  // increased from 90; display-mode KaTeX can be tall
  plot:       220,
  divider:    52,
  annotation: 70,
}

// ── Cursor animation style (constraint 8) ────────────────────────────────────

const CURSOR_KEYFRAME = `@keyframes wb-cursor-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.55)}}`

// ── Public types ──────────────────────────────────────────────────────────────

export interface WhiteboardMessage {
  type: 'whiteboard'
  action: 'write' | 'plot' | 'clear'
  latex?: string
  fn?: string
  domain?: [number, number]
  x?: number
  y?: number
}

export type WbMessage =
  | { type: 'wb_write';          latex?: string; scene?: GeometryElement[]; display?: boolean }
  | { type: 'wb_zoom';           region: 'top' | 'latest' | number }
  | { type: 'wb_clear';          snapshot?: boolean }
  | { type: 'wb_new_section';    label: string }
  | { type: 'wb_annotate_student'; latex?: string; label?: string; x_hint?: 'left' | 'center' | 'right'; color?: 'correction' | 'confirmation' | 'neutral' }
  | { type: 'wb_mark_incorrect' }

export interface WhiteboardHandle {
  writeBlock(latex: string, opts?: { display?: boolean }): void
  newSection(label: string): void
  zoomTo(target: 'top' | 'latest' | number): void
  clearBoard(opts?: { snapshot?: boolean }): void
  getSnapshot(): Promise<string | null>
  handleMessage(msg: WhiteboardMessage | WbMessage): void
  exportPng(): Promise<string | null>
  annotateStudentWork(annotation: {
    latex?: string
    label?: string
    color?: 'correction' | 'confirmation' | 'neutral'
  }): void
  markIncorrect(): void
}

export interface WhiteboardProps {
  visibleHeight?: number
  theme?: 'light' | 'dark'
  onSnapshot?: (imageB64: string) => void
}

// ── Internal block model ───────────────────────────────────────────────────────

type LatexBlock = {
  id: string; kind: 'latex'
  latex: string; display: boolean; yOffset: number; incorrect?: boolean
}
type PlotBlock = {
  id: string; kind: 'plot'
  fn?: string; domain?: [number, number]; scene?: GeometryElement[]; yOffset: number
}
type DividerBlock   = { id: string; kind: 'divider';    label: string; yOffset: number }
type AnnotationBlock = {
  id: string; kind: 'annotation'
  latex?: string; label?: string
  color: 'correction' | 'confirmation' | 'neutral'
  xOffset: number   // explicit x — annotations go in student-adjacent column
  yOffset: number
}

type Block = LatexBlock | PlotBlock | DividerBlock | AnnotationBlock

// Annotations are positioned independently — not through appendBlock
type BlockWithoutY =
  | Omit<LatexBlock,   'yOffset'>
  | Omit<PlotBlock,    'yOffset'>
  | Omit<DividerBlock, 'yOffset'>

// ── LatexItem — GSAP fade-in, variable speed, pointer-flash (constraints 4, 9, 10) ──

const LatexItem = memo(function LatexItem({
  block,
  highlighted,
  theme,
}: {
  block: LatexBlock
  highlighted?: boolean
  theme: 'light' | 'dark'
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [html, setHtml] = useState('')

  useEffect(() => {
    if (!block.latex) { setHtml(''); return }
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const katex = require('katex')
      setHtml(katex.renderToString(block.latex, {
        throwOnError: false,
        displayMode: block.display,
        output: 'html',
      }))
    } catch {
      setHtml(block.latex)
    }
  }, [block.latex, block.display])

  // Constraint 10: write speed proportional to content length
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const duration = Math.max(0.3, Math.min(2.0, block.latex.length * 0.04))
    const fallback = setTimeout(() => { if (el) el.style.opacity = '1' }, duration * 1000 + 300)

    import('framer-motion').then(({ animate }) => {
      clearTimeout(fallback)
      animate(el, { opacity: [0, 1], y: [8, 0] }, { duration, ease: 'easeOut' })
    }).catch(() => {
      if (el) el.style.opacity = '1'
    })

    return () => clearTimeout(fallback)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Constraint 9: pointer-before-write — outline flash when this block is referenced
  useEffect(() => {
    if (!highlighted || !ref.current) return
    const el = ref.current
    import('framer-motion').then(({ animate }) => {
      // 4-step yoyo flash: 0→2px→0→2px→0, each step 0.15s = 0.6s total
      animate(el, {
        boxShadow: [
          '0 0 0 0px rgba(196,151,106,0)',
          '0 0 0 2px rgba(196,151,106,0.85)',
          '0 0 0 0px rgba(196,151,106,0)',
          '0 0 0 2px rgba(196,151,106,0.85)',
          '0 0 0 0px rgba(196,151,106,0)',
        ],
      }, { duration: 0.6, ease: 'easeInOut' })
    }).catch(() => { /* ok */ })
  }, [highlighted])

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        left: PAD,
        top: block.yOffset,
        width: `calc(100% - ${PAD * 2}px)`,
        opacity: 0,
        padding: '8px 12px',
        borderRadius: 8,
        background: theme === 'dark' ? 'rgba(196,151,106,0.07)' : 'rgba(196,151,106,0.06)',
        border: '1px solid rgba(196,151,106,0.13)',
        color: block.incorrect ? INCORRECT_INK : theme === 'dark' ? TUTOR_INK : 'var(--text)',
        zIndex: 5,
        pointerEvents: 'none',
        minHeight: 44,
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
})

// ── Section divider ───────────────────────────────────────────────────────────

function SectionDivider({ block, tc }: { block: DividerBlock; tc: WbTC }) {
  return (
    <div style={{
      position: 'absolute',
      left: 0, right: 0,
      top: block.yOffset,
      height: BLOCK_H.divider,
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: `0 ${PAD}px`,
      zIndex: 5,
      pointerEvents: 'none',
    }}>
      <div style={{ flex: 1, height: 1, background: tc.border }} />
      <span style={{
        fontSize: 11,
        fontWeight: 600,
        color: tc.textMuted,
        letterSpacing: '0.07em',
        whiteSpace: 'nowrap',
        padding: '3px 8px',
        borderRadius: 12,
        background: tc.surface2,
        border: `1px solid ${tc.border}`,
      }}>
        {block.label}
      </span>
      <div style={{ flex: 1, height: 1, background: tc.border }} />
    </div>
  )
}

// ── Annotation block ──────────────────────────────────────────────────────────

function AnnotationItem({ block, tc }: { block: AnnotationBlock; tc: WbTC }) {
  const ink = ANNOTATION_INK[block.color] ?? ANNOTATION_INK.neutral
  const [html, setHtml] = useState('')

  useEffect(() => {
    if (!block.latex) { setHtml(''); return }
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const katex = require('katex')
      setHtml(katex.renderToString(block.latex, {
        throwOnError: false, displayMode: false, output: 'html',
      }))
    } catch {
      setHtml(block.latex)
    }
  }, [block.latex])

  return (
    <div style={{
      position: 'absolute',
      left: block.xOffset,   // constraint 6: placed adjacent to student work
      top: block.yOffset,
      maxWidth: 220,
      padding: '6px 10px',
      borderRadius: 8,
      background: `${ink}14`,
      border: `1px solid ${ink}55`,
      color: tc.text,
      fontSize: 12,
      lineHeight: 1.5,
      zIndex: 5,
      pointerEvents: 'none',
    }}>
      {block.label && (
        <div style={{
          fontSize: 9, fontWeight: 700, color: ink,
          letterSpacing: '.5px', textTransform: 'uppercase', marginBottom: 4,
        }}>
          {block.label}
        </div>
      )}
      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export const Whiteboard = forwardRef<WhiteboardHandle, WhiteboardProps>(
  function Whiteboard({ visibleHeight = 520, theme = 'light', onSnapshot }, ref) {

    // DOM refs
    const scrollRef      = useRef<HTMLDivElement>(null)
    const docRef         = useRef<HTMLDivElement>(null)
    const tutorLayerRef  = useRef<HTMLDivElement>(null)
    const fabricLayerRef = useRef<HTMLDivElement>(null)
    const fabricRef      = useRef<unknown>(null)

    // Layout manager (constraint 2)
    const layoutManagerRef = useRef(new WhiteboardLayoutManager())

    // State
    const [blocks, setBlocks]               = useState<Block[]>([])
    const [docHeight, setDocHeight]         = useState(visibleHeight)
    const [tool, setTool]                   = useState<'pen' | 'eraser'>('pen')
    const [color, setColor]                 = useState('#2d6a4f')
    const [snapshot, setSnapshot]           = useState<string | null>(null)
    const [cursorY, setCursorY]             = useState<number | null>(null)   // constraint 8
    const [highlightedBlockId, setHighlightedBlockId] = useState<string | null>(null)  // constraint 9

    // Mutable cursor
    const nextYRef = useRef(PAD)
    const lastAnnotationEndYRef = useRef<number>(0)  // prevents annotation stacking

    // Stable ref to current blocks (for annotateStudentWork to read without deps)
    const blocksRef = useRef<Block[]>([])
    useEffect(() => { blocksRef.current = blocks }, [blocks])

    // Keep onSnapshot in a ref so the Fabric listener captures the latest callback
    const onSnapshotRef = useRef(onSnapshot)
    useEffect(() => { onSnapshotRef.current = onSnapshot }, [onSnapshot])

    // ── Fabric.js init ──────────────────────────────────────────────────────

    useEffect(() => {
      if (!fabricLayerRef.current) return
      let fc: unknown = null

      async function init() {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const fabric = (await import('fabric')) as any
        const container = fabricLayerRef.current!
        const w = container.offsetWidth || 800

        const canvas = document.createElement('canvas')
        canvas.width  = w
        canvas.height = visibleHeight
        canvas.style.cssText = `
          position: absolute; top: 0; left: 0;
          width: 100%; height: 100%;
          z-index: 10;
        `
        container.appendChild(canvas)

        const f = new fabric.Canvas(canvas, {
          isDrawingMode: true,
          backgroundColor: 'transparent',
          selection: false,
        })
        const brush = new fabric.PencilBrush(f)
        brush.color = STUDENT_INK
        brush.width = 3
        f.freeDrawingBrush = brush
        fabricRef.current = fc = f

        // Snapshot-on-pause (1.5s inactivity → send PNG to backend)
        let snapshotTimer: ReturnType<typeof setTimeout> | null = null
        f.on('path:created', () => {
          if (snapshotTimer) clearTimeout(snapshotTimer)
          snapshotTimer = setTimeout(() => {
            const cb = onSnapshotRef.current
            if (!cb) return
            try {
              const dataUrl: string = f.toDataURL({ format: 'png', multiplier: 1 })
              const b64 = dataUrl.split(',')[1]
              if (b64) cb(b64)
            } catch { /* ignore */ }
          }, 1500)
        })
      }
      init()

      return () => {
        try { (fc as { dispose?(): void })?.dispose?.() } catch { /* ok */ }
        fabricRef.current = null
        if (fabricLayerRef.current) fabricLayerRef.current.innerHTML = ''
      }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Resize Fabric canvas when doc grows
    useEffect(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fc = fabricRef.current as any
      if (!fc) return
      const container = fabricLayerRef.current
      const w = container?.offsetWidth || 800
      fc.setDimensions({ width: w, height: docHeight })
      fc.calcOffset()
    }, [docHeight])

    // Sync brush color/size when tool changes
    useEffect(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fc = fabricRef.current as any
      if (!fc?.freeDrawingBrush) return
      if (tool === 'eraser') {
        fc.freeDrawingBrush.color = theme === 'dark' ? '#0d1117' : '#fefcf9'
        fc.freeDrawingBrush.width = 20
      } else {
        fc.freeDrawingBrush.color = color
        fc.freeDrawingBrush.width = 3
      }
    }, [tool, color, theme])

    // ── Block append (constraints 1, 2, 3, 4, 8) ────────────────────────────

    const appendBlock = useCallback((raw: BlockWithoutY) => {
      const h = BLOCK_H[raw.kind] ?? 90

      // Constraint 2: find first collision-free Y slot
      const y = layoutManagerRef.current.findNextSlot(h, nextYRef.current)

      // Advance cursor and register the slot immediately (before the 400ms delay)
      // so rapid consecutive writes don't overlap
      nextYRef.current = y + h + GAP
      layoutManagerRef.current.registerBlock({ x: 0, y, w: 99999, h })

      // Constraint 3: grow doc so cursor is visible before block appears
      setDocHeight(prev => {
        const needed = nextYRef.current + visibleHeight * 0.5
        return needed > prev ? needed : prev
      })

      // Constraint 8: show pulsing cursor at write position
      setCursorY(y)

      // Scroll to show cursor
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({
          top: Math.max(0, y - visibleHeight * 0.4),
          behavior: 'smooth',
        })
      })

      // Constraint 4: reveal block after cursor has pulsed for 400ms
      setTimeout(() => {
        setBlocks(prev => [...prev, { ...raw, yOffset: y } as Block])
        setCursorY(null)
      }, 400)
    }, [visibleHeight])

    // ── Imperative API ──────────────────────────────────────────────────────

    const writeBlock = useCallback((latex: string, opts?: { display?: boolean }) => {
      appendBlock({
        id: `lb-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        kind: 'latex',
        latex,
        display: opts?.display !== false,
      })
    }, [appendBlock])

    const newSection = useCallback((label: string) => {
      appendBlock({ id: `div-${Date.now()}`, kind: 'divider', label })
    }, [appendBlock])

    const zoomTo = useCallback((target: 'top' | 'latest' | number) => {
      const el = scrollRef.current
      if (!el) return
      let y: number
      if (target === 'top')         y = 0
      else if (target === 'latest') y = Math.max(0, nextYRef.current - visibleHeight * 0.5)
      else                          y = target
      el.scrollTo({ top: y, behavior: 'smooth' })
    }, [visibleHeight])

    const getSnapshot = useCallback(async (): Promise<string | null> => {
      if (!docRef.current) return null
      const w = docRef.current.offsetWidth
      const h = docHeight

      const tutorHtml = tutorLayerRef.current?.innerHTML ?? ''
      const svgStr = [
        `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">`,
        `<foreignObject width="${w}" height="${h}">`,
        `<div xmlns="http://www.w3.org/1999/xhtml" style="width:${w}px;height:${h}px;">`,
        tutorHtml,
        `</div></foreignObject></svg>`,
      ].join('')

      const out = document.createElement('canvas')
      out.width = w; out.height = h
      const ctx = out.getContext('2d')!
      ctx.fillStyle = theme === 'dark' ? '#0d1117' : '#fefcf9'
      ctx.fillRect(0, 0, w, h)

      try {
        const tutorImg = await loadImg(
          'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgStr),
        )
        ctx.drawImage(tutorImg, 0, 0)
      } catch { /* SVG foreignObject may be tainted */ }

      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const fc = fabricRef.current as any
        if (fc) {
          const fabricImg = await loadImg(fc.toDataURL({ format: 'png', multiplier: 1 }))
          ctx.drawImage(fabricImg, 0, 0)
        }
      } catch { /* ignore */ }

      return out.toDataURL('image/png')
    }, [docHeight, theme])

    const clearBoard = useCallback(async (opts?: { snapshot?: boolean }) => {
      if (opts?.snapshot) {
        const snap = await getSnapshot()
        setSnapshot(snap)
      }
      setBlocks([])
      nextYRef.current = PAD
      lastAnnotationEndYRef.current = 0
      layoutManagerRef.current.clear()   // constraint 2: reset registry on clear
      setDocHeight(visibleHeight)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(fabricRef.current as any)?.clear()
    }, [getSnapshot, visibleHeight])

    const clearStudentLayer = useCallback(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(fabricRef.current as any)?.clear()
    }, [])

    // ── Constraint 5: mark last latex block as incorrect ─────────────────────

    const markIncorrect = useCallback(() => {
      setBlocks(prev => {
        const lastIdx = [...prev].reverse().findIndex(b => b.kind === 'latex')
        if (lastIdx === -1) return prev
        const idx = prev.length - 1 - lastIdx
        return prev.map((b, i) =>
          i === idx && b.kind === 'latex' ? { ...b, incorrect: true } : b
        )
      })
    }, [])

    // ── Constraints 6, 9: annotate student work with position awareness ───────

    const annotateStudentWork = useCallback((annotation: {
      latex?: string
      label?: string
      color?: 'correction' | 'confirmation' | 'neutral'
    }) => {
      // Constraint 9: flash the most recent latex block before placing annotation
      const lastLatex = blocksRef.current.slice().reverse().find(b => b.kind === 'latex')
      if (lastLatex) {
        setHighlightedBlockId(lastLatex.id)
        setTimeout(() => setHighlightedBlockId(null), 700)
      }

      // Constraint 6: place annotation adjacent to most recent student stroke
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fc = fabricRef.current as any
      const regions = layoutManagerRef.current.getStudentOccupiedRegions(fc)
      const docWidth = docRef.current?.offsetWidth ?? 800

      let xOff: number
      let yOff: number

      if (regions.length > 0) {
        const latest = regions[regions.length - 1]
        const slot = layoutManagerRef.current.findAdjacentSlot(latest, docWidth)
        xOff = slot.x
        yOff = slot.y
      } else {
        // No student work yet: place in right half at current tutor Y
        xOff = Math.floor(docWidth * 0.55)
        yOff = nextYRef.current
      }

      // Prevent stacking: advance past the bottom of the previous annotation
      const annH = BLOCK_H.annotation
      const safeY = lastAnnotationEndYRef.current > 0
        ? Math.max(yOff, lastAnnotationEndYRef.current + GAP)
        : yOff
      lastAnnotationEndYRef.current = safeY + annH

      setBlocks(prev => [...prev, {
        id: `ann-${Date.now()}`,
        kind: 'annotation' as const,
        latex: annotation.latex,
        label: annotation.label ?? 'AI Note',
        color: annotation.color ?? 'neutral',
        xOffset: xOff,
        yOffset: safeY,
      }])
    }, [])

    // ── Unified WS message handler ────────────────────────────────────────────

    const handleMessage = useCallback((msg: WhiteboardMessage | WbMessage) => {
      switch (msg.type) {
        case 'wb_write': {
          const m = msg as { type: 'wb_write'; latex?: string; scene?: GeometryElement[]; display?: boolean }
          if (m.scene && m.scene.length > 0) {
            appendBlock({
              id: `plot-${Date.now()}`,
              kind: 'plot',
              scene: m.scene,
            })
          } else if (m.latex) {
            writeBlock(m.latex, { display: m.display })
          }
          return
        }
        case 'wb_zoom':
          zoomTo((msg as { region: 'top' | 'latest' | number }).region)
          return
        case 'wb_clear':
          clearBoard({ snapshot: (msg as { snapshot?: boolean }).snapshot })
          return
        case 'wb_new_section':
          newSection((msg as { label: string }).label)
          return
        case 'wb_annotate_student': {
          const m = msg as { type: 'wb_annotate_student'; latex?: string; label?: string; color?: 'correction' | 'confirmation' | 'neutral' }
          annotateStudentWork({ latex: m.latex, label: m.label, color: m.color })
          return
        }
        case 'wb_mark_incorrect':
          markIncorrect()
          return
        case 'whiteboard': {
          const m = msg as WhiteboardMessage
          if (m.action === 'clear')                { clearBoard(); return }
          if (m.action === 'write' && m.latex)     { writeBlock(m.latex); return }
          if (m.action === 'plot'  && m.fn) {
            appendBlock({
              id: `plot-${Date.now()}`,
              kind: 'plot',
              fn: m.fn,
              domain: m.domain ?? [-5, 5],
            })
          }
          return
        }
      }
    }, [writeBlock, zoomTo, clearBoard, newSection, appendBlock, annotateStudentWork, markIncorrect])

    useImperativeHandle(ref, () => ({
      writeBlock,
      newSection,
      zoomTo,
      clearBoard,
      getSnapshot,
      handleMessage,
      exportPng: getSnapshot,
      annotateStudentWork,
      markIncorrect,
    }), [writeBlock, newSection, zoomTo, clearBoard, getSnapshot, handleMessage, annotateStudentWork, markIncorrect])

    // ── Download ──────────────────────────────────────────────────────────────

    const handleDownload = useCallback(async () => {
      const dataUrl = snapshot ?? await getSnapshot()
      if (!dataUrl) return
      const a = document.createElement('a')
      a.href = dataUrl
      a.download = `whiteboard-${Date.now()}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setSnapshot(null)
    }, [snapshot, getSnapshot])

    // ── Render ─────────────────────────────────────────────────────────────────

    const bgColor   = theme === 'dark' ? '#0d1117' : '#fefcf9'
    const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.028)' : 'rgba(0,0,0,0.038)'
    const tc = mkTC(theme)

    return (
      <div data-theme={theme} style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

        {/* Cursor keyframe animation (constraint 8) */}
        <style>{CURSOR_KEYFRAME}</style>

        {/* ── Toolbar ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
          padding: '5px 10px',
          borderRadius: '10px 10px 0 0',
          background: tc.surface,
          borderTop: `1px solid ${tc.border}`,
          borderLeft: `1px solid ${tc.border}`,
          borderRight: `1px solid ${tc.border}`,
          borderBottom: 'none',
          userSelect: 'none',
        }}>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: tc.textMuted,
            textTransform: 'uppercase', letterSpacing: '0.07em',
            marginRight: 2,
          }}>
            Tutor
          </span>
          <div style={{ flex: 1 }} />

          {(['pen', 'eraser'] as const).map(t => (
            <button key={t} type="button" title={t === 'pen' ? 'Pen (P)' : 'Eraser (E)'}
              onClick={() => setTool(t)}
              style={{
                width: 28, height: 28, borderRadius: 6,
                border: `1px solid ${tool === t ? tc.caramel : tc.border}`,
                background: tool === t ? tc.caramelDim : 'none',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14,
                color: tool === t ? tc.caramel : tc.textDim,
              }}>
              {t === 'pen' ? '✏' : '⌫'}
            </button>
          ))}

          {(['#2d6a4f', '#c4976a', '#4a7fb5', '#c1440e', '#1a1a1a'] as const).map(c => (
            <button key={c} type="button" title={c}
              onClick={() => { setColor(c); setTool('pen') }}
              style={{
                width: 16, height: 16, borderRadius: '50%', background: c, flexShrink: 0,
                border: color === c && tool === 'pen'
                  ? `2px solid ${tc.text}`
                  : '2px solid transparent',
                cursor: 'pointer',
              }} />
          ))}

          <div style={{ width: 1, height: 18, background: tc.border, margin: '0 2px' }} />

          <button type="button" title="Clear your drawings" onClick={clearStudentLayer}
            style={{ padding: '3px 8px', borderRadius: 6, border: `1px solid ${tc.border}`, background: 'none', cursor: 'pointer', fontSize: 11, color: tc.textDim }}>
            Clear
          </button>
          <button type="button" title="Download whiteboard as PNG" onClick={handleDownload}
            style={{ padding: '3px 8px', borderRadius: 6, border: `1px solid ${tc.border}`, background: 'none', cursor: 'pointer', fontSize: 11, color: tc.textDim }}>
            ↓ Save
          </button>
        </div>

        {/* ── Scrollable canvas area ── */}
        <div
          ref={scrollRef}
          data-testid="wb-scroll"
          style={{
            height: visibleHeight,
            overflowY: 'auto',
            overflowX: 'hidden',
            border: `1px solid ${tc.border}`,
            borderRadius: snapshot ? 0 : '0 0 10px 10px',
            position: 'relative',
          }}
        >
          <div
            ref={docRef}
            data-testid="wb-doc"
            style={{
              position: 'relative',
              width: '100%',
              height: docHeight,
              backgroundColor: bgColor,
              backgroundImage: [
                `linear-gradient(${gridColor} 1px, transparent 1px)`,
                `linear-gradient(90deg, ${gridColor} 1px, transparent 1px)`,
              ].join(', '),
              backgroundSize: '24px 24px',
            }}
          >
            {/* Tutor layer */}
            <div
              ref={tutorLayerRef}
              data-testid="wb-tutor-layer"
              style={{ position: 'absolute', inset: 0, zIndex: 5, pointerEvents: 'none' }}
            >
              {blocks.map(block => {
                if (block.kind === 'latex')
                  return (
                    <LatexItem
                      key={block.id}
                      block={block}
                      highlighted={block.id === highlightedBlockId}
                      theme={theme}
                    />
                  )
                if (block.kind === 'divider')
                  return <SectionDivider key={block.id} block={block} tc={tc} />
                if (block.kind === 'plot')
                  return (
                    <div key={block.id} style={{
                      position: 'absolute',
                      left: PAD, top: block.yOffset,
                      width: `calc(100% - ${PAD * 2}px)`,
                      zIndex: 5,
                    }}>
                      <MafsPlot
                        fn={block.fn}
                        domain={block.domain}
                        scene={block.scene}
                        theme={theme}
                      />
                    </div>
                  )
                if (block.kind === 'annotation')
                  return <AnnotationItem key={block.id} block={block} tc={tc} />
                return null
              })}

              {/* Constraint 8: pulsing cursor at next write position */}
              {cursorY !== null && (
                <div style={{
                  position: 'absolute',
                  left: PAD,
                  top: cursorY + 4,
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: CORRECTION_INK,
                  animation: 'wb-cursor-pulse 1.1s infinite ease-in-out',
                  zIndex: 6,
                  pointerEvents: 'none',
                }} />
              )}
            </div>

            {/* Student layer — Fabric.js canvas mounted imperatively */}
            <div
              ref={fabricLayerRef}
              data-testid="wb-student-layer"
              style={{
                position: 'absolute', inset: 0,
                zIndex: 10,
                cursor: tool === 'eraser' ? 'cell' : 'crosshair',
              }}
            />

            {/* Empty state */}
            {blocks.length === 0 && cursorY === null && (
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                pointerEvents: 'none', zIndex: 4,
              }}>
                <div style={{ textAlign: 'center', color: tc.textMuted, opacity: 0.4 }}>
                  <div style={{ fontSize: 26, marginBottom: 8 }}>✦</div>
                  <div style={{ fontSize: 13 }}>Your tutor will write here.</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>Draw anywhere on the canvas.</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Pre-clear snapshot banner */}
        {snapshot && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 12px',
            fontSize: 12,
            background: tc.caramelDim,
            border: `1px solid ${tc.caramelGlow}`,
            borderTop: 'none',
            borderRadius: '0 0 10px 10px',
          }}>
            <span style={{ color: tc.caramel, fontWeight: 600, fontSize: 14 }}>⬇</span>
            <span style={{ flex: 1, color: tc.textDim }}>
              Board cleared for exam mode. Your notes are saved.
            </span>
            <button type="button" onClick={handleDownload}
              style={{
                padding: '4px 12px', borderRadius: 6,
                background: tc.caramel, color: '#fff',
                border: 'none', cursor: 'pointer',
                fontSize: 12, fontWeight: 600,
              }}>
              Download Notes
            </button>
          </div>
        )}
      </div>
    )
  },
)

Whiteboard.displayName = 'Whiteboard'

// ── Utility ───────────────────────────────────────────────────────────────────

function loadImg(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload  = () => resolve(img)
    img.onerror = reject
    img.src     = src
  })
}
