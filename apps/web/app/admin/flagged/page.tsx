'use client'

import { useAuth } from '@clerk/nextjs'
import { useCallback, useEffect, useState } from 'react'
import React from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface AdminFlag {
  flag_id: string
  problem_id: string
  user_id: string
  reason: string
  resolved: boolean
  created_at: string
  statement: string | null
  prompt_latex: string | null
  answer: string | null
  topic_id: string
  difficulty: number
}

interface FlagListResponse {
  flags: AdminFlag[]
  total: number
  page: number
  per_page: number
}

function truncate(s: string | null | undefined, n = 120): string {
  if (!s) return '—'
  return s.length > n ? s.slice(0, n) + '…' : s
}

export default function AdminFlaggedPage() {
  const { getToken } = useAuth()

  const [flags, setFlags] = useState<AdminFlag[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [showResolved, setShowResolved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editStatement, setEditStatement] = useState('')
  const [editAnswer, setEditAnswer] = useState('')

  const perPage = 50

  const fetchFlags = useCallback(async (pg: number, resolved: boolean) => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const params = new URLSearchParams({
        page: String(pg),
        per_page: String(perPage),
        resolved: String(resolved),
      })
      const res = await fetch(`${API_BASE}/admin/flagged?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      const data: FlagListResponse = await res.json()
      setFlags(data.flags)
      setTotal(data.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load flagged problems')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    fetchFlags(page, showResolved)
  }, [page, showResolved, fetchFlags])

  async function dismiss(flagId: string) {
    setActing(flagId)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/admin/flagged/${flagId}/dismiss`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      setFlags(prev => prev.filter(f => f.flag_id !== flagId))
      setTotal(t => t - 1)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Dismiss failed')
    } finally {
      setActing(null)
    }
  }

  async function deleteFlag(flagId: string) {
    if (!confirm('Delete this problem permanently?')) return
    setActing(flagId)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/admin/flagged/${flagId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      setFlags(prev => prev.filter(f => f.flag_id !== flagId))
      setTotal(t => t - 1)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setActing(null)
    }
  }

  function startEdit(flag: AdminFlag) {
    setEditingId(flag.flag_id)
    setEditStatement(flag.statement ?? flag.prompt_latex ?? '')
    setEditAnswer(flag.answer ?? '')
  }

  async function saveEdit(flagId: string) {
    setActing(flagId)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/admin/flagged/${flagId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ statement: editStatement || null, answer: editAnswer || null }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      setFlags(prev => prev.filter(f => f.flag_id !== flagId))
      setTotal(t => t - 1)
      setEditingId(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Edit failed')
    } finally {
      setActing(null)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
          Flagged Problems
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>
          {total} {showResolved ? 'resolved' : 'unresolved'} flag{total !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>Show:</span>
        {(['Unresolved', 'Resolved'] as const).map(label => {
          const isResolved = label === 'Resolved'
          const active = showResolved === isResolved
          return (
            <button
              key={label}
              onClick={() => { setShowResolved(isResolved); setPage(1) }}
              style={{
                padding: '5px 14px', borderRadius: 5, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', border: '1px solid var(--border)',
                background: active ? 'var(--caramel)' : 'var(--surface3)',
                color: active ? '#fff' : 'var(--text-dim)',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 14px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 6, color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Table */}
      <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--surface3)', borderBottom: '1px solid var(--border)' }}>
              {['Problem', 'Topic / Diff', 'Reason', 'Flagged', 'Actions'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Loading…
                </td>
              </tr>
            )}
            {!loading && flags.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No {showResolved ? 'resolved' : 'unresolved'} flags.
                </td>
              </tr>
            )}
            {!loading && flags.map((flag, i) => {
              const isActing = acting === flag.flag_id
              const isEditing = editingId === flag.flag_id
              const rowBg = i % 2 === 0 ? 'transparent' : 'var(--surface3)'
              const displayText = flag.statement ?? flag.prompt_latex

              return (
                <React.Fragment key={flag.flag_id}>
                  <tr style={{ background: rowBg, borderBottom: isEditing ? 'none' : '1px solid var(--border)', opacity: isActing ? 0.6 : 1 }}>
                    {/* Problem */}
                    <td style={{ padding: '10px 14px', maxWidth: 300 }}>
                      <div style={{ color: 'var(--text)', lineHeight: 1.4, wordBreak: 'break-word' }}>
                        {truncate(displayText)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        id: {flag.problem_id.slice(0, 10)}…
                      </div>
                    </td>

                    {/* Topic / difficulty */}
                    <td style={{ padding: '10px 14px', whiteSpace: 'nowrap' }}>
                      <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>{flag.topic_id}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>diff {flag.difficulty}</div>
                    </td>

                    {/* Reason */}
                    <td style={{ padding: '10px 14px', maxWidth: 220 }}>
                      <span style={{ color: 'var(--text-dim)' }}>{truncate(flag.reason, 80)}</span>
                    </td>

                    {/* Date */}
                    <td style={{ padding: '10px 14px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(flag.created_at).toLocaleDateString()}
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '10px 14px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {!showResolved && (
                          <button
                            disabled={isActing}
                            onClick={() => dismiss(flag.flag_id)}
                            style={{
                              padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                              cursor: 'pointer', border: '1px solid var(--border)',
                              background: 'transparent', color: 'var(--text-dim)',
                            }}
                          >
                            Dismiss
                          </button>
                        )}
                        <button
                          disabled={isActing}
                          onClick={() => isEditing ? setEditingId(null) : startEdit(flag)}
                          style={{
                            padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                            cursor: 'pointer', border: '1px solid var(--border)',
                            background: isEditing ? 'var(--surface3)' : 'transparent',
                            color: 'var(--caramel)',
                          }}
                        >
                          {isEditing ? 'Cancel' : 'Edit'}
                        </button>
                        <button
                          disabled={isActing}
                          onClick={() => deleteFlag(flag.flag_id)}
                          style={{
                            padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                            cursor: 'pointer', border: '1px solid #fca5a5',
                            background: 'transparent', color: '#dc2626',
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Inline edit row */}
                  {isEditing && (
                    <tr style={{ background: rowBg, borderBottom: '1px solid var(--border)' }}>
                      <td colSpan={5} style={{ padding: '12px 14px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 700 }}>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)', display: 'block', marginBottom: 4 }}>
                              Statement
                            </label>
                            <textarea
                              value={editStatement}
                              onChange={e => setEditStatement(e.target.value)}
                              rows={3}
                              style={{
                                width: '100%', padding: '8px 10px', borderRadius: 5,
                                border: '1px solid var(--border)', background: 'var(--surface3)',
                                color: 'var(--text)', fontSize: 13, resize: 'vertical', outline: 'none',
                                boxSizing: 'border-box',
                              }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)', display: 'block', marginBottom: 4 }}>
                              Answer
                            </label>
                            <input
                              value={editAnswer}
                              onChange={e => setEditAnswer(e.target.value)}
                              style={{
                                width: '100%', padding: '7px 10px', borderRadius: 5,
                                border: '1px solid var(--border)', background: 'var(--surface3)',
                                color: 'var(--text)', fontSize: 13, outline: 'none',
                                boxSizing: 'border-box',
                              }}
                            />
                          </div>
                          <div style={{ display: 'flex', gap: 8 }}>
                            <button
                              disabled={isActing}
                              onClick={() => saveEdit(flag.flag_id)}
                              style={{
                                padding: '6px 18px', borderRadius: 5, fontSize: 12, fontWeight: 600,
                                cursor: 'pointer', border: 'none',
                                background: 'var(--caramel)', color: '#fff',
                              }}
                            >
                              Save & resolve
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              style={{
                                padding: '6px 18px', borderRadius: 5, fontSize: 12, fontWeight: 600,
                                cursor: 'pointer', border: '1px solid var(--border)',
                                background: 'transparent', color: 'var(--text-dim)',
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, marginTop: 16, alignItems: 'center', justifyContent: 'flex-end' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface3)', color: 'var(--text)', fontSize: 12, cursor: page <= 1 ? 'default' : 'pointer' }}
          >
            ← Prev
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface3)', color: 'var(--text)', fontSize: 12, cursor: page >= totalPages ? 'default' : 'pointer' }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
