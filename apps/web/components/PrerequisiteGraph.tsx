'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

interface CourseNode { id: string; name: string }
interface PrerequisiteGraphProps { courses: CourseNode[] }

// ── Layout constants ────────────────────────────────────────────────────────
const NODE_W    = 148
const NODE_H    = 32
const COL_W     = NODE_W + 24   // total column width inc. padding
const COL_GAP   = 20
const STRIDE    = COL_W + COL_GAP
const SVG_W     = 4 * STRIDE - COL_GAP + 8
const ROW_Y0    = 48            // first row top
const ROW_STEP  = 48
const SVG_H     = ROW_Y0 + 5 * ROW_STEP + 56   // 5 rows + routing space below
const ROUTE_Y   = SVG_H - 18   // y level for arcs that skip columns

// ── Track definitions ───────────────────────────────────────────────────────
const TRACKS = [
  { label: 'Algebra',          col: 0, colorVar: '--algebra-color',  dimVar: '--algebra-dim'  },
  { label: 'Calculus',         col: 1, colorVar: '--calculus-color', dimVar: '--calculus-dim' },
  { label: 'Statistics',       col: 2, colorVar: '--stats-color',    dimVar: '--stats-dim'    },
  { label: 'Pure Mathematics', col: 3, colorVar: '--pure-color',     dimVar: '--pure-dim'     },
]

// course_id → [col, row]
const COURSE_POS: Record<string, [number, number]> = {
  prealgebra:             [0, 0], algebra_1:       [0, 1],
  geometry:               [0, 2], algebra_2:       [0, 3],
  precalculus:            [0, 4],
  calculus_1:             [1, 1], calculus_2:      [1, 2],
  calculus_3:             [1, 3], differential_equations: [1, 4],
  intro_prob_stats:       [2, 2], probability:     [2, 3],
  mathematical_statistics:[2, 4],
  linear_algebra:         [3, 1], discrete_math:   [3, 2],
  proofs:                 [3, 3], contest_math:    [3, 4],
}

const EDGES: [string, string][] = [
  ['prealgebra',    'algebra_1'],
  ['algebra_1',     'geometry'],
  ['algebra_1',     'algebra_2'],
  ['algebra_2',     'precalculus'],
  ['geometry',      'precalculus'],
  ['precalculus',   'calculus_1'],
  ['calculus_1',    'calculus_2'],
  ['calculus_2',    'calculus_3'],
  ['calculus_2',    'differential_equations'],
  ['algebra_2',     'intro_prob_stats'],
  ['intro_prob_stats', 'probability'],
  ['calculus_1',    'probability'],
  ['probability',   'mathematical_statistics'],
  ['calculus_1',    'linear_algebra'],
  ['algebra_2',     'discrete_math'],
  ['discrete_math', 'proofs'],
  ['algebra_2',     'contest_math'],
]

function nodeRect(id: string) {
  const pos = COURSE_POS[id]
  if (!pos) return null
  const [col, row] = pos
  return {
    x: col * STRIDE + 12,
    y: ROW_Y0 + row * ROW_STEP,
    cx: col * STRIDE + 12 + NODE_W / 2,
    cy: ROW_Y0 + row * ROW_STEP + NODE_H / 2,
    col, row,
  }
}

function edgePath(fromId: string, toId: string): string | null {
  const a = nodeRect(fromId)
  const b = nodeRect(toId)
  if (!a || !b) return null

  const colDiff = b.col - a.col

  if (colDiff === 0) {
    // Same column — straight vertical
    const x = a.cx
    const y1 = a.y + NODE_H
    const y2 = b.y - 4
    return `M ${x} ${y1} L ${x} ${y2}`
  }

  if (colDiff === 1) {
    // Adjacent column — S-curve
    const x1 = a.x + NODE_W
    const y1 = a.cy
    const x2 = b.x - 4
    const y2 = b.cy
    const mx = (x1 + x2) / 2
    return `M ${x1} ${y1} C ${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`
  }

  // Multi-column skip — arc below through ROUTE_Y
  const x1 = a.x + NODE_W
  const y1 = a.cy
  const x2 = b.x - 4
  const y2 = b.cy
  const drop = ROUTE_Y + (colDiff - 2) * 10
  return [
    `M ${x1} ${y1}`,
    `C ${x1 + 16} ${y1} ${x1 + 16} ${drop} ${(x1 + x2) / 2} ${drop}`,
    `C ${(x1 + x2) / 2 + (x2 - x1) * 0.3} ${drop} ${x2 - 16} ${y2 + 16} ${x2} ${y2}`,
  ].join(' ')
}

// Resolve a CSS variable value from the document root
function useCSSVar(name: string, fallback: string) {
  const [val, setVal] = useState(fallback)
  useEffect(() => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    if (v) setVal(v)
  }, [name])
  return val
}

function TrackColors() {
  // Inject CSS vars as SVG <defs> gradients / fills resolved at runtime
  return null
}

export function PrerequisiteGraph({ courses }: PrerequisiteGraphProps) {
  const courseMap = new Map(courses.map(c => [c.id, c]))
  const [hovered, setHovered] = useState<string | null>(null)

  // Resolve track colors at runtime (dark/light mode aware)
  const trackColorVars = ['--algebra-color', '--calculus-color', '--stats-color', '--pure-color']
  const trackDimVars   = ['--algebra-dim',   '--calculus-dim',   '--stats-dim',   '--pure-dim']

  const fallbackColors = ['#fbbf24', '#58c4dd', '#34d399', '#c084fc']
  const fallbackDims   = [
    'rgba(251,191,36,.1)', 'rgba(88,196,221,.1)',
    'rgba(52,211,153,.1)', 'rgba(192,132,252,.1)',
  ]

  return (
    <div style={{ overflowX: 'auto', overflowY: 'hidden' }}>
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ width: '100%', minWidth: SVG_W, height: SVG_H, display: 'block' }}
        aria-label="Course prerequisite map"
      >
        <defs>
          <marker id="pgArrow" markerWidth={6} markerHeight={6} refX={5} refY={3} orient="auto">
            <path d="M0,0 L0,6 L6,3 z" style={{ fill: 'var(--border2)' }} />
          </marker>
          {/* Per-track glow filters */}
          {TRACKS.map((t, i) => (
            <filter key={t.col} id={`glow-${i}`} x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          ))}
        </defs>

        {/* ── Track column backgrounds ──────────────────────────────────── */}
        {TRACKS.map(t => (
          <rect
            key={t.col}
            x={t.col * STRIDE}
            y={0}
            width={COL_W}
            height={SVG_H - 30}
            rx={10}
            style={{
              fill: `var(${t.dimVar})`,
              stroke: `var(${t.colorVar})`,
              strokeWidth: 0.5,
              strokeOpacity: 0.3,
            }}
          />
        ))}

        {/* ── Track column headers ──────────────────────────────────────── */}
        {TRACKS.map(t => (
          <text
            key={`h-${t.col}`}
            x={t.col * STRIDE + COL_W / 2}
            y={22}
            textAnchor="middle"
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              fill: `var(${t.colorVar})`,
              fontFamily: 'var(--font-instrument), system-ui, sans-serif',
            }}
          >
            {t.label.toUpperCase()}
          </text>
        ))}

        {/* ── Edges ────────────────────────────────────────────────────── */}
        {EDGES.map(([from, to]) => {
          const d = edgePath(from, to)
          if (!d) return null
          const isHighlighted = hovered === from || hovered === to
          return (
            <path
              key={`${from}-${to}`}
              d={d}
              fill="none"
              style={{
                stroke: isHighlighted ? 'var(--text-dim)' : 'var(--border2)',
                strokeWidth: isHighlighted ? 1.5 : 1,
                strokeOpacity: isHighlighted ? 1 : 0.6,
                transition: 'stroke 0.2s, stroke-width 0.2s',
              }}
              markerEnd="url(#pgArrow)"
            />
          )
        })}

        {/* ── Course nodes ──────────────────────────────────────────────── */}
        {Object.entries(COURSE_POS).map(([id, [col]]) => {
          const course = courseMap.get(id)
          if (!course) return null
          const rect = nodeRect(id)!
          const track = TRACKS[col]
          const isHov = hovered === id

          // Truncate long names
          const name = course.name.length > 22
            ? course.name.slice(0, 20) + '…'
            : course.name

          return (
            <Link key={id} href={`/catalog/${id}`}>
              <g
                onMouseEnter={() => setHovered(id)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
                filter={isHov ? `url(#glow-${col})` : undefined}
              >
                <rect
                  x={rect.x}
                  y={rect.y}
                  width={NODE_W}
                  height={NODE_H}
                  rx={7}
                  style={{
                    fill: isHov ? `var(${track.colorVar})` : `var(${track.dimVar})`,
                    stroke: `var(${track.colorVar})`,
                    strokeWidth: isHov ? 2 : 1.5,
                    transition: 'fill 0.2s, stroke-width 0.2s',
                  }}
                />
                <text
                  x={rect.cx}
                  y={rect.cy + 4.5}
                  textAnchor="middle"
                  style={{
                    fontSize: 11,
                    fontWeight: isHov ? 600 : 400,
                    fill: isHov ? '#fff' : 'var(--text)',
                    fontFamily: 'var(--font-instrument), system-ui, sans-serif',
                    pointerEvents: 'none',
                    transition: 'fill 0.2s, font-weight 0.2s',
                  }}
                >
                  {name}
                </text>
              </g>
            </Link>
          )
        })}
      </svg>
    </div>
  )
}
