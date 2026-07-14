/**
 * Manim-inspired animation utilities for the tutor whiteboard (Phase 1.5).
 *
 * Design rules:
 *  - Everything honors prefers-reduced-motion (motionOk() gates every effect).
 *  - Equations "write on" glyph-by-glyph; curves draw along their path length;
 *    highlights are drawn underlines, not color snaps. No jarring cuts.
 */

/** False when the user asked for reduced motion — render instantly then. */
export function motionOk(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  try {
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return true
  }
}

/**
 * Leaf glyph spans of a KaTeX render — the units of the write-on effect.
 * (Nested containers like \frac wrappers are excluded so nothing animates twice.)
 */
export function katexGlyphs(root: HTMLElement, cap = 140): HTMLElement[] {
  const spans = root.querySelectorAll<HTMLElement>('.katex span')
  const leaves: HTMLElement[] = []
  spans.forEach(s => {
    if (s.children.length === 0 && (s.textContent ?? '').trim().length > 0) {
      leaves.push(s)
    }
  })
  return leaves.length > cap ? [] : leaves // too dense → whole-block fade instead
}

/**
 * Draw-on for SVG curves: each stroked path animates stroke-dashoffset from
 * its full length to 0, staggered slightly, like a pen tracing the curve.
 */
export function strokeDrawOn(container: HTMLElement | null): void {
  if (!container || !motionOk()) return
  const svg = container.querySelector('svg')
  if (!svg) return
  const paths = svg.querySelectorAll<SVGPathElement>('path')
  let i = 0
  paths.forEach(p => {
    let len = 0
    try { len = p.getTotalLength() } catch { return }
    if (!len || !isFinite(len) || len < 4) return
    const delay = i * 0.08
    i += 1
    p.style.strokeDasharray = `${len}`
    p.style.strokeDashoffset = `${len}`
    p.style.transition = 'none'
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        p.style.transition =
          `stroke-dashoffset ${Math.min(1.4, 0.5 + len / 600)}s cubic-bezier(.4,0,.2,1) ${delay}s`
        p.style.strokeDashoffset = '0'
      })
    })
  })
}

/** Keyframe for the wb_highlight underline (scaleX draw from the left). */
export const UNDERLINE_KEYFRAME =
  '@keyframes wb-underline-draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}'
