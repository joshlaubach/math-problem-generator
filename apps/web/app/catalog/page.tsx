import { api, LegacyTopicMetadata } from '@/lib/api-client'
import { PrerequisiteGraph } from '@/components/PrerequisiteGraph'
import Link from 'next/link'

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
  { label: 'High School',  ids: ['prealgebra', 'algebra_1', 'geometry', 'algebra_2', 'precalculus'] },
  { label: 'Applied Math', ids: ['probability', 'statistics', 'calculus_1', 'calculus_2', 'calculus_3'] },
  { label: 'Advanced',     ids: ['linear_algebra', 'differential_equations', 'discrete_math', 'proofs', 'contest_math'] },
]

const COURSE_EMOJIS: Record<string, string> = {
  prealgebra: '➕', algebra_1: '📐', geometry: '📏', algebra_2: '🔢', precalculus: '📈',
  probability: '🎲', statistics: '📊', calculus_1: '∫', calculus_2: '∂', calculus_3: '∇',
  linear_algebra: '⬡', differential_equations: '~', discrete_math: '⊕', proofs: '∴', contest_math: '🏆',
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
          <div style={{ marginBottom: 48 }}>
            <h2 className="section-heading">Prerequisite Map</h2>
            <div className="warm-card-static" style={{ padding: '24px', overflow: 'auto' }}>
              <PrerequisiteGraph courses={courseNodes} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
              Click any course to view its units and topics.
            </p>
          </div>
        )}

        {/* Course level grids */}
        {LEVEL_GROUPS.map(({ label, ids }) => {
          const courses = ids
            .map(id => courseMap.get(id))
            .filter(Boolean) as { id: string; name: string; units: Set<string>; topics: number }[]
          if (courses.length === 0) return null
          return (
            <div key={label} style={{ marginBottom: 40 }}>
              <h2 className="section-heading">{label}</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14 }}>
                {courses.map((c, i) => (
                  <Link
                    key={c.id}
                    href={`/catalog/${c.id}`}
                    className="course-card"
                    style={{
                      textDecoration: 'none',
                      animation: `cardIn 0.5s ${0.05 + i * 0.07}s both cubic-bezier(0.16,1,0.3,1)`,
                    }}
                  >
                    <span className="course-emoji">{COURSE_EMOJIS[c.id] ?? '📘'}</span>
                    <div className="course-tag">{label === 'High School' ? 'HS' : label === 'Applied Math' ? 'Applied' : 'Advanced'}</div>
                    <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 16, fontWeight: 600, color: 'var(--text)', marginTop: 6, marginBottom: 4 }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 10 }}>
                      <span>{c.units.size} units</span>
                      <span>{c.topics} topics</span>
                    </div>
                    {PREREQ_NAMES[c.id]?.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
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
