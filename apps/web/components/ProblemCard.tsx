'use client'

import { useState, useRef } from 'react'
import { MathText } from '@/components/MathText'
import { MathInput } from '@/components/MathInput'
import { ProblemResponse } from '@/lib/api-client'

const DIFFICULTY_LABEL: Record<number, string> = {
  1: 'Introductory', 2: 'Easy', 3: 'Medium', 4: 'Hard', 5: 'Advanced', 6: 'Expert',
}

function normalizeAnswer(s: string): string {
  return s.trim().toLowerCase()
    .replace(/\s+/g, '')
    .replace(/\\[a-z]+/g, '')
    .replace(/[{}]/g, '')
    .replace(/\*\*/g, '')
    .replace(/\^/g, '')
}

// ---------------------------------------------------------------------------
// Proof table — rendered from structured proof_rows data
// ---------------------------------------------------------------------------

function ProofReasonCell({ text }: { text: string }) {
  if (text === '___') {
    return (
      <span style={{
        display: 'inline-block', minWidth: 160,
        borderBottom: '2px solid var(--caramel)',
        color: 'var(--caramel)', fontStyle: 'italic', fontSize: 12, paddingBottom: 2,
      }}>
        fill in property
      </span>
    )
  }
  return <MathText latex={text} prose />
}

function ProofTable({ rows }: { rows: Array<{ stmt: string; reason: string }> }) {
  return (
    <div style={{ overflowX: 'auto', margin: '14px 0' }}>
      <table style={{
        width: '100%', borderCollapse: 'collapse',
        fontSize: 14, fontFamily: 'var(--font-fraunces), Georgia, serif',
      }}>
        <thead>
          <tr>
            {['Statement', 'Reason'].map(h => (
              <th key={h} style={{
                padding: '8px 14px', textAlign: 'left',
                background: 'var(--surface2)', borderBottom: '2px solid var(--border2)',
                fontSize: 11, fontWeight: 700, letterSpacing: '0.06em',
                textTransform: 'uppercase', color: 'var(--text-dim)',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '9px 14px', color: 'var(--text)', verticalAlign: 'top' }}>
                <MathText latex={row.stmt} prose />
              </td>
              <td style={{ padding: '9px 14px', color: 'var(--text)', verticalAlign: 'top' }}>
                <ProofReasonCell text={row.reason} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Prompt renderer — handles three formats:
//   1. Proof problems: structured proof_rows from solution + prose statement
//   2. Algebra problems: "Solve for $x$: $equation$" (split into label + big equation)
//   3. Everything else: plain prose with inline $...$ math
// ---------------------------------------------------------------------------

function renderPrompt(raw: string, proofRows?: Array<{ stmt: string; reason: string }>) {
  // Proof with structured rows
  if (proofRows && proofRows.length > 0) {
    // Split statement at the closing question (last sentence)
    const qIdx = raw.lastIndexOf('Which ')
    const setup    = qIdx !== -1 ? raw.slice(0, qIdx).trim() : raw
    const question = qIdx !== -1 ? raw.slice(qIdx).trim() : ''
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{
          fontSize: 15, lineHeight: 1.75, color: 'var(--text)',
          fontFamily: 'var(--font-fraunces), Georgia, serif',
        }}>
          <MathText latex={setup} prose />
        </div>
        <ProofTable rows={proofRows} />
        {question && (
          <div style={{
            fontSize: 15, lineHeight: 1.6, color: 'var(--text)',
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontWeight: 500,
          }}>
            <MathText latex={question} prose />
          </div>
        )}
      </div>
    )
  }

  // Algebra: "Solve for $x$: $equation$" — split into label + big equation
  const splitIdx = raw.search(/:\s*\$/)
  if (splitIdx !== -1) {
    const label = raw.slice(0, splitIdx + 1)
    const eq    = raw.slice(splitIdx + 1).trim()
    return (
      <div>
        <div style={{
          fontSize: 15, lineHeight: 1.6, color: 'var(--text-dim)',
          fontFamily: 'var(--font-fraunces), Georgia, serif', marginBottom: 10,
        }}>
          <MathText latex={label} prose />
        </div>
        <div style={{
          fontSize: 20, lineHeight: 1.5, color: 'var(--text)',
          fontFamily: 'var(--font-fraunces), Georgia, serif', padding: '10px 0 4px',
        }}>
          <MathText latex={eq} prose />
        </div>
      </div>
    )
  }

  // Generic prose
  return (
    <div style={{
      fontSize: 16, lineHeight: 1.75, color: 'var(--text)',
      fontFamily: 'var(--font-fraunces), Georgia, serif',
    }}>
      <MathText latex={raw} prose />
    </div>
  )
}

// ---------------------------------------------------------------------------

interface ProblemCardProps {
  problem: ProblemResponse
  onSubmit?: (answer: string, timeTakenSeconds: number) => void
  disabled?: boolean
  answerValue?: string
  onAnswerChange?: (v: string) => void
  feedback?: string | null
  onReveal?: () => void
  checking?: boolean
}

export function ProblemCard({
  problem, onSubmit, disabled = false, answerValue, onAnswerChange,
  feedback = null, onReveal, checking = false,
}: ProblemCardProps) {
  const [internalAnswer, setInternalAnswer] = useState('')
  const answer = answerValue !== undefined ? answerValue : internalAnswer
  const setAnswer = (v: string) => { setInternalAnswer(v); onAnswerChange?.(v) }
  const startRef = useRef(Date.now())

  const isTextAnswer = problem.answer_type === 'text' || problem.answer_type === 'proof_reason'

  function handleSubmit() {
    if (!onSubmit || disabled || !answer.trim()) return
    const timeTaken = Math.round((Date.now() - startRef.current) / 1000)
    onSubmit(answer, timeTaken)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className="notebook-card" style={{ animation: 'cardIn 0.5s 0.05s both cubic-bezier(0.16,1,0.3,1)' }}>
      {/* Header row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 18,
      }}>
        <div className="card-eyebrow" style={{ marginBottom: 0 }}>Problem</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {problem.calculator_mode !== 'none' && (
            <span className="warm-tag" style={{ fontSize: 11 }}>
              {problem.calculator_mode} calc
            </span>
          )}
          <span className="warm-tag">
            {DIFFICULTY_LABEL[problem.difficulty] ?? `Level ${problem.difficulty}`}
          </span>
        </div>
      </div>

      {/* Problem statement */}
      <div style={{ marginBottom: 24 }}>
        {renderPrompt(
          problem.prompt_latex ?? '',
          (problem.solution as { proof_rows?: Array<{ stmt: string; reason: string }> } | null)?.proof_rows,
        )}
      </div>

      {/* Answer input */}
      {!disabled && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label style={{
            fontSize: 12, fontWeight: 600, color: 'var(--text-dim)',
            textTransform: 'uppercase', letterSpacing: '0.08em',
          }}>
            Your answer
          </label>

          {isTextAnswer ? (
            <input
              type="text"
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer…"
              style={{
                width: '100%', boxSizing: 'border-box',
                padding: '10px 14px', fontSize: 15,
                borderRadius: 8, border: '1px solid var(--border)',
                background: 'var(--surface)', color: 'var(--text)',
                outline: 'none', fontFamily: 'inherit',
              }}
            />
          ) : (
            <MathInput
              value={answer}
              onChange={setAnswer}
              placeholder="Type your answer…"
              className="warm-input"
            />
          )}

          {feedback && (
            <div role="status" style={{
              borderRadius: 8, border: '1px solid rgba(193,68,14,0.25)',
              background: 'var(--terra-dim)', padding: '10px 14px',
              fontSize: 13, color: 'var(--terracotta)', lineHeight: 1.5,
            }}>
              {feedback}
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!answer.trim() || checking}
            className="btn-caramel"
            style={{ justifyContent: 'center', padding: '11px' }}
          >
            {checking ? 'Checking…' : feedback ? 'Try Again' : 'Check Answer'}
          </button>

          {feedback && onReveal && (
            <button
              type="button"
              onClick={onReveal}
              disabled={checking}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 13, color: 'var(--text-dim)', textDecoration: 'underline',
                padding: '2px', alignSelf: 'center',
              }}
            >
              Show me the solution
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export { normalizeAnswer }
