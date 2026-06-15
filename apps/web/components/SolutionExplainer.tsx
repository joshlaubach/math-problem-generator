'use client'

import { MathText } from '@/components/MathText'
import { ProblemResponse } from '@/lib/api-client'

interface SolutionExplainerProps {
  problem: ProblemResponse
  isCorrect: boolean
  studentAnswer: string
  onNext: () => void
}

export function SolutionExplainer({ problem, isCorrect, studentAnswer, onNext }: SolutionExplainerProps) {
  return (
    <div
      className="warm-card-static"
      style={{
        overflow: 'hidden',
        animation: 'hintReveal 0.4s cubic-bezier(0.16,1,0.3,1) both',
      }}
    >
      {/* Result banner */}
      <div
        className={isCorrect ? 'result-correct' : 'result-wrong'}
        style={{ padding: '16px 22px', display: 'flex', alignItems: 'center', gap: 12 }}
      >
        <span style={{ fontSize: 24 }} aria-hidden>{isCorrect ? '✓' : '✗'}</span>
        <div>
          <p style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 16, fontWeight: 600,
            color: isCorrect ? 'var(--forest)' : 'var(--terracotta)',
            marginBottom: 2,
          }}>
            {isCorrect ? 'Correct!' : 'Not quite.'}
          </p>
          {!isCorrect && (
            <p style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              Your answer: <code style={{ fontFamily: 'monospace', color: 'var(--terracotta)' }}>{studentAnswer || '(empty)'}</code>
            </p>
          )}
        </div>
      </div>

      <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        {/* Correct answer */}
        <div>
          <div className="card-eyebrow">Correct Answer</div>
          <div style={{
            borderRadius: 8,
            background: 'var(--surface2)',
            padding: '10px 14px',
            fontSize: 15,
            color: 'var(--text)',
          }}>
            {problem.answer_type === 'text' || problem.answer_type === 'proof_reason'
              ? <span>{problem.final_answer}</span>
              : <MathText latex={problem.final_answer} inline />
            }
          </div>
        </div>

        {/* Worked solution — render only the structured steps. Never iterate the
            whole solution object: it may carry internal fields (final_answer_latex,
            sympy_verified, verification_details) that must not reach the student. */}
        {(() => {
          const steps = Array.isArray((problem.solution as { steps?: unknown } | null)?.steps)
            ? ((problem.solution as { steps: { expression_latex?: string; description_latex?: string }[] }).steps)
            : []
          if (steps.length === 0) return null
          return (
            <div>
              <div className="card-eyebrow">Solution</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {steps.map((step, i) => (
                  <div key={i} style={{
                    borderRadius: 7, background: 'var(--surface2)',
                    padding: '10px 14px', fontSize: 14,
                    display: 'flex', flexDirection: 'column', gap: 4,
                  }}>
                    {/* Description is prose ("Divide both sides by $-3$"); the
                        expression is a bare LaTeX equation, so render it as math. */}
                    {step.description_latex && (
                      <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                        <MathText latex={step.description_latex} prose />
                      </div>
                    )}
                    {step.expression_latex && (
                      <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                        {/* Prose mode for steps with embedded $...$ (DM proofs, mixed text+math).
                            Plain text for single words with no math operators (e.g. "substitution").
                            Inline math for pure LaTeX expressions (algebra/calculus). */}
                        {step.expression_latex.includes('$')
                          ? <MathText latex={step.expression_latex} prose />
                          : /^[a-zA-Z\s]+$/.test(step.expression_latex.trim())
                            ? <span>{step.expression_latex}</span>
                            : <MathText latex={step.expression_latex} inline />
                        }
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })()}

        {/* Next button */}
        <button
          type="button"
          onClick={onNext}
          className="btn-caramel"
          style={{ justifyContent: 'center', padding: '12px' }}
        >
          Next Problem →
        </button>
      </div>
    </div>
  )
}
