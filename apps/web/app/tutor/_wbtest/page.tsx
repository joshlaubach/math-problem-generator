'use client'

/**
 * Whiteboard dev harness — /tutor/_wbtest
 *
 * Drives every method of the Whiteboard imperative API so they can be
 * verified with Playwright (or by eye) before wiring real sessions.
 *
 * DELETE before merging to main.
 */

import React, { useRef, useState, useCallback } from 'react'
import { Whiteboard, type WhiteboardHandle } from '@/components/Whiteboard'

// String.raw alias — lets IDE highlight LaTeX without mangling backslashes
const r = String.raw

// ── Test fixtures ─────────────────────────────────────────────────────────────

const SAMPLE_BLOCKS = [
  { latex: r`P(A \cap B) = P(A) \cdot P(B|A)`,       label: 'Conditional Probability' },
  { latex: r`\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}`, label: 'Gaussian Integral' },
  { latex: r`\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}`, label: 'Basel Problem' },
  { latex: r`\frac{d}{dx}\left[\sin x\right] = \cos x`, label: 'Derivative of sin' },
  { latex: r`e^{i\pi} + 1 = 0`,                        label: "Euler's Identity" },
  { latex: r`\binom{n}{k} = \frac{n!}{k!(n-k)!}`,     label: 'Binomial Coefficient' },
]

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WbTestPage() {
  const wbRef   = useRef<WhiteboardHandle>(null)
  const [log, setLog]       = useState<string[]>(['Ready.'])
  const [theme, setTheme]   = useState<'light' | 'dark'>('light')
  const [blockIdx, setBlockIdx] = useState(0)

  const push = useCallback((msg: string) => {
    const time = new Date().toLocaleTimeString()
    setLog(prev => [...prev.slice(-24), `${time} — ${msg}`])
  }, [])

  // ── Action handlers ──────────────────────────────────────────────────────

  const writeNext = () => {
    const b = SAMPLE_BLOCKS[blockIdx % SAMPLE_BLOCKS.length]
    wbRef.current?.writeBlock(b.latex)
    push(`writeBlock: ${b.label}`)
    setBlockIdx(i => i + 1)
  }

  const writeBatch = async () => {
    push('Writing 4 blocks in rapid sequence…')
    for (let i = 0; i < 4; i++) {
      const b = SAMPLE_BLOCKS[(blockIdx + i) % SAMPLE_BLOCKS.length]
      wbRef.current?.writeBlock(b.latex)
      await sleep(320)
    }
    setBlockIdx(i => i + 4)
    push('Done — check no overlap and auto-scroll to latest.')
  }

  const insertSection = () => {
    const labels = ['Problem 1', 'Concept Review', 'Worked Example', 'Practice']
    const label = labels[blockIdx % labels.length]
    wbRef.current?.newSection(label)
    push(`newSection: "${label}"`)
  }

  const insertPlot = () => {
    wbRef.current?.handleMessage({
      type: 'whiteboard',
      action: 'plot',
      fn: 'Math.sin(x)',
      domain: [-6.28, 6.28],
    })
    push('plot: sin(x) via legacy handleMessage')
  }

  const zoomTop    = () => { wbRef.current?.zoomTo('top');    push('zoomTo("top")') }
  const zoomLatest = () => { wbRef.current?.zoomTo('latest'); push('zoomTo("latest")') }
  const zoomPx     = () => { wbRef.current?.zoomTo(200);     push('zoomTo(200px)') }

  const doClear    = () => { wbRef.current?.clearBoard();                    setBlockIdx(0); push('clearBoard()') }
  const doClearSnap = () => { wbRef.current?.clearBoard({ snapshot: true }); setBlockIdx(0); push('clearBoard({ snapshot: true })') }

  const doDownload = async () => {
    const snap = await wbRef.current?.getSnapshot()
    if (snap) {
      const bytes = atob(snap.split(',')[1]).length
      push(`getSnapshot() → ${(bytes / 1024).toFixed(1)} KB ✓`)
    } else {
      push('getSnapshot() → null ✗')
    }
  }

  // Legacy message compat
  const legacyWrite = () => {
    wbRef.current?.handleMessage({ type: 'whiteboard', action: 'write', latex: r`f(x) = x^2 + 3x - 4` })
    push('handleMessage {type:"whiteboard", action:"write"}')
  }
  const legacyClear = () => {
    wbRef.current?.handleMessage({ type: 'whiteboard', action: 'clear' })
    setBlockIdx(0)
    push('handleMessage {type:"whiteboard", action:"clear"}')
  }

  // Phase-4 wb_* messages
  const wbWrite   = () => { wbRef.current?.handleMessage({ type: 'wb_write', latex: r`A = \pi r^2` });  push('wb_write') }
  const wbSection = () => { wbRef.current?.handleMessage({ type: 'wb_new_section', label: 'Phase-4 Section' }); push('wb_new_section') }
  const wbZoom    = () => { wbRef.current?.handleMessage({ type: 'wb_zoom',  region: 'latest' }); push('wb_zoom latest') }
  const wbClearSn = () => { wbRef.current?.handleMessage({ type: 'wb_clear', snapshot: true });  setBlockIdx(0); push('wb_clear snapshot:true') }

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui' }}>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Whiteboard Dev Harness</h1>
        <span style={{ fontSize: 12, color: '#888', background: '#fee', padding: '2px 8px', borderRadius: 10 }}>
          DELETE before merge
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, alignItems: 'start' }}>

        {/* ── Whiteboard ── */}
        <Whiteboard ref={wbRef} visibleHeight={600} theme={theme} />

        {/* ── Controls ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          <Sect title="Theme">
            <Row>
              <Btn active={theme === 'light'} onClick={() => setTheme('light')}>Light</Btn>
              <Btn active={theme === 'dark'}  onClick={() => setTheme('dark')}>Dark</Btn>
            </Row>
          </Sect>

          <Sect title="Write Content">
            <Btn onClick={writeNext}>writeBlock (cycle)</Btn>
            <Btn onClick={writeBatch}>Write 4 in sequence</Btn>
            <Btn onClick={insertSection}>newSection</Btn>
            <Btn onClick={insertPlot}>Plot sin(x)</Btn>
          </Sect>

          <Sect title="Zoom / Scroll">
            <Row>
              <Btn onClick={zoomTop}>↑ Top</Btn>
              <Btn onClick={zoomLatest}>↓ Latest</Btn>
              <Btn onClick={zoomPx}>200px</Btn>
            </Row>
          </Sect>

          <Sect title="Clear">
            <Btn onClick={doClear}>clearBoard()</Btn>
            <Btn onClick={doClearSnap}>clearBoard + snapshot</Btn>
          </Sect>

          <Sect title="Export">
            <Btn onClick={doDownload}>getSnapshot() → check size</Btn>
          </Sect>

          <Sect title="Legacy handleMessage">
            <Btn onClick={legacyWrite}>whiteboard / write</Btn>
            <Btn onClick={legacyClear}>whiteboard / clear</Btn>
          </Sect>

          <Sect title="Phase-4 WS Messages">
            <Btn onClick={wbWrite}>wb_write</Btn>
            <Btn onClick={wbSection}>wb_new_section</Btn>
            <Btn onClick={wbZoom}>wb_zoom latest</Btn>
            <Btn onClick={wbClearSn}>wb_clear + snapshot</Btn>
          </Sect>

          <Sect title="Log">
            <div style={{
              maxHeight: 200, overflowY: 'auto',
              background: '#f8f8f8', border: '1px solid #ddd',
              borderRadius: 6, padding: '6px 8px',
              fontSize: 11, fontFamily: 'monospace',
              lineHeight: 1.75, color: '#555',
            }}>
              {log.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          </Sect>

          <Sect title="Test IDs (for Playwright)">
            <div style={{ fontSize: 11, color: '#888', lineHeight: 1.7, fontFamily: 'monospace' }}>
              <div>wb-scroll      — scroll container</div>
              <div>wb-doc         — growing document</div>
              <div>wb-tutor-layer — KaTeX blocks</div>
              <div>wb-student-layer — Fabric canvas</div>
            </div>
          </Sect>
        </div>
      </div>
    </div>
  )
}

// ── Minimal UI components ─────────────────────────────────────────────────────

function Sect({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#999' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', gap: 6 }}>{children}</div>
}

function Btn({ onClick, active, children }: { onClick: () => void; active?: boolean; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} style={{
      flex: 1, padding: '7px 10px', borderRadius: 6, cursor: 'pointer',
      border: `1px solid ${active ? '#b87333' : '#ddd'}`,
      background: active ? 'rgba(184,134,11,0.08)' : 'none',
      color: active ? '#b87333' : '#444',
      fontSize: 12, fontWeight: active ? 600 : 400,
      textAlign: 'left' as const,
    }}>
      {children}
    </button>
  )
}

function sleep(ms: number) { return new Promise<void>(res => setTimeout(res, ms)) }
