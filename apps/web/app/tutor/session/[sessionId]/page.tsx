'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import dynamic from 'next/dynamic'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'
import { useTutorSession } from '@/hooks/useTutorSession'
import type { WhiteboardHandle, WhiteboardMessage, WbMessage } from '@/components/Whiteboard'
import { ShowMyWorkPanel } from '@/components/ShowMyWorkPanel'

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

function ExamModeBanner({ onAccept, onDecline }: { onAccept: () => void; onDecline: () => void }) {
  return (
    <div style={{
      background: 'var(--caramel)', color: '#fff',
      padding: '8px 12px', borderBottom: '1px solid var(--border)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontSize: 13, flexShrink: 0,
    }}>
      <span>Tutor is proposing exam mode — ready to go solo?</span>
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
  const { getToken } = useAuth()
  const wbRef = useRef<WhiteboardHandle>(null)
  const leftPanelRef = useRef<HTMLDivElement>(null)

  const {
    state, problem, messages, hintLevel, maxHints,
    secondsRemaining, inGracePeriod, summary,
    lastError, currentIndex, totalProblems,
    examModeProposed, examModeActive,
    whiteboardMessages, ragMatch,
    connectToSession, sendText, submitAnswer, requestHint,
    walkMeThrough, goingTooFast, nextProblem, acceptExamMode,
    endSession, sendCanvasSnapshot, sendRagSearch, sendStudentWork,
  } = useTutorSession()

  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [exportUrl, setExportUrl] = useState<string | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [inputText, setInputText] = useState('')
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const [showSteps, setShowSteps] = useState(false)

  // Left-panel vertical split: fraction of (panel - header) given to tutor whiteboard
  const [splitRatio, setSplitRatio] = useState(0.55)
  const [leftPanelHeight, setLeftPanelHeight] = useState(600)

  const wbMsgCountRef = useRef(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const dragState = useRef<{ startY: number; startRatio: number } | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const [voiceState, setVoiceState] = useState<'idle' | 'recording' | 'transcribing'>('idle')

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

  // Connect on mount
  useEffect(() => {
    let cancelled = false
    getToken().then(token => {
      if (!token || cancelled) return
      connectToSession(sessionId, token)
    })
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

  const speakText = useCallback(async (text: string) => {
    const token = await getToken()
    if (!token) return
    try {
      const resp = await fetch(`${API_BASE}/tutor/synthesize`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!resp.ok) return
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.play()
      audio.onended = () => URL.revokeObjectURL(url)
    } catch { /* silent */ }
  }, [getToken])

  const toggleVoice = useCallback(async () => {
    if (voiceState === 'recording') {
      mediaRecorderRef.current?.stop()
      return
    }
    if (voiceState !== 'idle') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      audioChunksRef.current = []
      recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setVoiceState('transcribing')
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const token = await getToken()
        if (!token) { setVoiceState('idle'); return }
        const form = new FormData()
        form.append('file', blob, 'voice.webm')
        try {
          const resp = await fetch(`${API_BASE}/tutor/transcribe`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: form,
          })
          const data = await resp.json()
          if (data.text) setInputText(prev => prev + (prev ? ' ' : '') + data.text)
        } catch { /* silent */ }
        setVoiceState('idle')
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setVoiceState('recording')
    } catch { setVoiceState('idle') }
  }, [voiceState, getToken])

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
  if ((state === 'ended' || state === 'timeout' || state === 'solved') && summary) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', overflowY: 'auto' }}>
        <SessionEndScreen summary={summary} onDownloadWhiteboard={downloadWhiteboard} />
      </div>
    )
  }

  // ── Loading / connecting ─────────────────────────────────────────────────────
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
          {examModeActive && (
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
            visibleHeight={Math.max(200, tutorH)}
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
        <div style={{ height: studentH, flexShrink: 0, position: 'relative', overflow: 'hidden' }}>
          {/* Section label */}
          <div style={{
            position: 'absolute', top: 6, left: 60, zIndex: 20,
            fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
            color: theme === 'dark' ? '#30363d' : '#c8cde0',
            pointerEvents: 'none',
          }}>
            Your work
          </div>
          <MathWhiteboard
            mode="session"
            theme={theme}
            onSnapshot={sendScratchpadSnapshot}
          />
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
          padding: '0 12px', borderBottom: '1px solid var(--border)',
          background: theme === 'dark' ? '#161b22' : '#f6f7fb',
        }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>Chat</span>
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
        {examModeProposed && (
          <ExamModeBanner
            onAccept={acceptExamMode}
            onDecline={() => { /* dismiss without accepting */ }}
          />
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
              <MathText latex={problem.statement} />
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
              <MathText latex={ragMatch.statement_latex} />
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
          {!examModeActive && (
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

        {/* Answer input */}
        {problem && (
          <div style={{ padding: '6px 12px', flexShrink: 0, display: 'flex', gap: 6 }}>
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
        <div style={{ padding: '6px 12px 12px', flexShrink: 0, display: 'flex', gap: 6 }}>
          <button
            onClick={toggleVoice}
            disabled={voiceState === 'transcribing'}
            title={voiceState === 'recording' ? 'Stop recording' : 'Record voice message'}
            style={{
              flexShrink: 0, width: 36, borderRadius: 8, fontSize: 13, fontWeight: 700,
              border: `1px solid ${voiceState === 'recording' ? 'var(--terracotta)' : 'var(--border)'}`,
              background: voiceState === 'recording' ? 'var(--terracotta)' : 'var(--surface)',
              color: voiceState === 'recording' ? '#fff' : 'var(--text-muted)',
              cursor: voiceState === 'transcribing' ? 'default' : 'pointer',
            }}
          >
            {voiceState === 'transcribing' ? '…' : voiceState === 'recording' ? '■' : '⏺'}
          </button>
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendText())}
            placeholder="Message your tutor…"
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
