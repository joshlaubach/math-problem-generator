'use client'

/**
 * /tutor/session/[sessionId] — Full tutor session shell (Phases 4-6)
 *
 * Layout: 65% whiteboard (left) / 30% chat sidebar (right)
 * Features:
 *  - Phase 4: Problem queue, lesson mode, "Going too fast", "Walk me through"
 *  - Phase 5: Exam mode detection + accept/decline flow
 *  - Phase 6: Post-session summary with 3 sections + whiteboard download
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import dynamic from 'next/dynamic'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'
import { useTutorSession } from '@/hooks/useTutorSession'
import type { WhiteboardHandle } from '@/components/Whiteboard'

// ── Dynamic imports ────────────────────────────────────────────────────────────

const Whiteboard = dynamic(() => import('@/components/Whiteboard').then(m => m.Whiteboard), {
  ssr: false,
  loading: () => (
    <div style={{
      flex: 1, background: 'var(--surface)', borderRadius: 12,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'var(--text-muted)', fontSize: 13,
    }}>
      Loading whiteboard…
    </div>
  ),
})

// ── Sub-components ────────────────────────────────────────────────────────────

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

function MessageBubble({ role, content }: { role: 'student' | 'tutor' | 'system'; content: string }) {
  if (role === 'system') {
    return (
      <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', padding: '4px 0' }}>
        {content}
      </div>
    )
  }
  const isStudent = role === 'student'
  return (
    <div style={{ display: 'flex', justifyContent: isStudent ? 'flex-end' : 'flex-start' }}>
      <div style={{
        maxWidth: '82%', padding: '9px 13px',
        borderRadius: isStudent ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        background: isStudent ? 'var(--caramel)' : 'var(--surface2)',
        color: isStudent ? '#fff' : 'var(--text)',
        border: `1px solid ${isStudent ? 'transparent' : 'var(--border)'}`,
        fontSize: 13, lineHeight: 1.6,
      }}>
        {isStudent
          ? <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
          : <MathText latex={content} prose />
        }
      </div>
    </div>
  )
}

// ── Post-session summary ───────────────────────────────────────────────────────

function SessionEndScreen({
  summary,
  onDownloadWhiteboard,
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
      color: 'var(--text)', fontFamily: 'system-ui',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 10,
          background: 'var(--caramel)',
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

      {/* Section 1: Summary bullets */}
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

      {/* Section 2: Per-topic performance */}
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

      {/* Section 3: Practice problems for weak areas */}
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
                <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 8 }}>
                  {i + 1}.
                </span>
                <MathText latex={p} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
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

// ── Exam mode banner ───────────────────────────────────────────────────────────

function ExamModeBanner({
  onAccept, onDecline,
}: { onAccept: () => void; onDecline: () => void }) {
  return (
    <div style={{
      background: 'var(--caramel)', color: '#fff',
      padding: '10px 16px', borderRadius: 8,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      marginBottom: 8, fontSize: 13,
    }}>
      <span>Tutor is proposing exam mode — ready to go solo?</span>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={onAccept}
          style={{
            background: '#fff', color: 'var(--caramel)',
            border: 'none', padding: '4px 12px', borderRadius: 6,
            cursor: 'pointer', fontSize: 12, fontWeight: 600,
          }}
        >
          Yes, let's go
        </button>
        <button
          onClick={onDecline}
          style={{
            background: 'transparent', color: '#fff',
            border: '1px solid rgba(255,255,255,0.5)', padding: '4px 12px', borderRadius: 6,
            cursor: 'pointer', fontSize: 12,
          }}
        >
          Not yet
        </button>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TutorSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { getToken } = useAuth()
  const wbRef = useRef<WhiteboardHandle>(null)

  const {
    state, problem, messages, hintLevel, maxHints,
    secondsRemaining, inGracePeriod, summary,
    lastError, currentIndex, totalProblems,
    examModeProposed, examModeActive,
    whiteboardMessages, ragMatch,
    connectToSession, sendText, submitAnswer, requestHint,
    walkMeThrough, goingTooFast, nextProblem, acceptExamMode,
    endSession, sendCanvasSnapshot, sendRagSearch,
  } = useTutorSession()

  const handleSnapshot = useCallback((imageB64: string) => {
    sendCanvasSnapshot(imageB64)
  }, [sendCanvasSnapshot])

  const [answerText, setAnswerText] = useState('')
  const [inputText, setInputText] = useState('')
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // ── Connect on mount ───────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    getToken().then(token => {
      if (!token || cancelled) return
      connectToSession(sessionId, token)
    })
    return () => { cancelled = true }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-scroll messages ───────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Forward WS whiteboard events to the Whiteboard component ──────────────
  useEffect(() => {
    if (whiteboardMessages.length === 0) return
    const last = whiteboardMessages[whiteboardMessages.length - 1]
    wbRef.current?.handleMessage(last as any)
  }, [whiteboardMessages])

  // ── Download whiteboard ────────────────────────────────────────────────────
  const downloadWhiteboard = useCallback(async () => {
    const dataUrl = await wbRef.current?.exportPng()
    if (!dataUrl) return
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = `session-${sessionId.slice(0, 8)}.png`
    a.click()
  }, [sessionId])

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleSendText = useCallback(() => {
    const t = inputText.trim()
    if (!t) return
    sendText(t)
    setInputText('')
  }, [inputText, sendText])

  const handleSubmitAnswer = useCallback(() => {
    const a = answerText.trim()
    if (!a) return
    submitAnswer(a)
    setAnswerText('')
  }, [answerText, submitAnswer])

  // ── Session end / summary ──────────────────────────────────────────────────
  if ((state === 'ended' || state === 'timeout' || state === 'solved') && summary) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
        <SessionEndScreen summary={summary} onDownloadWhiteboard={downloadWhiteboard} />
        {/* Keep a hidden whiteboard for the PNG export */}
        <div style={{ position: 'absolute', visibility: 'hidden', pointerEvents: 'none' }}>
          <Whiteboard ref={wbRef} />
        </div>
      </div>
    )
  }

  // ── Loading / connecting ───────────────────────────────────────────────────
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

  // ── Error ──────────────────────────────────────────────────────────────────
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

  // ── Active session layout ──────────────────────────────────────────────────
  const isThinking = state === 'thinking'

  return (
    <div style={{
      display: 'flex', height: '100vh', overflow: 'hidden',
      background: 'var(--bg)', color: 'var(--text)',
    }}>
      {/* ── 65% whiteboard ──────────────────────────────────────────────── */}
      <div style={{
        flex: '0 0 65%', display: 'flex', flexDirection: 'column',
        padding: '12px 8px 12px 16px', minWidth: 0,
      }}>
        {/* Whiteboard header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 8, paddingRight: 8,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 6, background: 'var(--caramel)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
            }}>✦</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Whiteboard</span>
            {examModeActive && (
              <span style={{
                fontSize: 11, fontWeight: 700, color: '#fff',
                background: 'var(--terracotta)', padding: '2px 8px', borderRadius: 10,
              }}>EXAM MODE</span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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

        {/* Whiteboard canvas */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <Whiteboard ref={wbRef} visibleHeight={undefined} onSnapshot={handleSnapshot} />
        </div>

        {/* Answer input bar */}
        {problem && (
          <div style={{
            display: 'flex', gap: 8, marginTop: 8, paddingRight: 8,
          }}>
            <div style={{ flex: 1 }}>
              <MathInput
                value={answerText}
                onChange={setAnswerText}
                placeholder="Type your answer…"
              />
            </div>
            <button
              onClick={handleSubmitAnswer}
              disabled={!answerText.trim() || isThinking}
              className="btn-caramel"
              style={{ padding: '8px 16px', fontSize: 13, flexShrink: 0, justifyContent: 'center' }}
            >
              Submit
            </button>
          </div>
        )}
      </div>

      {/* ── 30% chat sidebar ────────────────────────────────────────────── */}
      <div style={{
        flex: '0 0 30%', display: 'flex', flexDirection: 'column',
        padding: '12px 16px 12px 8px', minWidth: 0,
        borderLeft: '1px solid var(--border)',
      }}>
        {/* Sidebar header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 8,
        }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>Chat</span>
          <button
            onClick={() => setShowEndConfirm(true)}
            style={{
              background: 'none', border: '1px solid var(--border)',
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
            onDecline={() => { /* just dismiss; don't accept */ }}
          />
        )}

        {/* Current problem statement */}
        {problem && (
          <div style={{
            padding: '10px 12px', borderRadius: 8, marginBottom: 8,
            background: 'var(--surface)', border: '1px solid var(--border)',
            fontSize: 13, lineHeight: 1.6,
          }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600 }}>
              Problem {currentIndex + 1}{totalProblems > 1 ? ` of ${totalProblems}` : ''}
            </div>
            <MathText latex={problem.statement} />
          </div>
        )}

        {/* RAG match card */}
        {ragMatch && (
          <div style={{
            padding: '8px 10px', borderRadius: 8, marginBottom: 8,
            background: 'rgba(74,158,255,0.07)',
            border: '1px solid rgba(74,158,255,0.22)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 700, color: 'var(--link)',
              marginBottom: 4,
            }}>
              <span>Looks familiar?</span>
              <span style={{
                marginLeft: 'auto', fontSize: 10,
                background: 'rgba(74,158,255,0.12)',
                padding: '1px 5px', borderRadius: 8,
              }}>
                {Math.round(ragMatch.similarity * 100)}% match
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
              <MathText latex={ragMatch.statement_latex} />
            </div>
          </div>
        )}

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', display: 'flex',
          flexDirection: 'column', gap: 8, paddingRight: 2,
        }}>
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} />
          ))}
          {isThinking && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Thinking…
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Action chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0 6px' }}>
          {!examModeActive && (
            <button
              onClick={() => requestHint()}
              disabled={hintLevel >= maxHints}
              style={chipStyle(false)}
            >
              Hint ({hintLevel}/{maxHints})
            </button>
          )}
          <button onClick={walkMeThrough} style={chipStyle(false)}>
            Walk me through
          </button>
          <button onClick={goingTooFast} style={chipStyle(false)}>
            Too fast
          </button>
          <button onClick={sendRagSearch} style={chipStyle(false)}>
            Search my problems
          </button>
          <button onClick={nextProblem} style={chipStyle(false)}>
            Next problem
          </button>
        </div>

        {/* Chat input */}
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendText())}
            placeholder="Message your tutor…"
            style={{
              flex: 1, padding: '8px 12px', borderRadius: 8, fontSize: 13,
              border: '1px solid var(--border)', background: 'var(--surface)',
              color: 'var(--text)',
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

      {/* ── End session confirm overlay ──────────────────────────────────── */}
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

// ── Shared styles ─────────────────────────────────────────────────────────────

function chipStyle(active: boolean): React.CSSProperties {
  return {
    padding: '4px 12px', borderRadius: 14, fontSize: 11, fontWeight: 500,
    cursor: 'pointer',
    border: `1px solid ${active ? 'var(--caramel)' : 'var(--border)'}`,
    background: active ? 'var(--caramel-dim)' : 'transparent',
    color: active ? 'var(--caramel)' : 'var(--text-dim)',
    transition: 'all 0.12s',
  }
}
