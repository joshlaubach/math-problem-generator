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
 * Also renders **bold**, *italic*, and --- (horizontal rule) markdown.
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
        output: 'htmlAndMathml',  // MathML twin = screen-reader-navigable math
        trust: false,      // SECURITY: never honor \href/\htmlData etc. (XSS)
        strict: 'ignore',
      })
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(escHtml(text.slice(lastIndex)));
  }

  return applyMarkdown(parts.join(''));
}

/** Apply basic markdown to the already-HTML-escaped prose string (post KaTeX pass). */
function applyMarkdown(html: string): string {
  // --- on its own line → <hr>
  html = html.replace(
    /(^|<br\/>)-{3,}(<br\/>|$)/g,
    '$1<hr style="border:none;border-top:1px solid var(--border);margin:6px 0">$2'
  )
  // **bold**
  html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
  // *italic* (not **…**)
  html = html.replace(/(?<!\*)\*([^*<>]+?)\*(?!\*)/g, '<em>$1</em>')
  return html
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
    output: 'htmlAndMathml',  // MathML twin = screen-reader-navigable math
    trust: false,      // SECURITY: never honor \href/\htmlData etc. (XSS)
    strict: 'ignore',
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
