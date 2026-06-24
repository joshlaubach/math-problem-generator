'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import { MathText } from '@/components/MathText'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface TemplateInfo {
  id: string
  name: string
  description: string
  total_problems: number
  time_limit_minutes: number | null
  calc_tier: string
  kind: string
}

const CALC_LABELS: Record<string, string> = {
  none: 'No calculator',
  scientific: 'Scientific calculator',
  graphing: 'Graphing calculator',
  cas: 'CAS calculator',
}

const PRESET_META: Record<string, { icon: string; color: string }> = {
  sat_math:     { icon: '📐', color: '#5B8DD9' },
  ap_calc_ab:   { icon: '∫',  color: '#9B59B6' },
  ap_calc_bc:   { icon: '∑',  color: '#8E44AD' },
  ap_statistics:{ icon: '📊', color: '#27AE60' },
}

export default function ExamPage() {
  const router = useRouter()
  const { getToken } = useAuth()
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [starting, setStarting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/exam/templates`)
      .then(r => r.json())
      .then(setTemplates)
      .catch(() => setError('Could not load exam templates.'))
  }, [])

  async function handleStart(templateId: string, untimed = false) {
    setStarting(templateId)
    setError(null)
    try {
      const token = await getToken()
      const resp = await fetch(`${API_BASE}/exam/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ template_id: templateId, untimed }),
      })
      const body = await resp.json().catch(() => ({}))
      if (!resp.ok) {
        const detail = (body as { detail?: string }).detail
        throw new Error(detail ?? 'Failed to start exam')
      }
      const { attempt_id } = body as { attempt_id: string }
      router.push(`/exam/${attempt_id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setStarting(null)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '40px 48px' }}>
      {/* Header */}
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <nav style={{ marginBottom: 32, fontSize: 13, color: 'var(--text-muted)' }}>
          <Link href="/" style={{ color: 'var(--text-dim)', textDecoration: 'none' }}>Home</Link>
          <span style={{ margin: '0 8px', opacity: 0.4 }}>/</span>
          <span style={{ color: 'var(--text)' }}>Exams</span>
        </nav>

        <h1 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 32, fontWeight: 700, color: 'var(--text)', marginBottom: 8,
        }}>
          Practice Exams
        </h1>
        <p style={{ fontSize: 15, color: 'var(--text-dim)', marginBottom: 36, lineHeight: 1.65, maxWidth: 560 }}>
          Real problems, server-side timer, and a worked-solution review after you submit.
          One exam credit per attempt, consumed on submit.
        </p>

        {error && (
          <div style={{
            marginBottom: 24, padding: '12px 16px', borderRadius: 8,
            border: '1px solid rgba(193,68,14,0.25)', background: 'var(--terra-dim)',
            fontSize: 14, color: 'var(--terracotta)',
          }}>
            {error}
          </div>
        )}

        {/* Template cards */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 16, marginBottom: 32,
        }}>
          {templates.map(t => {
            const meta = PRESET_META[t.id] ?? { icon: '📝', color: 'var(--caramel)' }
            const isStarting = starting === t.id
            return (
              <div key={t.id} className="warm-card" style={{ padding: '24px 26px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10,
                    background: `${meta.color}22`,
                    border: `1px solid ${meta.color}44`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20, flexShrink: 0,
                    color: meta.color,
                  }}>
                    {meta.icon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontFamily: 'var(--font-fraunces), Georgia, serif',
                      fontSize: 17, fontWeight: 700, color: 'var(--text)', marginBottom: 4,
                    }}>
                      {t.name}
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.55, marginBottom: 14 }}>
                      {t.description}
                    </p>

                    {/* Metadata chips */}
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
                      {[
                        `${t.total_problems} problems`,
                        t.time_limit_minutes ? `${t.time_limit_minutes} min` : 'Untimed',
                        CALC_LABELS[t.calc_tier] ?? t.calc_tier,
                      ].map(chip => (
                        <span key={chip} style={{
                          fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
                          background: 'var(--surface2)', padding: '3px 8px',
                          borderRadius: 4, border: '1px solid var(--border)',
                        }}>
                          {chip}
                        </span>
                      ))}
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        onClick={() => handleStart(t.id, false)}
                        disabled={!!starting}
                        className="btn-caramel"
                        style={{ fontSize: 13, padding: '8px 18px', opacity: starting && !isStarting ? 0.4 : 1 }}
                      >
                        {isStarting ? 'Generating exam…' : 'Start exam →'}
                      </button>
                      {t.time_limit_minutes !== null && (
                        <button
                          onClick={() => handleStart(t.id, true)}
                          disabled={!!starting}
                          className="btn-ghost"
                          style={{ fontSize: 12, padding: '8px 14px', opacity: starting && !isStarting ? 0.4 : 1 }}
                        >
                          Untimed
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Pricing note */}
        <div style={{
          background: 'var(--caramel-dim)',
          border: '1px solid rgba(196,151,106,0.25)',
          borderRadius: 10, padding: '16px 20px',
          fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.65,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
        }}>
          <span>
            Preset exams require an <strong style={{ color: 'var(--text)' }}>exam credit ($7.99)</strong> consumed on submit.
            Worked solutions are always free.
          </span>
          <Link href="/pricing" style={{
            color: 'var(--caramel)', fontWeight: 600, fontSize: 13,
            textDecoration: 'none', whiteSpace: 'nowrap',
          }}>
            Buy credits →
          </Link>
        </div>
      </div>
    </div>
  )
}
