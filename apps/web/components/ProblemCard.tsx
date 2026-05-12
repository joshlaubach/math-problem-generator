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

interface ProblemCardProps {
  problem: ProblemResponse
  onSubmit?: (answer: string, timeTakenSeconds: number) => void
  disabled?: boolean
  /** Controlled answer value — when provided, the card uses it instead of internal state */
  answerValue?: string
  /** Called when answer changes — required when answerValue is provided */
  onAnswerChange?: (v: string) => void
}

export function ProblemCard({
  problem, onSubmit, disabled = false, answerValue, onAnswerChange,
}: ProblemCardProps) {
  const [internalAnswer, setInternalAnswer] = useState('')
  const answer = answerValue !== undefined ? answerValue : internalAnswer
  const setAnswer = (v: string) => { setInternalAnswer(v); onAnswerChange?.(v) }
  const startRef = useRef(Date.now())

  function handleSubmit() {
    if (!onSubmit || disabled || !answer.trim()) return
    const timeTaken = Math.round((Date.now() - startRef.current) / 1000)
    onSubmit(answer, timeTaken)
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

      {/* Problem statement — prose mode handles mixed text + $...$ math */}
      <div style={{
        fontSize: 16,
        lineHeight: 1.75,
        color: 'var(--text)',
        marginBottom: 24,
        fontFamily: 'var(--font-fraunces), Georgia, serif',
      }}>
        <MathText latex={problem.prompt_latex} prose />
      </div>

      {/* Answer input */}
      {!disabled && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Your answer
          </label>
          <MathInput
            value={answer}
            onChange={setAnswer}
            placeholder="Type your answer…"
            className="warm-input"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!answer.trim()}
            className="btn-caramel"
            style={{ justifyContent: 'center', padding: '11px' }}
          >
            Check Answer
          </button>
        </div>
      )}
    </div>
  )
}

export { normalizeAnswer }
