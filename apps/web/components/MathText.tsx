import katex from 'katex';

interface MathTextProps {
  latex: string;
  inline?: boolean;
  /** prose mode: auto-renders $...$ (inline) and $$...$$ (display) within plain text */
  prose?: boolean;
  className?: string;
}

function escHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br/>');
}

/**
 * Renders a mixed prose+math string.
 * Finds $$...$$ (display) and $...$ (inline) delimiters; everything else is plain text.
 * Falls back gracefully if KaTeX can't parse a fragment.
 */
function renderProseHtml(text: string): string {
  const parts: string[] = [];
  // Matches $$...$$ first, then $...$
  const pattern = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(escHtml(text.slice(lastIndex, match.index)));
    }
    const isDisplay = match[1] !== undefined;
    const mathSrc = isDisplay ? match[1] : match[2];
    parts.push(
      katex.renderToString(mathSrc, {
        displayMode: isDisplay,
        throwOnError: false,
        output: 'html',
      })
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(escHtml(text.slice(lastIndex)));
  }

  return parts.join('');
}

export function MathText({ latex, inline = false, prose = false, className }: MathTextProps) {
  if (!latex?.trim()) {
    return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>[No content]</span>;
  }

  if (prose) {
    return (
      <div
        className={className}
        style={{ lineHeight: 1.75 }}
        dangerouslySetInnerHTML={{ __html: renderProseHtml(latex) }}
      />
    );
  }

  const html = katex.renderToString(latex, {
    throwOnError: false,
    displayMode: !inline,
    output: 'html',
  });

  if (inline) {
    return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
  }

  return (
    <div
      className={`overflow-x-auto py-2 ${className ?? ''}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
