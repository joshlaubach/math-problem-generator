'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface ExamProblem {
  index: number
  statement: string
  answer_type: string
}

interface ExamState {
  attempt_id: string
  template_id: string
  template_name: string
  total_problems: number
  remaining_seconds: number | null
  submitted_at: string | null
  problems: ExamProblem[]
}

function formatTime(seconds: number): string {
  if (seconds <= 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function ExamPage() {
  const { attemptId } = useParams<{ attemptId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()

  const [exam, setExam] = useState<ExamState | null>(null)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [flagged, setFlagged] = useState<Set<number>>(new Set())
  const [currentIdx, setCurrentIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null)
  const [timerExpired, setTimerExpired] = useState(false)
  const tokenRef = useRef<string | null>(null)

  // ── Fetch exam state ───────────────────────────────────────────────────────
  const fetchExam = useCallback(async () => {
    const token = tokenRef.current ?? await getToken()
    tokenRef.current = token
    const resp = await fetch(`${API_BASE}/exam/${attemptId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!resp.ok) throw new Error('Failed to load exam')
    return resp.json() as Promise<ExamState>
  }, [attemptId, getToken])

  useEffect(() => {
    fetchExam()
      .then(data => {
        setExam(data)
        setSecondsLeft(data.remaining_seconds)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [fetchExam])

  // ── Client-side countdown ──────────────────────────────────────────────────
  useEffect(() => {
    if (secondsLeft === null) return
    if (secondsLeft <= 0) { setTimerExpired(true); return }
    const id = setInterval(() => {
      setSecondsLeft(prev => {
        if (prev === null) return null
        const next = prev - 1
        if (next <= 0) { setTimerExpired(true); return 0 }
        return next
      })
    }, 1000)
    return () => clearInterval(id)
  }, [secondsLeft])

  // Re-sync remaining time from server every 5 minutes
  useEffect(() => {
    const id = setInterval(() => {
      fetchExam().then(d => setSecondsLeft(d.remaining_seconds)).catch(() => {})
    }, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [fetchExam])

  // ── Integrity monitoring ───────────────────────────────────────────────────
  const logEvent = useCallback(async (
    eventType: 'tab_blur' | 'tab_focus' | 'paste',
    problemIndex?: number,
  ) => {
    const token = tokenRef.current ?? await getToken()
    tokenRef.current = token
    fetch(`${API_BASE}/exam/${attemptId}/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ event_type: eventType, problem_index: problemIndex ?? null }),
    }).catch(() => {})
  }, [attemptId, getToken])

  useEffect(() => {
    const onVisibilityChange = () => {
      logEvent(document.hidden ? 'tab_blur' : 'tab_focus')
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
  }, [logEvent])

  // ── Submit ─────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    setSubmitting(true)
    setShowConfirm(false)
    setError(null)
    try {
      const token = await getToken()
      const stringAnswers: Record<string, string> = {}
      Object.entries(answers).forEach(([k, v]) => { stringAnswers[String(k)] = v })
      const resp = await fetch(`${API_BASE}/exam/${attemptId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ answers: stringAnswers }),
      })
      const body = await resp.json().catch(() => ({}))
      if (!resp.ok) {
        const detail = (body as { detail?: string }).detail
        throw new Error(detail ?? 'Submit failed')
      }
      router.push(`/exam/${attemptId}/review`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Submit failed')
      setSubmitting(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 12, color: 'var(--text-muted)', fontSize: 14,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8, background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff',
        }}>✦</div>
        Loading exam…
      </div>
    )
  }

  if (error && !exam) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--terracotta)' }}>{error}</div>
      </div>
    )
  }

  if (!exam) return null

  const problems = exam.problems
  const currentProblem = problems[currentIdx]
  const answered = Object.keys(answers).length
  const isUntimed = exam.remaining_seconds === null
  const timerColor = secondsLeft !== null && secondsLeft < 120 ? 'var(--terracotta)' : 'var(--text)'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div style={{
        height: 56, borderBottom: '1px solid var(--border)',
        background: 'var(--surface)', display: 'flex',
        alignItems: 'center', padding: '0 20px', gap: 16, flexShrink: 0,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6, background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, color: '#fff', flexShrink: 0,
        }}>✦</div>

        <div style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 15, fontWeight: 600, color: 'var(--text)', flex: 1,
        }}>
          {exam.template_name}
        </div>

        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          {answered}/{problems.length} answered
        </div>

        {/* Timer */}
        {!isUntimed && (
          <div style={{
            fontSize: 16, fontWeight: 700, color: timerExpired ? 'var(--terracotta)' : timerColor,
            fontVariantNumeric: 'tabular-nums', minWidth: 56, textAlign: 'right',
          }}>
            {timerExpired ? 'Time up' : formatTime(secondsLeft ?? 0)}
          </div>
        )}

        <button
          onClick={() => setShowConfirm(true)}
          disabled={submitting}
          className="btn-caramel"
          style={{ fontSize: 13, padding: '7px 16px' }}
        >
          {submitting ? 'Submitting…' : 'Submit exam'}
        </button>
      </div>

      {/* ── Timer expired banner ─────────────────────────────────────────────── */}
      {timerExpired && !exam.submitted_at && (
        <div style={{
          background: 'var(--terracotta)', color: '#fff',
          padding: '10px 20px', fontSize: 14, fontWeight: 600,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span>Time has expired. Submit now to grade your work.</span>
          <button
            onClick={() => setShowConfirm(true)}
            style={{ background: '#fff', color: 'var(--terracotta)', border: 'none', borderRadius: 6, padding: '5px 14px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
          >
            Submit →
          </button>
        </div>
      )}

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Problem list sidebar */}
        <div style={{
          width: 200, borderRight: '1px solid var(--border)',
          background: 'var(--surface)', overflowY: 'auto', flexShrink: 0, padding: '16px 12px',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
            Problems
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {problems.map(p => {
              const isCurrent = p.index === currentIdx
              const isAnswered = !!answers[p.index]
              const isFlagged = flagged.has(p.index)
              return (
                <button
                  key={p.index}
                  onClick={() => setCurrentIdx(p.index)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 10px', borderRadius: 6, textAlign: 'left', cursor: 'pointer',
                    background: isCurrent ? 'var(--caramel-dim)' : 'transparent',
                    border: isCurrent ? '1px solid rgba(196,151,106,0.3)' : '1px solid transparent',
                    color: isCurrent ? 'var(--caramel)' : 'var(--text)',
                  }}
                >
                  <div style={{
                    width: 22, height: 22, borderRadius: 4, flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700,
                    background: isAnswered ? 'var(--caramel)' : 'var(--surface2)',
                    color: isAnswered ? '#fff' : 'var(--text-dim)',
                    border: `1px solid ${isAnswered ? 'var(--caramel)' : 'var(--border)'}`,
                  }}>
                    {p.index + 1}
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                    {isAnswered ? 'Answered' : 'Blank'}
                  </span>
                  {isFlagged && <span style={{ fontSize: 10, marginLeft: 'auto', color: '#E8A020' }}>🚩</span>}
                </button>
              )
            })}
          </div>
        </div>

        {/* Problem view */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px 40px' }}>
          {currentProblem && (
            <div style={{ maxWidth: 700 }}>
              {/* Problem header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8, background: 'var(--caramel)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontWeight: 700, fontSize: 14, flexShrink: 0,
                }}>
                  {currentIdx + 1}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Problem {currentIdx + 1} of {problems.length}
                </div>
                <button
                  onClick={() => setFlagged(prev => {
                    const next = new Set(prev)
                    if (next.has(currentIdx)) next.delete(currentIdx); else next.add(currentIdx)
                    return next
                  })}
                  style={{
                    marginLeft: 'auto', background: 'none', border: 'none',
                    cursor: 'pointer', fontSize: 16, opacity: flagged.has(currentIdx) ? 1 : 0.3,
                  }}
                  title="Flag for review"
                >
                  🚩
                </button>
              </div>

              {/* Statement */}
              <div style={{
                background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border)',
                padding: '20px 24px', marginBottom: 24, fontSize: 15, lineHeight: 1.7,
              }}>
                <MathText latex={currentProblem.statement} prose />
              </div>

              {/* Answer input */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                  Your answer
                </div>
                <div onPaste={() => logEvent('paste', currentIdx)}>
                  <MathInput
                    value={answers[currentIdx] ?? ''}
                    onChange={val => setAnswers(prev => ({ ...prev, [currentIdx]: val }))}
                    placeholder="Enter your answer…"
                  />
                </div>
              </div>

              {/* Navigation */}
              <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
                {currentIdx > 0 && (
                  <button
                    onClick={() => setCurrentIdx(i => i - 1)}
                    className="btn-ghost"
                    style={{ fontSize: 13, padding: '8px 16px' }}
                  >
                    ← Previous
                  </button>
                )}
                {currentIdx < problems.length - 1 && (
                  <button
                    onClick={() => setCurrentIdx(i => i + 1)}
                    className="btn-caramel"
                    style={{ fontSize: 13, padding: '8px 16px' }}
                  >
                    Next →
                  </button>
                )}
                {currentIdx === problems.length - 1 && (
                  <button
                    onClick={() => setShowConfirm(true)}
                    className="btn-caramel"
                    style={{ fontSize: 13, padding: '8px 16px' }}
                  >
                    Review & Submit
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Submit confirmation modal ─────────────────────────────────────── */}
      {showConfirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)',
            padding: '32px 28px', maxWidth: 400, width: '90%',
            boxShadow: '0 8px 48px rgba(0,0,0,0.15)',
          }}>
            <h2 style={{
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 12,
            }}>
              Submit exam?
            </h2>
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 24 }}>
              You&apos;ve answered {answered} of {problems.length} problems.
              {problems.length - answered > 0 && ` ${problems.length - answered} blank answer${problems.length - answered > 1 ? 's' : ''} will be marked incorrect.`}
              {' '}This uses one exam credit.
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={handleSubmit} className="btn-caramel" style={{ flex: 1, justifyContent: 'center', padding: '11px' }}>
                Submit
              </button>
              <button onClick={() => setShowConfirm(false)} className="btn-ghost" style={{ flex: 1, justifyContent: 'center', padding: '11px' }}>
                Keep working
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{
          position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--terracotta)', color: '#fff', padding: '10px 20px',
          borderRadius: 8, fontSize: 13, fontWeight: 500, zIndex: 200,
        }}>
          {error}
        </div>
      )}
    </div>
  )
}
