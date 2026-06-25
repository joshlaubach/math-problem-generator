'use client'

/**
 * Mafs-based plot/geometry renderer for the whiteboard tutor zone.
 * Loaded dynamically (no SSR) from Whiteboard.tsx.
 *
 * Two render modes:
 *   fn + domain  → function plot (Plot.OfX)
 *   scene        → geometry scene (points, segments, polygons, circles, angles, vectors)
 */

import React from 'react'
import { Mafs, Coordinates, Plot, Point, Polygon, Circle, Vector, Line, Text } from 'mafs'
import 'mafs/core.css'

// ── Geometry element types (exported so Whiteboard.tsx can type WS messages) ──

export type GeometryElement =
  | { kind: 'point';   x: number; y: number; label?: string }
  | { kind: 'segment'; x1: number; y1: number; x2: number; y2: number; label?: string }
  | { kind: 'polygon'; points: [number, number][]; label?: string }
  | { kind: 'circle';  cx: number; cy: number; r: number; label?: string }
  | { kind: 'angle';   vertex: [number, number]; ray1: [number, number]; ray2: [number, number]; label?: string }
  | { kind: 'vector';  x: number; y: number; dx: number; dy: number; label?: string }

interface WhiteboardPlotProps {
  fn?: string
  domain?: [number, number]
  scene?: GeometryElement[]
  theme?: 'light' | 'dark'
}

// ── Shared light-mode override styles ─────────────────────────────────────────

const LIGHT_STYLE = `.wb-mafs-light .MafsView{--mafs-bg:#fefcf9!important;--mafs-fg:#1a1a1a!important;--mafs-line-color:#ccc!important;--grid-line-subdivision-color:#e8e8e8!important}`

// ── Safe expression evaluator (no eval / new Function) ───────────────────────
//
// Recursive-descent parser: supports +, -, *, /, ^ (right-assoc), unary -,
// parentheses, the variable x, Math constants PI/E, and common Math functions.
// Handles Math.sin(...) notation by stripping the "Math." prefix first.

type _Token =
  | { t: 'num'; v: number }
  | { t: 'id';  v: string }
  | { t: 'op';  v: string }
  | { t: 'lp'  }
  | { t: 'rp'  }

const _FUNS: Record<string, (n: number) => number> = {
  abs: Math.abs, sqrt: Math.sqrt,
  sin: Math.sin, cos: Math.cos, tan: Math.tan,
  asin: Math.asin, acos: Math.acos, atan: Math.atan,
  log: Math.log, log2: Math.log2, log10: Math.log10,
  exp: Math.exp, ceil: Math.ceil, floor: Math.floor,
  round: Math.round, sign: Math.sign,
}

const _CONST: Record<string, number> = {
  PI: Math.PI, pi: Math.PI, E: Math.E, e: Math.E,
}

function _tokenize(s: string): _Token[] {
  const out: _Token[] = []
  let i = 0
  while (i < s.length) {
    const ch = s[i]
    if (ch === ' ' || ch === '\t') { i++; continue }
    if (/[\d.]/.test(ch)) {
      let num = ''
      while (i < s.length && /[\d.eE]/.test(s[i])) {
        if ((s[i] === 'e' || s[i] === 'E') && /[+-]/.test(s[i + 1] ?? '')) {
          num += s[i++] + s[i++]
        } else {
          num += s[i++]
        }
      }
      out.push({ t: 'num', v: parseFloat(num) })
    } else if (/[a-zA-Z_]/.test(ch)) {
      let id = ''
      while (i < s.length && /\w/.test(s[i])) id += s[i++]
      out.push({ t: 'id', v: id })
    } else if ('+-*/^'.includes(ch)) {
      out.push({ t: 'op', v: ch }); i++
    } else if (ch === '(') {
      out.push({ t: 'lp' }); i++
    } else if (ch === ')') {
      out.push({ t: 'rp' }); i++
    } else {
      i++
    }
  }
  return out
}

type _Eval = (x: number) => number

function _compile(expr: string): _Eval | null {
  const src = expr.replace(/Math\./g, '').replace(/\*\*/g, '^')
  let toks: _Token[]
  try { toks = _tokenize(src) } catch { return null }
  let pos = 0

  const peek = (): _Token | undefined => toks[pos]
  const next = (): _Token => toks[pos++]
  const eat  = (op: string): boolean => {
    const t = peek()
    if (t?.t === 'op' && t.v === op) { pos++; return true }
    return false
  }

  function add(): _Eval {
    let lhs = mul()
    for (;;) {
      const t = peek()
      if (t?.t !== 'op' || (t.v !== '+' && t.v !== '-')) break
      pos++
      const op = t.v; const rhs = mul()
      const l = lhs, r = rhs
      lhs = op === '+' ? (x) => l(x) + r(x) : (x) => l(x) - r(x)
    }
    return lhs
  }

  function mul(): _Eval {
    let lhs = pow()
    for (;;) {
      const t = peek()
      if (t?.t !== 'op' || (t.v !== '*' && t.v !== '/')) break
      pos++
      const op = t.v; const rhs = pow()
      const l = lhs, r = rhs
      lhs = op === '*' ? (x) => l(x) * r(x) : (x) => l(x) / r(x)
    }
    return lhs
  }

  function pow(): _Eval {
    const b = unary()
    if (eat('^')) { const e = pow(); return (x) => Math.pow(b(x), e(x)) }
    return b
  }

  function unary(): _Eval {
    if (eat('-')) { const inner = atom(); return (x) => -inner(x) }
    if (eat('+')) return atom()
    return atom()
  }

  function atom(): _Eval {
    const t = peek()
    if (!t) throw new Error('unexpected end')

    if (t.t === 'num') { next(); const v = t.v; return () => v }

    if (t.t === 'id') {
      next()
      const name = t.v
      if (_CONST[name] !== undefined) { const v = _CONST[name]; return () => v }
      if (name === 'x') return (x) => x
      if (_FUNS[name]) {
        const fn = _FUNS[name]
        if (peek()?.t === 'lp') {
          pos++
          const arg = add()
          if (peek()?.t === 'rp') pos++
          return (x) => fn(arg(x))
        }
      }
      return () => NaN
    }

    if (t.t === 'lp') {
      pos++
      const inner = add()
      if (peek()?.t === 'rp') pos++
      return inner
    }

    throw new Error(`unexpected token ${t.t}`)
  }

  try {
    const compiled = add()
    return (x: number) => {
      try { const v = compiled(x); return isFinite(v) ? v : NaN } catch { return NaN }
    }
  } catch {
    return null
  }
}

function parseExpr(expr: string): ((x: number) => number) | null {
  return _compile(expr)
}

// ── Auto-fit bounds for geometry scenes ──────────────────────────────────────

function computeBounds(elements: GeometryElement[]): {
  xRange: [number, number]
  yRange: [number, number]
} {
  const xs: number[] = [0]
  const ys: number[] = [0]

  for (const el of elements) {
    if (el.kind === 'point')   { xs.push(el.x); ys.push(el.y) }
    if (el.kind === 'segment') { xs.push(el.x1, el.x2); ys.push(el.y1, el.y2) }
    if (el.kind === 'polygon') { el.points.forEach(([x, y]) => { xs.push(x); ys.push(y) }) }
    if (el.kind === 'circle')  { xs.push(el.cx - el.r, el.cx + el.r); ys.push(el.cy - el.r, el.cy + el.r) }
    if (el.kind === 'angle')   { [el.vertex, el.ray1, el.ray2].forEach(([x, y]) => { xs.push(x); ys.push(y) }) }
    if (el.kind === 'vector')  { xs.push(el.x, el.x + el.dx); ys.push(el.y, el.y + el.dy) }
  }

  const PAD = 1.5
  return {
    xRange: [Math.min(...xs) - PAD, Math.max(...xs) + PAD],
    yRange: [Math.min(...ys) - PAD, Math.max(...ys) + PAD],
  }
}

// ── Geometry scene renderer ───────────────────────────────────────────────────

function GeometryScene({ elements, theme }: { elements: GeometryElement[]; theme: 'light' | 'dark' }) {
  const { xRange, yRange } = computeBounds(elements)
  const ink = theme === 'dark' ? '#c4976a' : '#2d6a4f'

  return (
    <>
      {theme === 'light' && <style>{LIGHT_STYLE}</style>}
      <div
        className={theme === 'light' ? 'wb-mafs-light' : undefined}
        style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}
      >
        <Mafs height={200} viewBox={{ x: xRange, y: yRange }} preserveAspectRatio={false}>
          <Coordinates.Cartesian />
          {elements.map((el, i) => {
            if (el.kind === 'point') return (
              <React.Fragment key={i}>
                <Point x={el.x} y={el.y} color={ink} />
                {el.label && (
                  <Text x={el.x + 0.15} y={el.y + 0.35} attach="n" color={ink} size={14}>
                    {el.label}
                  </Text>
                )}
              </React.Fragment>
            )

            if (el.kind === 'segment') {
              const mx = (el.x1 + el.x2) / 2
              const my = (el.y1 + el.y2) / 2
              return (
                <React.Fragment key={i}>
                  <Line.Segment point1={[el.x1, el.y1]} point2={[el.x2, el.y2]} color={ink} />
                  {el.label && (
                    <Text x={mx} y={my + 0.3} attach="n" color={ink} size={14}>
                      {el.label}
                    </Text>
                  )}
                </React.Fragment>
              )
            }

            if (el.kind === 'polygon') {
              const cx = el.points.reduce((s, [x]) => s + x, 0) / el.points.length
              const cy = el.points.reduce((s, [, y]) => s + y, 0) / el.points.length
              return (
                <React.Fragment key={i}>
                  <Polygon points={el.points} color={ink} />
                  {el.label && (
                    <Text x={cx} y={cy} color={ink} size={14}>{el.label}</Text>
                  )}
                </React.Fragment>
              )
            }

            if (el.kind === 'circle') return (
              <React.Fragment key={i}>
                <Circle center={[el.cx, el.cy]} radius={el.r} color={ink} />
                {el.label && (
                  <Text x={el.cx} y={el.cy + el.r + 0.35} attach="n" color={ink} size={14}>
                    {el.label}
                  </Text>
                )}
              </React.Fragment>
            )

            if (el.kind === 'angle') return (
              <React.Fragment key={i}>
                <Line.Segment point1={el.vertex} point2={el.ray1} color={ink} />
                <Line.Segment point1={el.vertex} point2={el.ray2} color={ink} />
                {el.label && (
                  <Text x={el.vertex[0]} y={el.vertex[1] - 0.4} attach="s" color={ink} size={14}>
                    {el.label}
                  </Text>
                )}
              </React.Fragment>
            )

            if (el.kind === 'vector') {
              const mx = el.x + el.dx / 2
              const my = el.y + el.dy / 2
              return (
                <React.Fragment key={i}>
                  <Vector tail={[el.x, el.y]} tip={[el.x + el.dx, el.y + el.dy]} color={ink} />
                  {el.label && (
                    <Text x={mx} y={my + 0.3} attach="n" color={ink} size={14}>
                      {el.label}
                    </Text>
                  )}
                </React.Fragment>
              )
            }

            return null
          })}
        </Mafs>
      </div>
    </>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function WhiteboardPlot({
  fn,
  domain = [-5, 5],
  scene,
  theme = 'light',
}: WhiteboardPlotProps) {
  // Geometry mode
  if (scene && scene.length > 0) {
    return <GeometryScene elements={scene} theme={theme} />
  }

  // Function-plot mode
  if (!fn) return null

  const parsedFn = parseExpr(fn)
  if (!parsedFn) {
    return (
      <div style={{ padding: 8, fontSize: 12, color: 'var(--terracotta)' }}>
        Could not plot: {fn}
      </div>
    )
  }

  return (
    <>
      {theme === 'light' && <style>{LIGHT_STYLE}</style>}
      <div
        className={theme === 'light' ? 'wb-mafs-light' : undefined}
        style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}
      >
        <Mafs height={160} viewBox={{ x: domain, y: [-6, 6] }} preserveAspectRatio={false}>
          <Coordinates.Cartesian />
          <Plot.OfX y={parsedFn} color={theme === 'dark' ? '#c4976a' : '#2d6a4f'} />
        </Mafs>
      </div>
    </>
  )
}
