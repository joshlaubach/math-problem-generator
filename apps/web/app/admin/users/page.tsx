'use client'

import { useAuth } from '@clerk/nextjs'
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const ROLES = ['student', 'teacher', 'admin'] as const
const TIERS = ['free', 'basic', 'student', 'honors', 'classroom-student'] as const

type Role = (typeof ROLES)[number]
type Tier = (typeof TIERS)[number]

interface AdminUser {
  id: string
  email: string
  role: Role
  tier: Tier
  is_active: boolean
  clerk_user_id: string | null
  created_at: string
  daily_problems_generated: number
  display_name: string | null
}

interface UserListResponse {
  users: AdminUser[]
  total: number
  page: number
  per_page: number
}

const ROLE_COLORS: Record<Role, string> = {
  student: 'var(--text-dim)',
  teacher: '#6fa8dc',
  admin: 'var(--caramel)',
}

export default function AdminUsersPage() {
  const { getToken } = useAuth()

  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState<string | null>(null)

  const perPage = 50

  const fetchUsers = useCallback(async (pg: number, q: string, role: string) => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const params = new URLSearchParams({ page: String(pg), per_page: String(perPage) })
      if (q) params.set('search', q)
      if (role) params.set('role', role)
      const res = await fetch(`${API_BASE}/admin/users?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      const data: UserListResponse = await res.json()
      setUsers(data.users)
      setTotal(data.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    fetchUsers(page, search, roleFilter)
  }, [page, fetchUsers])  // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    fetchUsers(1, search, roleFilter)
  }

  async function patchUser(userId: string, body: object) {
    setUpdating(userId)
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error((data as { detail?: string }).detail ?? res.statusText)
      }
      const updated: AdminUser = await res.json()
      setUsers(prev => prev.map(u => u.id === userId ? updated : u))
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setUpdating(null)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 4 }}>
          <Link href="/admin/users" style={{ fontSize: 12, color: 'var(--caramel)', textDecoration: 'none', fontWeight: 600 }}>
            Users
          </Link>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Flagged · Analytics · Quotas</span>
        </div>
        <h1 style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
          User Management
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>
          {total} user{total !== 1 ? 's' : ''} total
        </p>
      </div>

      {/* Search + filter bar */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by email…"
          style={{
            flex: 1, padding: '7px 12px', borderRadius: 6,
            border: '1px solid var(--border)', background: 'var(--surface3)',
            color: 'var(--text)', fontSize: 13, outline: 'none',
          }}
        />
        <select
          value={roleFilter}
          onChange={e => { setRoleFilter(e.target.value); setPage(1); fetchUsers(1, search, e.target.value) }}
          style={{
            padding: '7px 10px', borderRadius: 6,
            border: '1px solid var(--border)', background: 'var(--surface3)',
            color: 'var(--text)', fontSize: 13, cursor: 'pointer',
          }}
        >
          <option value="">All roles</option>
          {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <button
          type="submit"
          style={{
            padding: '7px 16px', borderRadius: 6,
            background: 'var(--caramel)', color: '#fff',
            border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          Search
        </button>
      </form>

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
              {['Email', 'Role', 'Tier', 'Status', 'Problems today', 'Actions'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Loading…
                </td>
              </tr>
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No users found.
                </td>
              </tr>
            )}
            {!loading && users.map((user, i) => {
              const isUpdating = updating === user.id
              const rowBg = i % 2 === 0 ? 'transparent' : 'var(--surface3)'
              return (
                <tr key={user.id} style={{ background: rowBg, borderBottom: '1px solid var(--border)', opacity: isUpdating ? 0.6 : 1 }}>
                  {/* Email */}
                  <td style={{ padding: '10px 14px', color: 'var(--text)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <div style={{ fontWeight: 500 }}>{user.display_name ?? user.email.split('@')[0]}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{user.email}</div>
                  </td>

                  {/* Role */}
                  <td style={{ padding: '10px 14px' }}>
                    <select
                      value={user.role}
                      disabled={isUpdating}
                      onChange={e => patchUser(user.id, { role: e.target.value })}
                      style={{
                        padding: '4px 8px', borderRadius: 4, fontSize: 12,
                        border: '1px solid var(--border)', background: 'var(--surface3)',
                        color: ROLE_COLORS[user.role as Role] ?? 'var(--text)',
                        fontWeight: 600, cursor: 'pointer',
                      }}
                    >
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>

                  {/* Tier */}
                  <td style={{ padding: '10px 14px' }}>
                    <select
                      value={user.tier}
                      disabled={isUpdating}
                      onChange={e => patchUser(user.id, { tier: e.target.value })}
                      style={{
                        padding: '4px 8px', borderRadius: 4, fontSize: 12,
                        border: '1px solid var(--border)', background: 'var(--surface3)',
                        color: 'var(--text)', cursor: 'pointer',
                      }}
                    >
                      {TIERS.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>

                  {/* Active status */}
                  <td style={{ padding: '10px 14px' }}>
                    <button
                      disabled={isUpdating}
                      onClick={() => patchUser(user.id, { is_active: !user.is_active })}
                      style={{
                        padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        cursor: 'pointer', border: 'none',
                        background: user.is_active ? '#dcfce7' : '#fee2e2',
                        color: user.is_active ? '#166534' : '#991b1b',
                      }}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>

                  {/* Problems today */}
                  <td style={{ padding: '10px 14px', color: 'var(--text-dim)', textAlign: 'center' }}>
                    {user.daily_problems_generated}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '10px 14px' }}>
                    <button
                      disabled={isUpdating || user.daily_problems_generated === 0}
                      onClick={() => patchUser(user.id, { reset_quota: true })}
                      title="Reset daily problem quota to 0"
                      style={{
                        padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        cursor: user.daily_problems_generated === 0 ? 'default' : 'pointer',
                        border: '1px solid var(--border)',
                        background: 'transparent',
                        color: user.daily_problems_generated === 0 ? 'var(--text-muted)' : 'var(--caramel)',
                      }}
                    >
                      Reset quota
                    </button>
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
