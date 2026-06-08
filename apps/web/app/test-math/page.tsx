'use client';

import { useRef, useState } from 'react';
import { MathText } from '@/components/MathText';
import { MathInput } from '@/components/MathInput';
import { Whiteboard, type WhiteboardHandle } from '@/components/Whiteboard';
import { ShowMyWorkPanel } from '@/components/ShowMyWorkPanel';
import { StudentToolbar, type StudentToolbarHandle } from '@/components/StudentToolbar';

const EXAMPLES = [
  { label: 'Quadratic formula', latex: 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}' },
  { label: 'Gaussian integral', latex: '\\int_{-\\infty}^{\\infty} e^{-x^2}\\,dx = \\sqrt{\\pi}' },
  { label: "Euler's identity", latex: 'e^{i\\pi} + 1 = 0' },
  { label: 'Pythagorean theorem', latex: 'a^2 + b^2 = c^2' },
];

const WB_MSGS = [
  { label: 'Write equation', action: 'write' as const, latex: 'x^2 - 3x + 2 = 0', x: 5, y: 5 },
  { label: 'Write solution step', action: 'write' as const, latex: '(x-1)(x-2) = 0 \\Rightarrow x=1,\\,x=2', x: 5, y: 25 },
  { label: 'Write fraction', action: 'write' as const, latex: '\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}', x: 5, y: 45 },
  { label: 'Plot parabola', action: 'plot' as const, fn: 'x**2 - 3*x + 2', domain: [-1, 4] as [number, number], x: 2, y: 60 },
  { label: 'Clear board', action: 'clear' as const },
]

const WB_V2_MSGS: Array<{ label: string; msg: object | null }> = [
  { label: 'Section divider', msg: { type: 'wb_new_section', label: 'Step 1: Factor the quadratic' } },
  { label: 'Write (short)',   msg: { type: 'wb_write', latex: 'x = 2' } },
  { label: 'Write (long)',    msg: { type: 'wb_write', latex: '\\int_0^\\infty e^{-x^2}\\,dx = \\frac{\\sqrt{\\pi}}{2}', display: true } },
  { label: 'Mark incorrect',          msg: null },
  {
    label: 'Geometry scene',
    msg: {
      type: 'wb_write',
      scene: [
        { kind: 'polygon', points: [[0,0],[3,0],[1.5,2.6]], label: 'ABC' },
        { kind: 'point',   x: 0,   y: 0,   label: 'A' },
        { kind: 'point',   x: 3,   y: 0,   label: 'B' },
        { kind: 'point',   x: 1.5, y: 2.6, label: 'C' },
        { kind: 'segment', x1: 0, y1: 0, x2: 3, y2: 0, label: 'base = 3' },
      ],
    },
  },
  { label: 'Annotate student work',   msg: null },
  { label: 'Spam 5 writes (overlap test)', msg: null },
]

import { useEffect } from 'react';

export default function TestMathPage() {
  const [inputLatex, setInputLatex] = useState('\\frac{x+1}{2}');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [lastSubmit, setLastSubmit] = useState('');
  const wbRef  = useRef<WhiteboardHandle>(null);
  const stbRef = useRef<StudentToolbarHandle>(null);

  // Mirror the global app theme (sidebar toggle → document.documentElement[data-theme])
  useEffect(() => {
    const get = () =>
      document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
    setTheme(get())
    const obs = new MutationObserver(() => setTheme(get()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        padding: '48px 16px',
      }}
    >
      <div style={{ maxWidth: 672, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 40 }}>

        {/* Header */}
        <header>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)', margin: 0 }}>
            Math Rendering Test
          </h1>
          <p style={{ marginTop: 4, fontSize: 13, color: 'var(--text-muted)' }}>
            KaTeX block/inline rendering + MathLive round-trip + Whiteboard
          </p>
        </header>

        {/* Block KaTeX */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 16 }}>Block KaTeX</h2>
          {EXAMPLES.map((ex, i) => (
            <div key={ex.label} style={{
              borderBottom: i < EXAMPLES.length - 1 ? '1px solid var(--border)' : 'none',
              paddingBottom: 16, marginBottom: 16,
            }}>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{ex.label}</p>
              <MathText latex={ex.latex} />
            </div>
          ))}
        </section>

        {/* Inline KaTeX */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 12 }}>Inline KaTeX</h2>
          <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7 }}>
            The slope of a line is{' '}
            <MathText latex="m = \frac{\Delta y}{\Delta x}" inline />, and the
            area of a circle is{' '}
            <MathText latex="A = \pi r^2" inline />.
          </p>
        </section>

        {/* MathLive round-trip */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>MathLive Input Round-trip</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Type math below. The LaTeX string is echoed live and re-rendered by KaTeX.
          </p>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>
              Input field (MathLive)
            </label>
            <MathInput value={inputLatex} onChange={setInputLatex} placeholder="Type math here…" />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>
              LaTeX string
            </label>
            <code style={{
              display: 'block', background: 'var(--surface2)', color: 'var(--text)',
              fontSize: 12, borderRadius: 6, padding: '8px 12px', fontFamily: 'monospace',
              border: '1px solid var(--border)', wordBreak: 'break-all',
            }}>
              {inputLatex || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>empty</span>}
            </code>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>
              KaTeX render
            </label>
            <div style={{
              border: '1px solid var(--border)', borderRadius: 8,
              padding: '8px 16px', minHeight: 48, background: 'var(--surface2)',
            }}>
              {inputLatex
                ? <MathText latex={inputLatex} />
                : <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: 13 }}>nothing to render</span>
              }
            </div>
          </div>
        </section>

        {/* Whiteboard test */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>Whiteboard Test</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Fire mock tutor messages to test KaTeX rendering, GSAP animation, and Mafs plots.
          </p>

          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Legacy messages (write/plot/clear):</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {WB_MSGS.map((m) => (
                <button key={m.label} type="button"
                  onClick={() => wbRef.current?.handleMessage(m as any)}
                  style={{ padding: '5px 11px', borderRadius: 7, fontSize: 12, border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text-dim)', cursor: 'pointer' }}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Phase 2 — layout, geometry, annotations:</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {WB_V2_MSGS.map((m) => (
                <button key={m.label} type="button"
                  onClick={() => {
                    if (m.label === 'Mark incorrect') {
                      wbRef.current?.markIncorrect()
                    } else if (m.label === 'Annotate student work') {
                      wbRef.current?.annotateStudentWork({
                        latex: '\\leftarrow \\text{Check the sign here}',
                        label: 'Sign error', color: 'correction',
                      })
                    } else if (m.label === 'Spam 5 writes (overlap test)') {
                      ['f(x) = x^2', "f'(x) = 2x", '\\int x^2\\,dx = \\frac{x^3}{3} + C',
                       'x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}', 'e^{i\\pi}+1=0']
                        .forEach((latex, i) => setTimeout(() => wbRef.current?.handleMessage({ type: 'wb_write', latex }), i * 80))
                    } else if (m.msg) {
                      wbRef.current?.handleMessage(m.msg as any)
                    }
                  }}
                  style={{ padding: '5px 11px', borderRadius: 7, fontSize: 12, border: '1px solid var(--caramel)', background: 'var(--caramel-dim)', color: 'var(--caramel)', cursor: 'pointer' }}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <Whiteboard ref={wbRef} visibleHeight={480} theme={theme} />
        </section>

        {/* Show My Work panel test */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
            Show My Work Panel
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Step-by-step LaTeX entry. "Check steps" fires onSubmit with steps joined by \\rightarrow.
          </p>
          <ShowMyWorkPanel
            theme={theme}
            onSubmit={s => setLastSubmit(s)}
          />
          {lastSubmit && (
            <div style={{ fontSize: 12 }}>
              <span style={{ color: 'var(--text-muted)' }}>Last submit: </span>
              <code style={{ color: 'var(--text)', background: 'var(--surface2)', padding: '2px 6px', borderRadius: 4 }}>
                {lastSubmit}
              </code>
            </div>
          )}
        </section>

        {/* Student toolbar test */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
            Student Drawing Canvas
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Fabric.js v7: pen, highlight, eraser, line, arrow, shapes, angle marker, LaTeX insert,
            text, color palette, grid snap, image upload/paste, undo/redo, clear.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => stbRef.current?.undo()}
              style={{ padding: '5px 11px', borderRadius: 7, fontSize: 12, border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text-dim)', cursor: 'pointer' }}>
              Undo
            </button>
            <button onClick={() => stbRef.current?.redo()}
              style={{ padding: '5px 11px', borderRadius: 7, fontSize: 12, border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text-dim)', cursor: 'pointer' }}>
              Redo
            </button>
            <button onClick={() => stbRef.current?.clear()}
              style={{ padding: '5px 11px', borderRadius: 7, fontSize: 12, border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text-dim)', cursor: 'pointer' }}>
              Clear (external)
            </button>
          </div>
          <StudentToolbar ref={stbRef} theme={theme} width={624} height={280} />
        </section>

      </div>
    </div>
  );
}
