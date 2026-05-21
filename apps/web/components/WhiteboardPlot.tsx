'use client'

/**
 * Mafs function plot for the whiteboard tutor zone.
 * Loaded dynamically (no SSR) from Whiteboard.tsx.
 */

import React from 'react'
import { Mafs, Coordinates, Plot } from 'mafs'
import 'mafs/core.css'

interface WhiteboardPlotProps {
  fn: string        // JS-compatible math expression e.g. "x**2 - 3*x + 2"
  domain: [number, number]
  theme?: 'light' | 'dark'
}

function parseExpr(expr: string): ((x: number) => number) | null {
  try {
    // Convert Python-style operators to JS
    const jsExpr = expr
      .replace(/\*\*/g, '**')    // keep ** for exponentiation — we handle via Function
      .replace(/Math\.PI/g, 'Math.PI')
    // Use Function constructor for safe eval
    // eslint-disable-next-line no-new-func
    const fn = new Function('x', `
      const abs = Math.abs, sqrt = Math.sqrt, sin = Math.sin,
            cos = Math.cos, tan = Math.tan, log = Math.log,
            exp = Math.exp, PI = Math.PI, E = Math.E;
      try {
        return ${jsExpr.replace(/\*\*/g, (_, _offset) => '**')}
      } catch {
        return NaN
      }
    `)
    return (x: number) => {
      try { return fn(x) } catch { return NaN }
    }
  } catch {
    return null
  }
}

export default function WhiteboardPlot({ fn, domain, theme = 'light' }: WhiteboardPlotProps) {
  const parsedFn = parseExpr(fn)
  if (!parsedFn) {
    return (
      <div style={{ padding: 8, fontSize: 12, color: 'var(--terracotta)' }}>
        Could not plot: {fn}
      </div>
    )
  }

  return (
    <>
      {theme === 'light' && (
        <style>{`.wb-mafs-light .MafsView{--mafs-bg:#fefcf9!important;--mafs-fg:#1a1a1a!important;--mafs-line-color:#ccc!important;--grid-line-subdivision-color:#e8e8e8!important}`}</style>
      )}
      <div className={theme === 'light' ? 'wb-mafs-light' : undefined} style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
        <Mafs
          height={160}
          viewBox={{ x: domain, y: [-6, 6] }}
          preserveAspectRatio={false}
        >
          <Coordinates.Cartesian />
          <Plot.OfX y={parsedFn} color={theme === 'dark' ? '#c4976a' : '#2d6a4f'} />
        </Mafs>
      </div>
    </>
  )
}
