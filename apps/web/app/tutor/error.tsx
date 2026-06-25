'use client'

import Link from 'next/link'

export default function TutorError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
      gap: '1rem',
      padding: '2rem',
    }}>
      <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Session error</h2>
      <p style={{ color: 'var(--text-dim, #666)', fontSize: '0.875rem', textAlign: 'center', maxWidth: 360 }}>
        Something went wrong with your tutor session. Your session credit has not been charged.
      </p>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          onClick={reset}
          style={{
            padding: '0.5rem 1.25rem',
            background: 'var(--caramel, #c4976a)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Try again
        </button>
        <Link href="/dashboard" style={{ color: 'var(--caramel, #c4976a)', alignSelf: 'center' }}>
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
