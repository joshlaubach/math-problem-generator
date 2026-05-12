'use client'

import { useState } from 'react'
import { MathText } from './MathText'
import { Scratchpad } from './Scratchpad'
import type { LessonStep } from '@/lib/api-client'

interface PartialExampleProps {
  steps: LessonStep[]
  topicId: string
}

export function PartialExample({ steps, topicId }: PartialExampleProps) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})
  const [scratchpadOpen, setScratchpadOpen] = useState(false)
  const [scratchpadHasWork, setScratchpadHasWork] = useState(false)

  if (!steps || steps.length === 0) return null

  const sessionId = `lesson-partial-${topicId}`

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Scratchpad toggle */}
      <div style={{ marginBottom: 12 }}>
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
          {scratchpadOpen ? 'Hide scratchpad' : 'Open scratchpad to show your work'}
        </button>
        {scratchpadOpen && (
          <div style={{ marginTop: 10 }}>
            <Scratchpad
              sessionId={sessionId}
              onWorkSubmitted={() => setScratchpadHasWork(true)}
              disabled={false}
            />
          </div>
        )}
      </div>

      {steps.map((step, i) => {
        const isStudentStep = step.student_completes
        const isRevealed = revealed[i]

        return (
          <div
            key={i}
            style={{
              display: 'flex', gap: 16, alignItems: 'flex-start',
              padding: '14px 0',
              borderBottom: i < steps.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            {/* Step indicator */}
            <div style={{
              width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
              background: isStudentStep ? 'transparent' : 'var(--caramel)',
              border: isStudentStep ? '2px dashed var(--caramel)' : 'none',
              color: isStudentStep ? 'var(--caramel)' : '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700, marginTop: 2,
            }}>
              {isStudentStep ? '?' : i + 1}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              {/* Description always shown */}
              {step.description_latex && (
                <div style={{
                  fontSize: 14,
                  color: isStudentStep ? 'var(--caramel)' : 'var(--text-dim)',
                  lineHeight: 1.65, marginBottom: 8,
                  fontWeight: isStudentStep ? 500 : 400,
                }}>
                  <MathText latex={step.description_latex} prose />
                </div>
              )}

              {/* Expression: shown for given steps; hidden behind reveal for student steps */}
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
                <div>
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
                      onClick={() => setRevealed(r => ({ ...r, [i]: true }))}
                      disabled={!scratchpadHasWork}
                      title={scratchpadHasWork ? undefined : 'Show your work in the scratchpad first'}
                      style={{
                        fontSize: 13, padding: '8px 16px', borderRadius: 8,
                        border: '1px dashed var(--caramel)',
                        background: scratchpadHasWork ? 'var(--caramel-dim)' : 'var(--surface2)',
                        color: scratchpadHasWork ? 'var(--caramel)' : 'var(--text-muted)',
                        cursor: scratchpadHasWork ? 'pointer' : 'not-allowed',
                        fontWeight: 500,
                      }}
                    >
                      {scratchpadHasWork ? 'Show this step →' : 'Show your work above to reveal'}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
