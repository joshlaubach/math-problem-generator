'use client'

import { useAuth } from '@clerk/nextjs'
import { useCallback, useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface TierLimitRow {
  tier: string
  daily_limit: number | null
  monthly_limit: number | null
}

interface UserQuotaRow {
  id: string
  email: string
  display_name: string | null
  tier: string
  daily_problems_generated: number
  daily_limit_override: number | null
  effective_daily_limit: number | null
  last_reset_date: string | null
}

interface QuotasOverview {
  tier_limits: TierLimitRow[]
  users: UserQuotaRow[]
  total: number
  page: number
  per_page: number
}

const TIER_ORDER = ['free', 'basic', 'student', 'honors', 'classroom-student']

// Mirrors session_quota.py constants — shown even when the DB is unavailable
const FALLBACK_TIER_LIMITS: TierLimitRow[] = [
  { tier: 'free',               daily_limit: 3,    monthly_limit: 10  },
  { tier: 'basic',              daily_limit: 10,   monthly_limit: 30  },
  { tier: 'student',            daily_limit: null, monthly_limit: 100 },
  { tier: 'honors',             daily_limit: null, monthly_limit: 250 },
  { tier: 'classroom-student',  daily_limit: null, monthly_limit: 150 },
]

const TIER_COLORS: Record<string, string> = {
  free: 'var(--text-muted)',
  basic: '#6fa8dc',
  student: 'var(--caramel)',
  honors: '#a8d5a2',
  'classroom-student': '#c9a0dc',
}

function limitLabel(v: number | null) {
  return v === null ? '∞' : String(v)
}

function UsageBar({ used, limit }: { used: number; limit: number | null }) {
  if (limit === null) {
    return <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>unlimited</span>
  }
  const pct = Math.min((used / limit) * 100, 100)
  const color = pct >= 100 ? '#dc2626' : pct >= 80 ? '#d97706' : 'var(--caramel)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
      <div style={{ flex: 1, height: 5, background: 'var(--surface3)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600, whiteSpace: 'nowrap' }}>
        {used}/{limit}
      </span>
    </div>
  )
}

export default function AdminQuotasPage() {
  const { getToken } = useAuth()
  const [data, setData] = useState<QuotasOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [onlyActive, setOnlyActive] = useState(true)

  // Inline override editing
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState<string | null>(null)

  const perPage = 50

  const fetchData = useCallback(async (pg: number, active: boolean) => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const params = new URLSearchParams({
        page: String(pg),
        per_page: String(perPage),
        only_active: String(active),
      })
      const res = await fetch(`${API_BASE}/admin/quotas/overview?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      setData(await res.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load quotas')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => { fetchData(page, onlyActive) }, [page, onlyActive, fetchData])

  async function patchUser(userId: string, body: object) {
    setSaving(userId)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error((d as { detail?: string }).detail ?? res.statusText)
      }
      const updated = await res.json()
      setData(prev => {
        if (!prev) return prev
        return {
          ...prev,
          users: prev.users.map(u =>
            u.id === userId
              ? {
                  ...u,
                  daily_limit_override: updated.daily_limit_override ?? null,
                  effective_daily_limit: updated.daily_limit_override ?? u.effective_daily_limit,
                }
              : u
          ),
        }
      })
      setEditingId(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(null)
    }
  }

  const totalPages = data ? Math.ceil(data.total / perPage) : 0

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
          Quotas
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>
          Platform limits and per-user overrides
        </p>
      </div>

      {/* ── Tier defaults ── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Platform Defaults
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
          {(data?.tier_limits ?? FALLBACK_TIER_LIMITS).map(row => (
            <div key={row.tier} style={{
              border: '1px solid var(--border)', borderRadius: 9, padding: '12px 14px',
              borderTop: `3px solid ${TIER_COLORS[row.tier] ?? 'var(--border)'}`,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: TIER_COLORS[row.tier] ?? 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                {row.tier}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Daily</span>
                  <span style={{ fontWeight: 600, color: 'var(--text)' }}>{limitLabel(row.daily_limit)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Monthly</span>
                  <span style={{ fontWeight: 600, color: 'var(--text)' }}>{limitLabel(row.monthly_limit)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 14px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 6, color: '#991b1b', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* ── User quotas table ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          User Quotas {data && <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>({data.total})</span>}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['Active only', 'All users'] as const).map(label => {
            const isActive = label === 'Active only'
            const selected = onlyActive === isActive
            return (
              <button
                key={label}
                onClick={() => { setOnlyActive(isActive); setPage(1) }}
                style={{
                  padding: '4px 12px', borderRadius: 5, fontSize: 11, fontWeight: 600,
                  cursor: 'pointer', border: '1px solid var(--border)',
                  background: selected ? 'var(--caramel)' : 'var(--surface3)',
                  color: selected ? '#fff' : 'var(--text-dim)',
                }}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--surface3)', borderBottom: '1px solid var(--border)' }}>
              {['User', 'Tier', 'Today\'s Usage', 'Effective Limit', 'Override', 'Actions'].map(h => (
                <th key={h} style={{ padding: '9px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</td></tr>
            )}
            {!loading && data?.users.length === 0 && (
              <tr><td colSpan={6} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>
                {onlyActive ? 'No users with usage today or active overrides.' : 'No users found.'}
              </td></tr>
            )}
            {!loading && data?.users.map((u, i) => {
              const isSaving = saving === u.id
              const isEditing = editingId === u.id
              const rowBg = i % 2 === 0 ? 'transparent' : 'var(--surface3)'
              const hasOverride = u.daily_limit_override !== null

              return (
                <tr key={u.id} style={{ background: rowBg, borderBottom: '1px solid var(--border)', opacity: isSaving ? 0.6 : 1 }}>
                  {/* User */}
                  <td style={{ padding: '9px 14px' }}>
                    <div style={{ fontWeight: 500, color: 'var(--text)', fontSize: 12 }}>
                      {u.display_name ?? u.email.split('@')[0]}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.email}</div>
                  </td>

                  {/* Tier */}
                  <td style={{ padding: '9px 14px' }}>
                    <span style={{
                      padding: '2px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                      color: TIER_COLORS[u.tier] ?? 'var(--text-dim)',
                      border: `1px solid ${TIER_COLORS[u.tier] ?? 'var(--border)'}`,
                    }}>
                      {u.tier}
                    </span>
                  </td>

                  {/* Usage */}
                  <td style={{ padding: '9px 14px', minWidth: 150 }}>
                    <UsageBar used={u.daily_problems_generated} limit={u.effective_daily_limit} />
                  </td>

                  {/* Effective limit */}
                  <td style={{ padding: '9px 14px', color: 'var(--text-dim)', fontSize: 12 }}>
                    {limitLabel(u.effective_daily_limit)}
                    {hasOverride && (
                      <span style={{ fontSize: 10, color: 'var(--caramel)', marginLeft: 4, fontWeight: 600 }}>override</span>
                    )}
                  </td>

                  {/* Override value / inline edit */}
                  <td style={{ padding: '9px 14px', minWidth: 120 }}>
                    {isEditing ? (
                      <input
                        type="number"
                        min={1}
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        placeholder="e.g. 20"
                        autoFocus
                        style={{
                          width: 80, padding: '3px 7px', borderRadius: 4, fontSize: 12,
                          border: '1px solid var(--caramel)', background: 'var(--surface3)',
                          color: 'var(--text)', outline: 'none',
                        }}
                        onKeyDown={e => {
                          if (e.key === 'Enter') {
                            const v = parseInt(editValue, 10)
                            if (!isNaN(v) && v >= 1) patchUser(u.id, { daily_limit_override: v })
                          }
                          if (e.key === 'Escape') setEditingId(null)
                        }}
                      />
                    ) : (
                      <span style={{ fontSize: 12, color: hasOverride ? 'var(--caramel)' : 'var(--text-muted)' }}>
                        {hasOverride ? u.daily_limit_override : '—'}
                      </span>
                    )}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '9px 14px' }}>
                    <div style={{ display: 'flex', gap: 5 }}>
                      {isEditing ? (
                        <>
                          <button
                            disabled={isSaving}
                            onClick={() => {
                              const v = parseInt(editValue, 10)
                              if (!isNaN(v) && v >= 1) patchUser(u.id, { daily_limit_override: v })
                              else alert('Enter a number ≥ 1')
                            }}
                            style={{
                              padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                              cursor: 'pointer', border: 'none',
                              background: 'var(--caramel)', color: '#fff',
                            }}
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            style={{
                              padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                              cursor: 'pointer', border: '1px solid var(--border)',
                              background: 'transparent', color: 'var(--text-dim)',
                            }}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            disabled={isSaving}
                            onClick={() => { setEditingId(u.id); setEditValue(String(u.daily_limit_override ?? '')) }}
                            style={{
                              padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                              cursor: 'pointer', border: '1px solid var(--border)',
                              background: 'transparent', color: 'var(--caramel)',
                            }}
                          >
                            {hasOverride ? 'Edit' : 'Set limit'}
                          </button>
                          {hasOverride && (
                            <button
                              disabled={isSaving}
                              onClick={() => patchUser(u.id, { clear_limit_override: true })}
                              style={{
                                padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                                cursor: 'pointer', border: '1px solid var(--border)',
                                background: 'transparent', color: 'var(--text-muted)',
                              }}
                            >
                              Clear
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, marginTop: 16, alignItems: 'center', justifyContent: 'flex-end' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Page {page} of {totalPages}</span>
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
            style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface3)', color: 'var(--text)', fontSize: 12, cursor: page <= 1 ? 'default' : 'pointer' }}>
            ← Prev
          </button>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
            style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface3)', color: 'var(--text)', fontSize: 12, cursor: page >= totalPages ? 'default' : 'pointer' }}>
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
