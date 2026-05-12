'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'
import { Scratchpad } from '@/components/Scratchpad'
import { VoiceInput } from '@/components/VoiceInput'
import { AudioPlayer } from '@/components/AudioPlayer'
import { useTutorSession, type SessionType } from '@/hooks/useTutorSession'

// ── Types ─────────────────────────────────────────────────────────────────────

interface TutorChatProps {
  topicId: string
  difficulty: number
  sessionType: SessionType
  getToken: () => Promise<string | null>
  userTier?: string
}

// ── Countdown display ─────────────────────────────────────────────────────────

function CountdownTimer({
  secondsRemaining,
  inGracePeriod,
}: {
  secondsRemaining: number | null
  inGracePeriod: boolean
}) {
  if (secondsRemaining === null) return null
  const mins = Math.floor(secondsRemaining / 60)
  const secs = secondsRemaining % 60
  const label = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  const color = inGracePeriod
    ? 'var(--terracotta)'
    : secondsRemaining < 600
    ? 'var(--caramel)'
    : 'var(--text-muted)'

  return (
    <span style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums', color, fontWeight: 600 }}>
      {inGracePeriod ? '⚠ ' : ''}{label}
    </span>
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({ role, content }: { role: 'student' | 'tutor' | 'system'; content: string }) {
  if (role === 'system') {
    return (
      <div style={{
        textAlign: 'center', fontSize: 12,
        color: 'var(--text-muted)', padding: '4px 0',
      }}>
        {content}
      </div>
    )
  }

  const isStudent = role === 'student'
  return (
    <div style={{ display: 'flex', justifyContent: isStudent ? 'flex-end' : 'flex-start' }}>
      <div style={{
        maxWidth: '75%',
        padding: '10px 14px',
        borderRadius: isStudent ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        background: isStudent ? 'var(--caramel)' : 'var(--surface)',
        color: isStudent ? '#fff' : 'var(--text)',
        border: `1px solid ${isStudent ? 'transparent' : 'var(--border)'}`,
        fontSize: 14,
        lineHeight: 1.6,
      }}>
        {isStudent
          ? <span>{content}</span>
          : <MathText latex={content} prose />
        }
      </div>
    </div>
  )
}

// ── End-session confirmation ──────────────────────────────────────────────────

function EndSessionConfirm({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div style={{
      position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      borderRadius: 12, zIndex: 10,
    }}>
      <div className="notebook-card" style={{ maxWidth: 320, width: '100%', margin: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>End this session?</div>
        <div style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 16 }}>
          This session cannot be resumed or paused once ended.
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className="btn-caramel" style={{ flex: 1, justifyContent: 'center' }}
            onClick={onConfirm}>
            End Session
          </button>
          <button type="button" className="btn-ghost" style={{ flex: 1, justifyContent: 'center' }}
            onClick={onCancel}>
            Keep Going
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function TutorChat({ topicId, difficulty, sessionType, getToken, userTier = 'free' }: TutorChatProps) {
  const session = useTutorSession()
  const [inputText, setInputText] = useState('')
  const [answerText, setAnswerText] = useState('')
  const [mode, setMode] = useState<'chat' | 'answer'>('chat')
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const [voiceMode, setVoiceMode] = useState(false)
  const [lastTutorText, setLastTutorText] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-connect on mount
  useEffect(() => {
    getToken().then(token => {
      if (token) session.connect(topicId, difficulty, token, sessionType)
    })
    return () => session.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicId, difficulty, sessionType])

  // Navigation guard
  useEffect(() => {
    if (session.state !== 'ready' && session.state !== 'thinking') return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [session.state])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session.messages])

  // Track latest tutor message for TTS
  useEffect(() => {
    const last = [...session.messages].reverse().find(m => m.role === 'tutor')
    if (last) setLastTutorText(last.content)
  }, [session.messages])

  const handleSendText = useCallback(() => {
    const text = inputText.trim()
    if (!text) return
    session.sendText(text)
    setInputText('')
  }, [inputText, session])

  const handleSubmitAnswer = useCallback(() => {
    const answer = answerText.trim()
    if (!answer) return
    session.submitAnswer(answer)
    setAnswerText('')
    setMode('chat')
  }, [answerText, session])

  const handleEndSession = useCallback(() => {
    setShowEndConfirm(false)
    session.endSession()
  }, [session])

  const isActive = session.state === 'ready' || session.state === 'thinking'
  const isDone = session.state === 'solved' || session.state === 'ended' || session.state === 'timeout'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'relative' }}>

      {/* End session confirmation overlay */}
      {showEndConfirm && (
        <EndSessionConfirm
          onConfirm={handleEndSession}
          onCancel={() => setShowEndConfirm(false)}
        />
      )}

      {/* Problem header */}
      {session.problem && (
        <div className="notebook-card" style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <span className="card-eyebrow">Problem</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Hints: {session.hintLevel}/{session.maxHints}
              </span>
              <CountdownTimer
                secondsRemaining={session.secondsRemaining}
                inGracePeriod={session.inGracePeriod}
              />
              <button
                onClick={() => setVoiceMode(v => !v)}
                title={voiceMode ? 'Switch to text mode' : 'Switch to voice mode'}
                style={{
                  padding: '3px 8px', borderRadius: 6, border: '1px solid var(--border)',
                  background: voiceMode ? 'var(--caramel)' : 'none',
                  color: voiceMode ? '#fff' : 'var(--text-dim)',
                  cursor: 'pointer', fontSize: 12, fontWeight: 600,
                }}
              >
                {voiceMode ? '🎤 Voice' : '🎤'}
              </button>
            </div>
          </div>
          <MathText latex={session.problem.statement} prose />
        </div>
      )}

      {/* Connecting state */}
      {session.state === 'connecting' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '24px 0' }}>
          <div className="spinner" />
          <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            Preparing your tutor session…
          </span>
        </div>
      )}

      {/* Error state */}
      {session.state === 'error' && session.lastError && (
        <div style={{
          padding: '12px 16px', borderRadius: 10,
          background: 'var(--terra-dim)', border: '1px solid rgba(193,68,14,0.25)',
          color: 'var(--terracotta)', fontSize: 14,
        }}>
          {session.lastError}
        </div>
      )}

      {/* Correct overlay */}
      {session.state === 'solved' && session.summary && (
        <div className="notebook-card" style={{ padding: 24, animation: 'fadeIn 0.3s ease' }}>
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <div style={{ fontSize: 28, marginBottom: 4, color: 'var(--forest)' }}>✓</div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
              Correct!
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 24, fontSize: 13, color: 'var(--text-dim)' }}>
              <span>Hints: {session.summary.hints_used}</span>
              <span>Attempts: {session.summary.attempts}</span>
              <span>Score: {Math.round(session.summary.reward * 100)}%</span>
            </div>
          </div>
          {session.summary.ai_summary && session.summary.ai_summary.length > 0 && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 8 }}>
                Session Summary
              </div>
              <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {session.summary.ai_summary.map((bullet, i) => (
                  <li key={i} style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{bullet}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Timeout / ended overlay */}
      {(session.state === 'timeout' || session.state === 'ended') && session.summary && (
        <div className="notebook-card" style={{ padding: 24, animation: 'fadeIn 0.3s ease' }}>
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <div style={{ fontSize: 22, marginBottom: 8 }}>{session.state === 'timeout' ? '⏱' : '✓'}</div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
              {session.state === 'timeout' ? 'Session Time Limit Reached' : 'Session Complete'}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>Great effort — keep practicing!</div>
          </div>
          {session.summary.ai_summary && session.summary.ai_summary.length > 0 && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 8 }}>
                Session Summary
              </div>
              <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {session.summary.ai_summary.map((bullet, i) => (
                  <li key={i} style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{bullet}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Message list */}
      {session.messages.length > 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 8,
          maxHeight: 380, overflowY: 'auto', padding: '4px 0',
        }}>
          {session.messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} content={msg.content} />
          ))}
          {session.state === 'thinking' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <div className="spinner" style={{ width: 14, height: 14 }} />
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Tutor is thinking…</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Audio playback for voice mode */}
      <AudioPlayer text={lastTutorText} voiceMode={voiceMode} />

      {/* Scratchpad — shown when session has a problem */}
      {session.problem && isActive && (
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          <Scratchpad
            sessionId={sessionId}
            onWorkSubmitted={() => session.setScratchpadHasWork(true)}
            disabled={session.state === 'thinking'}
          />
        </div>
      )}

      {/* Input area — only when session is active */}
      {isActive && (
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>

          {/* Mode toggle */}
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="button"
              className={mode === 'chat' ? 'btn-caramel' : 'btn-ghost'}
              style={{ flex: 1, justifyContent: 'center', padding: '8px' }}
              onClick={() => setMode('chat')}>
              Ask a Question
            </button>
            <button type="button"
              className={mode === 'answer' ? 'btn-caramel' : 'btn-ghost'}
              style={{ flex: 1, justifyContent: 'center', padding: '8px' }}
              onClick={() => setMode('answer')}>
              Submit Answer
            </button>
          </div>

          {mode === 'chat' ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              {voiceMode ? (
                <div style={{ flex: 1, display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
                  <VoiceInput
                    onTranscript={(text) => {
                      setInputText(text)
                      // Auto-send when transcript arrives
                      session.sendText(text)
                      setInputText('')
                    }}
                    onLowConfidence={() => {
                      // Show system message asking to repeat
                    }}
                    disabled={session.state === 'thinking'}
                  />
                </div>
              ) : (
                <>
                  <input
                    type="text"
                    className="warm-input"
                    style={{ flex: 1 }}
                    value={inputText}
                    onChange={e => setInputText(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendText()}
                    placeholder="Ask the tutor anything about this problem…"
                    disabled={session.state === 'thinking'}
                  />
                  <button type="button" className="btn-caramel"
                    onClick={handleSendText}
                    disabled={!inputText.trim() || session.state === 'thinking'}>
                    Send
                  </button>
                </>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <MathInput
                value={answerText}
                onChange={setAnswerText}
                placeholder="Type your final answer…"
              />
              <button type="button" className="btn-caramel"
                style={{ justifyContent: 'center', padding: '11px' }}
                onClick={handleSubmitAnswer}
                disabled={!answerText.trim() || session.state === 'thinking'}>
                Check Answer
              </button>
            </div>
          )}

          {/* Hint button — gated on scratchpad work */}
          {session.hintLevel < session.maxHints && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <button type="button" className="btn-ghost"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={session.scratchpadHasWork ? session.requestHint : undefined}
                disabled={session.state === 'thinking' || !session.scratchpadHasWork}
                title={session.scratchpadHasWork ? undefined : 'Show your work in the scratchpad first'}>
                {session.hintLevel === 0 ? 'Get a Hint' : `Hint ${session.hintLevel + 1} of ${session.maxHints}`}
              </button>
              {!session.scratchpadHasWork && (
                <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', margin: 0 }}>
                  Show your work in the scratchpad to unlock hints
                </p>
              )}
            </div>
          )}

          {/* End session */}
          <button type="button" className="btn-ghost"
            style={{ width: '100%', justifyContent: 'center', opacity: 0.55, fontSize: 13 }}
            onClick={() => setShowEndConfirm(true)}>
            End Session
          </button>

          {/* Inline error (non-fatal, e.g. hint cap) */}
          {session.lastError && (
            <div style={{
              padding: '8px 12px', borderRadius: 8, fontSize: 13,
              background: 'var(--terra-dim)', border: '1px solid rgba(193,68,14,0.25)',
              color: 'var(--terracotta)',
            }}>
              {session.lastError}
            </div>
          )}
        </div>
      )}

      {/* Post-session back link */}
      {isDone && (
        <Link href={`/practice/${topicId}`} className="btn-ghost"
          style={{ justifyContent: 'center', marginTop: 4 }}>
          ← Back to Practice Mode
        </Link>
      )}
    </div>
  )
}
