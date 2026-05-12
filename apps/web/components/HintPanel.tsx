'use client'

import { useState } from 'react'
import { Lightbulb } from '@phosphor-icons/react'
import { api, ApiError, ProblemResponse } from '@/lib/api-client'
import { MathText } from '@/components/MathText'

interface HintPanelProps {
  problem: ProblemResponse
  getToken: () => Promise<string | null>
  userTier?: string
  isTeacher?: boolean
}

const TIER_MAX_HINTS: Record<string, number> = {
  free: 2, basic: 3, student: 4, honors: 4, 'classroom-student': 4,
}
const MAX_HINTS = 4

export function HintPanel({ problem, getToken, userTier = 'free', isTeacher = false }: HintPanelProps) {
  const [hints, setHints] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const maxHints = isTeacher ? MAX_HINTS : (TIER_MAX_HINTS[userTier] ?? 2)
  const canRequestMore = hints.length < MAX_HINTS
  const nextIsGated = !isTeacher && hints.length >= maxHints

  async function requestHint() {
    if (!canRequestMore || nextIsGated) return
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const res = await api.getHint(token ?? '', {
        problem_id: problem.id,
        problem_latex: problem.prompt_latex,
        hint_index: hints.length,
      })
      setHints(prev => [...prev, res.hint])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not get hint. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="warm-card-static"
      style={{
        padding: 24,
        animation: 'cardIn 0.5s 0.15s both cubic-bezier(0.16,1,0.3,1)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
        <div className="card-eyebrow" style={{ marginBottom: 0 }}>Hints</div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {hints.length} / {MAX_HINTS} used
        </span>
      </div>

      {/* Revealed hints */}
      {hints.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
          {hints.map((h, i) => (
            <div key={i} className="hint-item" style={{ animationDelay: `${i * 0.08}s` }}>
              <span className="hint-num">{i + 1}.</span>
              <span>
                <MathText latex={h} prose />
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <p style={{ fontSize: 13, color: 'var(--terracotta)', marginBottom: 12 }}>{error}</p>
      )}

      {/* Upgrade gate */}
      {nextIsGated ? (
        <div style={{
          borderRadius: 8,
          border: '1px solid rgba(196,151,106,0.25)',
          background: 'var(--caramel-dim)',
          padding: '12px 16px',
          fontSize: 13, color: 'var(--text-dim)',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--caramel)' }}>More hints</span> are available on a paid plan.{' '}
          <a href="/pricing" style={{ color: 'var(--caramel)', textDecoration: 'underline' }}>Upgrade →</a>
        </div>
      ) : canRequestMore ? (
        <button
          type="button"
          onClick={requestHint}
          disabled={loading}
          className="btn-ghost"
          style={{ width: '100%', justifyContent: 'center' }}
        >
          <Lightbulb size={15} weight="bold" />
          {loading
            ? 'Getting hint…'
            : hints.length === 0
            ? 'Get a Hint'
            : `Hint ${hints.length + 1}`}
        </button>
      ) : (
        <p style={{ fontSize: 12, textAlign: 'center', color: 'var(--text-muted)' }}>All hints used.</p>
      )}
    </div>
  )
}
