'use client'

import { useState } from 'react'
import Link from 'next/link'
import { MathText } from './MathText'
import type { PracticeProblem } from '@/lib/api-client'

interface PracticeProblemsProps {
  problems: PracticeProblem[]
  untestedVariants: string[]
  topicId: string
  topicName: string
}

export function PracticeProblems({
  problems,
  untestedVariants,
  topicId,
  topicName,
}: PracticeProblemsProps) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})

  if (!problems || problems.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {problems.map((prob, i) => (
        <div
          key={i}
          style={{
            padding: '16px 18px', borderRadius: 12,
            border: '1px solid var(--border)', background: 'var(--surface2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            {/* Problem number + statement */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
              <span style={{
                fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 5, padding: '2px 7px', flexShrink: 0, marginTop: 1,
              }}>
                {i + 1}
              </span>
              <div style={{ overflowX: 'auto', minWidth: 0 }}>
                <MathText latex={prob.prompt_latex} />
              </div>
            </div>

            {/* Answer reveal button */}
            <button
              onClick={() => setRevealed(r => ({ ...r, [i]: !r[i] }))}
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                border: '1px solid var(--border)', background: 'none',
                cursor: 'pointer', color: 'var(--text-dim)', flexShrink: 0,
                fontWeight: 500,
              }}
            >
              {revealed[i] ? 'Hide' : 'Check answer'}
            </button>
          </div>

          {/* Answer (revealed) */}
          {revealed[i] && prob.answer_latex && (
            <div style={{
              marginTop: 10, padding: '8px 12px', borderRadius: 8,
              background: 'var(--sage-dim, rgba(100,150,100,0.08))',
              border: '1px solid rgba(100,150,100,0.25)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Answer:</span>
              <MathText latex={prob.answer_latex} />
            </div>
          )}
        </div>
      ))}

      {/* Nudge callout card */}
      {untestedVariants && untestedVariants.length > 0 && (
        <div style={{
          marginTop: 8,
          padding: '18px 20px', borderRadius: 12,
          border: '1px solid rgba(196,151,106,0.35)',
          background: 'var(--caramel-dim)',
        }}>
          <div style={{
            fontSize: 12, fontWeight: 700, color: 'var(--caramel)',
            letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 8,
          }}>
            What these problems don&apos;t cover
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 12, lineHeight: 1.6 }}>
            These 4–5 problems cover the core pattern. An exam will also test:
          </p>
          <ul style={{ margin: '0 0 14px', padding: '0 0 0 18px', display: 'flex', flexDirection: 'column', gap: 5 }}>
            {untestedVariants.map((v, i) => (
              <li key={i} style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.5 }}>
                {v}
              </li>
            ))}
          </ul>
          <Link
            href={`/practice/${topicId}?name=${encodeURIComponent(topicName)}`}
            className="btn-caramel"
            style={{ textDecoration: 'none', padding: '9px 18px', fontSize: 13, display: 'inline-flex' }}
          >
            Generate practice problems →
          </Link>
        </div>
      )}
    </div>
  )
}
