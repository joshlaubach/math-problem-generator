'use client';
import { useEffect, useRef } from 'react';

export interface MathInputProps {
  value?: string;
  onChange?: (latex: string) => void;
  placeholder?: string;
  className?: string;
  readOnly?: boolean;
}

type MathFieldElement = HTMLElement & { value: string; readOnly: boolean };

// MathLive upright-letter shortcuts → KaTeX equivalents
function normalizeMathLive(latex: string): string {
  return latex
    .replace(/\\differentialD/g, '\\mathrm{d}')
    .replace(/\\imaginaryI/g, '\\mathrm{i}')
    .replace(/\\exponentialE/g, '\\mathrm{e}')
}

export function MathInput({
  value = '',
  onChange,
  placeholder,
  className,
  readOnly = false,
}: MathInputProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fieldRef = useRef<MathFieldElement | null>(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let destroyed = false;

    import('mathlive').then(() => {
      if (destroyed) return;
      const el = document.createElement('math-field') as MathFieldElement;

      const isDark = document.documentElement.dataset.theme === 'dark';

      // Theme-aware so the field doesn't render as a white box in dark mode.
      // color-scheme: dark is the key property that tells MathLive's Shadow DOM
      // to render math content (brackets, sqrt bars, etc.) in dark colors.
      const darkStyles = isDark ? [
        'color-scheme:dark',
        'color:#e6edf3',
        'background:#161b22',
        '--caret-color:#d29922',
        '--selection-background-color:rgba(210,153,34,0.25)',
        '--selection-color:#e6edf3',
        '--smart-fence-color:#d29922',
        '--placeholder-color:#6e7681',
      ] : [
        'color:var(--text)',
        'background:var(--surface)',
        '--caret-color:var(--caramel)',
        '--selection-background-color:var(--caramel-dim)',
      ];

      el.setAttribute(
        'style',
        [
          'width:100%',
          'font-size:1.1em',
          'padding:6px 8px',
          'border:1px solid var(--border)',
          'border-radius:6px',
          ...darkStyles,
        ].join(';'),
      );
      if (placeholder) el.setAttribute('placeholder', `\\text{${placeholder}}`);
      if (readOnly) el.setAttribute('read-only', '');
      el.value = value;

      el.addEventListener('input', () => {
        onChangeRef.current?.(normalizeMathLive(el.value));
      });

      container.appendChild(el);
      fieldRef.current = el;
    });

    return () => {
      destroyed = true;
      const el = fieldRef.current;
      if (el && container.contains(el)) container.removeChild(el);
      fieldRef.current = null;
    };
    // placeholder/readOnly set once at mount; value updates via the next effect
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const el = fieldRef.current;
    if (el && el.value !== value) el.value = value;
  }, [value]);

  return <div ref={containerRef} className={className} />;
}
