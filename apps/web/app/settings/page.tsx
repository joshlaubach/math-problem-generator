'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@clerk/nextjs'
import Link from 'next/link'

type Goal = 'pass' | 'b' | 'a' | 'mastery'

const GOALS = [
  {
    id: 'pass' as Goal,
    label: 'Just Pass',
    subtitle: 'C / D → C',
    description: 'Focused, practical practice at foundational difficulty levels.',
    threshold: '65% accuracy · Difficulty 2–3',
    color: 'var(--text-dim)',
  },
  {
    id: 'b' as Goal,
    label: 'Solid B',
    subtitle: 'B− / C → B',
    description: 'Understand the material well enough to do well on most assessments.',
    threshold: '75% accuracy · Difficulty 3–4',
    color: 'var(--caramel)',
  },
  {
    id: 'a' as Goal,
    label: 'Strong A',
    subtitle: 'B+ → A',
    description: 'Excel with harder problems and tighter accuracy requirements.',
    threshold: '85% accuracy · Difficulty 4–5',
    color: 'var(--forest)',
  },
  {
    id: 'mastery' as Goal,
    label: 'Mastery',
    subtitle: 'A → A+',
    description: 'Truly master every concept. Full difficulty range, highest accuracy bar.',
    threshold: '90%+ accuracy · Difficulty 5–6',
    color: 'var(--terracotta)',
  },
]

export default function SettingsPage() {
  const { getToken } = useAuth()
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  // ── Goal state ────────────────────────────────────────────────────────────
  const [currentGoal, setCurrentGoal] = useState<Goal | null>(null)
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null)
  const [goalLoading, setGoalLoading] = useState(false)
  const [goalSaved, setGoalSaved] = useState(false)
  const [goalError, setGoalError] = useState<string | null>(null)

  // ── Parent linking state ──────────────────────────────────────────────────
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [redeemCode, setRedeemCode] = useState('')
  const [redeemLoading, setRedeemLoading] = useState(false)
  const [redeemResult, setRedeemResult] = useState<string | null>(null)
  const [redeemError, setRedeemError] = useState<string | null>(null)
  const [linkedStudents, setLinkedStudents] = useState<{student_id: string; linked_at: string}[]>([])

  // ── Account deletion state ────────────────────────────────────────────────
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function deleteAccount() {
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      const token = await getToken()
      const r = await fetch(`${apiBase}/users/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        throw new Error((d as { detail?: string }).detail ?? 'Deletion failed')
      }
      window.location.href = '/'
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Deletion failed')
      setDeleteLoading(false)
    }
  }

  // Load current goal from progress endpoint
  useEffect(() => {
    getToken().then(async token => {
      if (!token) return
      try {
        const r = await fetch(`${apiBase}/me/progress`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const d = await r.json()
        if (d.goal) {
          setCurrentGoal(d.goal as Goal)
          setSelectedGoal(d.goal as Goal)
        }
      } catch {}
    })
  }, [getToken, apiBase])

  async function saveGoal() {
    if (!selectedGoal || selectedGoal === currentGoal) return
    setGoalLoading(true)
    setGoalError(null)
    setGoalSaved(false)
    try {
      const token = await getToken()
      const r = await fetch(`${apiBase}/users/me/goal`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: selectedGoal }),
      })
      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        throw new Error((d as { detail?: string }).detail ?? 'Failed to save')
      }
      setCurrentGoal(selectedGoal)
      setGoalSaved(true)
      setTimeout(() => setGoalSaved(false), 3000)
    } catch (err: unknown) {
      setGoalError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setGoalLoading(false)
    }
  }

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

        {/* ── Learning Goal ── */}
        <section style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 6,
          }}>
            Learning Goal
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 20, lineHeight: 1.6 }}>
            Sets your accuracy and difficulty targets for tracking topic completion.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {GOALS.map(g => {
              const active = selectedGoal === g.id
              const isCurrent = currentGoal === g.id
              return (
                <button
                  key={g.id}
                  onClick={() => { setSelectedGoal(g.id); setGoalSaved(false) }}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 12,
                    padding: '12px 14px', borderRadius: 10, textAlign: 'left', width: '100%',
                    border: `1.5px solid ${active ? g.color : 'var(--border)'}`,
                    background: active ? 'var(--surface2)' : 'var(--surface)',
                    cursor: 'pointer', transition: 'all 0.15s',
                    boxShadow: active ? `0 0 0 3px ${g.color}22` : 'none',
                  }}
                >
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', flexShrink: 0, marginTop: 2,
                    border: `2px solid ${active ? g.color : 'var(--border2)'}`,
                    background: active ? g.color : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.15s',
                  }}>
                    {active && <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#fff' }} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 2 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: active ? g.color : 'var(--text)' }}>
                        {g.label}
                      </span>
                      <span style={{
                        fontSize: 11, fontWeight: 500, padding: '1px 6px', borderRadius: 4,
                        color: active ? g.color : 'var(--text-muted)',
                        background: active ? `${g.color}18` : 'var(--surface2)',
                      }}>
                        {g.subtitle}
                      </span>
                      {isCurrent && !active && (
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>current</span>
                      )}
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '0 0 3px', lineHeight: 1.5 }}>
                      {g.description}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
                      {g.threshold}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={saveGoal}
              disabled={!selectedGoal || selectedGoal === currentGoal || goalLoading}
              className="btn-caramel"
              style={{
                padding: '9px 20px', fontSize: 13,
                opacity: (!selectedGoal || selectedGoal === currentGoal) ? 0.45 : 1,
              }}
            >
              {goalLoading ? 'Saving…' : 'Save Goal'}
            </button>
            {goalSaved && (
              <span style={{ fontSize: 13, color: 'var(--forest)' }}>✓ Goal updated</span>
            )}
            {goalError && (
              <span style={{ fontSize: 13, color: 'var(--terracotta)' }}>{goalError}</span>
            )}
          </div>
        </section>

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

        {/* Danger zone */}
        <section style={{
          background: 'var(--surface)', border: '1px solid var(--terracotta)',
          borderRadius: 12, padding: 20,
        }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4, color: 'var(--terracotta)' }}>
            Danger Zone
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 14 }}>
            Permanently delete your account and all associated data. This cannot be undone.
          </p>
          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              style={{
                padding: '8px 16px', background: 'transparent', border: '1px solid var(--terracotta)',
                borderRadius: 8, color: 'var(--terracotta)', fontSize: 13, fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Delete my account
            </button>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <p style={{ fontSize: 13, color: 'var(--terracotta)', fontWeight: 600, margin: 0 }}>
                Are you sure? This will permanently delete all your data.
              </p>
              {deleteError && <p style={{ fontSize: 12, color: 'var(--terracotta)', margin: 0 }}>{deleteError}</p>}
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={deleteAccount}
                  disabled={deleteLoading}
                  style={{
                    padding: '8px 16px', background: 'var(--terracotta)', border: 'none',
                    borderRadius: 8, color: '#fff', fontSize: 13, fontWeight: 600,
                    cursor: deleteLoading ? 'not-allowed' : 'pointer', opacity: deleteLoading ? 0.7 : 1,
                  }}
                >
                  {deleteLoading ? 'Deleting…' : 'Yes, delete everything'}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  style={{
                    padding: '8px 16px', background: 'transparent', border: '1px solid var(--border)',
                    borderRadius: 8, color: 'var(--text)', fontSize: 13, cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </>
  )
}
