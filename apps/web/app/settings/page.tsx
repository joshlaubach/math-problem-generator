'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@clerk/nextjs'
import Link from 'next/link'

export default function SettingsPage() {
  const { getToken } = useAuth()
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [redeemCode, setRedeemCode] = useState('')
  const [redeemLoading, setRedeemLoading] = useState(false)
  const [redeemResult, setRedeemResult] = useState<string | null>(null)
  const [redeemError, setRedeemError] = useState<string | null>(null)
  const [linkedStudents, setLinkedStudents] = useState<{student_id: string; linked_at: string}[]>([])

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  // Load linked students (for parents)
  useEffect(() => {
    getToken().then(async token => {
      if (!token) return
      try {
        const r = await fetch(`${apiBase}/parent/students`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        const d = await r.json()
        if (d.students) setLinkedStudents(d.students)
      } catch {}
    })
  }, [getToken, apiBase])

  async function generateLinkCode() {
    setLinkLoading(true)
    setLinkError(null)
    try {
      const token = await getToken()
      const r = await fetch(`${apiBase}/me/parent-link`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      const d = await r.json()
      if (d.link_code) setLinkCode(d.link_code)
      else setLinkError(d.detail ?? 'Failed to generate code')
    } catch {
      setLinkError('Request failed')
    } finally {
      setLinkLoading(false)
    }
  }

  async function redeemParentCode() {
    if (!redeemCode.trim()) return
    setRedeemLoading(true)
    setRedeemError(null)
    try {
      const token = await getToken()
      const r = await fetch(`${apiBase}/parent/link/${redeemCode.trim().toUpperCase()}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      const d = await r.json()
      if (d.ok) {
        setRedeemResult(`Linked to ${d.student_email}`)
        setRedeemCode('')
      } else {
        setRedeemError(d.detail ?? 'Failed to redeem code')
      }
    } catch {
      setRedeemError('Request failed')
    } finally {
      setRedeemLoading(false)
    }
  }

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span>/</span>
          <span className="current">Settings</span>
        </nav>
      </div>

      <div className="page-content" style={{ maxWidth: 560 }}>
        <h1 className="display-heading" style={{ marginBottom: 6 }}>Settings</h1>
        <p className="page-subtitle" style={{ marginBottom: 40 }}>
          Manage your account preferences and parent monitoring.
        </p>

        {/* Parent monitoring — student side */}
        <section style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 6,
          }}>
            Parent Monitoring
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 20, lineHeight: 1.6 }}>
            Generate a code to share with a parent or guardian. They&apos;ll be able to see your
            session summaries and (if you opt in per-session) conversation transcripts.
          </p>

          {linkCode ? (
            <div style={{
              padding: '20px 24px', borderRadius: 12,
              border: '1px solid rgba(196,151,106,0.4)', background: 'var(--caramel-dim)',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Share this code with your parent
              </div>
              <div style={{
                fontFamily: 'monospace', fontSize: 28, fontWeight: 700,
                color: 'var(--caramel)', letterSpacing: '0.15em',
              }}>
                {linkCode}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                They enter it at Settings → &quot;Link to a student&quot;. Code expires when used.
              </div>
              <button
                onClick={() => setLinkCode(null)}
                style={{
                  marginTop: 12, fontSize: 12, color: 'var(--text-dim)',
                  background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline',
                }}
              >
                Generate a new code
              </button>
            </div>
          ) : (
            <button
              onClick={generateLinkCode}
              disabled={linkLoading}
              className="btn-caramel"
              style={{ padding: '10px 20px' }}
            >
              {linkLoading ? 'Generating…' : 'Generate Parent Link Code'}
            </button>
          )}
          {linkError && (
            <p style={{ fontSize: 12, color: 'var(--terracotta)', marginTop: 8 }}>{linkError}</p>
          )}
        </section>

        {/* Parent side — redeem a code */}
        <section style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 6,
          }}>
            Link to a Student
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 20, lineHeight: 1.6 }}>
            If your child gave you an 8-character code, enter it here to link your accounts.
          </p>

          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              className="warm-input"
              value={redeemCode}
              onChange={e => setRedeemCode(e.target.value.toUpperCase().slice(0, 8))}
              placeholder="XXXXXXXX"
              maxLength={8}
              style={{ flex: 1, fontFamily: 'monospace', letterSpacing: '0.1em', textTransform: 'uppercase' }}
            />
            <button
              onClick={redeemParentCode}
              disabled={redeemCode.length < 6 || redeemLoading}
              className="btn-caramel"
              style={{ padding: '10px 16px', flexShrink: 0 }}
            >
              {redeemLoading ? '…' : 'Link'}
            </button>
          </div>
          {redeemResult && <p style={{ fontSize: 12, color: 'var(--forest)', marginTop: 8 }}>{redeemResult}</p>}
          {redeemError && <p style={{ fontSize: 12, color: 'var(--terracotta)', marginTop: 8 }}>{redeemError}</p>}

          {linkedStudents.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 8 }}>
                Linked students
              </div>
              {linkedStudents.map(s => (
                <div key={s.student_id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 14px', borderRadius: 8, background: 'var(--surface2)',
                  border: '1px solid var(--border)', marginBottom: 6, fontSize: 13,
                }}>
                  <span style={{ color: 'var(--text)' }}>{s.student_id.slice(0, 12)}…</span>
                  <Link
                    href={`/parent/students/${s.student_id}`}
                    style={{ fontSize: 12, color: 'var(--caramel)' }}
                  >
                    View sessions →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  )
}
