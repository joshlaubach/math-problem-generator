'use client'

/**
 * Interactive whiteboard for the AI tutor session.
 *
 * Two layers stacked via position:absolute:
 *   Layer 0 (tutor, z-index 5): GSAP-animated KaTeX renders + Mafs function plots
 *   Layer 1 (student, z-index 10): Fabric.js freehand canvas (transparent background)
 *
 * Spatial convention: tutor content flows top-left → bottom-right.
 * Student zone is implied lower-right quadrant.
 *
 * WS message types handled:
 *   {type:"whiteboard", action:"write", latex:"...", x:0-100, y:0-100}
 *   {type:"whiteboard", action:"plot",  fn:"x**2-3*x+2", domain:[-2,5], y:0-100}
 *   {type:"whiteboard", action:"clear"}
 */

import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  forwardRef,
} from 'react'
import dynamic from 'next/dynamic'

// Dynamic imports to avoid SSR issues
const MafsPlot = dynamic(() => import('./WhiteboardPlot'), {
  ssr: false,
  loading: () => <div style={{ width: '100%', height: 120, background: 'var(--surface)' }} />,
})

// ── Types ─────────────────────────────────────────────────────────────────────

export interface WhiteboardMessage {
  type: 'whiteboard'
  action: 'write' | 'plot' | 'clear'
  latex?: string
  fn?: string
  domain?: [number, number]
  x?: number   // percent 0-100
  y?: number   // percent 0-100
}

interface TutorItem {
  id: string
  type: 'latex' | 'plot'
  latex?: string
  fn?: string
  domain?: [number, number]
  x: number
  y: number
  visible: boolean
  animating: boolean
}

export interface WhiteboardHandle {
  handleMessage: (msg: WhiteboardMessage) => void
  exportPng: () => string | null
}

interface WhiteboardProps {
  height?: number
  theme?: 'light' | 'dark'
}

// ── Tutor item renderer ────────────────────────────────────────────────────────

function TutorLatexItem({
  item,
  onAnimDone,
}: {
  item: TutorItem
  onAnimDone: (id: string) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [katexHtml, setKatexHtml] = useState('')

  useEffect(() => {
    if (!item.animating || !ref.current) return
    let cancelled = false

    async function animate() {
      const gsap = (await import('gsap')).default
      if (cancelled || !ref.current) return
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: 8 },
        {
          opacity: 1,
          y: 0,
          duration: 0.45,
          ease: 'power2.out',
          onComplete: () => {
            if (!cancelled) onAnimDone(item.id)
          },
        }
      )
    }
    animate()
    return () => { cancelled = true }
  }, [item.id, item.animating, onAnimDone])

  // Render KaTeX via renderToString so React controls the DOM
  useEffect(() => {
    if (!item.latex) return
    try {
      const katex = require('katex')
      const html = katex.renderToString(item.latex, {
        throwOnError: false,
        displayMode: item.latex.includes('\\frac') || item.latex.includes('\\int'),
      })
      setKatexHtml(html)
    } catch {
      setKatexHtml(item.latex || '')
    }
  }, [item.latex])

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        left: `${item.x}%`,
        top: `${item.y}%`,
        opacity: item.animating ? 0 : 1,
        maxWidth: '45%',
        padding: '6px 10px',
        borderRadius: 6,
        background: 'rgba(196,151,106,0.08)',
        border: '1px solid rgba(196,151,106,0.15)',
        zIndex: 5,
      }}
    >
      <div
        className="wb-katex"
        style={{ fontSize: 15, color: 'var(--text)' }}
        dangerouslySetInnerHTML={{ __html: katexHtml }}
      />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export const Whiteboard = forwardRef<WhiteboardHandle, WhiteboardProps>(
  function Whiteboard({ height = 340, theme = 'light' }, ref) {
    const containerRef = useRef<HTMLDivElement>(null)
    const fabricLayerRef = useRef<HTMLDivElement>(null)  // Fabric.js mounts inside here
    const fabricRef = useRef<unknown>(null)  // fabric.Canvas instance

    const [tutorItems, setTutorItems] = useState<TutorItem[]>([])
    const [plots, setPlots] = useState<TutorItem[]>([])
    const [tool, setTool] = useState<'pen' | 'eraser'>('pen')
    const [color, setColor] = useState('#2d6a4f')
    const [strokeWidth, setStrokeWidth] = useState(3)

    // Init Fabric.js canvas — create canvas imperatively so React never owns it
    useEffect(() => {
      if (!fabricLayerRef.current) return
      let fc: any = null

      async function initFabric() {
        const fabric = await import('fabric')
        // Create canvas outside React's managed DOM tree
        const canvas = document.createElement('canvas')
        canvas.width = 800
        canvas.height = height
        canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;z-index:10;'
        fabricLayerRef.current!.appendChild(canvas)

        fc = new (fabric as any).Canvas(canvas, {
          isDrawingMode: true,
          backgroundColor: 'transparent',
          selection: false,
        })
        // Fabric v7: PencilBrush must be explicitly created
        const brush = new (fabric as any).PencilBrush(fc)
        brush.color = color
        brush.width = strokeWidth
        fc.freeDrawingBrush = brush
        fabricRef.current = fc
      }
      initFabric()

      return () => {
        try { fc?.dispose() } catch { /* ok */ }
        fabricRef.current = null
        if (fabricLayerRef.current) fabricLayerRef.current.innerHTML = ''
      }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Sync brush settings
    useEffect(() => {
      const canvas = fabricRef.current as any
      if (!canvas) return
      if (tool === 'eraser') {
        canvas.freeDrawingBrush.color = theme === 'dark' ? '#1a1a1a' : '#ffffff'
        canvas.freeDrawingBrush.width = 18
      } else {
        canvas.freeDrawingBrush.color = color
        canvas.freeDrawingBrush.width = strokeWidth
      }
    }, [tool, color, strokeWidth, theme])

    const handleAnimDone = useCallback((id: string) => {
      setTutorItems(prev =>
        prev.map(item => item.id === id ? { ...item, animating: false } : item)
      )
    }, [])

    const handleMessage = useCallback((msg: WhiteboardMessage) => {
      if (msg.action === 'clear') {
        setTutorItems([])
        setPlots([])
        return
      }

      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
      const x = msg.x ?? 2
      const y = msg.y ?? (tutorItems.length * 14 + 2)

      if (msg.action === 'write' && msg.latex) {
        setTutorItems(prev => [
          ...prev,
          { id, type: 'latex', latex: msg.latex, x, y, visible: true, animating: true },
        ])
      } else if (msg.action === 'plot' && msg.fn) {
        setPlots(prev => [
          ...prev,
          {
            id, type: 'plot', fn: msg.fn,
            domain: msg.domain ?? [-5, 5],
            x: 2, y: y + 20,
            visible: true, animating: false,
          },
        ])
      }
    }, [tutorItems.length])

    const clearStudentLayer = useCallback(() => {
      (fabricRef.current as any)?.clear()
    }, [])

    const exportPng = useCallback((): string | null => {
      return (fabricRef.current as any)?.toDataURL({ format: 'png', multiplier: 1 }) ?? null
    }, [])

    useImperativeHandle(ref, () => ({ handleMessage, exportPng }), [handleMessage, exportPng])

    const bg = theme === 'dark' ? '#1a1a1a' : '#fefcf9'
    const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {/* Toolbar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 10px',
          borderRadius: '10px 10px 0 0',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderBottom: 'none',
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Whiteboard
          </span>
          <div style={{ flex: 1 }} />
          {/* Pen */}
          <button
            type="button"
            title="Pen"
            onClick={() => setTool('pen')}
            style={{
              width: 28, height: 28, borderRadius: 6,
              border: `1px solid ${tool === 'pen' ? 'var(--caramel)' : 'var(--border)'}`,
              background: tool === 'pen' ? 'var(--caramel-dim)' : 'none',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, color: tool === 'pen' ? 'var(--caramel)' : 'var(--text-dim)',
            }}
          >✏</button>
          {/* Eraser */}
          <button
            type="button"
            title="Eraser"
            onClick={() => setTool('eraser')}
            style={{
              width: 28, height: 28, borderRadius: 6,
              border: `1px solid ${tool === 'eraser' ? 'var(--caramel)' : 'var(--border)'}`,
              background: tool === 'eraser' ? 'var(--caramel-dim)' : 'none',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, color: tool === 'eraser' ? 'var(--caramel)' : 'var(--text-dim)',
            }}
          >⌫</button>
          {/* Color swatches */}
          {['#2d6a4f', '#c4976a', '#4a7fb5', '#c1440e', '#1a1a1a'].map(c => (
            <button
              key={c}
              type="button"
              onClick={() => { setColor(c); setTool('pen') }}
              style={{
                width: 18, height: 18, borderRadius: '50%',
                background: c,
                border: color === c && tool === 'pen' ? '2px solid var(--text)' : '2px solid transparent',
                cursor: 'pointer', flexShrink: 0,
              }}
            />
          ))}
          {/* Clear student layer */}
          <button
            type="button"
            title="Clear your drawings"
            onClick={clearStudentLayer}
            style={{
              padding: '3px 8px', borderRadius: 6,
              border: '1px solid var(--border)', background: 'none',
              cursor: 'pointer', fontSize: 11, color: 'var(--text-dim)',
            }}
          >
            Clear
          </button>
        </div>

        {/* Canvas area */}
        <div
          ref={containerRef}
          style={{
            position: 'relative',
            width: '100%',
            height,
            background: bg,
            border: '1px solid var(--border)',
            borderRadius: '0 0 10px 10px',
            overflow: 'hidden',
            // Subtle grid
            backgroundImage: `linear-gradient(${gridColor} 1px, transparent 1px),
                               linear-gradient(90deg, ${gridColor} 1px, transparent 1px)`,
            backgroundSize: '24px 24px',
          }}
        >
          {/* Tutor layer: KaTeX items */}
          {tutorItems.map(item => (
            <TutorLatexItem key={item.id} item={item} onAnimDone={handleAnimDone} />
          ))}

          {/* Tutor layer: Mafs plots */}
          {plots.map(plot => (
            <div
              key={plot.id}
              style={{
                position: 'absolute',
                left: `${plot.x}%`,
                top: `${plot.y}%`,
                width: '55%',
                zIndex: 5,
              }}
            >
              <MafsPlot fn={plot.fn!} domain={plot.domain as [number, number]} theme={theme} />
            </div>
          ))}

          {/* Student layer: Fabric.js (canvas created imperatively to avoid React DOM conflicts) */}
          <div
            ref={fabricLayerRef}
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 10,
              cursor: tool === 'eraser' ? 'cell' : 'crosshair',
            }}
          />

          {/* Empty state hint */}
          {tutorItems.length === 0 && plots.length === 0 && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              pointerEvents: 'none', zIndex: 4,
            }}>
              <div style={{
                textAlign: 'center',
                color: 'var(--text-muted)', opacity: 0.5,
              }}>
                <div style={{ fontSize: 28, marginBottom: 8, opacity: 0.4 }}>✦</div>
                <div style={{ fontSize: 13 }}>Your tutor will write here.</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>Use the tools above to work in the lower area.</div>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }
)

Whiteboard.displayName = 'Whiteboard'
