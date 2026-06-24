'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface ReferralStats {
  code: string
  referred_count: number
  paid_referrals: number
  paid_sessions: number
  rewards_earned: number
  next_session_reward_at: number
  next_referral_reward_at: number
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div style={{
      height: 6, borderRadius: 3, background: 'var(--border)',
      overflow: 'hidden', marginTop: 8,
    }}>
      <div style={{
        height: '100%', width: `${pct}%`, borderRadius: 3,
        background: color, transition: 'width 0.4s ease',
      }} />
    </div>
  )
}

export default function ReferralPage() {
  const { getToken } = useAuth()
  const [data, setData] = useState<ReferralStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    getToken().then(token =>
      fetch(`${API_BASE}/referral/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
    ).then(r => {
      if (!r.ok) throw new Error('Failed to load referral info')
      return r.json()
    }).then(setData).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [getToken])

  function copyCode() {
    if (!data) return
    navigator.clipboard.writeText(data.code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function copyLink() {
    if (!data) return
    const url = `${window.location.origin}/sign-up?ref=${data.code}`
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 12, color: 'var(--text-muted)', fontSize: 14,
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--caramel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff' }}>✦</div>
        Loading…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--terracotta)', fontSize: 14 }}>{error ?? 'Could not load referral info.'}</div>
      </div>
    )
  }

  const sessionProgress = data.paid_sessions % 5 === 0 && data.paid_sessions > 0
    ? 5  // just hit milestone; show full bar until next cycle starts
    : data.paid_sessions % 5
  const refProgress = data.paid_referrals % 3 === 0 && data.paid_referrals > 0
    ? 3
    : data.paid_referrals % 3

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', overflowY: 'auto' }}>
      <div style={{ maxWidth: 680, margin: '0 auto', padding: '40px 24px' }}>

        {/* Breadcrumb */}
        <nav style={{ marginBottom: 32, fontSize: 13, color: 'var(--text-muted)' }}>
          <Link href="/dashboard" style={{ color: 'var(--text-dim)', textDecoration: 'none' }}>Dashboard</Link>
          <span style={{ margin: '0 8px', opacity: 0.4 }}>/</span>
          <span style={{ color: 'var(--text)' }}>Referrals</span>
        </nav>

        <h1 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 28, fontWeight: 700, color: 'var(--text)', marginBottom: 8,
        }}>
          Refer a friend
        </h1>
        <p style={{ fontSize: 15, color: 'var(--text-dim)', marginBottom: 32, lineHeight: 1.65 }}>
          Share Gradient with people you know. When 3 friends pay for their first session, you earn a free tutoring hour.
        </p>

        {/* Code card */}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: '28px 32px', marginBottom: 24,
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--caramel)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
            Your code
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <div style={{
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              fontSize: 36, fontWeight: 700, color: 'var(--text)',
              letterSpacing: '0.15em', lineHeight: 1,
            }}>
              {data.code}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={copyCode}
                style={{
                  padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                  background: copied ? 'rgba(39,174,96,0.12)' : 'var(--surface2)',
                  border: `1px solid ${copied ? 'rgba(39,174,96,0.3)' : 'var(--border)'}`,
                  color: copied ? '#27AE60' : 'var(--text-dim)',
                  cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                {copied ? 'Copied!' : 'Copy code'}
              </button>
              <button
                onClick={copyLink}
                className="btn-caramel"
                style={{ padding: '8px 16px', fontSize: 13 }}
              >
                Copy link
              </button>
            </div>
          </div>
          <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text-muted)' }}>
            Share: <span style={{ color: 'var(--text-dim)', fontFamily: 'monospace' }}>
              {typeof window !== 'undefined' ? window.location.origin : 'https://gradient.app'}/sign-up?ref={data.code}
            </span>
          </div>
        </div>

        {/* Stats row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Friends referred', value: data.referred_count },
            { label: 'Friends who paid', value: data.paid_referrals },
            { label: 'Rewards earned', value: data.rewards_earned },
          ].map(({ label, value }) => (
            <div key={label} style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 12, padding: '18px 20px',
            }}>
              <div style={{
                fontFamily: 'var(--font-fraunces), Georgia, serif',
                fontSize: 28, fontWeight: 700, color: 'var(--text)', marginBottom: 4,
              }}>
                {value}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Progress toward rewards */}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 16, padding: '24px 28px', marginBottom: 24,
        }}>
          <h2 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 17, fontWeight: 700, color: 'var(--text)', marginBottom: 20,
          }}>
            Progress toward rewards
          </h2>

          {/* Referral milestone */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
                Referral reward
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                {refProgress} / 3 paid referrals
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
              When 3 friends pay for their first session → you get a free tutoring hour
            </div>
            <ProgressBar value={refProgress} max={3} color="var(--caramel)" />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              {3 - refProgress > 0
                ? `${3 - refProgress} more paid referral${3 - refProgress !== 1 ? 's' : ''} to go`
                : 'Reward granted! Next at ' + data.next_referral_reward_at + ' paid referrals.'}
            </div>
          </div>

          {/* Session loyalty milestone */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
                Loyalty reward
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                {data.paid_sessions} / {data.next_session_reward_at} sessions
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
              Every 5 tutoring sessions you book → get the next one free
            </div>
            <ProgressBar value={sessionProgress} max={5} color="#5B8DD9" />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              {data.next_session_reward_at - data.paid_sessions > 0
                ? `${data.next_session_reward_at - data.paid_sessions} more session${data.next_session_reward_at - data.paid_sessions !== 1 ? 's' : ''} to go`
                : 'Reward granted! Keep booking sessions.'}
            </div>
          </div>
        </div>

        {/* How it works */}
        <div style={{
          background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.25)',
          borderRadius: 12, padding: '20px 24px',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--caramel)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 14 }}>
            How it works
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { n: 1, text: 'Share your code or link with a friend who could use a math tutor.' },
              { n: 2, text: 'Your friend signs up for Gradient and books their first session.' },
              { n: 3, text: 'Once 3 friends pay, you automatically receive a free 1-hour tutoring credit.' },
            ].map(({ n, text }) => (
              <div key={n} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                  background: 'var(--caramel)', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700,
                }}>
                  {n}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.55, paddingTop: 2 }}>
                  {text}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
