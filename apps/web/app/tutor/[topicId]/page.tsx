/**
 * /tutor/[topicId] — legacy route redirect
 *
 * The topic-locked tutor has been replaced by the general-purpose tutor.
 * Redirects old bookmarks and inbound links to the new intake form,
 * pre-filling the topic when possible.
 */
import { redirect } from 'next/navigation'

interface Props {
  params: { topicId: string }
}

export default function LegacyTutorPage({ params }: Props) {
  redirect(`/tutor/new?topic=${params.topicId}`)
}
