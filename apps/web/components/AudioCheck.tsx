'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Step = 'permission' | 'listening' | 'transcribing' | 'confirming' | 'done' | 'error'

export interface AudioCheckProps {
  token: string | null
  apiBase: string
  theme?: 'light' | 'dark'
  onComplete: (result: 'passed' | 'skipped' | 'failed') => void
}

// ── Constants ─────────────────────────────────────────────────────────────────

const RECORD_SECONDS = 3

const WAVEBAR_KF = `
@keyframes waveBar {
  0%, 100% { transform: scaleY(0.35); }
  50%       { transform: scaleY(1);   }
}
`

const STEP_ORDER: Step[] = ['permission', 'listening', 'transcribing', 'confirming']

// ── Component ─────────────────────────────────────────────────────────────────

export function AudioCheck({ token, apiBase, theme = 'light', onComplete }: AudioCheckProps) {
  const [step, setStep]           = useState<Step>('permission')
  const [transcript, setTranscript] = useState('')
  const [errMsg, setErrMsg]       = useState('')
  const [countdown, setCountdown] = useState(RECORD_SECONDS)
  const abortRef = useRef(false)

  const isDark = theme === 'dark'
  const c = {
    text:    isDark ? '#F2EDE4' : '#26221D',
    dim:     isDark ? '#ADA59C' : '#5C5349',
    muted:   isDark ? '#9C9082' : '#6E6457',
    surface: isDark ? '#211D18' : '#ffffff',
    surface2:isDark ? '#2A2520' : '#F4F1EA',
    border:  isDark ? '#3D3830' : '#E7E0D6',
    gold:    isDark ? '#d29922' : '#8A6A0E',
    green:   isDark ? '#34d399' : '#1A6B45',
    red:     isDark ? '#D4634A' : '#B5451F',
  }

  const handleSkip = useCallback(() => {
    abortRef.current = true
    onComplete('skipped')
  }, [onComplete])

  // ── Main check sequence ────────────────────────────────────────────────────

  useEffect(() => {
    abortRef.current = false
    run()
    return () => { abortRef.current = true }

    async function run() {
      // 1. Request mic
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
        })
      } catch {
        setErrMsg('Microphone not found — check your browser permissions.')
        setStep('error')
        return
      }
      if (abortRef.current) { stream.getTracks().forEach(t => t.stop()); return }

      setStep('listening')
      setCountdown(RECORD_SECONDS)

      // Countdown display
      const iv = setInterval(() => setCountdown(p => Math.max(0, p - 1)), 1000)

      // 2. Record RECORD_SECONDS of audio
      const chunks: Blob[] = []
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
      recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data) }

      await new Promise<void>(resolve => {
        recorder.onstop = () => resolve()
        recorder.start(100)
        setTimeout(() => { if (recorder.state !== 'inactive') recorder.stop() }, RECORD_SECONDS * 1000)
      })
      clearInterval(iv)
      stream.getTracks().forEach(t => t.stop())
      if (abortRef.current) return

      setStep('transcribing')

      // 3. POST to /tutor/transcribe
      let heard = ''
      if (token && chunks.length > 0) {
        try {
          const blob = new Blob(chunks, { type: mime || 'audio/webm' })
          const form = new FormData()
          form.append('file', blob, 'audio-check.webm')
          const resp = await fetch(`${apiBase}/tutor/transcribe`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: form,
          })
          if (resp.ok) heard = ((await resp.json() as { text?: string }).text ?? '').trim()
        } catch { /* non-fatal — mic still works even if STT unavailable */ }
      }
      if (abortRef.current) return

      setTranscript(heard)
      setStep('confirming')

      // 4. TTS confirmation so student knows speakers work too
      if (token) {
        try {
          const confirmText = heard
            ? `Got it — I heard you. You're all set.`
            : `Your microphone is working. You're all set.`
          const resp = await fetch(`${apiBase}/tutor/synthesize`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: confirmText }),
          })
          if (resp.ok) {
            const arr = await resp.arrayBuffer()
            const ctx = new AudioContext()
            const buf = await ctx.decodeAudioData(arr)
            await new Promise<void>(resolve => {
              const src = ctx.createBufferSource()
              src.buffer = buf
              src.connect(ctx.destination)
              src.onended = () => resolve()
              src.start()
              setTimeout(resolve, (buf.duration + 1) * 1000)
            })
            ctx.close()
          }
        } catch { /* non-fatal */ }
      }
      if (abortRef.current) return

      setStep('done')
      setTimeout(() => { if (!abortRef.current) onComplete('passed') }, 700)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render ─────────────────────────────────────────────────────────────────

  const stepIdx   = STEP_ORDER.indexOf(step)
  const isTerminal = step === 'done' || step === 'error'

  const msgs: Record<Step, string> = {
    permission:   'Requesting microphone access…',
    listening:    'Say anything — just testing I can hear you',
    transcribing: 'Processing your voice…',
    confirming:   transcript
      ? `I heard: "${transcript.length > 50 ? transcript.slice(0, 50) + '…' : transcript}"`
      : 'Checking your speakers…',
    done:  'You\'re all set.',
    error: errMsg || 'Microphone unavailable.',
  }

  const iconBg = step === 'done'      ? c.green
    : step === 'error'                ? c.red
    : step === 'listening'            ? c.gold
    : c.surface2

  const iconFg = (step === 'done' || step === 'error') ? '#fff' : c.text

  const icon = step === 'done'      ? '✓'
    : step === 'error'              ? '✕'
    : step === 'confirming'         ? '🔊'
    : '🎙'

  return (
    <div style={{
      background: c.surface,
      border: `1px solid ${c.border}`,
      borderRadius: 14,
      padding: '24px 24px 20px',
      width: 320,
      display: 'flex', flexDirection: 'column', gap: 18,
      boxShadow: '0 2px 20px rgba(0,0,0,0.07)',
    }}>
      <style>{WAVEBAR_KF}</style>

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.07em',
          textTransform: 'uppercase', color: c.gold,
        }}>
          Audio check
        </span>
        <div style={{ flex: 1, height: 1, background: c.border }} />
        <span style={{ fontSize: 11, color: c.muted }}>~10 sec</span>
      </div>

      {/* Icon + message */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
        <div style={{
          width: 52, height: 52, borderRadius: '50%', flexShrink: 0,
          background: iconBg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: step === 'done' || step === 'error' ? 22 : 26,
          color: iconFg,
          transition: 'background 0.35s',
        }}>
          {icon}
        </div>

        <div style={{
          fontSize: 13, textAlign: 'center', lineHeight: 1.55, minHeight: 42,
          color: step === 'error' ? c.red : c.text,
        }}>
          {msgs[step]}
          {step === 'listening' && (
            <span style={{ marginLeft: 5, color: c.gold, fontVariantNumeric: 'tabular-nums', fontSize: 12 }}>
              ({countdown}s)
            </span>
          )}
        </div>

        {/* Animated waveform bars while listening */}
        {step === 'listening' && (
          <div style={{ display: 'flex', gap: 3, alignItems: 'center', height: 22 }}>
            {[0.55, 0.9, 0.65, 1, 0.7, 0.85, 0.5].map((h, i) => (
              <div key={i} style={{
                width: 3, borderRadius: 2,
                background: c.gold,
                height: `${h * 18}px`,
                transformOrigin: 'center',
                animation: `waveBar 0.75s ${i * 0.1}s ease-in-out infinite`,
              }} />
            ))}
          </div>
        )}
      </div>

      {/* Progress dots */}
      {!isTerminal && (
        <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
          {STEP_ORDER.map((s, i) => (
            <div key={s} style={{
              width: 7, height: 7, borderRadius: '50%',
              background: i < stepIdx ? c.green : i === stepIdx ? c.gold : c.border,
              transition: 'background 0.3s',
            }} />
          ))}
        </div>
      )}

      {/* Skip / continue */}
      {step !== 'done' && (
        <button
          onClick={handleSkip}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 12, color: c.muted, padding: 0, textAlign: 'center',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = c.dim }}
          onMouseLeave={e => { e.currentTarget.style.color = c.muted }}
        >
          {step === 'error' ? 'Continue without voice →' : 'Skip — I\'ll type my answers'}
        </button>
      )}
    </div>
  )
}
