import { api, LegacyTopicMetadata, TopicLesson } from '@/lib/api-client'
import { TopicLesson as TopicLessonComponent } from '@/components/TopicLesson'
import { TopicName, stripHonors } from '@/components/TopicName'
import { GeneratingState } from './GeneratingState'
import Link from 'next/link'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

interface Props {
  params: Promise<{ courseId: string; unitId: string; topicId: string }>
}

export default async function TopicLessonPage({ params }: Props) {
  const { courseId, unitId, topicId } = await params

  let allTopics: LegacyTopicMetadata[] = []
  let apiAvailable = false
  try {
    allTopics = await api.getTopicsLegacy()
    apiAvailable = true
  } catch {
    // API unreachable — render gracefully rather than 404
  }
  const topic = allTopics.find(t => t.topic_id === topicId)

  // Only 404 when the API responded successfully but this topic genuinely doesn't exist
  if (apiAvailable && !topic) notFound()

  const courseName = topic?.course_name ?? courseId
  const unitName   = topic?.unit_name   ?? unitId
  const topicName  = topic?.topic_name  ?? topicId

  // Fetch topic lesson (on-demand generation, shared across all users)
  let lesson: TopicLesson | null = null
  let generating = false
  try {
    lesson = await api.getTopicLesson(topicId)
  } catch (err: unknown) {
    // 404 means topic not in registry; 500 means generation failed
    const status = (err as { status?: number }).status
    if (status === 404) notFound()
    generating = true
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
          <Link href={`/catalog/${courseId}/${unitId}`}>{unitName.replace(' (H)', '')}</Link>
          <span className="sep">/</span>
          <span className="current">{stripHonors(topicName)}</span>
        </nav>
      </div>

      <div className="page-content">
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 className="display-heading" style={{ marginBottom: 6 }}>
            <TopicName name={topicName} badgeSize={13} />
          </h1>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <p className="page-subtitle" style={{ margin: 0 }}>{unitName.replace(' (H)', '')}</p>
            <Link
              href={`/practice/${topicId}?name=${encodeURIComponent(topicName)}`}
              className="btn-caramel"
              style={{ textDecoration: 'none', padding: '7px 16px', fontSize: 12 }}
            >
              Practice this topic →
            </Link>
          </div>
        </div>

        {/* Content */}
        {generating ? (
          <GeneratingState topicName={topicName} />
        ) : lesson ? (
          <TopicLessonComponent lesson={lesson} />
        ) : (
          <GeneratingState topicName={topicName} />
        )}
      </div>
    </>
  )
}

