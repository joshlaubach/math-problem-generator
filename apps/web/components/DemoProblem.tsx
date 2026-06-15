'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface DemoProb {
  id: string
  prompt_latex: string
  answer_type: string
  final_answer: string
  solution: { steps?: { description_latex?: string; expression_latex?: string }[] } | null
}

type State = 'idle' | 'checking' | 'correct' | 'wrong'

export function DemoProblem() {
  const [prob, setProb] = useState<DemoProb | null>(null)
  const [answer, setAnswer] = useState('')
  const [state, setState] = useState<State>('idle')
  const [revealed, setRevealed] = useState(false)
  const [loadFailed, setLoadFailed] = useState(false)

  async function load() {
    setState('idle'); setAnswer(''); setRevealed(false); setLoadFailed(false); setProb(null)
    try {
      const r = await fetch(`${API_BASE}/demo/problem`, { cache: 'no-store' })
      if (!r.ok) throw new Error('bad status')
      setProb(await r.json())
    } catch {
      setLoadFailed(true)
    }
  }

  useEffect(() => { load() }, [])

  async function check() {
    if (!prob || !answer.trim() || state === 'checking') return
    setState('checking')
    try {
      const r = await fetch(`${API_BASE}/demo/check-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_answer: answer,
          correct_answer: prob.final_answer,
          answer_type: prob.answer_type,
        }),
      })
      const j = await r.json()
      setState(j.is_correct ? 'correct' : 'wrong')
    } catch {
      setState('idle')
    }
  }

  const steps = prob?.solution?.steps ?? []

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      padding: '20px 24px',
      maxWidth: 460,
      boxShadow: '0 4px 24px var(--caramel-dim)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12,
      }}>
        <div style={{
          fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em',
          color: 'var(--caramel)', fontWeight: 600,
        }}>
          Try it — no signup
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>✓ CAS-verified</div>
      </div>

      {loadFailed && (
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Demo unavailable — start the API to try a live problem.
        </p>
      )}

      {!loadFailed && !prob && (
        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Loading a problem…</p>
      )}

      {prob && (
        <>
          <div style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 17, color: 'var(--text)', marginBottom: 16, lineHeight: 1.6,
          }}>
            <MathText latex={prob.prompt_latex} prose />
          </div>

          {/* Solved state */}
          {state === 'correct' ? (
            <div style={{
              borderRadius: 8, padding: '12px 14px', marginBottom: 14,
              background: 'var(--sage-dim, rgba(122,158,126,0.12))',
              border: '1px solid rgba(122,158,126,0.3)',
            }}>
              <div style={{ fontWeight: 600, color: 'var(--forest, #4a7c52)', fontSize: 15 }}>
                ✓ Correct — and CAS-verified.
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>
                Equivalent forms count too: <code>1/2</code>, <code>0.5</code>, and{' '}
                <MathText latex="\frac{1}{2}" inline /> all pass.
              </div>
            </div>
          ) : (
            <>
              <MathInput
                value={answer}
                onChange={setAnswer}
                placeholder="Your answer…"
                className="warm-input"
              />
              {state === 'wrong' && (
                <div style={{ fontSize: 13, color: 'var(--terracotta)', marginTop: 8 }}>
                  Not quite — take another look and try again.
                </div>
              )}
              <button
                type="button"
                onClick={check}
                disabled={!answer.trim() || state === 'checking'}
                className="btn-caramel"
                style={{ width: '100%', justifyContent: 'center', padding: '10px', marginTop: 12 }}
              >
                {state === 'checking' ? 'Checking…' : state === 'wrong' ? 'Try Again' : 'Check Answer'}
              </button>
            </>
          )}

          {/* Reveal solution (after a wrong attempt) */}
          {state === 'wrong' && steps.length > 0 && (
            <button
              type="button"
              onClick={() => setRevealed(r => !r)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', marginTop: 10,
                fontSize: 13, color: 'var(--text-dim)', textDecoration: 'underline', padding: 0,
              }}
            >
              {revealed ? 'Hide solution' : 'Show me the solution'}
            </button>
          )}
          {revealed && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {steps.map((s, i) => (
                <div key={i} style={{
                  borderRadius: 7, background: 'var(--surface2)', padding: '8px 12px', fontSize: 13,
                }}>
                  {s.description_latex && (
                    <div style={{ color: 'var(--text-dim)' }}>
                      <MathText latex={s.description_latex} prose />
                    </div>
                  )}
                  {s.expression_latex && (
                    <div style={{ color: 'var(--text)', fontWeight: 500 }}>
                      <MathText latex={s.expression_latex} inline />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Footer actions */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 14, marginTop: 16,
            paddingTop: 14, borderTop: '1px solid var(--border)',
          }}>
            {state === 'correct' ? (
              <Link href="/sign-up" className="btn-caramel" style={{ textDecoration: 'none', padding: '8px 18px', fontSize: 14 }}>
                Keep going — it&apos;s free →
              </Link>
            ) : (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                One free problem. No account needed.
              </span>
            )}
            <button
              type="button"
              onClick={load}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', marginLeft: 'auto',
                fontSize: 13, color: 'var(--caramel)', padding: 0,
              }}
            >
              ↻ New problem
            </button>
          </div>
        </>
      )}
    </div>
  )
}
