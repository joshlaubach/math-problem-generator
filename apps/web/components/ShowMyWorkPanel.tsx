'use client'

import { useState } from 'react'
import { MathInput } from '@/components/MathInput'

export interface ShowMyWorkPanelProps {
  theme: 'light' | 'dark'
  onSubmit: (stepsLatex: string) => void
}

export function ShowMyWorkPanel({ theme, onSubmit }: ShowMyWorkPanelProps) {
  const [steps, setSteps] = useState<string[]>([''])

  const d = theme === 'dark'
  const surface  = d ? '#1c2128' : '#f8f9fc'
  const border   = d ? '#30363d' : '#dce0ee'
  const text     = d ? '#e6edf3' : '#0f1623'
  const textMuted = d ? '#8b949e' : '#4a5472'
  const caramel  = d ? '#d29922' : '#b8860b'
  const caramelDim = d ? 'rgba(210,153,34,0.12)' : 'rgba(184,134,11,0.10)'

  const addStep = () => setSteps(prev => [...prev, ''])
  const removeStep = (i: number) => setSteps(prev => prev.filter((_, j) => j !== i))
  const updateStep = (i: number, val: string) =>
    setSteps(prev => prev.map((s, j) => (j === i ? val : s)))

  const handleSubmit = () => {
    const filled = steps.filter(s => s.trim())
    if (!filled.length) return
    onSubmit(filled.join(' \\rightarrow '))
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 8,
      background: surface, border: `1px solid ${border}`,
      borderRadius: 10, padding: '12px 14px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{
          fontSize: 11, fontWeight: 600, color: textMuted,
          letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>
          Show My Work
        </span>
        <button
          onClick={handleSubmit}
          style={{
            padding: '3px 11px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            border: `1px solid ${caramel}`, background: caramelDim,
            color: caramel, cursor: 'pointer',
          }}
        >
          Check steps
        </button>
      </div>

      {/* Step rows */}
      {steps.map((step, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
          <span style={{
            fontSize: 11, color: textMuted, paddingTop: 10,
            minWidth: 18, textAlign: 'right', flexShrink: 0,
          }}>
            {i + 1}.
          </span>
          <div style={{ flex: 1 }}>
            <MathInput
              value={step}
              onChange={val => updateStep(i, val)}
              placeholder={i === 0 ? 'First step…' : 'Next step…'}
            />
          </div>
          {steps.length > 1 && (
            <button
              onClick={() => removeStep(i)}
              title="Remove step"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: textMuted, fontSize: 16, paddingTop: 7, flexShrink: 0,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>
      ))}

      {/* Add step */}
      <button
        onClick={addStep}
        style={{
          alignSelf: 'flex-start', padding: '3px 10px', borderRadius: 6,
          fontSize: 11, border: `1px solid ${border}`, background: 'transparent',
          color: text, cursor: 'pointer', marginTop: 2,
        }}
      >
        + Add step
      </button>
    </div>
  )
}
