'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import dynamic from 'next/dynamic'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'
import { useTutorSession } from '@/hooks/useTutorSession'
import { useVoicePipeline } from '@/hooks/useVoicePipeline'
import type { WhiteboardHandle, WhiteboardMessage, WbMessage } from '@/components/Whiteboard'
import { ShowMyWorkPanel } from '@/components/ShowMyWorkPanel'
import { VoiceIndicator, type VoiceIndicatorState } from '@/components/VoiceIndicator'

// ── Dynamic imports ────────────────────────────────────────────────────────────

const Whiteboard = dynamic(
  () => import('@/components/Whiteboard').then(m => m.Whiteboard),
  {
    ssr: false,
    loading: () => (
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-muted)', fontSize: 13,
      }}>
        Loading whiteboard…
      </div>
    ),
  }
)

const MathWhiteboard = dynamic(
  () => import('@/components/MathWhiteboard').then(m => m.MathWhiteboard),
  {
    ssr: false,
    loading: () => (
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-muted)', fontSize: 12,
      }}>
        Loading canvas…
      </div>
    ),
  }
)

// ── Sub-components ─────────────────────────────────────────────────────────────

function CountdownTimer({
  secondsRemaining, inGracePeriod,
}: { secondsRemaining: number | null; inGracePeriod: boolean }) {
  if (secondsRemaining === null) return null
  const mins = Math.floor(secondsRemaining / 60)
  const secs = secondsRemaining % 60
  const label = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  const color = inGracePeriod ? 'var(--terracotta)'
    : secondsRemaining < 600 ? 'var(--caramel)' : 'var(--text-muted)'
  return (
    <span style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums', color, fontWeight: 600 }}>
      {inGracePeriod ? '⚠ ' : ''}{label}
    </span>
  )
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

function MessageBubble({
  role, content, onSpeak,
}: {
  role: 'student' | 'tutor' | 'system'
  content: string
  onSpeak?: () => void
}) {
  if (role === 'system') {
    return (
      <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', padding: '4px 0' }}>
        {content}
      </div>
    )
  }
  const isStudent = role === 'student'
  return (
    <div style={{ display: 'flex', justifyContent: isStudent ? 'flex-end' : 'flex-start', gap: 4, alignItems: 'flex-end' }}>
      <div style={{
        maxWidth: '85%', padding: '8px 12px',
        borderRadius: isStudent ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        background: isStudent ? 'var(--caramel)' : 'var(--surface2)',
        color: isStudent ? '#fff' : 'var(--text)',
        border: `1px solid ${isStudent ? 'transparent' : 'var(--border)'}`,
        fontSize: 13, lineHeight: 1.6,
      }}>
        <MathText latex={content} prose />
      </div>
      {!isStudent && onSpeak && (
        <button
          onClick={onSpeak}
          title="Play audio"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 12, color: 'var(--text-muted)', padding: '2px 4px', flexShrink: 0,
            lineHeight: 1,
          }}
        >
          ▶
        </button>
      )}
    </div>
  )
}

function SessionEndScreen({
  summary, onDownloadWhiteboard,
}: {
  summary: NonNullable<ReturnType<typeof useTutorSession>['summary']>
  onDownloadWhiteboard: () => void
}) {
  const perf = summary.per_topic_performance ?? {}
  const practiceProblems = summary.practice_problems ?? []
  const bullets = summary.ai_summary ?? []

  const perfColor = (v: string) => {
    if (v === 'strong') return 'var(--sage)'
    if (v === 'needs_work') return 'var(--terracotta)'
    return 'var(--text-muted)'
  }
  const perfLabel = (v: string) => {
    if (v === 'strong') return '✓ Strong'
    if (v === 'needs_work') return '⚠ Needs work'
    return '· Attempted'
  }

  return (
    <div style={{
      maxWidth: 600, margin: '0 auto', padding: '48px 24px',
      color: 'var(--text)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 10, background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
        }}>✦</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 20 }}>Session Complete</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {summary.problems_solved ?? 0} / {summary.queue_total ?? 1} problem{(summary.queue_total ?? 1) !== 1 ? 's' : ''} solved
            {' · '}
            {Math.round((summary.duration_seconds ?? 0) / 60)} min
          </div>
        </div>
      </div>

      {bullets.length > 0 && (
        <div className="notebook-card" style={{ marginBottom: 20, padding: '16px 20px' }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>What you covered</div>
          <ul style={{ margin: 0, padding: '0 0 0 18px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {bullets.map((b, i) => (
              <li key={i} style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-dim)' }}>{b}</li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(perf).length > 0 && (
        <div className="notebook-card" style={{ marginBottom: 20, padding: '16px 20px' }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>Topic performance</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(perf).map(([topic, val]) => (
              <div key={topic} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13 }}>{topic}</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: perfColor(val) }}>
                  {perfLabel(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {practiceProblems.length > 0 && (
        <div className="notebook-card" style={{ marginBottom: 20, padding: '16px 20px' }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
            Practice for next time
            <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>
              (focus on your weak areas)
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {practiceProblems.map((p, i) => (
              <div key={i} style={{
                padding: '10px 14px', borderRadius: 8,
                background: 'var(--surface)', border: '1px solid var(--border)',
              }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 8 }}>{i + 1}.</span>
                <MathText latex={p} />
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
        <button
          onClick={onDownloadWhiteboard}
          className="btn-outline"
          style={{ flex: 1, padding: '10px 16px', fontSize: 13, justifyContent: 'center' }}
        >
          ↓ Download whiteboard
        </button>
        <Link href="/tutor/new" style={{ flex: 1, textDecoration: 'none' }}>
          <button
            className="btn-caramel"
            style={{ width: '100%', padding: '10px 16px', fontSize: 13, justifyContent: 'center' }}
          >
            Book another session →
          </button>
        </Link>
      </div>
    </div>
  )
}

function QuizMeBanner({ onAccept, onDecline }: { onAccept: () => void; onDecline: () => void }) {
  return (
    <div style={{
      background: 'var(--caramel)', color: '#fff',
      padding: '8px 12px', borderBottom: '1px solid var(--border)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontSize: 13, flexShrink: 0,
    }}>
      <span>Ready to be quizzed? No hints, just you and the problems.</span>
      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={onAccept}
          style={{
            background: '#fff', color: 'var(--caramel)',
            border: 'none', padding: '3px 10px', borderRadius: 6,
            cursor: 'pointer', fontSize: 12, fontWeight: 600,
          }}
        >
          Yes
        </button>
        <button
          onClick={onDecline}
          style={{
            background: 'transparent', color: '#fff',
            border: '1px solid rgba(255,255,255,0.5)', padding: '3px 10px', borderRadius: 6,
            cursor: 'pointer', fontSize: 12,
          }}
        >
          Not yet
        </button>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function TutorSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const searchParams = useSearchParams()
  const guestToken = searchParams.get('guest_token')
  const { getToken } = useAuth()
  const wbRef = useRef<WhiteboardHandle>(null)
  const leftPanelRef = useRef<HTMLDivElement>(null)

  const {
    state, problem, messages, hintLevel, maxHints,
    secondsRemaining, inGracePeriod, summary,
    lastError, currentIndex, totalProblems,
    quizProposed, quizActive, demoWarning, demoExpired,
    whiteboardMessages, ragMatch,
    connectToSession, sendText, submitAnswer, requestHint,
    walkMeThrough, goingTooFast, nextProblem, acceptQuiz,
    endSession, sendCanvasSnapshot, sendRagSearch, sendStudentWork,
  } = useTutorSession()

  const isReconnecting = state === 'reconnecting'

  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [exportUrl, setExportUrl] = useState<string | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [inputText, setInputText] = useState('')
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const [showSteps, setShowSteps] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [inputMode, setInputMode] = useState<'chat' | 'answer'>('chat')

  // Left-panel vertical split: fraction of (panel - header) given to tutor whiteboard
  const [splitRatio, setSplitRatio] = useState(0.55)
  const [leftPanelHeight, setLeftPanelHeight] = useState(600)

  const wbMsgCountRef = useRef(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const dragState = useRef<{ startY: number; startRatio: number } | null>(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  // Sentence-by-sentence TTS queue
  const audioQueueRef = useRef<HTMLAudioElement[]>([])
  const isPlayingQueueRef = useRef(false)
  const lastTutorMsgCountRef = useRef(0)
  const prevVoiceModeRef = useRef(false)

  // ── Sentence-by-sentence TTS ───────────────────────────────────────────────

  /** Split tutor text into sentences without breaking inside $...$ LaTeX spans. */
  const splitIntoSentences = useCallback((text: string): string[] => {
    const parts: string[] = []
    let current = ''
    let inMath = false
    let i = 0
    while (i < text.length) {
      const c = text[i]
      if (c === '$') { inMath = !inMath; current += c; i++; continue }
      if (!inMath && (c === '.' || c === '!' || c === '?')) {
        current += c
        const next = text[i + 1]
        const afterNext = text[i + 2]
        if (!next || (next === ' ' && afterNext && /[A-Z"''“‘]/.test(afterNext))) {
          const s = current.trim()
          if (s.length > 2) parts.push(s)
          current = ''; i += 2; continue
        }
      }
      current += c; i++
    }
    const tail = current.trim()
    if (tail.length > 2) parts.push(tail)
    return parts.length > 0 ? parts : [text]
  }, [])

  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingQueueRef.current = false
      setIsSpeaking(false)
      return
    }
    isPlayingQueueRef.current = true
    setIsSpeaking(true)
    const audio = audioQueueRef.current.shift()!
    currentAudioRef.current = audio
    audio.play().catch(() => {})
    audio.onended = () => {
      if (currentAudioRef.current === audio) currentAudioRef.current = null
      playNextInQueue()
    }
    audio.onerror = () => {
      if (currentAudioRef.current === audio) currentAudioRef.current = null
      playNextInQueue()
    }
  }, [])

  const enqueueAudio = useCallback((audio: HTMLAudioElement) => {
    audioQueueRef.current.push(audio)
    if (!isPlayingQueueRef.current) playNextInQueue()
  }, [playNextInQueue])

  /** Stop all current and queued audio (barge-in or voice mode off). */
  const stopAllAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    audioQueueRef.current = []
    isPlayingQueueRef.current = false
    setIsSpeaking(false)
  }, [])

  /** Synthesize text sentence-by-sentence, enqueue each for sequential play. */
  const synthesizeAndQueue = useCallback(async (text: string) => {
    const sentences = splitIntoSentences(text)
    const token = await getToken()
    if (!token) return
    for (const sentence of sentences) {
      if (!sentence.trim()) continue
      try {
        const resp = await fetch(`${API_BASE}/tutor/synthesize`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: sentence }),
        })
        if (!resp.ok) continue
        const blob = await resp.blob()
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audio.onended = () => URL.revokeObjectURL(url)
        audio.onerror = () => URL.revokeObjectURL(url)
        enqueueAudio(audio)
      } catch { /* skip sentence on network error */ }
    }
  }, [splitIntoSentences, getToken, enqueueAudio])

  // ── Voice pipeline (open-mic, streaming Deepgram) ──────────────────────────
  // playFillerRef allows handleTranscript to call playFiller before the hook
  // instance is in scope (React hooks must be called at the top level).
  const playFillerRef = useRef<() => void>(() => {})

  const handleTranscript = useCallback((text: string) => {
    playFillerRef.current()   // play filler immediately on speech_final
    sendText(text)
  }, [sendText])

  const handleBargeIn = useCallback(() => {
    stopAllAudio()
  }, [stopAllAudio])

  // Fetch a fresh token when voice mode is enabled; pass it to the pipeline hook.
  const [voiceToken, setVoiceToken] = useState('')
  useEffect(() => {
    if (!voiceMode) { setVoiceToken(''); return }
    let cancelled = false
    getToken().then(t => { if (!cancelled) setVoiceToken(t ?? '') })
    return () => { cancelled = true }
  }, [voiceMode, getToken])

  const voicePipeline = useVoicePipeline({
    sessionId,
    token: voiceToken,
    apiBase: API_BASE,
    enabled: voiceMode && !!voiceToken,
    onTranscript: handleTranscript,
    onBargeIn: handleBargeIn,
  })

  // Keep playFillerRef in sync so handleTranscript can call it
  useEffect(() => {
    playFillerRef.current = voicePipeline.playFiller
  }, [voicePipeline.playFiller])

  // Sync global theme
  useEffect(() => {
    const get = () => document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
    setTheme(get())
    const obs = new MutationObserver(() => setTheme(get()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  // Measure left panel height
  useEffect(() => {
    const el = leftPanelRef.current
    if (!el) return
    const obs = new ResizeObserver(entries => {
      const h = entries[0]?.contentRect.height
      if (h && h > 0) setLeftPanelHeight(Math.floor(h))
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Forward new tutor whiteboard messages to Whiteboard.handleMessage
  useEffect(() => {
    const newMsgs = whiteboardMessages.slice(wbMsgCountRef.current)
    newMsgs.forEach(msg => wbRef.current?.handleMessage(msg as unknown as WhiteboardMessage | WbMessage))
    wbMsgCountRef.current = whiteboardMessages.length
  }, [whiteboardMessages])

  // Connect on mount — guest sessions use the URL token directly; authed sessions use Clerk
  useEffect(() => {
    let cancelled = false
    if (guestToken) {
      connectToSession(sessionId, guestToken)
    } else {
      getToken().then(token => {
        if (!token || cancelled) return
        connectToSession(sessionId, token)
      })
    }
    return () => { cancelled = true }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Capture whiteboard export when session ends
  useEffect(() => {
    if ((state === 'ended' || state === 'timeout' || state === 'solved') && !exportUrl) {
      wbRef.current?.exportPng().then(url => {
        if (url) setExportUrl(url)
      })
    }
  }, [state]) // eslint-disable-line react-hooks/exhaustive-deps

  const downloadWhiteboard = useCallback(async () => {
    const url = exportUrl ?? (await wbRef.current?.exportPng()) ?? null
    if (!url) return
    const a = document.createElement('a')
    a.href = url
    a.download = `session-${sessionId.slice(0, 8)}.png`
    a.click()
  }, [exportUrl, sessionId])

  const handleSendText = useCallback(() => {
    const t = inputText.trim()
    if (!t) return
    sendText(t)
    setInputText('')
  }, [inputText, sendText])

  /** Play a single tutor message aloud (triggered by the ▶ button on a bubble). */
  const speakText = useCallback(async (text: string) => {
    stopAllAudio()
    await synthesizeAndQueue(text)
  }, [stopAllAudio, synthesizeAndQueue])

  // Sync spoken-message count when voice mode is first enabled (avoid replaying old messages);
  // stop any playing audio when voice mode is turned off
  useEffect(() => {
    if (voiceMode && !prevVoiceModeRef.current) {
      lastTutorMsgCountRef.current = messages.filter(m => m.role === 'tutor').length
    }
    if (!voiceMode && prevVoiceModeRef.current) {
      stopAllAudio()
    }
    prevVoiceModeRef.current = voiceMode
  }, [voiceMode, stopAllAudio]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-play new tutor messages in voice mode (sentence-by-sentence)
  useEffect(() => {
    if (!voiceMode) return
    const tutorMsgs = messages.filter(m => m.role === 'tutor')
    if (tutorMsgs.length > lastTutorMsgCountRef.current) {
      lastTutorMsgCountRef.current = tutorMsgs.length
      synthesizeAndQueue(tutorMsgs[tutorMsgs.length - 1].content)
    }
  }, [messages, voiceMode, synthesizeAndQueue])

  // In voice mode, the open-mic pipeline handles recording automatically.
  // The mic button is only meaningful in non-voice-mode for dictating text.
  const [pttState, setPttState] = useState<'idle' | 'recording' | 'transcribing'>('idle')
  const pttRecorderRef = useRef<MediaRecorder | null>(null)
  const pttChunksRef = useRef<Blob[]>([])

  const togglePTT = useCallback(async () => {
    if (voiceMode) return   // open-mic handles this
    if (pttState === 'recording') { pttRecorderRef.current?.stop(); return }
    if (pttState !== 'idle') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      pttChunksRef.current = []
      recorder.ondataavailable = e => { if (e.data.size > 0) pttChunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setPttState('transcribing')
        const blob = new Blob(pttChunksRef.current, { type: 'audio/webm' })
        const token = await getToken()
        if (!token) { setPttState('idle'); return }
        const form = new FormData()
        form.append('file', blob, 'voice.webm')
        try {
          const resp = await fetch(`${API_BASE}/tutor/transcribe`, {
            method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form,
          })
          const data = await resp.json()
          if (data.text) setInputText(prev => prev + (prev ? ' ' : '') + data.text)
        } catch { /* silent */ }
        setPttState('idle')
      }
      recorder.start()
      pttRecorderRef.current = recorder
      setPttState('recording')
    } catch { setPttState('idle') }
  }, [pttState, voiceMode, getToken])

  const handleSubmitAnswer = useCallback(() => {
    const a = answerText.trim()
    if (!a) return
    submitAnswer(a)
    setAnswerText('')
  }, [answerText, submitAnswer])

  // Snapshot routing: tutor whiteboard → annotation; student canvas → chat-only
  const sendWhiteboardSnapshot = useCallback((imageB64: string) => {
    sendCanvasSnapshot(imageB64, 'whiteboard')
  }, [sendCanvasSnapshot])

  const sendScratchpadSnapshot = useCallback((imageB64: string) => {
    sendCanvasSnapshot(imageB64, 'scratchpad')
  }, [sendCanvasSnapshot])

  // Drag-to-resize the left panel split
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragState.current = { startY: e.clientY, startRatio: splitRatio }

    const HEADER_H = 44
    const onMove = (ev: MouseEvent) => {
      if (!dragState.current || !leftPanelRef.current) return
      const panelH = leftPanelRef.current.getBoundingClientRect().height - HEADER_H
      const dy = ev.clientY - dragState.current.startY
      const newRatio = Math.min(0.85, Math.max(0.15, dragState.current.startRatio + dy / panelH))
      setSplitRatio(newRatio)
    }
    const onUp = () => {
      dragState.current = null
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [splitRatio])

  // Derived heights (total left panel minus 44px header)
  const HEADER_H = 44
  const splitAreaH = Math.max(200, leftPanelHeight - HEADER_H)
  const tutorH = Math.floor(splitAreaH * splitRatio)
  const studentH = splitAreaH - tutorH - 14  // 14px for drag handle

  // ── Session end / summary ────────────────────────────────────────────────────
  if (demoExpired) {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}>
        <div style={{
          background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)',
          padding: '40px 36px', maxWidth: 420, width: '100%', textAlign: 'center',
          boxShadow: '0 4px 32px rgba(0,0,0,0.08)',
        }}>
          <div style={{ fontSize: 36, marginBottom: 16 }}>✦</div>
          <h2 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 24, fontWeight: 700, color: 'var(--text)', marginBottom: 12,
          }}>
            Your free session has ended
          </h2>
          <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7, marginBottom: 28 }}>
            You just had a 30-minute session with a patient, real AI math tutor. A full session is up to 2 hours.
          </p>
          <Link href="/sign-up" className="btn-caramel" style={{
            display: 'block', textDecoration: 'none', textAlign: 'center',
            padding: '13px 24px', fontSize: 15, fontWeight: 600, marginBottom: 12,
          }}>
            Create a free account →
          </Link>
          <Link href="/pricing" style={{
            display: 'block', fontSize: 13, color: 'var(--text-dim)', textDecoration: 'none',
          }}>
            See session pricing
          </Link>
        </div>
      </div>
    )
  }

  if ((state === 'ended' || state === 'timeout' || state === 'solved') && summary) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', overflowY: 'auto' }}>
        <SessionEndScreen summary={summary} onDownloadWhiteboard={downloadWhiteboard} />
      </div>
    )
  }

  // ── Loading / connecting ─────────────────────────────────────────────────────
  // 'reconnecting' intentionally excluded — the session UI stays visible with a banner
  if (state === 'idle' || state === 'connecting' || state === 'loading') {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 12, color: 'var(--text-muted)', fontSize: 14,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8, background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
        }}>✦</div>
        {state === 'loading' ? 'Building your problem set…' : 'Connecting to your tutor…'}
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (state === 'error') {
    return (
      <div style={{
        minHeight: '100vh', background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16, color: 'var(--text)', fontSize: 14,
      }}>
        <div style={{ color: 'var(--terracotta)', fontWeight: 600 }}>Connection failed</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          {lastError ?? 'Could not connect to the session.'}
        </div>
        <Link href="/tutor/new" style={{ color: 'var(--caramel)', fontSize: 13 }}>
          ← Book a new session
        </Link>
      </div>
    )
  }

  // ── Active session ───────────────────────────────────────────────────────────
  const isThinking = state === 'thinking'

  // Combine pipeline state with page-level TTS and LLM states.
  // Pipeline knows: idle | recording | transcribing
  // Page knows: thinking (Claude generating) | speaking (TTS playing)
  const voiceIndicatorState: VoiceIndicatorState =
    voicePipeline.voiceState === 'recording' ? 'recording'
    : voicePipeline.voiceState === 'transcribing' ? 'transcribing'
    : isSpeaking ? 'speaking'
    : isThinking ? 'thinking'
    : 'idle'

  return (
    <div style={{
      display: 'flex', height: '100vh', overflow: 'hidden',
      background: 'var(--bg)', color: 'var(--text)',
    }}>

      {/* ── Left: split whiteboard (65%) ───────────────────────────────────── */}
      <div
        ref={leftPanelRef}
        style={{ flex: '0 0 65%', display: 'flex', flexDirection: 'column', minWidth: 0 }}
      >
        {/* Header bar */}
        <div style={{
          height: HEADER_H, flexShrink: 0, display: 'flex', alignItems: 'center',
          padding: '0 12px', gap: 10,
          borderBottom: '1px solid var(--border)',
          background: theme === 'dark' ? '#161b22' : '#f6f7fb',
        }}>
          <div style={{
            width: 26, height: 26, borderRadius: 6, background: 'var(--caramel)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13,
          }}>✦</div>
          <span style={{ fontWeight: 600, fontSize: 13 }}>Whiteboard</span>
          {quizActive && (
            <span style={{
              fontSize: 10, fontWeight: 700, color: '#fff',
              background: 'var(--terracotta)', padding: '2px 7px', borderRadius: 10,
            }}>EXAM MODE</span>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
            {totalProblems > 0 && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {currentIndex + 1} / {totalProblems}
              </span>
            )}
            <CountdownTimer secondsRemaining={secondsRemaining} inGracePeriod={inGracePeriod} />
            <button
              onClick={downloadWhiteboard}
              style={{
                background: 'none', border: '1px solid var(--border)',
                borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
                fontSize: 11, color: 'var(--text-muted)',
              }}
            >
              ↓ PNG
            </button>
          </div>
        </div>

        {/* Tutor whiteboard — top portion */}
        <div style={{ height: tutorH, flexShrink: 0, position: 'relative', overflow: 'hidden' }}>
          <Whiteboard
            ref={wbRef}
            theme={theme}
            visibleHeight={Math.max(161, tutorH - 39)}
            onSnapshot={sendWhiteboardSnapshot}
          />
        </div>

        {/* Drag handle */}
        <div
          onMouseDown={handleDragStart}
          title="Drag to resize panels"
          style={{
            height: 14, flexShrink: 0, cursor: 'row-resize',
            background: theme === 'dark' ? '#1c2128' : '#eef0f8',
            borderTop: '1px solid var(--border)',
            borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 3,
            userSelect: 'none',
          }}
        >
          {[0,1,2,3,4].map(i => (
            <div key={i} style={{
              width: 4, height: 4, borderRadius: '50%',
              background: theme === 'dark' ? '#484f58' : '#9aa0b4',
            }} />
          ))}
        </div>

        {/* Student canvas — MathWhiteboard (bottom portion) */}
        <div style={{ flex: '1 1 0', minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {/* Visible section header — distinguishes student scratch from tutor canvas */}
          <div style={{
            height: 26, flexShrink: 0, display: 'flex', alignItems: 'center',
            padding: '0 10px', gap: 8,
            background: theme === 'dark' ? '#1c2128' : '#eef0f8',
            borderBottom: `1px solid ${theme === 'dark' ? '#30363d' : '#d8dce8'}`,
          }}>
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
              color: theme === 'dark' ? '#8b949e' : '#6c7289',
            }}>
              Your scratch work
            </span>
            <span style={{
              marginLeft: 'auto', fontSize: 10,
              color: theme === 'dark' ? '#484f58' : '#9aa0b4',
            }}>
              Draw here · tutor can see your work
            </span>
          </div>
          <div style={{ flex: '1 1 0', minHeight: 0, position: 'relative' }}>
            <MathWhiteboard
              mode="session"
              theme={theme}
              onSnapshot={sendScratchpadSnapshot}
            />
          </div>
        </div>
      </div>

      {/* ── Right: Chat sidebar (35%) ──────────────────────────────────────── */}
      <div style={{
        flex: '0 0 35%', display: 'flex', flexDirection: 'column',
        borderLeft: '1px solid var(--border)', minWidth: 0, overflow: 'hidden',
      }}>
        {/* Sidebar header */}
        <div style={{
          height: HEADER_H, flexShrink: 0, display: 'flex', alignItems: 'center',
          padding: '0 12px', gap: 8, borderBottom: '1px solid var(--border)',
          background: theme === 'dark' ? '#161b22' : '#f6f7fb',
        }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>Chat</span>
          <button
            onClick={() => setVoiceMode(v => !v)}
            title={voiceMode ? 'Voice mode on — click to disable' : 'Enable voice mode'}
            style={{
              background: voiceMode ? 'var(--caramel)' : 'none',
              border: `1px solid ${voiceMode ? 'var(--caramel)' : 'var(--border)'}`,
              borderRadius: 6, padding: '3px 8px', cursor: 'pointer',
              fontSize: 11, color: voiceMode ? '#fff' : 'var(--text-muted)',
              fontWeight: 600,
            }}
          >
            🎤 {voiceMode ? 'Voice on' : 'Voice'}
          </button>
          <button
            onClick={() => setShowEndConfirm(true)}
            style={{
              marginLeft: 'auto', background: 'none', border: '1px solid var(--border)',
              borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
              fontSize: 11, color: 'var(--text-muted)',
            }}
          >
            End session
          </button>
        </div>

        {/* Exam mode banner */}
        {quizProposed && (
          <QuizMeBanner
            onAccept={acceptQuiz}
            onDecline={() => { /* dismiss without accepting */ }}
          />
        )}

        {/* Demo warning banner */}
        {demoWarning && !demoExpired && (
          <div style={{
            background: 'var(--caramel)', color: '#fff',
            padding: '8px 14px', fontSize: 13, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span>5 minutes left in your free demo session.</span>
            <Link href="/sign-up" style={{
              color: '#fff', fontWeight: 700, fontSize: 12,
              border: '1px solid rgba(255,255,255,0.6)', padding: '3px 10px',
              borderRadius: 6, textDecoration: 'none',
            }}>
              Create account →
            </Link>
          </div>
        )}

        {/* Reconnecting banner */}
        {isReconnecting && (
          <div style={{
            background: 'var(--caramel)', color: '#fff',
            padding: '6px 12px', fontSize: 12, flexShrink: 0,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>↻</span>
            Reconnecting — your session is saved
          </div>
        )}

        {/* Current problem */}
        {problem && (
          <div style={{
            padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0,
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
              Problem {currentIndex + 1}{totalProblems > 1 ? ` of ${totalProblems}` : ''}
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.6 }}>
              <MathText latex={problem.statement} prose />
            </div>
          </div>
        )}

        {/* RAG match */}
        {ragMatch && (
          <div style={{
            padding: '8px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0,
            background: 'rgba(74,158,255,0.06)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 700, color: 'var(--link)', marginBottom: 4,
            }}>
              <span>Looks familiar?</span>
              <span style={{
                marginLeft: 'auto', fontSize: 10,
                background: 'rgba(74,158,255,0.12)', padding: '1px 5px', borderRadius: 8,
              }}>
                {Math.round(ragMatch.similarity * 100)}% match
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
              <MathText latex={ragMatch.statement_latex} prose />
            </div>
          </div>
        )}

        {/* Messages — scrollable flex-1 */}
        <div style={{
          flex: 1, overflowY: 'auto',
          padding: '10px 12px',
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              role={m.role}
              content={m.content}
              onSpeak={m.role === 'tutor' ? () => speakText(m.content) : undefined}
            />
          ))}
          {isThinking && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Thinking…
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Action chips */}
        <div style={{
          padding: '6px 12px', flexShrink: 0,
          display: 'flex', flexWrap: 'wrap', gap: 5,
          borderTop: '1px solid var(--border)',
        }}>
          {!quizActive && (
            <button
              onClick={() => requestHint()}
              disabled={hintLevel >= maxHints}
              style={chipStyle(false)}
            >
              Hint ({hintLevel}/{maxHints})
            </button>
          )}
          <button onClick={walkMeThrough} style={chipStyle(false)}>Walk me through</button>
          <button onClick={goingTooFast} style={chipStyle(false)}>Too fast</button>
          <button onClick={sendRagSearch} style={chipStyle(false)}>Search my problems</button>
          <button onClick={nextProblem} style={chipStyle(false)}>Next problem</button>
        </div>

        {/* Show My Work — collapsible LaTeX step entry */}
        <div style={{ flexShrink: 0, borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => setShowSteps(s => !s)}
            style={{
              width: '100%', padding: '6px 12px', fontSize: 11, fontWeight: 600,
              border: 'none', cursor: 'pointer', letterSpacing: '0.04em',
              background: showSteps
                ? theme === 'dark' ? '#1c2128' : '#f0f2f8'
                : 'transparent',
              color: showSteps ? 'var(--caramel)' : 'var(--text-muted)',
              borderBottom: showSteps ? '1px solid var(--border)' : 'none',
              display: 'flex', alignItems: 'center', gap: 6,
              textAlign: 'left',
            }}
          >
            <span>{showSteps ? '▾' : '▸'}</span>
            <span>∑ Show My Work</span>
          </button>
          {showSteps && (
            <div style={{ height: 160, overflowY: 'auto', padding: '8px 12px' }}>
              <ShowMyWorkPanel theme={theme} onSubmit={sendStudentWork} />
            </div>
          )}
        </div>

        {/* Unified input area */}
        <div style={{ padding: '6px 12px 12px', flexShrink: 0 }}>
          {/* Voice agent indicator */}
          {voiceMode && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2px 0 6px' }}>
              <VoiceIndicator state={voiceIndicatorState} size={44} />
            </div>
          )}

          {/* Mode tabs — only when a problem is active */}
          {problem && (
            <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
              {(['chat', 'answer'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setInputMode(m)}
                  style={{
                    flex: 1, padding: '5px 0', borderRadius: 6, fontSize: 11, fontWeight: 600,
                    border: `1px solid ${inputMode === m ? 'var(--caramel)' : 'var(--border)'}`,
                    background: inputMode === m
                      ? (theme === 'dark' ? 'rgba(196,151,106,0.15)' : 'rgba(196,151,106,0.1)')
                      : 'transparent',
                    color: inputMode === m ? 'var(--caramel)' : 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {m === 'chat' ? 'Message' : 'Submit Answer'}
                </button>
              ))}
            </div>
          )}

          {/* Answer input */}
          {problem && inputMode === 'answer' && (
            <div style={{ display: 'flex', gap: 6 }}>
              <div style={{ flex: 1 }}>
                <MathInput
                  value={answerText}
                  onChange={setAnswerText}
                  placeholder="Your answer…"
                />
              </div>
              <button
                onClick={handleSubmitAnswer}
                disabled={!answerText.trim() || isThinking}
                className="btn-caramel"
                style={{ padding: '8px 14px', fontSize: 13, flexShrink: 0, justifyContent: 'center' }}
              >
                Submit
              </button>
            </div>
          )}

          {/* Chat input */}
          {(!problem || inputMode === 'chat') && (
            <div style={{ display: 'flex', gap: 6 }}>
              {!voiceMode && (
                <button
                  onClick={togglePTT}
                  disabled={pttState === 'transcribing'}
                  title={pttState === 'recording' ? 'Stop recording' : 'Record voice message'}
                  style={{
                    flexShrink: 0, width: 36, borderRadius: 8, fontSize: 13, fontWeight: 700,
                    border: `1px solid ${pttState === 'recording' ? 'var(--terracotta)' : 'var(--border)'}`,
                    background: pttState === 'recording' ? 'var(--terracotta)' : 'var(--surface)',
                    color: pttState === 'recording' ? '#fff' : 'var(--text-muted)',
                    cursor: pttState === 'transcribing' ? 'default' : 'pointer',
                  }}
                >
                  {pttState === 'transcribing' ? '…' : pttState === 'recording' ? '■' : '⏺'}
                </button>
              )}
              <input
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendText())}
                placeholder={voiceMode ? 'Or type a message…' : 'Message your tutor…'}
                style={{
                  flex: 1, padding: '8px 12px', borderRadius: 8, fontSize: 13,
                  border: '1px solid var(--border)', background: 'var(--surface)',
                  color: 'var(--text)', outline: 'none',
                }}
              />
              <button
                onClick={handleSendText}
                disabled={!inputText.trim() || isThinking}
                className="btn-caramel"
                style={{ padding: '8px 14px', fontSize: 13, flexShrink: 0, justifyContent: 'center' }}
              >
                →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── End session confirm ────────────────────────────────────────────── */}
      {showEndConfirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div className="notebook-card" style={{ maxWidth: 320, width: '90%', margin: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>End this session?</div>
            <div style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 16 }}>
              This session cannot be resumed once ended.
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => { endSession(); setShowEndConfirm(false) }}
                className="btn-caramel"
                style={{ flex: 1, padding: '10px', fontSize: 13, justifyContent: 'center' }}
              >
                End session
              </button>
              <button
                onClick={() => setShowEndConfirm(false)}
                style={{
                  flex: 1, padding: '10px', fontSize: 13, borderRadius: 8,
                  border: '1px solid var(--border)', background: 'transparent',
                  color: 'var(--text)', cursor: 'pointer',
                }}
              >
                Keep going
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Shared styles ──────────────────────────────────────────────────────────────

function chipStyle(active: boolean): React.CSSProperties {
  return {
    padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 500,
    cursor: 'pointer',
    border: `1px solid ${active ? 'var(--caramel)' : 'var(--border)'}`,
    background: active ? 'var(--caramel-dim)' : 'transparent',
    color: active ? 'var(--caramel)' : 'var(--text-dim)',
    transition: 'all 0.12s',
  }
}
