'use client'

import { useEffect, useState } from 'react'

export default function ExamLayout({ children }: { children: React.ReactNode }) {
  const [tooNarrow, setTooNarrow] = useState(false)

  useEffect(() => {
    function check() { setTooNarrow(window.innerWidth < 768) }
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  if (tooNarrow) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg)', padding: '32px 24px', textAlign: 'center',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12, background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24, color: '#fff', marginBottom: 24,
        }}>
          ✦
        </div>
        <h2 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 12,
        }}>
          Exams require a tablet or laptop
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, maxWidth: 320 }}>
          The exam interface needs more screen space than a phone can provide. Please open Gradient on a tablet or computer to take an exam.
        </p>
      </div>
    )
  }

  return <>{children}</>
}
