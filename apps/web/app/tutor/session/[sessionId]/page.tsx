'use client'

/**
 * /tutor/session/[sessionId] — general-purpose tutor session shell
 *
 * Phase 4 will build the full session UI here (65% whiteboard / 30% chat).
 * This placeholder confirms session creation and will be replaced.
 */

import { useParams } from 'next/navigation'
import Link from 'next/link'

export default function TutorSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 20,
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: 'system-ui',
      padding: 24,
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: 'var(--caramel)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 22,
      }}>
        ✦
      </div>

      <div style={{ textAlign: 'center', maxWidth: 440 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>
          Session Ready
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, margin: '0 0 24px' }}>
          Your tutoring session has been created. The full session interface
          is being built in Phase 4 — check back soon!
        </p>
        <code style={{
          display: 'block',
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          borderRadius: 8, padding: '8px 12px',
          fontSize: 11, fontFamily: 'monospace',
          color: 'var(--text-dim)', marginBottom: 24,
          wordBreak: 'break-all',
        }}>
          session_id: {sessionId}
        </code>
        <Link
          href="/tutor/new"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            color: 'var(--caramel)', fontSize: 13, textDecoration: 'none',
            fontWeight: 500,
          }}
        >
          ← Back to intake form
        </Link>
      </div>
    </div>
  )
}
