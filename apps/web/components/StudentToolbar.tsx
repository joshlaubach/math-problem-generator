'use client'

import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import { MathInput } from '@/components/MathInput'
import katex from 'katex'

// ── Constants ─────────────────────────────────────────────────────────────────

const SWATCHES = [
  '#0f1623', '#4a9eff', '#c4976a', '#f87171',
  '#4ade80', '#facc15', '#a78bfa', '#94a3b8',
] as const
type Swatch = typeof SWATCHES[number]

type Tool =
  | 'select' | 'pen' | 'highlight' | 'eraser'
  | 'line' | 'arrow' | 'rect' | 'circle' | 'triangle'
  | 'angle' | 'text' | 'latex'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StudentToolbarHandle {
  clear: () => void
  undo: () => void
  redo: () => void
  exportPng: () => string | null
}

export interface StudentToolbarProps {
  theme: 'light' | 'dark'
  width?: number
  height?: number
  onSnapshot?: (imageB64: string) => void
}

// ── Component ─────────────────────────────────────────────────────────────────

export const StudentToolbar = forwardRef<StudentToolbarHandle, StudentToolbarProps>(
  function StudentToolbar({ theme, width = 560, height = 260, onSnapshot }, ref) {
    const canvasElRef  = useRef<HTMLCanvasElement>(null)
    const fabricRef    = useRef<any>(null)   // fabric.Canvas instance
    const FRef         = useRef<any>(null)   // fabric module (named exports)
    const historyRef   = useRef<object[]>([])
    const histIdx      = useRef(-1)
    const snapTimer    = useRef<ReturnType<typeof setTimeout> | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Refs for canvas event handlers — avoids stale React-closure bugs
    const toolRef      = useRef<Tool>('pen')
    const colorRef     = useRef<Swatch>(SWATCHES[1])
    const gridSnapRef  = useRef(false)

    // Shape-drawing runtime state (lives in a ref, not React state)
    const draw = useRef({
      active: false, shape: null as any,
      x0: 0, y0: 0,
      pts: [] as Array<{ x: number; y: number }>,
      ray1: null as any,
    })

    // React state — drives toolbar rendering only
    const [tool,  setTool]  = useState<Tool>('pen')
    const [color, setColor] = useState<Swatch>(SWATCHES[1])
    const [gridSnap, setGridSnap] = useState(false)
    const [showShapes, setShowShapes] = useState(false)
    const [showLatex,  setShowLatex]  = useState(false)
    const [latexVal,   setLatexVal]   = useState('')
    const [placing,    setPlacing]    = useState(false)

    // Sync React state → refs so canvas handlers always see current values
    useEffect(() => { toolRef.current  = tool },     [tool])
    useEffect(() => { colorRef.current = color },    [color])
    useEffect(() => { gridSnapRef.current = gridSnap }, [gridSnap])

    // ── Theme ─────────────────────────────────────────────────────────────────
    const d = theme === 'dark'
    const bg        = d ? '#0d1117' : '#ffffff'
    const surface   = d ? '#1c2128' : '#f6f7fb'
    const border    = d ? '#30363d' : '#dce0ee'
    const text      = d ? '#e6edf3' : '#0f1623'
    const textMuted = d ? '#8b949e' : '#4a5472'
    const caramel   = d ? '#d29922' : '#b8860b'
    const caramelDim = d ? 'rgba(210,153,34,0.12)' : 'rgba(184,134,11,0.10)'

    // ── Fabric init ───────────────────────────────────────────────────────────
    useEffect(() => {
      const el = canvasElRef.current
      if (!el || fabricRef.current) return
      let gone = false

      import('fabric').then((mod: any) => {
        if (gone) return
        const F = mod   // fabric v7: Canvas, PencilBrush, etc. are named exports
        FRef.current = F

        const canvas = new F.Canvas(el, {
          width, height, backgroundColor: bg, isDrawingMode: true,
        })
        fabricRef.current = canvas

        // ── default pen ──────────────────────────────────────────────────────
        const pen = new F.PencilBrush(canvas)
        pen.color = colorRef.current
        pen.width = 2
        canvas.freeDrawingBrush = pen

        // ── history ──────────────────────────────────────────────────────────
        const save = () => {
          historyRef.current.splice(histIdx.current + 1)
          historyRef.current.push(canvas.toJSON())
          histIdx.current = historyRef.current.length - 1
        }

        // ── snapshot ─────────────────────────────────────────────────────────
        const scheduleSnap = () => {
          if (!onSnapshot) return
          if (snapTimer.current) clearTimeout(snapTimer.current)
          snapTimer.current = setTimeout(() => {
            const url = canvas.toDataURL({ format: 'png', multiplier: 1 })
            onSnapshot(url.split(',')[1])
          }, 1500)
        }

        // ── unified mouse handlers ───────────────────────────────────────────
        canvas.on('mouse:down', (opt: any) => {
          const t = toolRef.current
          const F2 = FRef.current
          if (!F2) return
          const p = canvas.getScenePoint(opt.e)
          const ds = draw.current

          if (t === 'line' || t === 'arrow') {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
            ds.shape = new F2.Line([p.x, p.y, p.x, p.y], {
              stroke: colorRef.current, strokeWidth: 2,
              selectable: false, strokeLineCap: 'round',
            })
            canvas.add(ds.shape)
          }

          if (t === 'rect') {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
            ds.shape = new F2.Rect({
              left: p.x, top: p.y, width: 0, height: 0,
              stroke: colorRef.current, strokeWidth: 2,
              fill: 'transparent', selectable: false,
            })
            canvas.add(ds.shape)
          }

          if (t === 'circle') {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
            ds.shape = new F2.Circle({
              left: p.x, top: p.y, radius: 1,
              stroke: colorRef.current, strokeWidth: 2,
              fill: 'transparent', selectable: false,
              originX: 'center', originY: 'center',
            })
            canvas.add(ds.shape)
          }

          if (t === 'triangle') {
            ds.active = true; ds.x0 = p.x; ds.y0 = p.y
            ds.shape = new F2.Triangle({
              left: p.x, top: p.y, width: 0, height: 0,
              stroke: colorRef.current, strokeWidth: 2,
              fill: 'transparent', selectable: false,
            })
            canvas.add(ds.shape)
          }

          if (t === 'text') {
            const itext = new F2.IText('', {
              left: p.x, top: p.y,
              fill: colorRef.current, fontSize: 18,
              fontFamily: 'system-ui, sans-serif',
            })
            canvas.add(itext)
            canvas.setActiveObject(itext)
            itext.enterEditing()
            canvas.renderAll()
            save(); scheduleSnap()
          }

          if (t === 'angle') {
            ds.pts.push(p)
            if (ds.pts.length === 2) {
              ds.ray1 = new F2.Line(
                [ds.pts[0].x, ds.pts[0].y, p.x, p.y],
                { stroke: colorRef.current, strokeWidth: 2, selectable: false }
              )
              canvas.add(ds.ray1)
              canvas.renderAll()
            }
            if (ds.pts.length === 3) {
              const [v, a, b] = ds.pts
              const ray2 = new F2.Line([v.x, v.y, b.x, b.y], {
                stroke: colorRef.current, strokeWidth: 2, selectable: false,
              })
              const ang1 = Math.atan2(a.y - v.y, a.x - v.x)
              const ang2 = Math.atan2(b.y - v.y, b.x - v.x)
              const r = 22
              const ax = v.x + r * Math.cos(ang1), ay = v.y + r * Math.sin(ang1)
              const bx = v.x + r * Math.cos(ang2), by = v.y + r * Math.sin(ang2)
              const arc = new F2.Path(
                `M ${ax} ${ay} A ${r} ${r} 0 0 1 ${bx} ${by}`,
                { stroke: colorRef.current, strokeWidth: 1.5, fill: 'transparent', selectable: false }
              )
              canvas.add(ray2, arc)
              canvas.renderAll()
              ds.pts = []; ds.ray1 = null
              save(); scheduleSnap()
            }
          }
        })

        canvas.on('mouse:move', (opt: any) => {
          const t = toolRef.current
          const ds = draw.current
          if (!ds.active || !ds.shape) return
          const p = canvas.getScenePoint(opt.e)

          if (t === 'line' || t === 'arrow') {
            ds.shape.set({ x2: p.x, y2: p.y })
          }
          if (t === 'rect') {
            ds.shape.set({
              left: Math.min(p.x, ds.x0), top: Math.min(p.y, ds.y0),
              width: Math.abs(p.x - ds.x0), height: Math.abs(p.y - ds.y0),
            })
          }
          if (t === 'circle') {
            const r = Math.max(1, Math.hypot(p.x - ds.x0, p.y - ds.y0) / 2)
            ds.shape.set({
              radius: r,
              left: (ds.x0 + p.x) / 2,
              top: (ds.y0 + p.y) / 2,
            })
          }
          if (t === 'triangle') {
            ds.shape.set({
              left: Math.min(p.x, ds.x0), top: Math.min(p.y, ds.y0),
              width: Math.abs(p.x - ds.x0), height: Math.abs(p.y - ds.y0),
            })
          }
          canvas.renderAll()
        })

        canvas.on('mouse:up', (opt: any) => {
          const t = toolRef.current
          const ds = draw.current
          if (!ds.active) return

          if (t === 'arrow' && ds.shape) {
            const F2 = FRef.current
            const p = canvas.getScenePoint(opt.e)
            const angle = Math.atan2(p.y - ds.y0, p.x - ds.x0)
            const tip = new F2.Triangle({
              left: p.x, top: p.y, width: 12, height: 14,
              fill: colorRef.current, stroke: colorRef.current,
              angle: (angle * 180 / Math.PI) + 90,
              originX: 'center', originY: 'center', selectable: false,
            })
            canvas.add(tip)
          }

          ds.active = false; ds.shape = null
          canvas.renderAll()
          save(); scheduleSnap()
        })

        canvas.on('path:created', (opt: any) => {
          if (toolRef.current === 'highlight' && opt.path) {
            opt.path.set({ opacity: 0.32 })
            canvas.renderAll()
          }
          save(); scheduleSnap()
        })

        canvas.on('object:modified', () => { save(); scheduleSnap() })

        canvas.on('object:moving', (opt: any) => {
          if (!gridSnapRef.current || !opt.target) return
          opt.target.set({
            left: Math.round((opt.target.left ?? 0) / 20) * 20,
            top:  Math.round((opt.target.top  ?? 0) / 20) * 20,
          })
        })

        save()  // save initial empty state
      })

      return () => {
        gone = true
        if (snapTimer.current) clearTimeout(snapTimer.current)
        try { fabricRef.current?.dispose() } catch {}
        fabricRef.current = null
        FRef.current = null
      }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // ── Sync canvas background when theme changes ─────────────────────────────
    useEffect(() => {
      const canvas = fabricRef.current
      if (!canvas) return
      canvas.setBackgroundColor(bg, () => canvas.renderAll())
    }, [bg]) // eslint-disable-line react-hooks/exhaustive-deps

    // ── Sync tool → canvas mode ───────────────────────────────────────────────
    useEffect(() => {
      const canvas = fabricRef.current
      const F = FRef.current
      if (!canvas || !F) return

      canvas.isDrawingMode = false
      canvas.selection = false
      canvas.defaultCursor = 'crosshair'

      if (tool === 'select') {
        canvas.selection = true
        canvas.defaultCursor = 'default'
        canvas.getObjects().forEach((o: any) => { o.selectable = true; o.evented = true })
        canvas.renderAll()
        return
      }
      if (tool === 'pen') {
        const b = new F.PencilBrush(canvas)
        b.color = color; b.width = 2
        canvas.freeDrawingBrush = b
        canvas.isDrawingMode = true
        return
      }
      if (tool === 'highlight') {
        const b = new F.PencilBrush(canvas)
        b.color = color; b.width = 14
        canvas.freeDrawingBrush = b
        canvas.isDrawingMode = true
        return
      }
      if (tool === 'eraser') {
        try {
          const b = new F.EraserBrush(canvas)
          b.width = 22
          canvas.freeDrawingBrush = b
          canvas.isDrawingMode = true
        } catch {
          // Fallback: paint over with background color
          const b = new F.PencilBrush(canvas)
          b.color = bg; b.width = 22
          canvas.freeDrawingBrush = b
          canvas.isDrawingMode = true
        }
      }
      // line / arrow / rect / circle / triangle / angle / text / latex
      // → handled by mouse:down/move/up; isDrawingMode stays false
    }, [tool, color]) // eslint-disable-line react-hooks/exhaustive-deps

    // ── History actions ───────────────────────────────────────────────────────
    const doUndo = () => {
      const canvas = fabricRef.current
      if (!canvas || histIdx.current <= 0) return
      histIdx.current--
      canvas.loadFromJSON(historyRef.current[histIdx.current])
        .then(() => canvas.renderAll())
    }
    const doRedo = () => {
      const canvas = fabricRef.current
      if (!canvas || histIdx.current >= historyRef.current.length - 1) return
      histIdx.current++
      canvas.loadFromJSON(historyRef.current[histIdx.current])
        .then(() => canvas.renderAll())
    }
    const doClear = () => {
      const canvas = fabricRef.current
      if (!canvas) return
      canvas.clear()
      canvas.setBackgroundColor(bg, () => canvas.renderAll())
    }

    useImperativeHandle(ref, () => ({
      clear:    doClear,
      undo:     doUndo,
      redo:     doRedo,
      exportPng: () => fabricRef.current?.toDataURL({ format: 'png', multiplier: 1 }) ?? null,
    }), []) // eslint-disable-line react-hooks/exhaustive-deps

    // ── LaTeX placement ───────────────────────────────────────────────────────
    const handleAddLatex = async () => {
      const canvas = fabricRef.current
      const F = FRef.current
      if (!canvas || !F || !latexVal.trim()) {
        setShowLatex(false); setLatexVal(''); setTool('select'); return
      }
      setPlacing(true)
      try {
        const div = document.createElement('div')
        div.style.cssText = 'position:absolute;top:-9999px;left:-9999px;font-size:20px;line-height:1.5;padding:4px 8px;'
        document.body.appendChild(div)
        katex.render(latexVal, div, { throwOnError: false, displayMode: false })
        await new Promise(r => requestAnimationFrame(r))
        const w = Math.max(div.offsetWidth + 16, 80)
        const h = Math.max(div.offsetHeight + 8, 36)
        const html = div.innerHTML
        document.body.removeChild(div)

        const svgStr = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
          <foreignObject x="0" y="0" width="${w}" height="${h}">
            <div xmlns="http://www.w3.org/1999/xhtml"
                 style="color:${colorRef.current};font-size:20px;line-height:1.5;padding:4px 8px;">
              ${html}
            </div>
          </foreignObject>
        </svg>`
        const dataUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)))

        F.Image.fromURL(dataUrl, (img: any) => {
          img.set({ left: 40, top: 40, selectable: true })
          canvas.add(img)
          canvas.setActiveObject(img)
          canvas.renderAll()
        })
      } catch (e) {
        console.warn('LaTeX render error:', e)
      }
      setPlacing(false); setShowLatex(false); setLatexVal(''); setTool('select')
    }

    // ── Image paste ───────────────────────────────────────────────────────────
    useEffect(() => {
      const onPaste = async (e: ClipboardEvent) => {
        const item = Array.from(e.clipboardData?.items ?? []).find(i => i.type.startsWith('image/'))
        if (!item) return
        const blob = item.getAsFile()
        if (!blob) return
        const url = URL.createObjectURL(blob)
        const canvas = fabricRef.current; const F = FRef.current
        if (!canvas || !F) return
        F.Image.fromURL(url, (img: any) => {
          const maxW = canvas.width * 0.5
          if (img.width > maxW) img.scaleToWidth(maxW)
          img.set({ left: 40, top: 40, selectable: true })
          canvas.add(img); canvas.renderAll()
          URL.revokeObjectURL(url)
        })
      }
      document.addEventListener('paste', onPaste)
      return () => document.removeEventListener('paste', onPaste)
    }, [])

    // ── File upload ───────────────────────────────────────────────────────────
    const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      const url = URL.createObjectURL(file)
      const canvas = fabricRef.current; const F = FRef.current
      if (!canvas || !F) return
      F.Image.fromURL(url, (img: any) => {
        const maxW = canvas.width * 0.5
        if (img.width > maxW) img.scaleToWidth(maxW)
        img.set({ left: 40, top: 40, selectable: true })
        canvas.add(img); canvas.renderAll()
        URL.revokeObjectURL(url)
      })
      e.target.value = ''
    }

    // ── Render helpers ────────────────────────────────────────────────────────
    const isShapeActive = tool === 'rect' || tool === 'circle' || tool === 'triangle'

    const Btn = ({
      id, icon, label, onClick,
    }: { id?: Tool; icon: string; label: string; onClick?: () => void }) => {
      const active = id ? tool === id : false
      return (
        <button
          title={label}
          onClick={onClick ?? (() => { id && setTool(id); setShowShapes(false) })}
          style={{
            width: 28, height: 28, borderRadius: 5, fontSize: 14, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
            border: `1px solid ${active ? caramel : 'transparent'}`,
            background: active ? caramelDim : 'transparent',
            color: active ? caramel : text,
          }}
        >
          {icon}
        </button>
      )
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* ── Toolbar row ────────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap',
          padding: '4px 8px', background: surface,
          border: `1px solid ${border}`, borderBottom: 'none',
          borderRadius: '8px 8px 0 0',
        }}>
          <Btn id="select"    icon="↖" label="Select / Move" />
          <Btn id="pen"       icon="✏" label="Pen (2px)" />
          <Btn id="highlight" icon="☆" label="Highlighter (opacity 0.3, 14px)" />
          <Btn id="text"      icon="T" label="Text (click to place)" />
          <Btn id="line"      icon="╱" label="Line" />
          <Btn id="arrow"     icon="→" label="Arrow" />
          <Btn id="angle"     icon="∠" label="Angle marker (3-click)" />
          <Btn id="latex"     icon="ƒ" label="Insert LaTeX formula"
               onClick={() => { setTool('latex'); setShowShapes(false); setShowLatex(true) }} />
          <Btn id="eraser"    icon="⌫" label="Eraser" />

          {/* Shapes pop-out */}
          <div style={{ position: 'relative' }}>
            <button
              title="Shapes"
              onClick={() => setShowShapes(s => !s)}
              style={{
                width: 28, height: 28, borderRadius: 5, fontSize: 14, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
                border: `1px solid ${isShapeActive ? caramel : 'transparent'}`,
                background: isShapeActive ? caramelDim : 'transparent',
                color: isShapeActive ? caramel : text,
              }}
            >
              ▭
            </button>
            {showShapes && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, zIndex: 30,
                background: surface, border: `1px solid ${border}`,
                borderRadius: 6, padding: 4, display: 'flex', flexDirection: 'column', gap: 2,
                boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
              }}>
                {([
                  { id: 'rect' as Tool,     icon: '▭', label: 'Rectangle' },
                  { id: 'circle' as Tool,   icon: '○', label: 'Circle' },
                  { id: 'triangle' as Tool, icon: '△', label: 'Triangle' },
                ] as const).map(s => (
                  <button key={s.id} title={s.label}
                    onClick={() => { setTool(s.id); setShowShapes(false) }}
                    style={{
                      width: 28, height: 28, borderRadius: 5, fontSize: 14,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      cursor: 'pointer',
                      border: `1px solid ${tool === s.id ? caramel : 'transparent'}`,
                      background: tool === s.id ? caramelDim : 'transparent',
                      color: tool === s.id ? caramel : text,
                    }}>
                    {s.icon}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div style={{ width: 1, height: 20, background: border, margin: '0 2px', flexShrink: 0 }} />

          {/* Color swatches */}
          {SWATCHES.map(sw => (
            <button key={sw} title={sw}
              onClick={() => setColor(sw)}
              style={{
                width: 18, height: 18, borderRadius: '50%',
                background: sw, flexShrink: 0, cursor: 'pointer',
                border: `2px solid ${color === sw ? text : 'transparent'}`,
                outline: color === sw ? `1px solid ${border}` : 'none',
                outlineOffset: '1px',
              }}
            />
          ))}

          {/* Divider */}
          <div style={{ width: 1, height: 20, background: border, margin: '0 2px', flexShrink: 0 }} />

          {/* Grid snap */}
          <button
            title={`Grid snap ${gridSnap ? 'on' : 'off'} (20px)`}
            onClick={() => setGridSnap(s => !s)}
            style={{
              width: 28, height: 28, borderRadius: 5, fontSize: 12, flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
              border: `1px solid ${gridSnap ? caramel : 'transparent'}`,
              background: gridSnap ? caramelDim : 'transparent',
              color: gridSnap ? caramel : text,
            }}>
            ⊞
          </button>

          {/* Image upload */}
          <button title="Upload image"
            onClick={() => fileInputRef.current?.click()}
            style={{
              width: 28, height: 28, borderRadius: 5, fontSize: 14, flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', border: '1px solid transparent',
              background: 'transparent', color: textMuted,
            }}>
            ⬆
          </button>
          <input ref={fileInputRef} type="file" accept="image/*"
            style={{ display: 'none' }} onChange={handleFile} />

          <div style={{ flex: 1 }} />

          {/* Undo / Redo / Clear */}
          <button title="Undo" onClick={doUndo}
            style={{ width: 28, height: 28, borderRadius: 5, fontSize: 14, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: '1px solid transparent', background: 'transparent', color: text }}>
            ↩
          </button>
          <button title="Redo" onClick={doRedo}
            style={{ width: 28, height: 28, borderRadius: 5, fontSize: 14, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: '1px solid transparent', background: 'transparent', color: text }}>
            ↪
          </button>
          <button title="Clear canvas" onClick={doClear}
            style={{ width: 28, height: 28, borderRadius: 5, fontSize: 13, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: '1px solid transparent', background: 'transparent', color: '#f87171' }}>
            ✕
          </button>
        </div>

        {/* ── Canvas ────────────────────────────────────────────────────────── */}
        <canvas ref={canvasElRef}
          style={{ display: 'block', border: `1px solid ${border}`, borderRadius: '0 0 8px 8px' }}
        />

        {/* ── LaTeX overlay ─────────────────────────────────────────────────── */}
        {showLatex && (
          <div style={{
            position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 40, borderRadius: 8,
          }}>
            <div style={{
              background: surface, border: `1px solid ${border}`,
              borderRadius: 10, padding: 20, width: 340,
              display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: text }}>Insert formula</div>
              <MathInput value={latexVal} onChange={setLatexVal} placeholder="Type LaTeX…" />
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={handleAddLatex} disabled={placing}
                  style={{
                    flex: 1, padding: '8px', borderRadius: 7, fontSize: 13,
                    background: caramel, color: '#fff', border: 'none',
                    cursor: placing ? 'wait' : 'pointer', fontWeight: 600,
                  }}>
                  {placing ? 'Placing…' : 'Place on canvas'}
                </button>
                <button
                  onClick={() => { setShowLatex(false); setLatexVal(''); setTool('select') }}
                  style={{
                    flex: 1, padding: '8px', borderRadius: 7, fontSize: 13,
                    background: 'transparent', color: textMuted,
                    border: `1px solid ${border}`, cursor: 'pointer',
                  }}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
)
