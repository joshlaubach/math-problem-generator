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
      el.setAttribute(
        'style',
        'width:100%;font-size:1.1em;padding:6px 8px;border:1px solid #d1d5db;border-radius:6px;background:#fff;',
      );
      if (placeholder) el.setAttribute('placeholder', `\\text{${placeholder}}`);
      if (readOnly) el.setAttribute('read-only', '');
      el.value = value;

      el.addEventListener('input', () => {
        onChangeRef.current?.(el.value);
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
