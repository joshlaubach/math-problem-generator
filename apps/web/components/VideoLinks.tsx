interface VideoLink {
  id: string;
  title: string;
  url: string;
  source: string;
}

interface VideoLinksProps {
  links: VideoLink[];
}

export function VideoLinks({ links }: VideoLinksProps) {
  if (links.length === 0) return null;

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-800">Video Resources</h2>
      <ul className="space-y-2">
        {links.map((v) => (
          <li key={v.id}>
            <a
              href={v.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <span className="text-2xl" aria-hidden>▶</span>
              <span>
                <span className="text-sm font-medium text-gray-900">{v.title}</span>
                <span className="ml-2 text-xs text-gray-400">{v.source}</span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
