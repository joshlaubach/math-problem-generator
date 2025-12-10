/**
 * MathText component for rendering LaTeX with KaTeX
 * Uses react-katex for high-quality mathematical typesetting
 */

import { BlockMath, InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import './MathText.css';

interface MathTextProps {
  latex: string;
  inline?: boolean;
}

export function MathText({ latex, inline = false }: MathTextProps) {
  // Handle empty or invalid LaTeX
  if (!latex || latex.trim().length === 0) {
    return <span className="math-text-empty">[No content]</span>;
  }

  try {
    if (inline) {
      return (
        <span className="math-text inline">
          <InlineMath math={latex} />
        </span>
      );
    } else {
      return (
        <div className="math-text block">
          <BlockMath math={latex} />
        </div>
      );
    }
  } catch (error) {
    // Fallback for invalid LaTeX
    console.warn('KaTeX rendering error:', error);
    return (
      <code className={`math-text-fallback ${inline ? 'inline' : 'block'}`}>
        {latex}
      </code>
    );
  }
}

