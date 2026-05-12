'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface Props { topicName: string }

export function GeneratingState({ topicName }: Props) {
  const router = useRouter()
  const [countdown, setCountdown] = useState(8)

  // Auto-reload after 8 seconds — lesson generation takes ~5s
  useEffect(() => {
    if (countdown <= 0) {
      router.refresh()
      return
    }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown, router])

  return (
    <div style={{
      padding: '32px 28px', borderRadius: 16,
      border: '1px solid var(--border)', background: 'var(--surface2)',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 24, marginBottom: 12, animation: 'spinnerSpin 1.5s linear infinite', display: 'inline-block' }}>⟳</div>
      <div style={{
        fontFamily: 'var(--font-fraunces), Georgia, serif',
        fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8,
      }}>
        Generating lesson for {topicName}
      </div>
      <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 20 }}>
        This lesson is being written now — first visitor pays the generation cost so everyone after is instant.
        Reloading in {countdown}s…
      </p>
      <button
        onClick={() => router.refresh()}
        style={{
          padding: '9px 20px', borderRadius: 8, border: '1px solid var(--border)',
          background: 'none', cursor: 'pointer', fontSize: 13, color: 'var(--text-dim)',
        }}
      >
        Reload now
      </button>
    </div>
  )
}
