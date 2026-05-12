'use client'

import { useState, useRef, useEffect, useCallback, useId } from 'react'
import Link from 'next/link'

// ─── Types ────────────────────────────────────────────────────────────────────

type CalcLevel = 'basic' | 'scientific' | 'graphing' | 'cas'

type CASOperation =
  | 'evaluate' | 'simplify' | 'expand' | 'factor' | 'solve'
  | 'diff' | 'integrate' | 'integrate_definite' | 'limit'
  | 'det' | 'eigenvals' | 'laplace' | 'ilaplace' | 'series'

interface HistoryEntry {
  id: string
  expression: string
  result: string
  latex?: string
  status: 'pending' | 'done' | 'error'
  level: CalcLevel
  operation?: string
}

export interface CalculatorWidgetProps {
  calcMode: 'none' | 'scientific' | 'graphing' | 'cas'
  difficulty: number
  userTier: string
  getToken: () => Promise<string | null>
  onSendToAnswer: (latex: string) => void
  topicId?: string
  problemId?: string
  sessionId?: string
  apiBase?: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getAvailableLevels(
  calcMode: string,
): CalcLevel[] {
  if (calcMode === 'none') return []
  const levels: CalcLevel[] = ['basic', 'scientific']
  if (calcMode === 'graphing' || calcMode === 'cas') levels.push('graphing')
  // Always show CAS tab on cas topics — the panel itself gates by tier + difficulty
  if (calcMode === 'cas') levels.push('cas')
  return levels
}

function uid() {
  return Math.random().toString(36).slice(2)
}

// Safe expression parser for graphing
function parseGraphFn(expr: string): ((x: number) => number) | null {
  if (!expr.trim()) return null
  const js = expr
    .replace(/\^/g, '**')
    .replace(/π/g, 'Math.PI')
    .replace(/\be\b/g, 'Math.E')
    .replace(/\bsin\b/g, 'Math.sin')
    .replace(/\bcos\b/g, 'Math.cos')
    .replace(/\btan\b/g, 'Math.tan')
    .replace(/\basin\b/g, 'Math.asin')
    .replace(/\bacos\b/g, 'Math.acos')
    .replace(/\batan\b/g, 'Math.atan')
    .replace(/\bsqrt\b/g, 'Math.sqrt')
    .replace(/\babs\b/g, 'Math.abs')
    .replace(/\blog\b/g, 'Math.log10')
    .replace(/\bln\b/g, 'Math.log')
    .replace(/\bexp\b/g, 'Math.exp')
  try {
    // eslint-disable-next-line no-new-func
    const f = new Function('x', `'use strict'; return (${js})`) as (x: number) => number
    const test = f(1)
    if (!isFinite(test) && !isNaN(test)) return null
    return f
  } catch {
    return null
  }
}

// Bisection root-finder
function findZero(f: (x: number) => number, a: number, b: number): number | null {
  if (f(a) * f(b) > 0) return null
  for (let i = 0; i < 60; i++) {
    const m = (a + b) / 2
    if (Math.abs(f(m)) < 1e-10 || (b - a) / 2 < 1e-10) return m
    if (f(a) * f(m) < 0) b = m; else a = m
  }
  return (a + b) / 2
}

// Golden-section search for min
function findMin(f: (x: number) => number, a: number, b: number): { x: number; y: number } {
  const phi = (Math.sqrt(5) - 1) / 2
  let c = b - phi * (b - a)
  let d = a + phi * (b - a)
  for (let i = 0; i < 60; i++) {
    if (Math.abs(b - a) < 1e-10) break
    if (f(c) < f(d)) { b = d } else { a = c }
    c = b - phi * (b - a)
    d = a + phi * (b - a)
  }
  const x = (a + b) / 2
  return { x, y: f(x) }
}

const CAS_OPS: { value: CASOperation; label: string }[] = [
  { value: 'evaluate',            label: 'Evaluate / Simplify' },
  { value: 'expand',              label: 'Expand' },
  { value: 'factor',              label: 'Factor' },
  { value: 'solve',               label: 'Solve for x' },
  { value: 'diff',                label: 'Differentiate' },
  { value: 'integrate',           label: 'Integrate (indefinite)' },
  { value: 'integrate_definite',  label: 'Integrate (definite)' },
  { value: 'limit',               label: 'Limit' },
  { value: 'series',              label: 'Series Expansion' },
  { value: 'det',                 label: 'Determinant' },
  { value: 'eigenvals',           label: 'Eigenvalues' },
  { value: 'laplace',             label: 'Laplace Transform' },
  { value: 'ilaplace',            label: 'Inverse Laplace' },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

// Inline MathLive field configured for calculator use
function CalcMathField({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const fieldRef = useRef<(HTMLElement & { value: string }) | null>(null)
  const onChangeRef = useRef(onChange)

  useEffect(() => { onChangeRef.current = onChange })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let destroyed = false
    import('mathlive').then(() => {
      if (destroyed) return
      const el = document.createElement('math-field') as HTMLElement & { value: string }
      el.setAttribute('style', [
        'width:100%',
        'font-size:1.05em',
        'padding:8px 10px',
        'border:1px solid var(--border2)',
        'border-radius:8px',
        'background:var(--surface)',
        'color:var(--text)',
      ].join(';'))
      el.setAttribute('virtual-keyboard-mode', 'onfocus')
      if (placeholder) el.setAttribute('placeholder', `\\text{${placeholder}}`)
      el.addEventListener('input', () => onChangeRef.current?.(el.value))
      container.appendChild(el)
      fieldRef.current = el
    })
    return () => {
      destroyed = true
      const el = fieldRef.current
      if (el && container.contains(el)) container.removeChild(el)
      fieldRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const el = fieldRef.current
    if (el && el.value !== value) el.value = value
  }, [value])

  return <div ref={containerRef} style={{ flex: 1 }} />
}

// Rendered LaTeX via KaTeX
function LatexDisplay({ latex }: { latex: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!ref.current) return
    import('katex').then(katex => {
      if (!ref.current) return
      try {
        katex.default.render(latex, ref.current, { throwOnError: false, displayMode: false })
      } catch {
        if (ref.current) ref.current.textContent = latex
      }
    })
  }, [latex])
  return <span ref={ref} />
}

// History log entry
function HistoryRow({ entry, onSend }: { entry: HistoryEntry; onSend: (e: HistoryEntry) => void }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 4,
      padding: '8px 10px',
      borderRadius: 8,
      background: 'var(--surface2)',
      border: '1px solid var(--border)',
      fontSize: 13,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {entry.operation ?? entry.level}
        </span>
        {entry.status === 'done' && (
          <button
            type="button"
            onClick={() => onSend(entry)}
            style={{
              fontSize: 11, fontWeight: 600,
              color: 'var(--caramel)', background: 'none', border: 'none',
              cursor: 'pointer', padding: '0 4px',
            }}
          >
            → Send
          </button>
        )}
      </div>

      <div style={{ color: 'var(--text-dim)', fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>
        {entry.expression}
      </div>

      {entry.status === 'pending' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 12 }}>
          <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
          Computing…
        </div>
      )}

      {entry.status === 'done' && entry.latex && (
        <div style={{ color: 'var(--text)', fontWeight: 500 }}>
          = <LatexDisplay latex={entry.latex} />
        </div>
      )}

      {entry.status === 'done' && !entry.latex && (
        <div style={{ color: 'var(--text)', fontWeight: 500 }}>= {entry.result}</div>
      )}

      {entry.status === 'error' && (
        <div style={{ color: 'var(--terracotta)', fontSize: 12 }}>{entry.result}</div>
      )}
    </div>
  )
}

// Numeric button grid
function CalcButton({
  label, onClick, wide, accent,
}: {
  label: string; onClick: () => void; wide?: boolean; accent?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        gridColumn: wide ? 'span 2' : undefined,
        padding: '9px 4px',
        borderRadius: 7,
        border: '1px solid var(--border)',
        background: accent ? 'var(--caramel-dim)' : 'var(--surface2)',
        color: accent ? 'var(--caramel)' : 'var(--text)',
        fontSize: 13,
        fontWeight: accent ? 700 : 500,
        cursor: 'pointer',
        transition: 'background 0.15s',
        lineHeight: 1,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = accent ? 'var(--caramel-glow)' : 'var(--surface3)')}
      onMouseLeave={e => (e.currentTarget.style.background = accent ? 'var(--caramel-dim)' : 'var(--surface2)')}
    >
      {label}
    </button>
  )
}

// ─── Basic / Scientific Panel ─────────────────────────────────────────────────

function ArithmeticPanel({
  level,
  onAppend,
  onEvaluate,
  onClear,
  onBackspace,
}: {
  level: 'basic' | 'scientific'
  onAppend: (s: string) => void
  onEvaluate: () => void
  onClear: () => void
  onBackspace: () => void
}) {
  const sciRows: Array<{ label: string; insert: string }[]> = [
    [
      { label: 'sin', insert: '\\sin(' },
      { label: 'cos', insert: '\\cos(' },
      { label: 'tan', insert: '\\tan(' },
      { label: 'sin⁻¹', insert: '\\arcsin(' },
    ],
    [
      { label: 'cos⁻¹', insert: '\\arccos(' },
      { label: 'tan⁻¹', insert: '\\arctan(' },
      { label: 'log', insert: '\\log(' },
      { label: 'ln', insert: '\\ln(' },
    ],
    [
      { label: '√', insert: '\\sqrt{' },
      { label: 'x²', insert: '^{2}' },
      { label: 'xⁿ', insert: '^{' },
      { label: '|x|', insert: '\\left|' },
    ],
    [
      { label: 'π', insert: '\\pi' },
      { label: 'e', insert: 'e' },
      { label: 'n!', insert: '!' },
      { label: '%', insert: '\\%' },
    ],
  ]

  const numPad = [
    ['7', '8', '9', '÷'],
    ['4', '5', '6', '×'],
    ['1', '2', '3', '−'],
    ['0', '.', '()', '+'],
  ]

  const insertMap: Record<string, string> = {
    '÷': '\\div', '×': '\\cdot', '−': '-', '()': '\\left(\\right)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {level === 'scientific' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 5 }}>
          {sciRows.flat().map(b => (
            <CalcButton key={b.label} label={b.label} onClick={() => onAppend(b.insert)} accent />
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 5 }}>
        <CalcButton label="C" onClick={onClear} accent />
        <CalcButton label="⌫" onClick={onBackspace} />
        <CalcButton label="(" onClick={() => onAppend('(')} />
        <CalcButton label=")" onClick={() => onAppend(')')} />

        {numPad.flat().map(k => (
          <CalcButton key={k} label={k} onClick={() => onAppend(insertMap[k] ?? k)} />
        ))}

        <CalcButton label="=" onClick={onEvaluate} wide accent />
      </div>
    </div>
  )
}

// ─── Graphing Panel ───────────────────────────────────────────────────────────

function GraphingPanel({ onSend }: { onSend: (val: string, label: string) => void }) {
  const [expr1, setExpr1] = useState('x^2 - 2')
  const [expr2, setExpr2] = useState('')
  const [xMin, setXMin] = useState(-5)
  const [xMax, setXMax] = useState(5)
  const [calcOpen, setCalcOpen] = useState(false)
  const [calcResult, setCalcResult] = useState<{ label: string; value: string } | null>(null)

  const fn1 = parseGraphFn(expr1)
  const fn2 = expr2.trim() ? parseGraphFn(expr2) : null

  function runCalc(type: 'zero' | 'min' | 'max' | 'intersect') {
    setCalcOpen(false)
    setCalcResult(null)
    if (!fn1) return

    if (type === 'zero') {
      const step = (xMax - xMin) / 200
      for (let x = xMin; x < xMax; x += step) {
        const r = findZero(fn1, x, x + step)
        if (r !== null) {
          setCalcResult({ label: 'Zero', value: r.toFixed(6) })
          return
        }
      }
      setCalcResult({ label: 'Zero', value: 'No zero found in range' })
    } else if (type === 'min') {
      const { x, y } = findMin(fn1, xMin, xMax)
      setCalcResult({ label: 'Minimum', value: `x = ${x.toFixed(6)}, y = ${y.toFixed(6)}` })
    } else if (type === 'max') {
      const { x, y } = findMin(x => -fn1(x), xMin, xMax)
      setCalcResult({ label: 'Maximum', value: `x = ${x.toFixed(6)}, y = ${fn1(x).toFixed(6)}` })
    } else if (type === 'intersect') {
      if (!fn2) return
      const diff = (x: number) => fn1(x) - fn2(x)
      const step = (xMax - xMin) / 200
      for (let x = xMin; x < xMax; x += step) {
        const r = findZero(diff, x, x + step)
        if (r !== null) {
          setCalcResult({ label: 'Intersection', value: `x = ${r.toFixed(6)}, y = ${fn1(r).toFixed(6)}` })
          return
        }
      }
      setCalcResult({ label: 'Intersection', value: 'No intersection found in range' })
    }
  }

  // Mafs is loaded dynamically to avoid SSR issues
  const [MafsComponents, setMafsComponents] = useState<{
    Mafs: React.ComponentType<Record<string, unknown>>
    Coordinates: { Cartesian: React.ComponentType<Record<string, unknown>> }
    Plot: { OfX: React.ComponentType<{ y: (x: number) => number; color?: string }> }
  } | null>(null)

  useEffect(() => {
    import('mafs').then(m => {
      setMafsComponents({
        Mafs: m.Mafs as React.ComponentType<Record<string, unknown>>,
        Coordinates: m.Coordinates as { Cartesian: React.ComponentType<Record<string, unknown>> },
        Plot: m.Plot as { OfX: React.ComponentType<{ y: (x: number) => number; color?: string }> },
      })
    })
    import('mafs/core.css').catch(() => {})
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Function inputs */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--caramel)', fontWeight: 700, minWidth: 24 }}>y₁=</span>
          <input
            value={expr1}
            onChange={e => setExpr1(e.target.value)}
            placeholder="x^2 - 2"
            style={{
              flex: 1, padding: '6px 10px', borderRadius: 7,
              border: '1px solid var(--border2)', background: 'var(--surface)',
              color: 'var(--text)', fontSize: 13, outline: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--forest)', fontWeight: 700, minWidth: 24 }}>y₂=</span>
          <input
            value={expr2}
            onChange={e => setExpr2(e.target.value)}
            placeholder="optional second function"
            style={{
              flex: 1, padding: '6px 10px', borderRadius: 7,
              border: '1px solid var(--border2)', background: 'var(--surface)',
              color: 'var(--text)', fontSize: 13, outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Window range */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, color: 'var(--text-dim)' }}>
        <span>x:</span>
        <input
          type="number" value={xMin} onChange={e => setXMin(Number(e.target.value))}
          style={{ width: 52, padding: '4px 6px', borderRadius: 5, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text)', fontSize: 12, textAlign: 'center' }}
        />
        <span>to</span>
        <input
          type="number" value={xMax} onChange={e => setXMax(Number(e.target.value))}
          style={{ width: 52, padding: '4px 6px', borderRadius: 5, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text)', fontSize: 12, textAlign: 'center' }}
        />
      </div>

      {/* Graph */}
      <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)' }}>
        {MafsComponents ? (
          <MafsComponents.Mafs
            viewBox={{ x: [xMin, xMax], y: [-5, 5] }}
            preserveAspectRatio={false}
            height={200}
          >
            <MafsComponents.Coordinates.Cartesian />
            {fn1 && <MafsComponents.Plot.OfX y={fn1} color="var(--caramel)" />}
            {fn2 && <MafsComponents.Plot.OfX y={fn2} color="var(--forest)" />}
          </MafsComponents.Mafs>
        ) : (
          <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Loading graph…
          </div>
        )}
      </div>

      {/* CALC menu */}
      <div style={{ position: 'relative' }}>
        <button
          type="button"
          onClick={() => setCalcOpen(o => !o)}
          style={{
            width: '100%', padding: '8px 14px',
            borderRadius: 8, border: '1px solid var(--border2)',
            background: 'var(--surface2)', color: 'var(--text)',
            fontSize: 13, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}
        >
          <span>CALC</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{calcOpen ? '▲' : '▼'}</span>
        </button>

        {calcOpen && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20,
            background: 'var(--surface)', border: '1px solid var(--border2)',
            borderRadius: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            overflow: 'hidden', marginTop: 4,
          }}>
            {(['zero', 'min', 'max', 'intersect'] as const).map((t, i) => (
              <button
                key={t}
                type="button"
                onClick={() => runCalc(t)}
                disabled={t === 'intersect' && !fn2}
                style={{
                  width: '100%', padding: '10px 14px',
                  borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
                  background: 'none', border: 'none',
                  color: t === 'intersect' && !fn2 ? 'var(--text-muted)' : 'var(--text)',
                  fontSize: 13, cursor: t === 'intersect' && !fn2 ? 'not-allowed' : 'pointer',
                  textAlign: 'left',
                }}
              >
                {i + 1}: {t.charAt(0).toUpperCase() + t.slice(1)}{t === 'intersect' && !fn2 ? ' (needs y₂)' : ''}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* CALC result */}
      {calcResult && (
        <div style={{
          padding: '10px 14px',
          borderRadius: 8,
          background: 'var(--caramel-dim)',
          border: '1px solid rgba(196,151,106,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
        }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--caramel)', fontWeight: 600, marginBottom: 2 }}>
              {calcResult.label}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>
              {calcResult.value}
            </div>
          </div>
          <button
            type="button"
            onClick={() => onSend(calcResult.value, calcResult.label)}
            style={{
              padding: '6px 12px', borderRadius: 6,
              background: 'var(--caramel)', color: '#fff',
              border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            → Send
          </button>
        </div>
      )}
    </div>
  )
}

// ─── CAS Panel ────────────────────────────────────────────────────────────────

function CASPanel({
  userTier,
  difficulty,
  getToken,
  topicId,
  problemId,
  sessionId,
  apiBase,
  onHistory,
}: {
  userTier: string
  difficulty: number
  getToken: () => Promise<string | null>
  topicId: string
  problemId: string
  sessionId: string
  apiBase: string
  onHistory: (entry: HistoryEntry) => void
}) {
  const isPremium = userTier !== 'free'
  const isDiffOk = difficulty >= 5
  const [operation, setOperation] = useState<CASOperation>('evaluate')
  const [inputLatex, setInputLatex] = useState('')
  const [variable, setVariable] = useState('x')
  const [lower, setLower] = useState('')
  const [upper, setUpper] = useState('')
  const [at, setAt] = useState('0')

  // Premium gate
  if (!isPremium) {
    return (
      <div style={{
        padding: '24px 20px', textAlign: 'center',
        border: '1px solid var(--border)', borderRadius: 10,
        background: 'var(--surface2)',
      }}>
        <div style={{ fontSize: 24, marginBottom: 10 }}>🔒</div>
        <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 6, fontSize: 14 }}>
          CAS requires a paid plan
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 16 }}>
          Symbolic computation — differentiate, integrate, factor, solve — is available on Student plan and above.
        </p>
        <Link href="/pricing" style={{
          display: 'inline-flex', padding: '8px 18px', borderRadius: 8,
          background: 'var(--caramel)', color: '#fff',
          fontSize: 13, fontWeight: 700, textDecoration: 'none',
        }}>
          View plans →
        </Link>
      </div>
    )
  }

  // Difficulty gate
  if (!isDiffOk) {
    return (
      <div style={{
        padding: '20px', textAlign: 'center',
        border: '1px solid var(--border)', borderRadius: 10,
        background: 'var(--surface2)',
      }}>
        <div style={{ fontSize: 20, marginBottom: 8 }}>📐</div>
        <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 6, fontSize: 14 }}>
          CAS available on difficulty 5–6
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
          This problem is difficulty {difficulty}. Increase the difficulty to unlock symbolic computation.
        </p>
      </div>
    )
  }

  async function evaluate() {
    if (!inputLatex.trim()) return
    const id = uid()
    const entry: HistoryEntry = {
      id, expression: inputLatex, result: '', status: 'pending',
      level: 'cas', operation,
    }
    onHistory(entry)

    try {
      const token = await getToken()
      const res = await fetch(`${apiBase}/calc/cas`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          expression: inputLatex,
          operation,
          variable,
          lower: lower || undefined,
          upper: upper || undefined,
          at: at || undefined,
          topic_id: topicId,
          difficulty,
          problem_id: problemId,
          session_id: sessionId,
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        onHistory({ ...entry, status: 'error', result: data.detail ?? 'Evaluation failed' })
      } else {
        onHistory({ ...entry, status: 'done', latex: data.latex, result: data.expression })
      }
    } catch {
      onHistory({ ...entry, status: 'error', result: 'Request failed. Is the server running?' })
    }
  }

  const needsBounds = operation === 'integrate_definite'
  const needsAt = operation === 'limit' || operation === 'series'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Operation selector */}
      <select
        value={operation}
        onChange={e => setOperation(e.target.value as CASOperation)}
        style={{
          padding: '7px 10px', borderRadius: 8,
          border: '1px solid var(--border2)', background: 'var(--surface)',
          color: 'var(--text)', fontSize: 13, outline: 'none',
        }}
      >
        {CAS_OPS.map(op => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* Expression input */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <CalcMathField value={inputLatex} onChange={setInputLatex} placeholder="Enter expression…" />
      </div>

      {/* Variable */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, color: 'var(--text-dim)' }}>
        <span>Variable:</span>
        <input
          value={variable}
          onChange={e => setVariable(e.target.value)}
          style={{
            width: 40, padding: '4px 6px', borderRadius: 5,
            border: '1px solid var(--border2)', background: 'var(--surface)',
            color: 'var(--text)', fontSize: 13, textAlign: 'center',
          }}
        />
        {needsBounds && (
          <>
            <span>from</span>
            <input value={lower} onChange={e => setLower(e.target.value)} placeholder="a"
              style={{ width: 44, padding: '4px 6px', borderRadius: 5, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, textAlign: 'center' }} />
            <span>to</span>
            <input value={upper} onChange={e => setUpper(e.target.value)} placeholder="b"
              style={{ width: 44, padding: '4px 6px', borderRadius: 5, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, textAlign: 'center' }} />
          </>
        )}
        {needsAt && (
          <>
            <span>at</span>
            <input value={at} onChange={e => setAt(e.target.value)} placeholder="0"
              style={{ width: 44, padding: '4px 6px', borderRadius: 5, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, textAlign: 'center' }} />
          </>
        )}
      </div>

      <button
        type="button"
        onClick={evaluate}
        disabled={!inputLatex.trim()}
        className="btn-caramel"
        style={{ width: '100%', justifyContent: 'center', padding: '9px', fontSize: 13 }}
      >
        Evaluate
      </button>
    </div>
  )
}

// ─── Main CalculatorWidget ────────────────────────────────────────────────────

export function CalculatorWidget({
  calcMode,
  difficulty,
  userTier,
  getToken,
  onSendToAnswer,
  topicId = '',
  problemId = '',
  sessionId = '',
  apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000',
}: CalculatorWidgetProps) {
  const available = getAvailableLevels(calcMode)
  const [level, setLevel] = useState<CalcLevel>(() => available[available.length - 1] ?? 'basic')
  const [inputLatex, setInputLatex] = useState('')
  const [history, setHistoryRaw] = useState<HistoryEntry[]>([])
  const historyRef = useRef<HistoryEntry[]>([])

  // Keep level in available range as calcMode/difficulty changes
  useEffect(() => {
    const avail = getAvailableLevels(calcMode)
    if (avail.length && !avail.includes(level)) {
      setLevel(avail[avail.length - 1])
    }
  }, [calcMode]) // eslint-disable-line react-hooks/exhaustive-deps

  function addOrUpdateHistory(entry: HistoryEntry) {
    setHistoryRaw(prev => {
      const idx = prev.findIndex(e => e.id === entry.id)
      if (idx === -1) return [entry, ...prev]
      const updated = [...prev]
      updated[idx] = entry
      return updated
    })
  }

  function handleSend(entry: HistoryEntry) {
    const latex = entry.latex ?? entry.result
    onSendToAnswer(latex)
  }

  function handleSendRaw(value: string, _label: string) {
    onSendToAnswer(value)
  }

  // Basic/Scientific evaluation (client-side)
  function evaluateArithmetic() {
    if (!inputLatex.trim()) return
    const id = uid()
    // Convert LaTeX to evaluable JS expression
    let expr = inputLatex
      .replace(/\\cdot/g, '*')
      .replace(/\\div/g, '/')
      .replace(/\\times/g, '*')
      .replace(/\\left\(/g, '(')
      .replace(/\\right\)/g, ')')
      .replace(/\\left\|/g, 'Math.abs(')
      .replace(/\\right\|/g, ')')
      .replace(/\\sin\(/g, 'Math.sin(')
      .replace(/\\cos\(/g, 'Math.cos(')
      .replace(/\\tan\(/g, 'Math.tan(')
      .replace(/\\arcsin\(/g, 'Math.asin(')
      .replace(/\\arccos\(/g, 'Math.acos(')
      .replace(/\\arctan\(/g, 'Math.atan(')
      .replace(/\\log\(/g, 'Math.log10(')
      .replace(/\\ln\(/g, 'Math.log(')
      .replace(/\\sqrt\{/g, 'Math.sqrt(')
      .replace(/\^{(\d+)}/g, '**($1)')
      .replace(/\^{/g, '**(')
      .replace(/\\pi/g, 'Math.PI')
      .replace(/\\%/g, '/100')
      .replace(/}/g, ')')
    try {
      // eslint-disable-next-line no-new-func
      const result = new Function(`'use strict'; return (${expr})`)()
      const formatted = typeof result === 'number' ? String(parseFloat(result.toFixed(10))) : String(result)
      addOrUpdateHistory({ id, expression: inputLatex, result: formatted, status: 'done', level })
    } catch {
      addOrUpdateHistory({ id, expression: inputLatex, result: 'Invalid expression', status: 'error', level })
    }
    setInputLatex('')
  }

  function handleAppend(s: string) {
    setInputLatex(prev => prev + s)
  }

  function handleClear() { setInputLatex('') }

  function handleBackspace() {
    setInputLatex(prev => prev.slice(0, -1))
  }

  if (calcMode === 'none') {
    return (
      <div style={{
        padding: '20px', textAlign: 'center',
        border: '1px solid var(--border)', borderRadius: 10,
        background: 'var(--surface2)',
      }}>
        <div style={{ fontSize: 20, marginBottom: 8 }}>🚫</div>
        <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 14, marginBottom: 6 }}>
          No calculator for this topic
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
          This topic is designed to be solved without a calculator.
        </p>
      </div>
    )
  }

  const levelLabels: Record<CalcLevel, string> = {
    basic: 'Basic', scientific: 'Scientific', graphing: 'Graphing', cas: 'CAS',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      {/* Level tabs */}
      {available.length > 1 && (
        <div style={{
          display: 'flex', gap: 4,
          padding: 3,
          background: 'var(--surface2)',
          borderRadius: 9,
          border: '1px solid var(--border)',
        }}>
          {available.map(lvl => (
            <button
              key={lvl}
              type="button"
              onClick={() => setLevel(lvl)}
              style={{
                flex: 1, padding: '6px 4px',
                borderRadius: 7, border: 'none',
                background: level === lvl ? 'var(--surface)' : 'transparent',
                color: level === lvl ? 'var(--caramel)' : 'var(--text-muted)',
                fontWeight: level === lvl ? 700 : 500,
                fontSize: 12, cursor: 'pointer',
                boxShadow: level === lvl ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
                transition: 'all 0.15s',
              }}
            >
              {levelLabels[lvl]}
            </button>
          ))}
        </div>
      )}

      {/* Input display (Basic / Scientific) */}
      {(level === 'basic' || level === 'scientific') && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <CalcMathField
              value={inputLatex}
              onChange={setInputLatex}
              placeholder="Type or use buttons…"
            />
            <button
              type="button"
              onClick={evaluateArithmetic}
              style={{
                padding: '8px 14px', borderRadius: 8,
                background: 'var(--caramel)', color: '#fff',
                border: 'none', fontSize: 13, fontWeight: 700, cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              =
            </button>
          </div>
          <ArithmeticPanel
            level={level}
            onAppend={handleAppend}
            onEvaluate={evaluateArithmetic}
            onClear={handleClear}
            onBackspace={handleBackspace}
          />
        </div>
      )}

      {/* Graphing panel */}
      {level === 'graphing' && (
        <GraphingPanel onSend={handleSendRaw} />
      )}

      {/* CAS panel */}
      {level === 'cas' && (
        <CASPanel
          userTier={userTier}
          difficulty={difficulty}
          getToken={getToken}
          topicId={topicId}
          problemId={problemId}
          sessionId={sessionId}
          apiBase={apiBase}
          onHistory={addOrUpdateHistory}
        />
      )}

      {/* History */}
      {history.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            History
          </div>
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 5,
            maxHeight: 240, overflowY: 'auto',
          }}>
            {history.map(e => (
              <HistoryRow key={e.id} entry={e} onSend={handleSend} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
