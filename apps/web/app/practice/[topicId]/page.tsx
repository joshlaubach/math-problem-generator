'use client'

import { useState, useRef, useEffect } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { useAuth, useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { Lightbulb, Robot, Lock, Star } from '@phosphor-icons/react'
import { api, ApiError, ProblemResponse, CalculatorMode } from '@/lib/api-client'
import { ProblemCard, normalizeAnswer } from '@/components/ProblemCard'
import { HintPanel } from '@/components/HintPanel'
import { SolutionExplainer } from '@/components/SolutionExplainer'
import { DifficultySelector } from '@/components/DifficultySelector'
import { BottomSheet } from '@/components/BottomSheet'
import { CalculatorToggleButton, ResponsiveCalculator } from '@/components/CalculatorSidebar'
import { TopicName, stripHonors } from '@/components/TopicName'

type Phase = 'setup' | 'loading' | 'active' | 'reviewing'
type RightTab = 'hints' | 'tutor'

const CALC_LABELS: Record<CalculatorMode, string> = {
  none: '',
  scientific: 'Scientific Calculator Required',
  graphing:   'Graphing Calculator Required',
  cas:        'CAS Required',
}

const HONORS_FULL_TIERS    = new Set(['honors', 'classroom-student'])
const HONORS_PARTIAL_TIERS = new Set(['student'])

// ── Calculator badge ──────────────────────────────────────────────────────────
function CalculatorBadge({ mode }: { mode: CalculatorMode }) {
  if (mode === 'none') return null
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: 'var(--caramel-dim)',
      border: '1px solid rgba(196,151,106,0.35)',
      borderRadius: 8, padding: '4px 12px',
      fontSize: 12, fontWeight: 600, color: 'var(--caramel)',
    }}>
      {CALC_LABELS[mode]}
    </div>
  )
}

// ── Accuracy ring ─────────────────────────────────────────────────────────────
function AccuracyRing({ correct, attempted }: { correct: number; attempted: number }) {
  const pct = attempted === 0 ? 0 : Math.round((correct / attempted) * 100)
  const r = 18
  const c = 2 * Math.PI * r
  return (
    <div style={{ position: 'relative', width: 44, height: 44, flexShrink: 0 }}>
      <svg width="44" height="44" viewBox="0 0 44 44" style={{ transform: 'rotate(-90deg)' }}>
        <circle fill="none" stroke="var(--border2)" strokeWidth="4" cx="22" cy="22" r={r} />
        <circle fill="none" stroke="var(--caramel)" strokeWidth="4" strokeLinecap="round"
          cx="22" cy="22" r={r}
          strokeDasharray={c}
          strokeDashoffset={attempted === 0 ? c : c * (1 - pct / 100)}
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 12, fontWeight: 700, color: 'var(--caramel)',
      }}>
        {attempted === 0 ? '–' : `${pct}%`}
      </div>
    </div>
  )
}

// ── Hints empty state ─────────────────────────────────────────────────────────
function HintsEmptyState() {
  return (
    <div className="warm-card-static" style={{
      padding: 24,
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
      minHeight: 140, justifyContent: 'center',
    }}>
      <Lightbulb size={28} color="var(--text-muted)" weight="thin" />
      <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', margin: 0 }}>
        Start a problem to unlock hints
      </p>
    </div>
  )
}

// ── Session stats panel ───────────────────────────────────────────────────────
function SessionStatsPanel({ correct, attempted }: { correct: number; attempted: number }) {
  return (
    <div className="warm-card-static" style={{ padding: 24 }}>
      <div className="card-eyebrow">Session Stats</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {[
          { label: 'Problems attempted', value: attempted },
          { label: 'Correct answers',    value: correct },
          { label: 'Accuracy',           value: `${attempted === 0 ? 0 : Math.round((correct / attempted) * 100)}%` },
        ].map(row => (
          <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
            <span style={{ color: 'var(--text-dim)' }}>{row.label}</span>
            <span style={{ fontWeight: 600, color: 'var(--text)' }}>{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Tutor launcher panel ──────────────────────────────────────────────────────
function TutorLauncherPanel({
  topicId,
  topicName,
  difficulty,
  userTier,
}: {
  topicId: string
  topicName: string
  difficulty: number
  userTier: string
}) {
  const isFree = userTier === 'free'

  return (
    <div className="warm-card-static" style={{ padding: 24 }}>
      <div className="card-eyebrow" style={{ marginBottom: 8 }}>Tutor Mode</div>
      <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 16 }}>
        Work through a problem step-by-step with an AI tutor using Socratic guidance.
      </p>
      {isFree ? (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 0,
          background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.25)',
          fontSize: 13, color: 'var(--text-dim)',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--caramel)' }}>Tutor Mode</span> is available on paid plans.{' '}
          <a href="/pricing" style={{ color: 'var(--caramel)', textDecoration: 'underline' }}>Upgrade →</a>
        </div>
      ) : (
        <Link
          href={`/tutor/new?topic=${topicId}&name=${encodeURIComponent(topicName)}`}
          className="btn-caramel"
          style={{ display: 'flex', justifyContent: 'center', textDecoration: 'none' }}
        >
          Start Tutor Session →
        </Link>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function PracticePage() {
  const { topicId } = useParams<{ topicId: string }>()
  const searchParams = useSearchParams()
  const { getToken } = useAuth()
  const { user } = useUser()

  const userTier  = (user?.publicMetadata?.tier as string | undefined) ?? 'free'
  const isTeacher = userTier === 'classroom-student' || (user?.publicMetadata?.is_teacher as boolean | undefined)

  const [phase, setPhase]         = useState<Phase>('setup')
  const [difficulty, setDifficulty] = useState(3)
  const [rightTab, setRightTab]   = useState<RightTab>('hints')
  const [problem, setProblem]     = useState<ProblemResponse | null>(null)
  const [result, setResult]       = useState<{ isCorrect: boolean; answer: string } | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [sessionStats, setSessionStats] = useState({ attempted: 0, correct: 0 })
  const [calcMode, setCalcMode]   = useState<CalculatorMode>('none')
  const [isHonors, setIsHonors]   = useState(false)
  const [calcOpen, setCalcOpen]   = useState(false)
  const [hintsOpen, setHintsOpen] = useState(false)
  const [answerValue, setAnswerValue] = useState('')
  const sessionId   = useRef(`session-${Date.now()}`).current
  const startTimeRef = useRef(Date.now())
  const [topicName, setTopicName] = useState<string>(
    searchParams.get('name') ?? topicId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  )

  useEffect(() => {
    api.getTopicsLegacy().then(topics => {
      const match = topics.find(t => t.topic_id === topicId)
      if (match) {
        if (!searchParams.get('name')) setTopicName(match.topic_name)
        setCalcMode(match.calculator_mode ?? 'none')
        setIsHonors(match.is_honors ?? false)
      }
    }).catch(() => {})
  }, [topicId, searchParams])

  const honorsBlocked = isHonors && !HONORS_FULL_TIERS.has(userTier) && !HONORS_PARTIAL_TIERS.has(userTier)

  async function startProblem() {
    setPhase('loading')
    setError(null)
    setProblem(null)
    setResult(null)
    try {
      const token = await getToken()
      const p = await api.generateProblem(token ?? '', {
        topic_id: topicId,
        difficulty,
        calculator_mode: calcMode,
      })
      setProblem(p)
      setAnswerValue('')
      startTimeRef.current = Date.now()
      setPhase('active')
      setRightTab('hints')
    } catch (err) {
      const msg = err instanceof ApiError
        ? err.status === 404
          ? `Topic "${topicId}" is not available yet. Try another topic.`
          : err.message
        : 'Failed to generate problem. Make sure the API server is running.'
      setError(msg)
      setPhase('setup')
    }
  }

  async function handleAnswer(answer: string, timeTakenSeconds: number) {
    if (!problem) return
    const isCorrect = normalizeAnswer(answer) === normalizeAnswer(problem.final_answer)
    setResult({ isCorrect, answer })
    setPhase('reviewing')
    setSessionStats(s => ({ attempted: s.attempted + 1, correct: s.correct + (isCorrect ? 1 : 0) }))
    try {
      const token = await getToken()
      await api.submitAttempt(token ?? '', {
        user_id: user?.id ?? 'anonymous',
        problem_id: problem.id,
        topic_id: problem.topic_id,
        course_id: problem.course_id,
        difficulty: problem.difficulty,
        is_correct: isCorrect,
        time_taken_seconds: timeTakenSeconds,
      })
    } catch { /* fire-and-forget */ }
  }

  function handleTeacherReveal() {
    if (!problem) return
    setResult({ isCorrect: true, answer: problem.final_answer })
    setPhase('reviewing')
  }

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <Link href="/catalog">Catalog</Link>
          <span className="sep">/</span>
          <span className="current">{stripHonors(topicName)}</span>
        </nav>
      </div>

      <div className="page-content" style={{ paddingBottom: 40 }}>

        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 20, marginBottom: 16 }}>
          <div>
            <h1 className="display-heading" style={{ marginBottom: 4 }}>
              <TopicName name={topicName} badgeSize={13} />
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <p style={{ fontSize: 14, color: 'var(--text-dim)', margin: 0 }}>
                {sessionStats.attempted === 0
                  ? 'Choose a difficulty and start your first problem.'
                  : `${sessionStats.correct} of ${sessionStats.attempted} correct this session`}
              </p>
              <CalculatorBadge mode={calcMode} />
              <CalculatorToggleButton
                calcMode={calcMode}
                open={calcOpen}
                onToggle={() => setCalcOpen(o => !o)}
              />
              {isHonors && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  background: 'rgba(212,168,122,0.15)',
                  border: '1px solid rgba(196,151,106,0.3)',
                  borderRadius: 6, padding: '3px 9px',
                  fontSize: 11, fontWeight: 600, color: 'var(--caramel)',
                }}>
                  <Star size={11} weight="fill" /> Honors
                </span>
              )}
            </div>
          </div>

          {sessionStats.attempted > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12,
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '10px 16px', animation: 'fadeIn 0.3s ease',
            }}>
              <AccuracyRing correct={sessionStats.correct} attempted={sessionStats.attempted} />
              <div>
                <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 18, fontWeight: 600, color: 'var(--text)', lineHeight: 1 }}>
                  {sessionStats.correct}/{sessionStats.attempted}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>correct</div>
              </div>
            </div>
          )}
        </div>

        {/* Honors gate */}
        {honorsBlocked ? (
          <div className="warm-card-static" style={{
            padding: '28px 32px', maxWidth: 520, textAlign: 'center',
            borderLeft: '4px solid var(--caramel)', animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both',
          }}>
            <Lock size={28} color="var(--caramel)" style={{ marginBottom: 12 }} />
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
              Honors Content
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 20 }}>
              This is an honors topic, available on the <strong style={{ color: 'var(--caramel)' }}>Student plan</strong> and above.
            </p>
            <Link href="/pricing" className="btn-caramel" style={{ textDecoration: 'none', display: 'inline-flex' }}>
              View plans →
            </Link>
          </div>
        ) : (
          <div className={`practice-grid${calcOpen ? ' calc-open' : ''}`}>

            {/* ── Left column ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>

              {/* Setup */}
              {phase === 'setup' && (
                <div className="warm-card-static" style={{ padding: 28, animation: 'viewIn 0.4s cubic-bezier(0.16,1,0.3,1) both' }}>
                  <DifficultySelector value={difficulty} onChange={setDifficulty} />
                  {error && (
                    <div style={{
                      marginTop: 16, borderRadius: 8,
                      border: '1px solid rgba(193,68,14,0.25)', background: 'var(--terra-dim)',
                      padding: '12px 16px', fontSize: 13, color: 'var(--terracotta)', lineHeight: 1.5,
                    }}>
                      {error}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={startProblem}
                    className="btn-caramel"
                    style={{ marginTop: 20, width: '100%', justifyContent: 'center', padding: '12px' }}
                  >
                    {sessionStats.attempted === 0 ? '✦ Start Session' : '→ Next Problem'}
                  </button>
                </div>
              )}

              {/* Loading */}
              {phase === 'loading' && (
                <div className="warm-card-static" style={{ padding: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                  <div className="spinner" />
                  <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Generating your problem…</p>
                </div>
              )}

              {/* Active + reviewing */}
              {(phase === 'active' || phase === 'reviewing') && problem && (
                <>
                  {isTeacher && phase === 'active' && (
                    <button
                      type="button"
                      onClick={handleTeacherReveal}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        background: 'var(--surface2)', border: '1px solid var(--border)',
                        borderRadius: 8, padding: '8px 16px',
                        fontSize: 13, fontWeight: 500, color: 'var(--text-dim)',
                        cursor: 'pointer', transition: 'all 0.2s',
                        alignSelf: 'flex-start',
                      }}
                    >
                      Reveal Solution (Teacher)
                    </button>
                  )}

                  <ProblemCard
                    problem={problem}
                    onSubmit={phase === 'active' ? handleAnswer : undefined}
                    disabled={phase === 'reviewing'}
                    answerValue={answerValue}
                    onAnswerChange={setAnswerValue}
                  />

                  {phase === 'reviewing' && result && (
                    <SolutionExplainer
                      problem={problem}
                      isCorrect={result.isCorrect}
                      studentAnswer={result.answer}
                      onNext={() => setPhase('setup')}
                    />
                  )}

                  {/* Mobile: session stats inline during reviewing */}
                  {phase === 'reviewing' && (
                    <div className="md:hidden">
                      <SessionStatsPanel correct={sessionStats.correct} attempted={sessionStats.attempted} />
                    </div>
                  )}

                  {/* Mobile: hints trigger */}
                  {phase === 'active' && (
                    <button
                      type="button"
                      className="md:hidden btn-ghost"
                      onClick={() => setHintsOpen(true)}
                      style={{ width: '100%', justifyContent: 'center' }}
                    >
                      <Lightbulb size={15} weight="bold" /> Get Hints
                    </button>
                  )}
                </>
              )}
            </div>

            {/* ── Right column (desktop only) ── */}
            <div className="hidden md:flex" style={{ flexDirection: 'column' }}>
              <div className="right-panel-tabs">
                <button
                  type="button"
                  className={`right-panel-tab ${rightTab === 'hints' ? 'active' : ''}`}
                  onClick={() => setRightTab('hints')}
                >
                  <Lightbulb size={14} weight={rightTab === 'hints' ? 'fill' : 'regular'} /> Hints
                </button>
                <button
                  type="button"
                  className={`right-panel-tab ${rightTab === 'tutor' ? 'active' : ''}`}
                  onClick={() => setRightTab('tutor')}
                >
                  <Robot size={14} weight={rightTab === 'tutor' ? 'fill' : 'regular'} /> Tutor
                </button>
              </div>

              {rightTab === 'hints' && (
                <>
                  {(phase === 'setup' || phase === 'loading') && <HintsEmptyState />}
                  {phase === 'active' && problem && (
                    <HintPanel
                      problem={problem}
                      getToken={getToken}
                      userTier={userTier}
                      isTeacher={!!isTeacher}
                    />
                  )}
                  {phase === 'reviewing' && (
                    <SessionStatsPanel correct={sessionStats.correct} attempted={sessionStats.attempted} />
                  )}
                </>
              )}

              {rightTab === 'tutor' && (
                <TutorLauncherPanel
                  topicId={topicId}
                  topicName={topicName}
                  difficulty={difficulty}
                  userTier={userTier}
                />
              )}
            </div>

            {/* ── Calculator (third column, desktop) ── */}
            <ResponsiveCalculator
              open={calcOpen}
              onClose={() => setCalcOpen(false)}
              calcMode={calcMode}
              difficulty={difficulty}
              userTier={userTier}
              getToken={getToken}
              onSendToAnswer={setAnswerValue}
              topicId={topicId}
              problemId={problem?.id}
              sessionId={sessionId}
            />
          </div>
        )}
      </div>

      {/* Mobile: hints bottom sheet */}
      <BottomSheet open={hintsOpen} onClose={() => setHintsOpen(false)} title="Hints">
        {problem && (
          <HintPanel
            problem={problem}
            getToken={getToken}
            userTier={userTier}
            isTeacher={!!isTeacher}
          />
        )}
      </BottomSheet>
    </>
  )
}
