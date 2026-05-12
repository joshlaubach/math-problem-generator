import Link from 'next/link';

interface CourseCardProps {
  courseId: string;
  courseName: string;
  topicCount: number;
  unitCount: number;
  prereqNames: string[];
}

export function CourseCard({
  courseId,
  courseName,
  topicCount,
  unitCount,
  prereqNames,
}: CourseCardProps) {
  return (
    <Link href={`/catalog/${courseId}`} className="group block">
      <div className="rounded-xl border border-gray-200 bg-white p-5 h-full hover:shadow-md hover:border-blue-300 transition-all duration-150">
        <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
          {courseName}
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          {unitCount} unit{unitCount !== 1 ? 's' : ''} · {topicCount} topic
          {topicCount !== 1 ? 's' : ''}
        </p>
        {prereqNames.length > 0 && (
          <p className="mt-2 text-xs text-gray-400">
            Requires: {prereqNames.join(', ')}
          </p>
        )}
      </div>
    </Link>
  );
}
