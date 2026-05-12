'use client'

import { useState } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

type Goal = 'pass' | 'b' | 'a' | 'mastery'

interface GoalOption {
  id: Goal
  label: string
  subtitle: string
  description: string
  difficulty: string
  color: string
}

const GOALS: GoalOption[] = [
  {
    id: 'pass',
    label: 'Just Pass',
    subtitle: 'C / D → C',
    description: 'I need to pass the class. Focused, practical practice at foundational levels.',
    difficulty: 'Difficulty 2–3',
    color: 'var(--text-dim)',
  },
  {
    id: 'b',
    label: 'Solid B',
    subtitle: 'B− / C → B',
    description: 'I want to understand the material well enough to do well on most assessments.',
    difficulty: 'Difficulty 3–4',
    color: 'var(--caramel)',
  },
  {
    id: 'a',
    label: 'Strong A',
    subtitle: 'B+ → A',
    description: 'I want to excel. Harder problems, tighter accuracy requirements.',
    difficulty: 'Difficulty 4–5',
    color: 'var(--sage)',
  },
  {
    id: 'mastery',
    label: 'Mastery',
    subtitle: 'A → A+',
    description: 'I want to truly master every concept. Full difficulty range, high accuracy bar.',
    difficulty: 'Difficulty 5–6',
    color: 'var(--terracotta)',
  },
]

export default function OnboardingPage() {
  const { getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()

  const [step, setStep] = useState<1 | 2>(1)
  const [ageChecked, setAgeChecked] = useState(false)
  const [tosChecked, setTosChecked] = useState(false)
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canProceedStep1 = ageChecked && tosChecked

  async function handleStep1() {
    if (!canProceedStep1) return
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
      const resp = await fetch(`${apiBase}/users/me/confirm-age`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? 'Request failed')
      }
      setStep(2)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  async function handleStep2() {
    if (!selectedGoal) return
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
      const resp = await fetch(`${apiBase}/users/me/goal`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: selectedGoal }),
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? 'Failed to save goal')
      }
      router.push('/dashboard')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: '24px 16px',
    }}>
      <div style={{
        background: 'var(--surface)', borderRadius: 16,
        border: '1px solid var(--border)',
        padding: '40px 36px',
        maxWidth: step === 2 ? 520 : 440,
        width: '100%',
        boxShadow: '0 4px 32px rgba(0,0,0,0.06)',
        transition: 'max-width 0.2s',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: 'var(--caramel)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, color: '#fff',
          }}>
            ✦
          </div>
          <span style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 18, fontWeight: 600, color: 'var(--text)',
          }}>
            Gradient
          </span>
        </div>

        {/* Step indicator */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 28 }}>
          {[1, 2].map(s => (
            <div key={s} style={{
              flex: 1, height: 3, borderRadius: 2,
              background: s <= step ? 'var(--caramel)' : 'var(--border)',
              transition: 'background 0.2s',
            }} />
          ))}
        </div>

        {/* ── Step 1: Age + ToS ── */}
        {step === 1 && (
          <>
            <h1 style={{
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 8,
            }}>
              One last step
            </h1>
            {user?.firstName && (
              <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 20 }}>
                Welcome, {user.firstName}! Before you start, we need two confirmations.
              </p>
            )}

            {/* Age */}
            <label style={{
              display: 'flex', alignItems: 'flex-start', gap: 12,
              cursor: 'pointer', marginBottom: 16,
              padding: '14px 16px', borderRadius: 10,
              border: `1px solid ${ageChecked ? 'rgba(196,151,106,0.4)' : 'var(--border)'}`,
              background: ageChecked ? 'var(--caramel-dim)' : 'var(--surface2)',
              transition: 'all 0.15s',
            }}>
              <input
                type="checkbox"
                checked={ageChecked}
                onChange={e => setAgeChecked(e.target.checked)}
                style={{ marginTop: 2, width: 16, height: 16, accentColor: 'var(--caramel)', flexShrink: 0 }}
              />
              <span style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.55 }}>
                I confirm that I am <strong>13 years of age or older</strong>. If I am under 18, a parent or guardian has consented to my use of this platform.
              </span>
            </label>

            {/* ToS */}
            <label style={{
              display: 'flex', alignItems: 'flex-start', gap: 12,
              cursor: 'pointer', marginBottom: 24,
              padding: '14px 16px', borderRadius: 10,
              border: `1px solid ${tosChecked ? 'rgba(196,151,106,0.4)' : 'var(--border)'}`,
              background: tosChecked ? 'var(--caramel-dim)' : 'var(--surface2)',
              transition: 'all 0.15s',
            }}>
              <input
                type="checkbox"
                checked={tosChecked}
                onChange={e => setTosChecked(e.target.checked)}
                style={{ marginTop: 2, width: 16, height: 16, accentColor: 'var(--caramel)', flexShrink: 0 }}
              />
              <span style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.55 }}>
                I agree to Gradient&apos;s{' '}
                <Link href="/terms" target="_blank" style={{ color: 'var(--caramel)', textDecoration: 'underline' }}>Terms of Service</Link>{' '}
                and{' '}
                <Link href="/privacy" target="_blank" style={{ color: 'var(--caramel)', textDecoration: 'underline' }}>Privacy Policy</Link>.
                I understand that my learning data will be collected and used as described.
              </span>
            </label>

            {error && <ErrorBox message={error} />}

            <button
              onClick={handleStep1}
              disabled={!canProceedStep1 || loading}
              className="btn-caramel"
              style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 14, opacity: canProceedStep1 ? 1 : 0.5 }}
            >
              {loading ? 'Saving…' : 'Continue →'}
            </button>

            <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.6 }}>
              For schools using Gradient with students, please review our{' '}
              <Link href="/dpa" target="_blank" style={{ color: 'var(--caramel)' }}>Data Processing Agreement</Link>.
            </p>
          </>
        )}

        {/* ── Step 2: Goal selection ── */}
        {step === 2 && (
          <>
            <h1 style={{
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 8,
            }}>
              What&apos;s your goal?
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 24, lineHeight: 1.6 }}>
              This sets your progress targets. You can change it anytime in Settings.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
              {GOALS.map(g => {
                const active = selectedGoal === g.id
                return (
                  <button
                    key={g.id}
                    onClick={() => setSelectedGoal(g.id)}
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: 14,
                      padding: '14px 16px', borderRadius: 12, textAlign: 'left',
                      border: `1.5px solid ${active ? g.color : 'var(--border)'}`,
                      background: active ? 'var(--surface2)' : 'var(--surface)',
                      cursor: 'pointer', transition: 'all 0.15s',
                      boxShadow: active ? `0 0 0 3px ${g.color}22` : 'none',
                    }}
                  >
                    {/* Radio dot */}
                    <div style={{
                      width: 18, height: 18, borderRadius: '50%', flexShrink: 0, marginTop: 2,
                      border: `2px solid ${active ? g.color : 'var(--border)'}`,
                      background: active ? g.color : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.15s',
                    }}>
                      {active && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                        <span style={{ fontSize: 15, fontWeight: 600, color: active ? g.color : 'var(--text)' }}>
                          {g.label}
                        </span>
                        <span style={{
                          fontSize: 11, fontWeight: 500, color: active ? g.color : 'var(--text-dim)',
                          background: active ? `${g.color}18` : 'var(--surface2)',
                          padding: '2px 7px', borderRadius: 4,
                        }}>
                          {g.subtitle}
                        </span>
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0, lineHeight: 1.5 }}>
                        {g.description}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0', lineHeight: 1 }}>
                        {g.difficulty} · Accuracy threshold: {
                          g.id === 'pass' ? '65%' : g.id === 'b' ? '75%' : g.id === 'a' ? '85%' : '90%+'
                        }
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>

            {error && <ErrorBox message={error} />}

            <button
              onClick={handleStep2}
              disabled={!selectedGoal || loading}
              className="btn-caramel"
              style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: 14, opacity: selectedGoal ? 1 : 0.5 }}
            >
              {loading ? 'Saving…' : 'Go to Dashboard →'}
            </button>

            <button
              onClick={() => router.push('/dashboard')}
              style={{
                width: '100%', marginTop: 10, padding: '10px', fontSize: 13,
                background: 'none', border: 'none', color: 'var(--text-dim)',
                cursor: 'pointer', textDecoration: 'underline',
              }}
            >
              Skip for now
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div style={{
      marginBottom: 16, padding: '10px 14px', borderRadius: 8,
      border: '1px solid rgba(193,68,14,0.25)', background: 'var(--terra-dim)',
      fontSize: 13, color: 'var(--terracotta)',
    }}>
      {message}
    </div>
  )
}
