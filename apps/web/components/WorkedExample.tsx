'use client'

import { MathText } from './MathText'
import type { LessonStep } from '@/lib/api-client'

interface WorkedExampleProps {
  steps: LessonStep[]
}

const useProse = (s: string) =>
  /(?<!\\)\$[^$]+\$/.test(s) || !/\\[a-zA-Z]/.test(s)

export function WorkedExample({ steps }: WorkedExampleProps) {
  if (!steps || steps.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {steps.map((step, i) => (
        <div
          key={i}
          style={{
            display: 'flex', gap: 16, alignItems: 'flex-start',
            padding: '14px 0',
            borderBottom: i < steps.length - 1 ? '1px solid var(--border)' : 'none',
          }}
        >
          {/* Step number */}
          <div style={{
            width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
            background: 'var(--caramel)', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700, marginTop: 2,
          }}>
            {i + 1}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Expression */}
            {step.expression_latex && (
              <div style={{
                padding: '8px 12px', borderRadius: 8,
                background: 'var(--surface2)', border: '1px solid var(--border)',
                marginBottom: 8, overflowX: 'auto',
              }}>
                <MathText
                  latex={step.expression_latex}
                  prose={useProse(step.expression_latex)}
                />
              </div>
            )}

            {/* Narrative description */}
            {step.description_latex && (
              <div style={{
                fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65,
              }}>
                <MathText latex={step.description_latex} prose />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
