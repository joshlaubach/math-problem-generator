import { api, LegacyTopicMetadata } from '@/lib/api-client'
import Link from 'next/link'
import { notFound } from 'next/navigation'

interface Props { params: Promise<{ courseId: string }> }

function groupByUnit(topics: LegacyTopicMetadata[]) {
  const unitMap = new Map<string, { id: string; name: string; is_honors: boolean; topics: LegacyTopicMetadata[] }>()
  for (const t of topics) {
    if (!unitMap.has(t.unit_id)) unitMap.set(t.unit_id, { id: t.unit_id, name: t.unit_name, is_honors: t.is_honors, topics: [] })
    unitMap.get(t.unit_id)!.topics.push(t)
  }
  return Array.from(unitMap.values())
}

const CALC_ICON: Record<string, string> = {
  scientific: '🖩',
  graphing:   '📈',
  cas:        '💻',
}

export default async function CoursePage({ params }: Props) {
  const { courseId } = await params
  const allTopics = await api.getTopicsLegacy().catch(() => [] as LegacyTopicMetadata[])
  const courseTopics = allTopics.filter(t => t.course_id === courseId)

  if (allTopics.length > 0 && courseTopics.length === 0) notFound()

  const courseName = courseTopics[0]?.course_name ?? courseId
  const units = groupByUnit(courseTopics)

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <Link href="/catalog">Catalog</Link>
          <span className="sep">/</span>
          <span className="current">{courseName}</span>
        </nav>
      </div>

      <div className="page-content">
        <h1 className="display-heading" style={{ marginBottom: 6 }}>{courseName}</h1>
        <p className="page-subtitle">
          {units.length} unit{units.length !== 1 ? 's' : ''} · {courseTopics.length} topic{courseTopics.length !== 1 ? 's' : ''}
        </p>

        {allTopics.length === 0 && (
          <div style={{ borderRadius: 10, border: '1px solid rgba(196,151,106,0.3)', background: 'var(--caramel-dim)', padding: '14px 18px', fontSize: 13, color: 'var(--text-dim)', marginBottom: 24 }}>
            Could not load curriculum. Make sure the API server is running.
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {units.map((unit, i) => (
            <Link
              key={unit.id}
              href={`/catalog/${courseId}/${unit.id}`}
              className="warm-card"
              style={{
                display: 'flex', alignItems: 'center', gap: 16,
                padding: '18px 22px', textDecoration: 'none',
                animation: `cardIn 0.5s ${0.05 + i * 0.06}s both cubic-bezier(0.16,1,0.3,1)`,
              }}
            >
              <div style={{
                width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                background: 'var(--caramel-dim)',
                border: '1px solid rgba(196,151,106,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-fraunces), Georgia, serif',
                fontSize: 15, fontWeight: 600, color: 'var(--caramel)',
              }}>
                {i + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
                    {unit.name.replace(' (H)', '')}
                  </span>
                  {unit.is_honors && (
                    <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--caramel)', background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.3)', borderRadius: 4, padding: '1px 6px', letterSpacing: '0.06em' }}>
                      ⭐ HONORS
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 10 }}>
                  <span>{unit.topics.length} topic{unit.topics.length !== 1 ? 's' : ''}</span>
                  {(() => {
                    const calcMode = unit.topics[0]?.calculator_mode
                    return calcMode && calcMode !== 'none'
                      ? <span>{CALC_ICON[calcMode]} {calcMode}</span>
                      : null
                  })()}
                </div>
              </div>
              <span style={{ color: 'var(--caramel)', fontSize: 18, opacity: 0.6 }}>→</span>
            </Link>
          ))}
        </div>

      </div>
    </>
  )
}
