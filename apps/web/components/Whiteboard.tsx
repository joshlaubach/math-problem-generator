'use client'

/**
 * Whiteboard — persistent scrollable canvas for AI tutor sessions.
 *
 * Layer stack (bottom → top, both inside the scrollable doc):
 *   0. CSS dot-grid background
 *   1. Tutor layer — GSAP-animated KaTeX blocks + section dividers (z-index 5, pointer-events none)
 *   2. Student layer — Fabric.js freehand canvas (z-index 10)
 *
 * The doc grows vertically as the tutor writes. Fabric.js canvas is resized
 * to match the doc height so student drawings work across the full area.
 *
 * Imperative API (via forwardRef → WhiteboardHandle):
 *   writeBlock(latex, opts?)   — tutor writes a math block (GSAP fade-in)
 *   newSection(label)          — horizontal divider with label
 *   zoomTo(target)             — smooth-scroll: 'top' | 'latest' | yPx
 *   clearBoard(opts?)          — clear all content (snapshot first if opts.snapshot)
 *   getSnapshot()              — async PNG composite of full board
 *
 * Backward-compat (used by TutorChat.tsx and useTutorSession.ts):
 *   handleMessage(msg)         — legacy WhiteboardMessage + new wb_* messages
 *   exportPng()                — alias for getSnapshot()
 *
 * Phase-4 WS message types handled by handleMessage:
 *   { type: 'wb_write',       latex, display? }
 *   { type: 'wb_zoom',        region }
 *   { type: 'wb_clear',       snapshot? }
 *   { type: 'wb_new_section', label }
 *   { type: 'whiteboard',     action: 'write'|'plot'|'clear', ... }  ← legacy
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

// ── Dynamic imports (no SSR) ─────────────────────────────────────────────────

const MafsPlot = dynamic(() => import('./WhiteboardPlot'), {
  ssr: false,
  loading: () => <div style={{ width: '100%', height: 160, borderRadius: 8 }} />,
})

// ── Public types ──────────────────────────────────────────────────────────────

/** Legacy message type (kept for TutorChat.tsx / useTutorSession.ts compat) */
export interface WhiteboardMessage {
  type: 'whiteboard'
  action: 'write' | 'plot' | 'clear'
  latex?: string
  fn?: string
  domain?: [number, number]
  x?: number  // ignored in new layout (vertical auto-flow)
  y?: number  // ignored in new layout
}

/** Phase-4 WS message types */
export type WbMessage =
  | { type: 'wb_write';       latex: string; display?: boolean }
  | { type: 'wb_zoom';        region: 'top' | 'latest' | number }
  | { type: 'wb_clear';       snapshot?: boolean }
  | { type: 'wb_new_section'; label: string }

export interface WhiteboardHandle {
  writeBlock(latex: string, opts?: { display?: boolean }): void
  newSection(label: string): void
  zoomTo(target: 'top' | 'latest' | number): void
  clearBoard(opts?: { snapshot?: boolean }): void
  getSnapshot(): Promise<string | null>
  /** Unified handler — accepts both legacy and Phase-4 WS messages */
  handleMessage(msg: WhiteboardMessage | WbMessage): void
  /** Alias for getSnapshot() — backward compat */
  exportPng(): Promise<string | null>
}

export interface WhiteboardProps {
  visibleHeight?: number
  theme?: 'light' | 'dark'
}

// ── Internal block model ───────────────────────────────────────────────────────

type LatexBlock   = { id: string; kind: 'latex';   latex: string; display: boolean; yOffset: number }
type PlotBlock    = { id: string; kind: 'plot';    fn: string; domain: [number, number]; yOffset: number }
type DividerBlock = { id: string; kind: 'divider'; label: string; yOffset: number }
type Block = LatexBlock | PlotBlock | DividerBlock

// Generous approximate heights so blocks never overlap
const BLOCK_H: Record<Block['kind'], number> = {
  latex:   90,
  plot:    220,
  divider: 52,
}
const GAP = 14    // vertical gap between blocks
const PAD = 12    // left/right padding inside doc

// ── Animated KaTeX block ──────────────────────────────────────────────────────

const LatexItem = memo(function LatexItem({ block }: { block: LatexBlock }) {
  const ref  = useRef<HTMLDivElement>(null)
  const [html, setHtml] = useState('')

  // Render KaTeX on content change
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

  // GSAP fade-in on mount (runs once)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    // Fallback: ensure visible even if GSAP fails to load
    const fallback = setTimeout(() => { if (el) el.style.opacity = '1' }, 700)

    ;(async () => {
      try {
        const gsap = (await import('gsap')).default
        clearTimeout(fallback)
        gsap.fromTo(
          el,
          { opacity: 0, y: 10 },
          { opacity: 1, y: 0, duration: 0.45, ease: 'power2.out' },
        )
      } catch {
        if (el) el.style.opacity = '1'
      }
    })()

    return () => clearTimeout(fallback)
  }, []) // intentionally runs only on mount

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        left: PAD,
        top: block.yOffset,
        width: `calc(100% - ${PAD * 2}px)`,
        opacity: 0,           // GSAP will reveal
        padding: '8px 12px',
        borderRadius: 8,
        background: 'rgba(196,151,106,0.07)',
        border: '1px solid rgba(196,151,106,0.13)',
        color: 'var(--text)',
        zIndex: 5,
        pointerEvents: 'none',
        minHeight: 44,
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
})

// ── Section divider ───────────────────────────────────────────────────────────

function SectionDivider({ block }: { block: DividerBlock }) {
  return (
    <div
      style={{
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
      }}
    >
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      <span style={{
        fontSize: 11,
        fontWeight: 600,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.07em',
        whiteSpace: 'nowrap',
        padding: '3px 8px',
        borderRadius: 12,
        background: 'var(--surface2)',
        border: '1px solid var(--border)',
      }}>
        {block.label}
      </span>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export const Whiteboard = forwardRef<WhiteboardHandle, WhiteboardProps>(
  function Whiteboard({ visibleHeight = 520, theme = 'light' }, ref) {

    // DOM refs
    const scrollRef      = useRef<HTMLDivElement>(null)  // scrollable viewport
    const docRef         = useRef<HTMLDivElement>(null)  // growing doc
    const tutorLayerRef  = useRef<HTMLDivElement>(null)  // tutor DOM layer
    const fabricLayerRef = useRef<HTMLDivElement>(null)  // Fabric.js mounts here
    const fabricRef      = useRef<unknown>(null)         // fabric.Canvas instance

    // State
    const [blocks, setBlocks]       = useState<Block[]>([])
    const [docHeight, setDocHeight] = useState(visibleHeight)
    const [tool, setTool]           = useState<'pen' | 'eraser'>('pen')
    const [color, setColor]         = useState('#2d6a4f')
    const [snapshot, setSnapshot]   = useState<string | null>(null)

    // Mutable cursor — updated synchronously in appendBlock, no re-render
    const nextYRef = useRef(PAD)

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
        brush.color = '#2d6a4f'
        brush.width = 3
        f.freeDrawingBrush = brush
        fabricRef.current = fc = f
      }
      init()

      return () => {
        try { (fc as { dispose?(): void })?.dispose?.() } catch { /* ok */ }
        fabricRef.current = null
        if (fabricLayerRef.current) fabricLayerRef.current.innerHTML = ''
      }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Resize Fabric canvas when doc grows (Fabric v7: use setDimensions)
    useEffect(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fc = fabricRef.current as any
      if (!fc) return
      const container = fabricLayerRef.current
      const w = container?.offsetWidth || 800
      // setDimensions is the Fabric v7 API (setWidth/setHeight removed)
      fc.setDimensions({ width: w, height: docHeight })
      fc.calcOffset()
    }, [docHeight])

    // Sync brush
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

    // ── Block append ────────────────────────────────────────────────────────

    const appendBlock = useCallback((raw: Omit<Block, 'yOffset'>) => {
      const y = nextYRef.current
      const h = BLOCK_H[raw.kind]
      nextYRef.current = y + h + GAP

      // Grow doc height if content is near the bottom
      setDocHeight(prev => {
        const needed = nextYRef.current + visibleHeight * 0.5
        return needed > prev ? needed : prev
      })

      setBlocks(prev => [...prev, { ...raw, yOffset: y } as Block])

      // Auto-scroll to show the new block
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({
          top: Math.max(0, nextYRef.current - visibleHeight * 0.6),
          behavior: 'smooth',
        })
      })
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

      // Render tutor DOM layer to an SVG via foreignObject
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
      } catch { /* SVG foreignObject might be tainted — skip tutor layer */ }

      // Overlay Fabric.js student layer
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
      setDocHeight(visibleHeight)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(fabricRef.current as any)?.clear()
    }, [getSnapshot, visibleHeight])

    const clearStudentLayer = useCallback(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(fabricRef.current as any)?.clear()
    }, [])

    // ── Unified WS message handler (legacy + Phase-4) ────────────────────

    const handleMessage = useCallback((msg: WhiteboardMessage | WbMessage) => {
      switch (msg.type) {
        // Phase-4 types
        case 'wb_write':       { writeBlock(msg.latex, { display: (msg as { display?: boolean }).display }); return }
        case 'wb_zoom':        { zoomTo((msg as { region: 'top' | 'latest' | number }).region); return }
        case 'wb_clear':       { clearBoard({ snapshot: (msg as { snapshot?: boolean }).snapshot }); return }
        case 'wb_new_section': { newSection((msg as { label: string }).label); return }

        // Legacy whiteboard type
        case 'whiteboard': {
          const m = msg as WhiteboardMessage
          if (m.action === 'clear')                      { clearBoard(); return }
          if (m.action === 'write' && m.latex)           { writeBlock(m.latex); return }
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
    }, [writeBlock, zoomTo, clearBoard, newSection, appendBlock])

    useImperativeHandle(ref, () => ({
      writeBlock,
      newSection,
      zoomTo,
      clearBoard,
      getSnapshot,
      handleMessage,
      exportPng: getSnapshot,
    }), [writeBlock, newSection, zoomTo, clearBoard, getSnapshot, handleMessage])

    // ── Download ─────────────────────────────────────────────────────────

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

    // ── Render ────────────────────────────────────────────────────────────

    const bgColor   = theme === 'dark' ? '#0d1117' : '#fefcf9'
    const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.028)' : 'rgba(0,0,0,0.038)'

    return (
      // data-theme propagates CSS variables into the whiteboard so var(--text),
      // var(--border) etc. resolve correctly in both light and dark mode.
      <div data-theme={theme} style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

        {/* ── Toolbar ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
          padding: '5px 10px',
          borderRadius: '10px 10px 0 0',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderBottom: 'none',
          userSelect: 'none',
        }}>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.07em',
            marginRight: 2,
          }}>
            Whiteboard
          </span>
          <div style={{ flex: 1 }} />

          {/* Pen / Eraser */}
          {(['pen', 'eraser'] as const).map(t => (
            <button key={t} type="button" title={t === 'pen' ? 'Pen (P)' : 'Eraser (E)'}
              onClick={() => setTool(t)}
              style={{
                width: 28, height: 28, borderRadius: 6,
                border: `1px solid ${tool === t ? 'var(--caramel)' : 'var(--border)'}`,
                background: tool === t ? 'var(--caramel-dim)' : 'none',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14,
                color: tool === t ? 'var(--caramel)' : 'var(--text-dim)',
              }}>
              {t === 'pen' ? '✏' : '⌫'}
            </button>
          ))}

          {/* Color swatches */}
          {(['#2d6a4f', '#c4976a', '#4a7fb5', '#c1440e', '#1a1a1a'] as const).map(c => (
            <button key={c} type="button" title={c}
              onClick={() => { setColor(c); setTool('pen') }}
              style={{
                width: 16, height: 16, borderRadius: '50%', background: c, flexShrink: 0,
                border: color === c && tool === 'pen'
                  ? '2px solid var(--text)'
                  : '2px solid transparent',
                cursor: 'pointer',
              }} />
          ))}

          <div style={{ width: 1, height: 18, background: 'var(--border)', margin: '0 2px' }} />

          {/* Clear student drawings */}
          <button type="button" title="Clear your drawings" onClick={clearStudentLayer}
            style={toolBtnStyle}>
            Clear
          </button>

          {/* Download / Save */}
          <button type="button" title="Download whiteboard as PNG" onClick={handleDownload}
            style={toolBtnStyle}>
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
            border: '1px solid var(--border)',
            borderRadius: snapshot ? 0 : '0 0 10px 10px',
            position: 'relative',
          }}
        >
          {/* Growing document */}
          <div
            ref={docRef}
            data-testid="wb-doc"
            style={{
              position: 'relative',
              width: '100%',
              height: docHeight,
              // Use backgroundColor (not background shorthand) to avoid React's
              // "conflicting shorthand / longhand property" warning with backgroundImage
              backgroundColor: bgColor,
              backgroundImage: [
                `linear-gradient(${gridColor} 1px, transparent 1px)`,
                `linear-gradient(90deg, ${gridColor} 1px, transparent 1px)`,
              ].join(', '),
              backgroundSize: '24px 24px',
            }}
          >
            {/* Tutor layer — all React-rendered blocks */}
            <div
              ref={tutorLayerRef}
              data-testid="wb-tutor-layer"
              style={{ position: 'absolute', inset: 0, zIndex: 5, pointerEvents: 'none' }}
            >
              {blocks.map(block => {
                if (block.kind === 'latex')
                  return <LatexItem key={block.id} block={block} />
                if (block.kind === 'divider')
                  return <SectionDivider key={block.id} block={block} />
                if (block.kind === 'plot')
                  return (
                    <div key={block.id} style={{
                      position: 'absolute',
                      left: PAD, top: block.yOffset,
                      width: `calc(100% - ${PAD * 2}px)`,
                      zIndex: 5,
                    }}>
                      <MafsPlot fn={block.fn} domain={block.domain} theme={theme} />
                    </div>
                  )
                return null
              })}
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
            {blocks.length === 0 && (
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                pointerEvents: 'none', zIndex: 4,
              }}>
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', opacity: 0.4 }}>
                  <div style={{ fontSize: 26, marginBottom: 8 }}>✦</div>
                  <div style={{ fontSize: 13 }}>Your tutor will write here.</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>Draw anywhere on the canvas.</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Pre-clear snapshot banner ── */}
        {snapshot && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 12px',
            fontSize: 12,
            background: 'var(--caramel-dim)',
            border: '1px solid var(--caramel-glow)',
            borderTop: 'none',
            borderRadius: '0 0 10px 10px',
          }}>
            <span style={{ color: 'var(--caramel)', fontWeight: 600, fontSize: 14 }}>⬇</span>
            <span style={{ flex: 1, color: 'var(--text-dim)' }}>
              Board cleared for exam mode — your notes are saved.
            </span>
            <button type="button" onClick={handleDownload}
              style={{
                padding: '4px 12px', borderRadius: 6,
                background: 'var(--caramel)', color: '#fff',
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

// ── Shared button style ───────────────────────────────────────────────────────

const toolBtnStyle: React.CSSProperties = {
  padding: '3px 8px',
  borderRadius: 6,
  border: '1px solid var(--border)',
  background: 'none',
  cursor: 'pointer',
  fontSize: 11,
  color: 'var(--text-dim)',
}

// ── Utility ───────────────────────────────────────────────────────────────────

function loadImg(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload  = () => resolve(img)
    img.onerror = reject
    img.src     = src
  })
}
