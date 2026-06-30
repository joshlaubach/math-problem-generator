'use client'

export default function SessionError({ error: _error, reset }: { error: Error; reset: () => void }) {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16,
      fontFamily: 'system-ui, sans-serif', color: 'var(--text)',
      background: 'var(--bg)',
    }}>
      <p style={{ fontSize: 16, margin: 0 }}>Something went wrong.</p>
      <p style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
        Your session credit has been preserved — start a new session from your dashboard.
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <a
          href="/dashboard"
          style={{
            padding: '8px 16px', background: 'var(--caramel)', color: '#fff',
            borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 600,
          }}
        >
          Return to dashboard
        </a>
        <button
          onClick={reset}
          style={{
            padding: '8px 16px', background: 'transparent',
            border: '1px solid var(--border)', borderRadius: 8,
            fontSize: 14, cursor: 'pointer', color: 'var(--text)',
          }}
        >
          Try again
        </button>
      </div>
    </div>
  )
}
