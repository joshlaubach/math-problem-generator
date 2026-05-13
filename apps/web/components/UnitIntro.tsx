import Link from 'next/link'
import { MathText } from './MathText'
import { TopicName } from './TopicName'
import type { UnitIntro as UnitIntroType } from '@/lib/api-client'

interface UnitIntroProps {
  intro: UnitIntroType
  courseId: string
  unitId: string
}

export function UnitIntro({ intro, courseId, unitId }: UnitIntroProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Hook */}
      <div style={{
        padding: '18px 22px', borderRadius: 12,
        border: '1px solid rgba(196,151,106,0.35)',
        background: 'var(--caramel-dim)',
        borderLeft: '3px solid var(--caramel)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--caramel)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
          Why this unit matters
        </div>
        <div style={{ fontSize: 15, color: 'var(--text)', lineHeight: 1.7 }}>
          <MathText latex={intro.hook} prose />
        </div>
      </div>

      {/* Concept */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
          The big idea
        </div>
        <div style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7 }}>
          <MathText latex={intro.concept} prose />
        </div>
      </div>

      {/* Topic roadmap */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
          Topics in this unit
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {intro.topic_roadmap.map((item, i) => (
            <Link
              key={item.topic_id}
              href={`/catalog/${courseId}/${unitId}/${item.topic_id}`}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 14,
                padding: '14px 18px', borderRadius: 12,
                border: '1px solid var(--border)', background: 'var(--surface)',
                textDecoration: 'none', color: 'inherit',
                transition: 'border-color 0.15s, background 0.15s',
                animation: `cardIn 0.4s ${0.05 + i * 0.04}s both cubic-bezier(0.16,1,0.3,1)`,
              }}
            >
              {/* Topic number */}
              <span style={{
                width: 24, height: 24, borderRadius: '50%',
                background: 'var(--surface2)', border: '1px solid var(--border)',
                color: 'var(--text-muted)', fontSize: 11, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, marginTop: 1,
              }}>
                {i + 1}
              </span>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontFamily: 'var(--font-fraunces), Georgia, serif',
                  fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 3,
                }}>
                  <TopicName name={item.topic_name} />
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-dim)', margin: 0 }}>
                  <MathText latex={item.description} prose />
                </div>
              </div>

              <span style={{ fontSize: 16, color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }}>
                →
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
