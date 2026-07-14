'use client'

/**
 * /tutor/demo — Guest demo session entry
 *
 * Collects DOB, validates age ≥ 13, creates a 30-minute guest session via
 * POST /tutor/guest-session, then redirects to the session page.
 * No account required.
 */

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

function computeAge(dob: string): number | null {
  try {
    const birth = new Date(dob)
    if (isNaN(birth.getTime())) return null
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const m = today.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
    return age
  } catch {
    return null
  }
}

export default function DemoPage() {
  const router = useRouter()
  const [dob, setDob] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const age = computeAge(dob)
  const dobValid = dob.length === 10 && age !== null && age >= 13 && age <= 120

  async function handleStart() {
    if (!dobValid) return
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/tutor/guest-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date_of_birth: dob }),
      })
      const body = await resp.json().catch(() => ({}))
      if (!resp.ok) {
        const detail = (body as { detail?: string }).detail
        throw new Error(detail ?? 'Failed to start session')
      }
      const { guest_token, session_id } = body as { guest_token: string; session_id: string }
      // Hand the token off via sessionStorage, never the URL — query strings
      // land in browser history, referrers, and server access logs.
      let storedOk = false
      try {
        sessionStorage.setItem(`guest_token:${session_id}`, guest_token)
        storedOk = sessionStorage.getItem(`guest_token:${session_id}`) === guest_token
      } catch { storedOk = false }
      router.push(storedOk
        ? `/tutor/session/${session_id}`
        : `/tutor/session/${session_id}?guest_token=${encodeURIComponent(guest_token)}`)
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
        background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)',
        padding: '40px 36px', maxWidth: 440, width: '100%',
        boxShadow: '0 4px 32px rgba(0,0,0,0.06)',
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

        <h1 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 24, fontWeight: 700, color: 'var(--text)', marginBottom: 8,
        }}>
          Try a free session
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 28, lineHeight: 1.6 }}>
          30 minutes with a real AI math tutor — no account needed. One free session per week.
        </p>

        {/* DOB */}
        <div style={{ marginBottom: 24 }}>
          <label style={{
            display: 'block', fontSize: 13, fontWeight: 500,
            color: 'var(--text-dim)', marginBottom: 6,
          }}>
            Date of birth
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6, fontWeight: 400 }}>
              (required — must be 13 or older)
            </span>
          </label>
          <input
            type="date"
            value={dob}
            onChange={e => { setDob(e.target.value); setError(null) }}
            max={new Date().toISOString().split('T')[0]}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              border: `1px solid ${dobValid ? 'rgba(196,151,106,0.4)' : 'var(--border)'}`,
              background: 'var(--surface2)', color: 'var(--text)',
              fontSize: 14, outline: 'none', boxSizing: 'border-box',
            }}
          />
          {dob && age !== null && age < 13 && (
            <p style={{ fontSize: 12, color: 'var(--terracotta)', marginTop: 4 }}>
              You must be at least 13 to start a session.
            </p>
          )}
        </div>

        {error && (
          <div style={{
            marginBottom: 16, padding: '10px 14px', borderRadius: 8,
            border: '1px solid rgba(193,68,14,0.25)', background: 'var(--terra-dim)',
            fontSize: 13, color: 'var(--terracotta)',
          }}>
            {error}
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={!dobValid || loading}
          className="btn-caramel"
          style={{
            width: '100%', justifyContent: 'center', padding: '12px',
            fontSize: 15, fontWeight: 600, opacity: dobValid ? 1 : 0.5,
          }}
        >
          {loading ? 'Starting session…' : 'Start my free session →'}
        </button>

        <p style={{
          marginTop: 20, fontSize: 12, color: 'var(--text-muted)',
          textAlign: 'center', lineHeight: 1.6,
        }}>
          Already have an account?{' '}
          <Link href="/sign-in" style={{ color: 'var(--caramel)' }}>Sign in</Link>
          {' '}to access your full sessions.
        </p>
        <p style={{
          marginTop: 8, fontSize: 11, color: 'var(--text-muted)',
          textAlign: 'center', lineHeight: 1.5,
        }}>
          By starting a session you agree to our{' '}
          <Link href="/terms" style={{ color: 'var(--caramel)' }}>Terms of Service</Link>
          {' '}and{' '}
          <Link href="/privacy" style={{ color: 'var(--caramel)' }}>Privacy Policy</Link>.
        </p>
      </div>
    </div>
  )
}
