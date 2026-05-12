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
            <MathText latex={problem.final_answer} inline />
          </div>
        </div>

        {/* Worked solution */}
        {problem.solution && Object.keys(problem.solution).length > 0 && (
          <div>
            <div className="card-eyebrow">Solution</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(problem.solution).map(([key, val]) => {
                // Array of step objects: { expression_latex, description_latex }
                if (Array.isArray(val)) {
                  return (
                    <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(val as { expression_latex?: string; description_latex?: string }[]).map((step, i) => (
                        <div key={i} style={{
                          borderRadius: 7, background: 'var(--surface2)',
                          padding: '10px 14px', fontSize: 14,
                          display: 'flex', flexDirection: 'column', gap: 4,
                        }}>
                          {step.expression_latex && (
                            <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                              <MathText latex={step.expression_latex} prose />
                            </div>
                          )}
                          {step.description_latex && (
                            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
                              <MathText latex={step.description_latex} prose />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                }
                // Scalar value
                return (
                  <div
                    key={key}
                    style={{
                      borderRadius: 7, background: 'var(--surface2)',
                      padding: '9px 14px', fontSize: 14,
                      color: 'var(--text-dim)', display: 'flex', gap: 8, alignItems: 'baseline',
                    }}
                  >
                    <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', flexShrink: 0 }}>
                      {key}
                    </span>
                    {typeof val === 'string'
                      ? val.includes('\\') ? <MathText latex={val} inline /> : <span>{val}</span>
                      : <span>{String(val)}</span>
                    }
                  </div>
                )
              })}
            </div>
          </div>
        )}

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
