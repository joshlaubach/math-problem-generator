'use client'
import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
// Clerk optional — whiteboard is accessible without sign-in (saves to local storage)
function useOptionalUser() {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useUser } = require('@clerk/nextjs')
    return useUser()
  } catch { return { user: null } }
}

const MathWhiteboard = dynamic(
  () => import('@/components/MathWhiteboard').then(m => m.MathWhiteboard),
  { ssr: false, loading: () => <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#8b949e', fontSize: 14 }}>Loading whiteboard…</div> },
)

export default function WhiteboardPage() {
  const { user } = useOptionalUser()
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const get = () =>
      document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
    setTheme(get())
    const obs = new MutationObserver(() => setTheme(get()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  return (
    <div style={{ width: '100%', height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Minimal header */}
      <div style={{
        height: 44, flexShrink: 0,
        display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12,
        background: theme === 'dark' ? '#161b22' : '#f6f7fb',
        borderBottom: `1px solid ${theme === 'dark' ? '#30363d' : '#dce0ee'}`,
      }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: theme === 'dark' ? '#e6edf3' : '#0f1623' }}>
          Math Whiteboard
        </span>
        <a href="/dashboard" style={{ fontSize: 12, color: theme === 'dark' ? '#8b949e' : '#4a5472', textDecoration: 'none', marginLeft: 'auto' }}>
          ← Dashboard
        </a>
      </div>
      {/* Full-height whiteboard */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <MathWhiteboard
          mode="full"
          theme={theme}
          userId={user?.id}
        />
      </div>
    </div>
  )
}
