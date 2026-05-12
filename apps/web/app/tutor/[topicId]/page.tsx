'use client'

import { useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { useAuth, useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { TutorChat } from '@/components/TutorChat'
import { DifficultySelector } from '@/components/DifficultySelector'
import type { SessionType } from '@/hooks/useTutorSession'

export default function TutorPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const searchParams = useSearchParams()
  const { getToken } = useAuth()
  const { user } = useUser()

  const userTier = (user?.publicMetadata?.tier as string | undefined) ?? 'free'
  const topicName = searchParams.get('name')
    ?? topicId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  const [started, setStarted] = useState(false)
  const [difficulty, setDifficulty] = useState(
    Number(searchParams.get('difficulty')) || 3
  )
  const [sessionType, setSessionType] = useState<SessionType>(
    (searchParams.get('session') as SessionType) || '1hr'
  )

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <Link href={`/practice/${topicId}?name=${encodeURIComponent(topicName)}`}>{topicName}</Link>
          <span className="sep">/</span>
          <span className="current">Tutor Session</span>
        </nav>
      </div>

      <div className="page-content" style={{ paddingBottom: 40 }}>
        <h1 className="display-heading" style={{ marginBottom: 4 }}>Tutor Session</h1>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 28 }}>{topicName}</p>

        {!started ? (
          <div
            className="warm-card-static"
            style={{ padding: 28, maxWidth: 520, animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}
          >
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 20 }}>
              Work through a problem with an AI tutor. The tutor uses Socratic questioning
              to guide you to the answer without giving it away.
            </p>
            <DifficultySelector value={difficulty} onChange={setDifficulty} />
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
              onClick={() => setStarted(true)}
              className="btn-caramel"
              style={{ marginTop: 20, width: '100%', justifyContent: 'center', padding: '12px' }}
            >
              ✦ Start Tutor Session
            </button>
          </div>
        ) : (
          <div style={{ maxWidth: 720, animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}>
            <TutorChat
              topicId={topicId}
              difficulty={difficulty}
              sessionType={sessionType}
              getToken={getToken}
              userTier={userTier}
            />
          </div>
        )}
      </div>
    </>
  )
}
