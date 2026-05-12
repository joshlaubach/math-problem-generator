'use client'

import { useAuth } from '@clerk/nextjs'
import { useCallback, useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface DailyCount {
  date: string
  count: number
}

interface TopicStat {
  topic_id: string
  attempts: number
  correct: number
  correct_rate: number
}

interface AnalyticsOverview {
  cached_at: string
  cache_ttl_seconds: number
  total_users: number
  active_users: number
  new_users_7d: number
  users_by_role: Record<string, number>
  users_by_tier: Record<string, number>
  total_problems: number
  unresolved_flags: number
  total_attempts: number
  correct_attempts: number
  attempts_today: number
  correct_rate: number
  top_topics: TopicStat[]
  daily_problems_7d: DailyCount[]
  daily_attempts_7d: DailyCount[]
}

// ── Stat card ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}) {
  return (
    <div style={{
      background: 'var(--surface2)',
      border: `1px solid ${accent ? 'rgba(196,151,106,0.35)' : 'var(--border)'}`,
      borderRadius: 10,
      padding: '16px 18px',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: accent ? 'var(--caramel)' : 'var(--text)', lineHeight: 1.1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>
      )}
    </div>
  )
}

// ── Mini bar chart ─────────────────────────────────────────────────────────────

function BarChart({ data, color = 'var(--caramel)' }: { data: DailyCount[]; color?: string }) {
  if (!data.length) {
    return (
      <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
        No data for last 7 days
      </div>
    )
  }

  // Fill in missing dates so the chart always shows 7 bars
  const filled: DailyCount[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setUTCDate(d.getUTCDate() - i)
    const key = d.toISOString().slice(0, 10)
    const found = data.find(x => x.date === key)
    filled.push({ date: key, count: found?.count ?? 0 })
  }

  const max = Math.max(...filled.map(d => d.count), 1)

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 5, height: 80, paddingBottom: 18 }}>
      {filled.map(d => (
        <div key={d.date} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, height: '100%', justifyContent: 'flex-end' }}>
          <div
            title={`${d.date}: ${d.count}`}
            style={{
              width: '100%',
              height: `${Math.max((d.count / max) * 100, d.count > 0 ? 6 : 2)}%`,
              background: d.count > 0 ? color : 'var(--border)',
              borderRadius: '3px 3px 0 0',
              transition: 'height 0.3s ease',
            }}
          />
          <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4, whiteSpace: 'nowrap' }}>
            {d.date.slice(5).replace('-', '/')}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Breakdown table ────────────────────────────────────────────────────────────

function BreakdownTable({ title, rows, total }: { title: string; rows: [string, number][]; total: number }) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '10px 14px', background: 'var(--surface3)', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 600, color: 'var(--text-dim)' }}>
        {title}
      </div>
      {rows.length === 0 ? (
        <div style={{ padding: '16px 14px', fontSize: 12, color: 'var(--text-muted)' }}>No data</div>
      ) : (
        rows.map(([label, count]) => {
          const pct = total > 0 ? Math.round((count / total) * 100) : 0
          return (
            <div key={label} style={{ padding: '8px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 12, color: 'var(--text)', width: 120, flexShrink: 0 }}>{label}</div>
              <div style={{ flex: 1, height: 6, background: 'var(--surface3)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--caramel)', borderRadius: 3, transition: 'width 0.4s ease' }} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', width: 52, textAlign: 'right', flexShrink: 0 }}>
                {count} <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>({pct}%)</span>
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function AdminAnalyticsPage() {
  const { getToken } = useAuth()
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async (bust = false) => {
    bust ? setRefreshing(true) : setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const url = `${API_BASE}/admin/analytics/overview${bust ? '?bust=true' : ''}`
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? res.statusText)
      }
      setData(await res.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [getToken])

  useEffect(() => { fetchData() }, [fetchData])

  const cacheAgeMinutes = data
    ? Math.floor((Date.now() - new Date(data.cached_at).getTime()) / 60000)
    : 0

  const roleRows = data
    ? Object.entries(data.users_by_role).sort((a, b) => b[1] - a[1])
    : []
  const tierRows = data
    ? Object.entries(data.users_by_tier).sort((a, b) => b[1] - a[1])
    : []

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 26, fontWeight: 600, color: 'var(--text)', margin: 0 }}>
            Analytics
          </h1>
          {data && (
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              Cached {cacheAgeMinutes === 0 ? 'just now' : `${cacheAgeMinutes}m ago`}
              {' · '}refreshes every {data.cache_ttl_seconds / 60}m
            </p>
          )}
        </div>
        <button
          disabled={refreshing || loading}
          onClick={() => fetchData(true)}
          style={{
            padding: '7px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            cursor: refreshing || loading ? 'default' : 'pointer',
            border: '1px solid var(--border)',
            background: 'transparent',
            color: refreshing ? 'var(--text-muted)' : 'var(--caramel)',
            opacity: refreshing ? 0.6 : 1,
          }}
        >
          {refreshing ? 'Refreshing…' : '↺ Refresh'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 14px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 6, color: '#991b1b', fontSize: 13, marginBottom: 20 }}>
          {error}
        </div>
      )}

      {loading && !data && (
        <div style={{ padding: '48px 14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
          Loading analytics…
        </div>
      )}

      {data && (
        <>
          {/* ── Stat cards ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
            <StatCard label="Total Users" value={data.total_users.toLocaleString()} sub={`${data.active_users.toLocaleString()} active`} />
            <StatCard label="New Users (7d)" value={`+${data.new_users_7d}`} accent />
            <StatCard label="Total Problems" value={data.total_problems.toLocaleString()} />
            <StatCard label="Unresolved Flags" value={data.unresolved_flags} accent={data.unresolved_flags > 0} />
            <StatCard label="Total Attempts" value={data.total_attempts.toLocaleString()} />
            <StatCard label="Today's Attempts" value={data.attempts_today.toLocaleString()} accent />
            <StatCard
              label="Correct Rate"
              value={`${(data.correct_rate * 100).toFixed(1)}%`}
              sub={`${data.correct_attempts.toLocaleString()} of ${data.total_attempts.toLocaleString()}`}
            />
            <StatCard
              label="Inactive Users"
              value={(data.total_users - data.active_users).toLocaleString()}
              sub={`${data.total_users > 0 ? Math.round(((data.total_users - data.active_users) / data.total_users) * 100) : 0}% of total`}
            />
          </div>

          {/* ── Charts row ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            {/* Daily problems */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 10 }}>
                Problems Generated — last 7 days
              </div>
              <BarChart data={data.daily_problems_7d} />
            </div>
            {/* Daily attempts */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 10 }}>
                Attempts — last 7 days
              </div>
              <BarChart data={data.daily_attempts_7d} color="#6fa8dc" />
            </div>
          </div>

          {/* ── Breakdown tables ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            <BreakdownTable title="Users by Role" rows={roleRows} total={data.total_users} />
            <BreakdownTable title="Users by Tier" rows={tierRows} total={data.total_users} />
          </div>

          {/* ── Top topics ── */}
          {data.top_topics.length > 0 && (
            <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', background: 'var(--surface3)', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 600, color: 'var(--text-dim)' }}>
                Top Topics by Attempt Volume
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--surface3)', borderBottom: '1px solid var(--border)' }}>
                    {['#', 'Topic', 'Attempts', 'Correct', 'Correct Rate'].map(h => (
                      <th key={h} style={{ padding: '8px 14px', textAlign: h === '#' || h === 'Attempts' || h === 'Correct' || h === 'Correct Rate' ? 'right' : 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.top_topics.map((t, i) => (
                    <tr key={t.topic_id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 ? 'var(--surface3)' : 'transparent' }}>
                      <td style={{ padding: '8px 14px', color: 'var(--text-muted)', fontSize: 11, textAlign: 'right', width: 32 }}>{i + 1}</td>
                      <td style={{ padding: '8px 14px', color: 'var(--text)', fontFamily: 'monospace', fontSize: 12 }}>{t.topic_id}</td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-dim)', textAlign: 'right' }}>{t.attempts.toLocaleString()}</td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-dim)', textAlign: 'right' }}>{t.correct.toLocaleString()}</td>
                      <td style={{ padding: '8px 14px', textAlign: 'right' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                          background: t.correct_rate >= 0.7 ? '#dcfce7' : t.correct_rate >= 0.4 ? '#fef9c3' : '#fee2e2',
                          color: t.correct_rate >= 0.7 ? '#166534' : t.correct_rate >= 0.4 ? '#854d0e' : '#991b1b',
                        }}>
                          {(t.correct_rate * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.top_topics.length === 0 && (
            <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No attempt data yet — top topics will appear once students start practicing.
            </div>
          )}
        </>
      )}
    </div>
  )
}
