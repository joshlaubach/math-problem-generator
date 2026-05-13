import { api, LegacyTopicMetadata, UnitIntro } from '@/lib/api-client'
import { UnitIntro as UnitIntroComponent } from '@/components/UnitIntro'
import { TopicName } from '@/components/TopicName'
import Link from 'next/link'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

interface Props { params: Promise<{ courseId: string; unitId: string }> }

export default async function UnitPage({ params }: Props) {
  const { courseId, unitId } = await params
  let allTopics: LegacyTopicMetadata[] = []
  let apiAvailable = false
  try {
    allTopics = await api.getTopicsLegacy()
    apiAvailable = true
  } catch {
    // API unreachable — render gracefully rather than 404
  }
  const unitTopics = allTopics.filter(t => t.course_id === courseId && t.unit_id === unitId)

  // Only 404 when the API responded successfully but this unit genuinely doesn't exist
  if (apiAvailable && unitTopics.length === 0) notFound()

  const courseName = unitTopics[0]?.course_name ?? courseId
  const unitName   = unitTopics[0]?.unit_name   ?? unitId
  const isHonors   = unitTopics[0]?.is_honors ?? false
  const displayName = unitName.replace(' (H)', '')

  // Fetch unit intro (server-side, on-demand generation)
  let intro: UnitIntro | null = null
  try {
    intro = await api.getUnitIntro(unitId)
  } catch {
    // Not yet generated — will show topic list fallback
  }

  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/dashboard">Dashboard</Link>
          <span className="sep">/</span>
          <Link href="/catalog">Catalog</Link>
          <span className="sep">/</span>
          <Link href={`/catalog/${courseId}`}>{courseName}</Link>
          <span className="sep">/</span>
          <span className="current">{displayName}</span>
        </nav>
      </div>

      <div className="page-content">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
          <h1 className="display-heading" style={{ marginBottom: 0 }}>{displayName}</h1>
          {isHonors && (
            <span style={{
              fontSize: 11, fontWeight: 700, color: 'var(--caramel)',
              background: 'var(--caramel-dim)', border: '1px solid rgba(196,151,106,0.3)',
              borderRadius: 5, padding: '3px 8px', letterSpacing: '0.06em',
            }}>
              ⭐ HONORS
            </span>
          )}
        </div>
        <p className="page-subtitle">{unitTopics.length} topic{unitTopics.length !== 1 ? 's' : ''}</p>

        {intro ? (
          <UnitIntroComponent intro={intro} courseId={courseId} unitId={unitId} />
        ) : (
          /* Fallback: intro still generating — show plain topic list */
          <div>
            <div style={{
              padding: '14px 18px', borderRadius: 10,
              border: '1px solid rgba(196,151,106,0.3)', background: 'var(--caramel-dim)',
              fontSize: 13, color: 'var(--text-dim)', marginBottom: 24,
            }}>
              Unit overview is being generated. Topics are available now — click any to start learning.
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {unitTopics.map((topic, i) => (
                <Link
                  key={topic.topic_id}
                  href={`/catalog/${courseId}/${unitId}/${topic.topic_id}`}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 16, padding: '16px 20px', borderRadius: 12,
                    border: '1px solid var(--border)', background: 'var(--surface)',
                    textDecoration: 'none', color: 'inherit',
                    animation: `cardIn 0.5s ${0.05 + i * 0.05}s both cubic-bezier(0.16,1,0.3,1)`,
                  }}
                >
                  <div style={{
                    fontFamily: 'var(--font-fraunces), Georgia, serif',
                    fontSize: 14, fontWeight: 600, color: 'var(--text)',
                  }}>
                    <TopicName name={topic.topic_name} />
                  </div>
                  <span style={{ fontSize: 16, color: 'var(--text-muted)' }}>→</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
