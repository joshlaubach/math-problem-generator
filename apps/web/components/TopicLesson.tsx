'use client'

import { MathText } from './MathText'
import { WorkedExample } from './WorkedExample'
import { PartialExample } from './PartialExample'
import { PracticeProblems } from './PracticeProblems'
import type { TopicLesson as TopicLessonType } from '@/lib/api-client'

interface TopicLessonProps {
  lesson: TopicLessonType
}

function Section({ eyebrow, children }: { eyebrow: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
        letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 14,
        paddingBottom: 8, borderBottom: '1px solid var(--border)',
      }}>
        {eyebrow}
      </div>
      {children}
    </div>
  )
}

export function TopicLesson({ lesson }: TopicLessonProps) {
  return (
    <div>
      {/* Fallback notice */}
      {lesson._fallback && (
        <div style={{
          padding: '10px 14px', borderRadius: 8, marginBottom: 24,
          border: '1px solid rgba(196,151,106,0.3)', background: 'var(--caramel-dim)',
          fontSize: 13, color: 'var(--text-dim)',
        }}>
          This lesson is still generating — check back in a moment for the full version.
        </div>
      )}

      {/* Hook */}
      <Section eyebrow="Before you start">
        <div style={{
          padding: '18px 22px', borderRadius: 12,
          border: '1px solid rgba(196,151,106,0.35)',
          background: 'var(--caramel-dim)',
          borderLeft: '3px solid var(--caramel)',
        }}>
          <div style={{ fontSize: 15, color: 'var(--text)', lineHeight: 1.7 }}>
            <MathText latex={lesson.hook} prose />
          </div>
        </div>
      </Section>

      {/* Concept */}
      <Section eyebrow="The concept">
        <div style={{ fontSize: 15, color: 'var(--text)', lineHeight: 1.75 }}>
          <MathText latex={lesson.concept} prose />
        </div>
      </Section>

      {/* Anatomy */}
      <Section eyebrow="Anatomy">
        <div style={{
          padding: '16px 20px', borderRadius: 12,
          border: '1px solid var(--border)', background: 'var(--surface2)',
        }}>
          <div style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7 }}>
            <MathText latex={lesson.anatomy} prose />
          </div>
        </div>
      </Section>

      {/* Worked example */}
      <Section eyebrow="Worked example">
        <WorkedExample steps={lesson.worked_example} />
      </Section>

      {/* Your turn (partial example) */}
      <Section eyebrow="Your turn">
        <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 16, lineHeight: 1.6 }}>
          The given steps are shown. Fill in the steps marked with <strong style={{ color: 'var(--caramel)' }}>?</strong> — show your work in the scratchpad before revealing the answer.
        </p>
        <PartialExample steps={lesson.partial_example} topicId={lesson.topic_id} />
      </Section>

      {/* Common mistakes */}
      <Section eyebrow="Common mistakes">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {lesson.common_mistakes.map((mistake, i) => (
            <div
              key={i}
              style={{
                padding: '12px 16px', borderRadius: 10,
                border: '1px solid rgba(193,68,14,0.2)',
                background: 'var(--terra-dim)',
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}
            >
              <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>⚠</span>
              <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
                <MathText latex={mistake} prose />
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Practice problems */}
      <Section eyebrow="Practice">
        <PracticeProblems
          problems={lesson.practice_problems}
          untestedVariants={lesson.untested_variants}
          topicId={lesson.topic_id}
          topicName={lesson.topic_name}
        />
      </Section>
    </div>
  )
}
