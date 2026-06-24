'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import { MathText } from '@/components/MathText'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface WorkedStep { step: string; explanation: string }
interface ProblemResult {
  index: number
  statement: string
  student_answer: string | null
  correct: boolean
  correct_answer: string
  worked_steps: WorkedStep[]
}
interface ReviewData {
  score: number
  problems_correct: number
  total_problems: number
  results: ProblemResult[]
  review_summary: string
  integrity_flag_count: number
}

export default function ExamReviewPage() {
  const { attemptId } = useParams<{ attemptId: string }>()
  const { getToken } = useAuth()
  const [data, setData] = useState<ReviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openSteps, setOpenSteps] = useState<Set<number>>(new Set())

  useEffect(() => {
    getToken().then(token =>
      fetch(`${API_BASE}/exam/${attemptId}/review`, {
        headers: { Authorization: `Bearer ${token}` },
      })
    ).then(r => {
      if (!r.ok) throw new Error('Failed to load review')
      return r.json()
    }).then(setData).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [attemptId, getToken])

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 12, color: 'var(--text-muted)', fontSize: 14,
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--caramel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff' }}>✦</div>
        Loading your results…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--terracotta)' }}>{error ?? 'Could not load review.'}</div>
      </div>
    )
  }

  const pct = Math.round(data.score * 100)
  const scoreColor = pct >= 80 ? '#27AE60' : pct >= 60 ? '#E8A020' : 'var(--terracotta)'
  const wrongResults = data.results.filter(r => !r.correct)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', overflowY: 'auto' }}>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '40px 24px' }}>

        {/* Score card */}
        <div style={{
          background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)',
          padding: '32px 36px', marginBottom: 32, textAlign: 'center',
        }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--caramel)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, color: '#fff', marginBottom: 20 }}>✦</div>

          <div style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 60, fontWeight: 700, color: scoreColor, lineHeight: 1, marginBottom: 8,
          }}>
            {pct}%
          </div>
          <div style={{ fontSize: 16, color: 'var(--text-dim)', marginBottom: 4 }}>
            {data.problems_correct} / {data.total_problems} correct
          </div>

          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 24 }}>
            <Link href="/exam" className="btn-caramel" style={{ textDecoration: 'none', padding: '10px 22px', fontSize: 14 }}>
              Take another exam
            </Link>
            <Link href="/tutor/new" className="btn-ghost" style={{ textDecoration: 'none', padding: '10px 22px', fontSize: 14 }}>
              Book a tutoring session
            </Link>
          </div>
        </div>

        {/* AI review summary */}
        {data.review_summary && (
          <div style={{
            background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.25)',
            borderRadius: 12, padding: '20px 24px', marginBottom: 32,
            fontSize: 14, lineHeight: 1.75, color: 'var(--text-dim)',
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--caramel)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
              Tutor Summary
            </div>
            {data.review_summary}
          </div>
        )}

        {/* Per-problem results */}
        <h2 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 16,
        }}>
          Problem by problem
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.results.map(r => (
            <div key={r.index} style={{
              background: 'var(--surface)', border: `1px solid ${r.correct ? 'rgba(39,174,96,0.25)' : 'rgba(193,68,14,0.2)'}`,
              borderRadius: 10, overflow: 'hidden',
            }}>
              {/* Header row */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '14px 18px',
                background: r.correct ? 'rgba(39,174,96,0.06)' : 'rgba(193,68,14,0.05)',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 6, flexShrink: 0,
                  background: r.correct ? '#27AE60' : 'var(--terracotta)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontSize: 14, fontWeight: 700,
                }}>
                  {r.correct ? '✓' : '✗'}
                </div>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>
                  Problem {r.index + 1}
                </div>
                {!r.correct && r.student_answer && (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    Your answer: <span style={{ color: 'var(--terracotta)', fontWeight: 500 }}>
                      <MathText latex={r.student_answer} />
                    </span>
                  </div>
                )}
                {!r.correct && !r.student_answer && (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    Blank
                  </div>
                )}
              </div>

              {/* Statement */}
              <div style={{ padding: '12px 18px', borderTop: '1px solid var(--border)', fontSize: 14, lineHeight: 1.65 }}>
                <MathText latex={r.statement} prose />
              </div>

              {/* Correct answer + worked steps (wrong only) */}
              {!r.correct && (
                <div style={{ borderTop: '1px solid var(--border)', padding: '14px 18px' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#27AE60', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Correct answer
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: r.worked_steps.length ? 14 : 0 }}>
                    <MathText latex={r.correct_answer} />
                  </div>

                  {r.worked_steps.length > 0 && (
                    <>
                      <button
                        onClick={() => setOpenSteps(prev => {
                          const next = new Set(prev)
                          if (next.has(r.index)) next.delete(r.index); else next.add(r.index)
                          return next
                        })}
                        style={{
                          background: 'none', border: '1px solid var(--border)',
                          borderRadius: 6, padding: '6px 12px', fontSize: 12,
                          fontWeight: 600, color: 'var(--text-dim)', cursor: 'pointer',
                          marginBottom: openSteps.has(r.index) ? 14 : 0,
                        }}
                      >
                        {openSteps.has(r.index) ? 'Hide steps ↑' : 'Show worked solution ↓'}
                      </button>

                      {openSteps.has(r.index) && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                          {r.worked_steps.map((step, si) => (
                            <div key={si} style={{
                              display: 'flex', gap: 12, alignItems: 'flex-start',
                            }}>
                              <div style={{
                                width: 24, height: 24, borderRadius: 4, flexShrink: 0, marginTop: 2,
                                background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.3)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 11, fontWeight: 700, color: 'var(--caramel)',
                              }}>
                                {si + 1}
                              </div>
                              <div>
                                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>
                                  <MathText latex={step.step} />
                                </div>
                                {step.explanation && (
                                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.55 }}>
                                    {step.explanation}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div style={{
          marginTop: 40, padding: '24px 28px',
          background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.25)',
          borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
              Want to work through your mistakes?
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              Book a tutoring session and your exam problems come pre-loaded as context.
            </div>
          </div>
          <Link href="/tutor/new" className="btn-caramel" style={{ textDecoration: 'none', padding: '10px 20px', fontSize: 14, whiteSpace: 'nowrap' }}>
            Book session →
          </Link>
        </div>

      </div>
    </div>
  )
}
