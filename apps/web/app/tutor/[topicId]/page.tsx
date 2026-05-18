'use client'

import { useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { useAuth, useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { TutorChat } from '@/components/TutorChat'
import { DifficultySelector } from '@/components/DifficultySelector'
import { TopicName, stripHonors } from '@/components/TopicName'
import type { SessionType } from '@/hooks/useTutorSession'

// ── Tutor profiles ────────────────────────────────────────────────────────────

export interface TutorProfile {
  id: string
  name: string
  tagline: string
  voiceId: string
  accentColor: string
}

export const TUTOR_PROFILES: TutorProfile[] = [
  { id: 'josh',    name: 'Josh',    tagline: 'Your personal tutor',       voiceId: 'echo',    accentColor: 'var(--caramel)' },
  { id: 'james',   name: 'James',   tagline: 'Clear & methodical',         voiceId: 'onyx',    accentColor: '#4a7fb5' },
  { id: 'isaac',   name: 'Isaac',   tagline: 'Encouraging & patient',      voiceId: 'fable',   accentColor: '#2d6a4f' },
  { id: 'robert',  name: 'Robert',  tagline: 'Rigorous & precise',         voiceId: 'alloy',   accentColor: '#6b4c9a' },
  { id: 'sarah',   name: 'Sarah',   tagline: 'Warm & Socratic',            voiceId: 'nova',    accentColor: '#c1440e' },
  { id: 'emily',   name: 'Emily',   tagline: 'Energetic & visual',         voiceId: 'shimmer', accentColor: '#a67c52' },
  { id: 'natalie', name: 'Natalie', tagline: 'Big-picture thinker',        voiceId: 'nova',    accentColor: '#357a6e' },
]

// ── Profile picker ────────────────────────────────────────────────────────────

function TutorProfilePicker({
  selected,
  onChange,
}: {
  selected: string
  onChange: (id: string) => void
}) {
  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 10 }}>
        Choose Your Tutor
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
        {TUTOR_PROFILES.map(p => {
          const isSelected = selected === p.id
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onChange(p.id)}
              style={{
                padding: '10px 8px',
                borderRadius: 10,
                border: `2px solid ${isSelected ? p.accentColor : 'var(--border)'}`,
                background: isSelected ? `${p.accentColor}15` : 'var(--surface)',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.18s ease',
                outline: 'none',
              }}
            >
              <div style={{
                width: 36, height: 36,
                borderRadius: '50%',
                background: isSelected ? p.accentColor : 'var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 6px',
                fontSize: 14, fontWeight: 700,
                color: isSelected ? '#fff' : 'var(--text-muted)',
                transition: 'all 0.18s ease',
              }}>
                {p.name[0]}
              </div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', lineHeight: 1.2 }}>{p.name}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.3 }}>{p.tagline}</div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Session credit summary ────────────────────────────────────────────────────

function CreditSummaryRow({ sessionType }: { sessionType: SessionType }) {
  const cost = sessionType === '1hr' ? '1 credit ($40 value)' : '1 credit ($40 value)'
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 14px', borderRadius: 8,
      background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.2)',
      fontSize: 13,
    }}>
      <span style={{ color: 'var(--text-dim)' }}>
        {sessionType === '1hr' ? '1-Hour' : '2-Hour'} Tutor Session
      </span>
      <span style={{ fontWeight: 700, color: 'var(--caramel)' }}>{cost}</span>
    </div>
  )
}

// ── Commitment modal ──────────────────────────────────────────────────────────

const COMMITMENT_BOXES = [
  'I understand this session will use 1 credit from my account.',
  'I have uninterrupted time available for this session.',
  'Refunds are only issued for verified technical failures — not for ending early.',
]

function CommitmentScreen({
  topicName,
  sessionType,
  tutorName,
  onStartNow,
  onScheduleLater,
  onBack,
}: {
  topicName: string
  sessionType: SessionType
  tutorName: string
  onStartNow: () => void
  onScheduleLater: () => void
  onBack: () => void
}) {
  const [checked, setChecked] = useState([false, false, false])
  const allChecked = checked.every(Boolean)

  const toggle = (i: number) =>
    setChecked(prev => prev.map((v, j) => (j === i ? !v : v)))

  return (
    <div
      className="warm-card-static"
      style={{ padding: 28, maxWidth: 520, animation: 'viewIn 0.35s cubic-bezier(0.16,1,0.3,1) both' }}
    >
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--caramel)', marginBottom: 6 }}>
          Before You Start
        </div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
          Session with {tutorName} — <TopicName name={topicName} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
          {sessionType === '1hr' ? '1-hour' : '2-hour'} session
        </div>
      </div>

      <CreditSummaryRow sessionType={sessionType} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, margin: '20px 0' }}>
        {COMMITMENT_BOXES.map((label, i) => (
          <label
            key={i}
            style={{
              display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer',
              padding: '10px 12px', borderRadius: 8,
              background: checked[i] ? 'var(--forest-dim, rgba(45,106,79,0.08))' : 'var(--surface)',
              border: `1px solid ${checked[i] ? 'rgba(45,106,79,0.3)' : 'var(--border)'}`,
              transition: 'all 0.18s ease',
            }}
          >
            <input
              type="checkbox"
              checked={checked[i]}
              onChange={() => toggle(i)}
              style={{ marginTop: 2, accentColor: 'var(--forest, #2d6a4f)', width: 16, height: 16, flexShrink: 0, cursor: 'pointer' }}
            />
            <span style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{label}</span>
          </label>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button
          type="button"
          onClick={onStartNow}
          disabled={!allChecked}
          className="btn-caramel"
          style={{
            width: '100%', justifyContent: 'center', padding: '12px',
            opacity: allChecked ? 1 : 0.45,
            cursor: allChecked ? 'pointer' : 'not-allowed',
            transition: 'opacity 0.2s',
          }}
        >
          ✦ Start Now
        </button>
        <button
          type="button"
          onClick={onScheduleLater}
          disabled={!allChecked}
          className="btn-ghost"
          style={{
            width: '100%', justifyContent: 'center', padding: '10px',
            opacity: allChecked ? 1 : 0.45,
            cursor: allChecked ? 'pointer' : 'not-allowed',
          }}
        >
          Schedule for Later
        </button>
        <button
          type="button"
          onClick={onBack}
          className="btn-ghost"
          style={{ width: '100%', justifyContent: 'center', padding: '9px', opacity: 0.6, fontSize: 13 }}
        >
          ← Back
        </button>
      </div>
    </div>
  )
}

// ── Schedule Later ────────────────────────────────────────────────────────────

function ScheduleScreen({
  topicName,
  sessionType,
  tutorName,
  onConfirm,
  onBack,
}: {
  topicName: string
  sessionType: SessionType
  tutorName: string
  onConfirm: (scheduledAt: string) => void
  onBack: () => void
}) {
  const [dateValue, setDateValue] = useState('')
  const [timeValue, setTimeValue] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Min date = now + 5 min
  const minDate = new Date(Date.now() + 5 * 60 * 1000)
  const minDateStr = minDate.toISOString().slice(0, 10)
  const now = new Date()
  const minTimeStr = dateValue === minDateStr
    ? `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes() + 5).padStart(2,'0')}`
    : '00:00'

  const isValid = Boolean(dateValue && timeValue)

  const handleConfirm = async () => {
    if (!isValid) return
    setSubmitting(true)
    const scheduledAt = new Date(`${dateValue}T${timeValue}`).toISOString()
    onConfirm(scheduledAt)
  }

  return (
    <div
      className="warm-card-static"
      style={{ padding: 28, maxWidth: 440, animation: 'viewIn 0.35s cubic-bezier(0.16,1,0.3,1) both' }}
    >
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--caramel)', marginBottom: 6 }}>
          Schedule Session
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>
          {tutorName} · <TopicName name={topicName} />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 20 }}>
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6 }}>
            Date
          </label>
          <input
            type="date"
            className="warm-input"
            style={{ width: '100%' }}
            min={minDateStr}
            value={dateValue}
            onChange={e => setDateValue(e.target.value)}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6 }}>
            Time
          </label>
          <input
            type="time"
            className="warm-input"
            style={{ width: '100%' }}
            min={minTimeStr}
            value={timeValue}
            onChange={e => setTimeValue(e.target.value)}
          />
        </div>
      </div>

      <div style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.2)', fontSize: 13, color: 'var(--text-dim)', marginBottom: 16 }}>
        1 credit will be reserved now and redeemed when your session starts. You will receive a reminder email 30 minutes before your session.
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={!isValid || submitting}
          className="btn-caramel"
          style={{ width: '100%', justifyContent: 'center', padding: '12px', opacity: isValid ? 1 : 0.45 }}
        >
          {submitting ? 'Scheduling…' : 'Confirm & Reserve Credit'}
        </button>
        <button
          type="button"
          onClick={onBack}
          className="btn-ghost"
          style={{ width: '100%', justifyContent: 'center', padding: '9px', opacity: 0.6, fontSize: 13 }}
        >
          ← Back
        </button>
      </div>
    </div>
  )
}

// ── Scheduled confirmation ────────────────────────────────────────────────────

function ScheduledConfirmation({ scheduledAt, topicName, tutorName }: { scheduledAt: string; topicName: string; tutorName: string }) {
  const dt = new Date(scheduledAt)
  const formatted = dt.toLocaleString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
  return (
    <div
      className="warm-card-static"
      style={{ padding: 28, maxWidth: 440, textAlign: 'center', animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}
    >
      <div style={{ fontSize: 32, marginBottom: 12 }}>✓</div>
      <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
        Session Scheduled
      </div>
      <div style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 4 }}>
        {tutorName} · <TopicName name={topicName} />
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--caramel)', marginBottom: 20 }}>
        {formatted}
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
        A reminder email will be sent 30 minutes before your session. 1 credit has been reserved.
      </div>
      <Link href="/dashboard" className="btn-caramel" style={{ justifyContent: 'center', display: 'flex' }}>
        Back to Dashboard
      </Link>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type PageStep = 'setup' | 'commitment' | 'schedule' | 'scheduled' | 'started'

export default function TutorPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const searchParams = useSearchParams()
  const { getToken } = useAuth()
  const { user } = useUser()

  const userTier = (user?.publicMetadata?.tier as string | undefined) ?? 'free'
  const topicName = searchParams.get('name')
    ?? topicId.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  const [step, setStep] = useState<PageStep>('setup')
  const [difficulty, setDifficulty] = useState(
    Number(searchParams.get('difficulty')) || 3
  )
  const [sessionType, setSessionType] = useState<SessionType>(
    (searchParams.get('session') as SessionType) || '1hr'
  )
  const [tutorId, setTutorId] = useState('josh')
  const [scheduledAt, setScheduledAt] = useState<string | null>(null)

  const selectedTutor = TUTOR_PROFILES.find(p => p.id === tutorId) ?? TUTOR_PROFILES[0]

  const handleScheduleConfirm = async (isoDate: string) => {
    // Fire-and-forget reminder email via API; ignore errors at UI level
    try {
      const token = await getToken()
      if (token) {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001'}/email/schedule-reminder`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({
              topic_name: topicName,
              tutor_name: selectedTutor.name,
              scheduled_at: isoDate,
              session_type: sessionType,
            }),
          }
        )
      }
    } catch {
      // non-blocking
    }
    setScheduledAt(isoDate)
    setStep('scheduled')
  }

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <Link href={`/practice/${topicId}?name=${encodeURIComponent(topicName)}`}>{stripHonors(topicName)}</Link>
          <span className="sep">/</span>
          <span className="current">Tutor Session</span>
        </nav>
      </div>

      <div className="page-content" style={{ paddingBottom: 40 }}>
        {step !== 'started' && (
          <>
            <h1 className="display-heading" style={{ marginBottom: 4 }}>Tutor Session</h1>
            <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 28 }}>
              <TopicName name={topicName} />
            </p>
          </>
        )}

        {step === 'setup' && (
          <div
            className="warm-card-static"
            style={{ padding: 28, maxWidth: 580, animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}
          >
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 20 }}>
              Work through a problem with an AI tutor. The tutor uses Socratic questioning
              to guide you to the answer without giving it away.
            </p>

            <TutorProfilePicker selected={tutorId} onChange={setTutorId} />

            <div style={{ marginTop: 20 }}>
              <DifficultySelector value={difficulty} onChange={setDifficulty} />
            </div>

            <div style={{ display: 'flex', gap: 6, marginTop: 16 }}>
              {(['1hr', '2hr'] as SessionType[]).map(t => (
                <button
                  key={t}
                  type="button"
                  className={sessionType === t ? 'btn-caramel' : 'btn-ghost'}
                  style={{ flex: 1, justifyContent: 'center', padding: '8px', fontSize: 13 }}
                  onClick={() => setSessionType(t)}
                >
                  {t === '1hr' ? '1-Hour Session' : '2-Hour Session'}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setStep('commitment')}
              className="btn-caramel"
              style={{ marginTop: 20, width: '100%', justifyContent: 'center', padding: '12px' }}
            >
              ✦ Continue
            </button>
          </div>
        )}

        {step === 'commitment' && (
          <CommitmentScreen
            topicName={topicName}
            sessionType={sessionType}
            tutorName={selectedTutor.name}
            onStartNow={() => setStep('started')}
            onScheduleLater={() => setStep('schedule')}
            onBack={() => setStep('setup')}
          />
        )}

        {step === 'schedule' && (
          <ScheduleScreen
            topicName={topicName}
            sessionType={sessionType}
            tutorName={selectedTutor.name}
            onConfirm={handleScheduleConfirm}
            onBack={() => setStep('commitment')}
          />
        )}

        {step === 'scheduled' && scheduledAt && (
          <ScheduledConfirmation
            scheduledAt={scheduledAt}
            topicName={topicName}
            tutorName={selectedTutor.name}
          />
        )}

        {step === 'started' && (
          <div style={{ maxWidth: 720, animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}>
            <TutorChat
              topicId={topicId}
              difficulty={difficulty}
              sessionType={sessionType}
              getToken={getToken}
              userTier={userTier}
              tutorName={selectedTutor.name}
              tutorVoiceId={selectedTutor.voiceId}
            />
          </div>
        )}
      </div>
    </>
  )
}
