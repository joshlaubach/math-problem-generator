'use client'

import { useUser, useAuth } from '@clerk/nextjs'
import Link from 'next/link'
import { useEffect, useState, useRef } from 'react'
import { api, LegacyTopicMetadata } from '@/lib/api-client'
import { courseIcon } from '@/lib/course-icons'

const GOAL_LABELS: Record<string, string> = {
  pass: 'Passing',
  b: 'Solid B',
  a: 'Strong A',
  mastery: 'Mastery',
}

interface ProgressData {
  goal: string
  threshold: { accuracy: number; min_difficulty: number }
  summary: { topics_attempted: number; topics_complete: number; topics_needing_review: number }
  topics: { topic_id: string; total_attempts: number; accuracy: number; complete: boolean; needs_review: boolean }[]
  session_credits: { available: number | null; expiring_soon: number; next_expiry: string | null }
  streak?: { current: number; longest: number; active_today: boolean }
}

// Pretty-print a topic_id when we have no human name for it yet.
function prettifyTopicId(id: string): string {
  return id.replace(/^[a-z0-9]+_/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

interface QuotaData {
  tier: string
  resets_at: string
  problems: { used: number; limit: number; allowed: boolean }
}

// ── Course config ─────────────────────────────────────────────────────────────
const LEVELS = [
  { label: 'Algebra',          ids: ['prealgebra', 'algebra_1', 'geometry', 'algebra_2', 'precalculus'] },
  { label: 'Calculus',         ids: ['calculus_1', 'calculus_2', 'calculus_3', 'differential_equations'] },
  { label: 'Statistics',       ids: ['intro_prob_stats', 'probability', 'mathematical_statistics'] },
  { label: 'Pure Mathematics', ids: ['linear_algebra', 'discrete_math', 'proofs', 'contest_math'] },
]


function deriveCourses(topics: LegacyTopicMetadata[]) {
  const map = new Map<string, { id: string; name: string; topicCount: number }>()
  for (const t of topics) {
    if (!map.has(t.course_id)) map.set(t.course_id, { id: t.course_id, name: t.course_name, topicCount: 0 })
    map.get(t.course_id)!.topicCount++
  }
  return map
}

// ── Animated counter ──────────────────────────────────────────────────────────
function AnimatedStat({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [value, setValue] = useState(0)
  const fromRef = useRef(0)

  // Re-animate whenever the target changes — the real values arrive after the
  // async progress fetch, so a one-shot animation would freeze on the initial 0.
  useEffect(() => {
    const from = fromRef.current
    const duration = 900
    const start = performance.now()
    let raf = 0
    function easeOut(t: number) { return 1 - Math.pow(1 - t, 3) }
    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1)
      setValue(Math.round(from + (target - from) * easeOut(progress)))
      if (progress < 1) raf = requestAnimationFrame(tick)
      else fromRef.current = target
    }
    const timeout = setTimeout(() => { raf = requestAnimationFrame(tick) }, 350)
    return () => { clearTimeout(timeout); cancelAnimationFrame(raf) }
  }, [target])

  return <>{value}{suffix}</>
}

// ── Progress ring ─────────────────────────────────────────────────────────────
function ProgressRing({ pct, color, label, sub }: { pct: number; color: string; label: string; sub: string }) {
  const r = 26
  const c = 2 * Math.PI * r
  const offset = c * (1 - pct / 100)

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <div style={{ position: 'relative', width: 60, height: 60, flexShrink: 0 }}>
        <svg width="60" height="60" viewBox="0 0 60 60" style={{ transform: 'rotate(-90deg)' }}>
          <circle fill="none" stroke="var(--border2)" strokeWidth="5" cx="30" cy="30" r={r} />
          <circle
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            cx="30" cy="30" r={r}
            strokeDasharray={c}
            strokeDashoffset={c}
            style={{
              strokeDashoffset: offset,
              transition: 'stroke-dashoffset 1.4s cubic-bezier(0.16,1,0.3,1)',
            }}
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 13, fontWeight: 600, color,
        }}>
          {pct}%
        </div>
      </div>
      <div>
        <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
      </div>
    </div>
  )
}

// ── Streak banner ─────────────────────────────────────────────────────────────
function StreakBanner({ streak }: { streak: { current: number; longest: number; active_today: boolean } }) {
  const { current, longest, active_today } = streak
  const hasStreak = current > 0

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      padding: '16px 20px', borderRadius: 14, marginBottom: 24,
      border: '1px solid var(--border)',
      background: hasStreak
        ? 'linear-gradient(120deg, var(--caramel-dim), var(--surface2))'
        : 'var(--surface2)',
    }}>
      <div style={{
        fontSize: 30, lineHeight: 1, flexShrink: 0,
        filter: hasStreak ? 'none' : 'grayscale(1) opacity(0.5)',
      }} aria-hidden>
        🔥
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 18, fontWeight: 600, color: 'var(--text)', lineHeight: 1.2,
        }}>
          {hasStreak
            ? `${current}-day streak`
            : 'Start a streak today'}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 2 }}>
          {!hasStreak
            ? 'Solve a problem today to begin your streak.'
            : active_today
              ? `Nice — you're in today. ${longest > current ? `Best: ${longest} days.` : 'This is your best streak yet!'}`
              : 'Practice today to keep it alive.'}
        </div>
      </div>
      {hasStreak && !active_today && (
        <Link href="/catalog" className="btn-caramel" style={{ textDecoration: 'none', flexShrink: 0, padding: '8px 16px', fontSize: 13 }}>
          Practice →
        </Link>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user, isLoaded } = useUser()
  const { getToken } = useAuth()
  const [topics, setTopics] = useState<LegacyTopicMetadata[]>([])
  const [progress, setProgress] = useState<ProgressData | null>(null)
  const [quota, setQuota] = useState<QuotaData | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  useEffect(() => {
    api.getTopicsLegacy().then(setTopics).catch(() => {})
  }, [])

  useEffect(() => {
    getToken().then(token => {
      if (!token) return
      const headers = { Authorization: `Bearer ${token}` }
      Promise.all([
        fetch(`${apiBase}/me/progress`, { headers }).then(r => r.json()).catch(() => null),
        fetch(`${apiBase}/me/quota`, { headers }).then(r => r.json()).catch(() => null),
      ]).then(([prog, quot]) => {
        if (prog && !prog.detail) setProgress(prog as ProgressData)
        if (quot && !quot.detail) setQuota(quot as QuotaData)
      })
    })
  }, [getToken, apiBase])

  const courseMap = deriveCourses(topics)
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const firstName = isLoaded ? (user?.firstName ?? 'there') : '…'

  const totalAttempts = progress?.summary.topics_attempted ?? 0
  const totalComplete = progress?.summary.topics_complete ?? 0
  const accuracyPct = progress && totalAttempts > 0
    ? Math.round(
        (progress.topics.reduce((sum, t) => sum + t.accuracy * t.total_attempts, 0) /
         progress.topics.reduce((sum, t) => sum + t.total_attempts, 0)) * 100
      )
    : null
  const problemsUsed = quota?.problems.used ?? null
  const goalLabel = GOAL_LABELS[progress?.goal ?? ''] ?? null
  const topicName = (id: string) => topics.find(t => t.topic_id === id)?.topic_name ?? prettifyTopicId(id)

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <span className="current">Dashboard</span>
        </nav>
      </div>

      <div className="page-content">

        {/* Header */}
        <h1 className="display-heading" style={{ marginBottom: 6 }}>
          {greeting},{' '}
          <em>{firstName}</em>
        </h1>
        <p className="page-subtitle">
          {quota
            ? `${quota.problems.used} problem${quota.problems.used !== 1 ? 's' : ''} solved this month · resets ${quota.resets_at}`
            : 'Track your progress across all courses.'}
        </p>

        {/* Streak */}
        {progress?.streak && <StreakBanner streak={progress.streak} />}

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 40 }}>
          {[
            {
              label: 'Topics Attempted',
              target: totalAttempts,
              suffix: '',
              stagger: '0.2s',
              fallback: '–',
            },
            {
              label: 'Topics Complete',
              target: totalComplete,
              suffix: '',
              stagger: '0.28s',
              fallback: '–',
            },
            {
              label: 'Accuracy',
              target: accuracyPct ?? 0,
              suffix: '%',
              stagger: '0.36s',
              fallback: '–',
            },
          ].map(s => (
            <div key={s.label} className="stat-card" style={{ ['--stagger' as string]: s.stagger }}>
              <div className="stat-value">
                {s.target === 0 && totalAttempts === 0 && s.label !== 'Topics Attempted'
                  ? s.fallback
                  : <AnimatedStat target={s.target} suffix={s.suffix} />
                }
              </div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Goal + credit banner */}
        {(goalLabel || (progress?.session_credits?.available !== null && (progress?.session_credits?.available ?? 0) >= 0)) && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 18px', borderRadius: 12,
            border: '1px solid var(--border)', background: 'var(--surface2)',
            marginBottom: 32, gap: 12, flexWrap: 'wrap',
          }}>
            {goalLabel && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Goal:</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--caramel)' }}>{goalLabel}</span>
                {progress && (
                  <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                    · {Math.round(progress.threshold.accuracy * 100)}%+ accuracy at diff {progress.threshold.min_difficulty}+
                  </span>
                )}
              </div>
            )}
            {progress?.session_credits?.available !== null && (
              <div style={{ fontSize: 13, color: 'var(--text-dim)', display: 'flex', gap: 6 }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>
                  {progress?.session_credits?.available ?? 0}
                </span>
                tutor session{(progress?.session_credits?.available ?? 0) !== 1 ? 's' : ''} available
                {(progress?.session_credits?.expiring_soon ?? 0) > 0 && (
                  <span style={{ color: 'var(--terracotta)' }}>
                    · {progress?.session_credits?.expiring_soon} expiring soon
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Progress rings — topics needing review */}
        {progress && progress.topics.filter(t => t.needs_review).length > 0 && (
          <div style={{ marginBottom: 40 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 12, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Needs Review
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {progress.topics.filter(t => t.needs_review).slice(0, 4).map((t, i) => (
                <div key={t.topic_id} className="warm-card"
                  style={{ padding: '16px 20px', cursor: 'default', animation: `cardIn 0.5s ${0.3 + i * 0.1}s both cubic-bezier(0.16,1,0.3,1)` }}>
                  <ProgressRing
                    pct={Math.round(t.accuracy * 100)}
                    color="var(--terracotta)"
                    label={topicName(t.topic_id)}
                    sub={`${t.total_attempts} attempts · ${Math.round(t.accuracy * 100)}% accuracy`}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Problems quota bar */}
        {quota && (
          <div style={{ marginBottom: 32 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
              <span>Problems this month</span>
              <span>{quota.problems.used} / {quota.problems.limit}</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(100, (quota.problems.used / quota.problems.limit) * 100)}%`,
                background: quota.problems.used / quota.problems.limit > 0.8 ? 'var(--terracotta)' : 'var(--caramel)',
                borderRadius: 3, transition: 'width 1s ease',
              }} />
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              Resets {quota.resets_at}
            </div>
          </div>
        )}

        {/* API warning */}
        {topics.length === 0 && (
          <div style={{
            borderRadius: 10, border: '1px solid rgba(196,151,106,0.3)',
            background: 'var(--caramel-dim)', padding: '14px 18px',
            fontSize: 13, color: 'var(--text-dim)', marginBottom: 32,
          }}>
            Loading courses… make sure the API is running at{' '}
            <code style={{ fontFamily: 'monospace', color: 'var(--caramel)' }}>
              {process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}
            </code>
          </div>
        )}

        {/* Course sections */}
        {LEVELS.map(({ label, ids }) => {
          const courses = ids
            .map(id => courseMap.get(id))
            .filter(Boolean) as { id: string; name: string; topicCount: number }[]
          if (courses.length === 0) return null
          return (
            <div key={label} style={{ marginBottom: 36 }}>
              <h2 className="section-heading">{label}</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14 }}>
                {courses.map((c, i) => (
                  <Link
                    key={c.id}
                    href={`/catalog/${c.id}`}
                    className="course-card"
                    style={{
                      textDecoration: 'none',
                      ['--stagger' as string]: `${0.05 + i * 0.07}s`,
                      animation: `cardIn 0.5s ${0.05 + i * 0.07}s both cubic-bezier(0.16,1,0.3,1)`,
                    }}
                  >
                    <div
                      className="course-emoji"
                      dangerouslySetInnerHTML={{ __html: courseIcon(c.id) }}
                    />
                    <span className="course-tag">
                      {label === 'Algebra' ? 'ALG' : label === 'Calculus' ? 'CALC' : label === 'Statistics' ? 'STATS' : 'PURE'}
                    </span>
                    <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 16, fontWeight: 600, color: 'var(--text)', marginTop: 6, marginBottom: 4 }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 10 }}>
                      <span>{c.topicCount} topics</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )
        })}

      </div>
    </>
  )
}
