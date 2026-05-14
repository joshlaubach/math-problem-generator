'use client'

import { useState } from 'react'
import { MathText } from './MathText'
import { MathScratchpad } from './MathScratchpad'
import type { LessonStep } from '@/lib/api-client'

interface PartialExampleProps {
  steps: LessonStep[]
  topicId: string
}

export function PartialExample({ steps, topicId: _ }: PartialExampleProps) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})
  const [scratchpadOpen, setScratchpadOpen] = useState(false)
  const [hasWork, setHasWork] = useState(false)

  if (!steps || steps.length === 0) return null

  // Step 0 is the problem statement — rendered as a problem card, not a numbered step
  const problemStep = steps[0]
  const workingSteps = steps.slice(1)
  let stepCounter = 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

      {/* Problem card */}
      {problemStep && (
        <div style={{
          padding: '16px 20px', borderRadius: 12, marginBottom: 20,
          border: '1.5px solid rgba(196,151,106,0.4)',
          background: 'var(--caramel-dim)',
        }}>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: '0.07em',
            textTransform: 'uppercase', color: 'var(--caramel)', marginBottom: 10,
          }}>
            Problem
          </div>
          {problemStep.expression_latex && (
            <div style={{ marginBottom: problemStep.description_latex ? 10 : 0 }}>
              <MathText latex={problemStep.expression_latex} />
            </div>
          )}
          {problemStep.description_latex && (
            <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
              <MathText latex={problemStep.description_latex} prose />
            </div>
          )}
        </div>
      )}

      {/* Scratchpad toggle */}
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => setScratchpadOpen(v => !v)}
          style={{
            fontSize: 12, padding: '5px 12px', borderRadius: 8,
            border: '1px solid var(--border)', background: 'none',
            cursor: 'pointer', color: 'var(--text-dim)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <span>{scratchpadOpen ? '▾' : '▸'}</span>
          {scratchpadOpen ? 'Hide scratchpad' : 'Open scratchpad'}
          {hasWork && !scratchpadOpen && (
            <span style={{
              fontSize: 10, padding: '1px 6px', borderRadius: 4,
              background: 'var(--caramel-dim)', color: 'var(--caramel)',
              fontWeight: 600,
            }}>
              ✓ work saved
            </span>
          )}
        </button>

        {scratchpadOpen && (
          <div style={{ marginTop: 10 }}>
            <MathScratchpad onChange={setHasWork} />
          </div>
        )}
      </div>

      {/* Working steps */}
      {workingSteps.map((step, i) => {
        const isStudentStep = step.student_completes
        const isRevealed = revealed[i + 1]
        if (!isStudentStep) stepCounter++
        const displayNum = isStudentStep ? '?' : stepCounter

        return (
          <div
            key={i}
            style={{
              display: 'flex', gap: 16, alignItems: 'flex-start',
              padding: '14px 0',
              borderBottom: i < workingSteps.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <div style={{
              width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
              background: isStudentStep ? 'transparent' : 'var(--caramel)',
              border: isStudentStep ? '2px dashed var(--caramel)' : 'none',
              color: isStudentStep ? 'var(--caramel)' : '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700, marginTop: 2,
            }}>
              {displayNum}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              {step.description_latex && (
                <div style={{
                  fontSize: 14,
                  color: isStudentStep ? 'var(--caramel)' : 'var(--text-dim)',
                  lineHeight: 1.65, marginBottom: step.expression_latex ? 8 : 0,
                  fontWeight: isStudentStep ? 500 : 400,
                }}>
                  <MathText latex={step.description_latex} prose />
                </div>
              )}

              {!isStudentStep && step.expression_latex && (
                <div style={{
                  padding: '8px 12px', borderRadius: 8,
                  background: 'var(--surface2)', border: '1px solid var(--border)',
                  overflowX: 'auto',
                }}>
                  <MathText latex={step.expression_latex} />
                </div>
              )}

              {isStudentStep && (
                <>
                  {isRevealed && step.expression_latex ? (
                    <div style={{
                      padding: '8px 12px', borderRadius: 8,
                      background: 'var(--sage-dim, rgba(100,150,100,0.08))',
                      border: '1px solid rgba(100,150,100,0.25)',
                      overflowX: 'auto',
                    }}>
                      <MathText latex={step.expression_latex} />
                    </div>
                  ) : (
                    <button
                      onClick={() => setRevealed(r => ({ ...r, [i + 1]: true }))}
                      disabled={!hasWork}
                      title={hasWork ? undefined : 'Open the scratchpad and show your work first'}
                      style={{
                        fontSize: 13, padding: '8px 16px', borderRadius: 8,
                        border: '1px dashed var(--caramel)',
                        background: hasWork ? 'var(--caramel-dim)' : 'var(--surface2)',
                        color: hasWork ? 'var(--caramel)' : 'var(--text-muted)',
                        cursor: hasWork ? 'pointer' : 'not-allowed',
                        fontWeight: 500,
                      }}
                    >
                      {hasWork ? 'Reveal this step →' : 'Show your work in the scratchpad to reveal'}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
