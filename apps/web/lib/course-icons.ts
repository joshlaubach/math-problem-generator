/**
 * Shared KaTeX icons for all 16 courses.
 * Imported by both the server-rendered catalog page and the client dashboard.
 * katex.renderToString works in both Node.js and browser environments.
 */
import katex from 'katex'

export const COURSE_LATEX: Record<string, string> = {
  prealgebra:              '\\tfrac{1}{2}',
  algebra_1:               'x',
  geometry:                'a^2{+}b^2',
  algebra_2:               'x^2',
  precalculus:             '\\sin\\theta',
  intro_prob_stats:        '\\bar{x}',
  probability:             'E[X{\\mid}Y]',
  mathematical_statistics: '\\hat{\\theta}',
  calculus_1:              '\\dfrac{dy}{dx}',
  calculus_2:              '\\int_a^b\\!f\\,dx',
  calculus_3:              '\\nabla f',
  differential_equations:  "y''+y=0",
  linear_algebra:          'A\\mathbf{x}{=}\\lambda\\mathbf{x}',
  discrete_math:           'A\\cap B',
  proofs:                  'P\\Rightarrow Q',
  contest_math:            '\\displaystyle\\sum_{k=1}^n k',
}

export function courseIcon(id: string): string {
  const latex = COURSE_LATEX[id]
  if (!latex) return '?'
  return katex.renderToString(latex, { throwOnError: false, output: 'html' })
}
