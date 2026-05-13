import { api, LegacyTopicMetadata } from '@/lib/api-client'
import { PrerequisiteGraph } from '@/components/PrerequisiteGraph'
import Link from 'next/link'
import katex from 'katex'

const PREREQ_NAMES: Record<string, string[]> = {
  algebra_1: ['Pre-Algebra'], geometry: ['Algebra I'], algebra_2: ['Algebra I'],
  precalculus: ['Algebra II', 'Geometry'], probability: ['Algebra II'],
  statistics: ['Probability'], calculus_1: ['Pre-Calculus'],
  calculus_2: ['Calculus I'], calculus_3: ['Calculus II'],
  linear_algebra: ['Calculus I'], differential_equations: ['Calculus II'],
  discrete_math: ['Algebra II'], proofs: ['Discrete Mathematics'],
  contest_math: ['Algebra II'],
}

const LEVEL_GROUPS = [
  { label: 'High School',  level: 'hs',      ids: ['prealgebra', 'algebra_1', 'geometry', 'algebra_2', 'precalculus'] },
  { label: 'Applied Math', level: 'applied',  ids: ['probability', 'statistics', 'calculus_1', 'calculus_2', 'calculus_3'] },
  { label: 'Advanced',     level: 'adv',      ids: ['linear_algebra', 'differential_equations', 'discrete_math', 'proofs', 'contest_math'] },
]

const LEVEL_CSS_COLOR: Record<string, string> = {
  hs:      'var(--hs-color)',
  applied: 'var(--applied-color)',
  adv:     'var(--adv-color)',
}

const COURSE_LATEX: Record<string, string> = {
  prealgebra:              '\\tfrac{1}{2}',
  algebra_1:               'x',
  geometry:                'a^2{+}b^2',
  algebra_2:               'x^2',
  precalculus:             '\\sin\\theta',
  probability:             'P(A)',
  statistics:              '\\bar{x}',
  calculus_1:              '\\dfrac{dy}{dx}',
  calculus_2:              '\\int_a^b\\!f\\,dx',
  calculus_3:              '\\nabla f',
  linear_algebra:          'A\\mathbf{x}{=}\\lambda\\mathbf{x}',
  differential_equations:  "y''+y=0",
  discrete_math:           'A\\cap B',
  proofs:                  'P\\Rightarrow Q',
  contest_math:            '\\displaystyle\\sum_{k=1}^n k',
}

function courseIcon(id: string): string {
  const latex = COURSE_LATEX[id]
  if (!latex) return '?'
  return katex.renderToString(latex, { throwOnError: false, output: 'html' })
}

function deriveCatalog(topics: LegacyTopicMetadata[]) {
  const courseMap = new Map<string, { id: string; name: string; units: Set<string>; topics: number }>()
  for (const t of topics) {
    if (!courseMap.has(t.course_id)) {
      courseMap.set(t.course_id, { id: t.course_id, name: t.course_name, units: new Set(), topics: 0 })
    }
    const c = courseMap.get(t.course_id)!
    c.units.add(t.unit_id)
    c.topics++
  }
  return courseMap
}

export default async function CatalogPage() {
  const topics = await api.getTopicsLegacy().catch(() => [] as LegacyTopicMetadata[])
  const courseMap = deriveCatalog(topics)
  const courseNodes = Array.from(courseMap.values()).map(c => ({ id: c.id, name: c.name }))

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <span className="current">Course Catalog</span>
        </nav>
      </div>

      <div className="page-content">
        <h1 className="display-heading" style={{ marginBottom: 6 }}>
          Course <em>Catalog</em>
        </h1>
        <p className="page-subtitle">
          {courseMap.size > 0 ? `${courseMap.size} courses · ${topics.length} topics across three levels` : 'Fifteen courses from Pre-Algebra to graduate mathematics'}
        </p>

        {/* No data */}
        {topics.length === 0 && (
          <div style={{
            borderRadius: 10, border: '1px solid rgba(196,151,106,0.3)',
            background: 'var(--caramel-dim)', padding: '14px 18px',
            fontSize: 13, color: 'var(--text-dim)', marginBottom: 32,
          }}>
            Could not load curriculum. Make sure the API server is running.
          </div>
        )}

        {/* Prerequisite map */}
        {courseNodes.length > 0 && (
          <div style={{ marginBottom: 56 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: 'var(--text-muted)',
                flexShrink: 0,
              }} />
              <h2 style={{
                fontSize: 13, fontWeight: 700, letterSpacing: '0.1em',
                textTransform: 'uppercase', color: 'var(--text-muted)', margin: 0,
              }}>
                Prerequisite Map
              </h2>
              <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, var(--border), transparent)' }} />
            </div>
            <div className="warm-card-static" style={{ padding: '24px', overflow: 'auto' }}>
              <PrerequisiteGraph courses={courseNodes} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
              Click any course to view its units and topics.
            </p>
          </div>
        )}

        {/* Course level grids */}
        {LEVEL_GROUPS.map(({ label, level, ids }) => {
          const courses = ids
            .map(id => courseMap.get(id))
            .filter(Boolean) as { id: string; name: string; units: Set<string>; topics: number }[]
          if (courses.length === 0) return null
          const levelColor = LEVEL_CSS_COLOR[level]
          return (
            <div key={label} style={{ marginBottom: 48 }}>
              {/* Level heading with accent dot */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: levelColor,
                  boxShadow: `0 0 10px ${levelColor}`,
                  flexShrink: 0,
                }} />
                <h2 style={{
                  fontSize: 13, fontWeight: 700, letterSpacing: '0.1em',
                  textTransform: 'uppercase', color: levelColor, margin: 0,
                }}>
                  {label}
                </h2>
                <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg, color-mix(in srgb, ${levelColor} 30%, transparent), transparent)` }} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                {courses.map((c, i) => (
                  <Link
                    key={c.id}
                    href={`/catalog/${c.id}`}
                    className="course-card"
                    data-level={level}
                    style={{
                      textDecoration: 'none',
                      animation: `cardIn 0.55s ${0.04 + i * 0.06}s both cubic-bezier(0.16,1,0.3,1)`,
                    }}
                  >
                    <div
                      className="course-emoji"
                      dangerouslySetInnerHTML={{ __html: courseIcon(c.id) }}
                    />
                    <div className="course-tag">
                      {label === 'High School' ? 'HS' : label === 'Applied Math' ? 'Applied' : 'Advanced'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-fraunces), Georgia, serif',
                      fontSize: 15, fontWeight: 600, color: 'var(--text)',
                      marginBottom: 6, lineHeight: 1.3,
                    }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 10 }}>
                      <span>{c.units.size} units</span>
                      <span>{c.topics} topics</span>
                    </div>
                    {PREREQ_NAMES[c.id]?.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.4 }}>
                        Requires: {PREREQ_NAMES[c.id].join(', ')}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          )
        })}

      </div>
    </>
  )
}
