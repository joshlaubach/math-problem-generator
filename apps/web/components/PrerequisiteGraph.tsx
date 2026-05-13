import Link from 'next/link';

interface CourseNode {
  id: string;
  name: string;
}

interface PrerequisiteGraphProps {
  courses: CourseNode[];
}

// ─── Layout constants ─────────────────────────────────────────────────────────

const NODE_W = 196;
const NODE_H = 40;
const COL_X = [16, 296, 576];
const ROW_START_Y = 44;
const ROW_GAP = 56;
const SVG_W = 856;

const COL_LABELS = ['High School', 'Applied Math', 'Advanced'];
// Uses CSS variables so colors adapt to light/dark mode
const COL_COLORS = ['var(--hs-color)', 'var(--applied-color)', 'var(--adv-color)'];

// Fixed course columns (col index)
const COURSE_COL: Record<string, number> = {
  // High School
  prealgebra: 0, algebra_1: 0, geometry: 0, algebra_2: 0, precalculus: 0,
  // Applied Math
  probability: 1, statistics: 1, calculus_1: 1, calculus_2: 1, calculus_3: 1,
  // Advanced
  linear_algebra: 2, differential_equations: 2, discrete_math: 2, proofs: 2, contest_math: 2,
};

const COL_ORDER: string[][] = [
  ['prealgebra', 'algebra_1', 'geometry', 'algebra_2', 'precalculus'],
  ['probability', 'statistics', 'calculus_1', 'calculus_2', 'calculus_3'],
  ['linear_algebra', 'differential_equations', 'discrete_math', 'proofs', 'contest_math'],
];

// Prerequisite edges (source → target)
const PREREQ_EDGES: [string, string][] = [
  ['prealgebra', 'algebra_1'],
  ['algebra_1', 'geometry'],
  ['algebra_1', 'algebra_2'],
  ['algebra_2', 'precalculus'],
  ['geometry', 'precalculus'],
  ['algebra_2', 'probability'],
  ['probability', 'statistics'],
  ['precalculus', 'calculus_1'],
  ['calculus_1', 'calculus_2'],
  ['calculus_2', 'calculus_3'],
  ['calculus_1', 'linear_algebra'],
  ['calculus_2', 'differential_equations'],
  ['algebra_2', 'discrete_math'],
  ['discrete_math', 'proofs'],
  ['algebra_2', 'contest_math'],
];

function nodePos(id: string): { x: number; y: number } | null {
  const col = COURSE_COL[id];
  if (col === undefined) return null;
  const row = COL_ORDER[col].indexOf(id);
  if (row === -1) return null;
  return { x: COL_X[col], y: ROW_START_Y + row * ROW_GAP };
}

function arrowPath(from: { x: number; y: number }, to: { x: number; y: number }): string {
  const x1 = from.x + NODE_W;
  const y1 = from.y + NODE_H / 2;
  const x2 = to.x;
  const y2 = to.y + NODE_H / 2;
  const sameCol = Math.abs(from.x - to.x) < 4;

  if (sameCol) {
    const ox = from.x + NODE_W + 24;
    return `M ${x1} ${y1} C ${ox} ${y1} ${ox} ${y2} ${x1} ${y2}`;
  }
  const cx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${cx} ${y1} ${cx} ${y2} ${x2} ${y2}`;
}

export function PrerequisiteGraph({ courses }: PrerequisiteGraphProps) {
  const courseMap = new Map(courses.map((c) => [c.id, c]));
  const maxRows = Math.max(...COL_ORDER.map((col) => col.length));
  const svgH = ROW_START_Y + maxRows * ROW_GAP + 16;

  return (
    <div className="overflow-x-auto rounded-xl p-2" style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
      <svg
        viewBox={`0 0 ${SVG_W} ${svgH}`}
        style={{ width: '100%', minWidth: 480, height: svgH }}
        aria-label="Course prerequisite dependency graph"
      >
        <defs>
          <marker id="arrow" markerWidth={7} markerHeight={7} refX={6} refY={3.5} orient="auto">
            <path d="M0,0 L0,7 L7,3.5 z" fill="var(--text-muted)" />
          </marker>
        </defs>

        {/* Column headers */}
        {COL_LABELS.map((label, i) => (
          <text
            key={label}
            x={COL_X[i] + NODE_W / 2}
            y={22}
            textAnchor="middle"
            fontSize={12}
            fontWeight="700"
            fill={COL_COLORS[i]}
            letterSpacing="0.03em"
          >
            {label.toUpperCase()}
          </text>
        ))}

        {/* Edges */}
        {PREREQ_EDGES.map(([fromId, toId]) => {
          const from = nodePos(fromId);
          const to = nodePos(toId);
          if (!from || !to) return null;
          return (
            <path
              key={`${fromId}-${toId}`}
              d={arrowPath(from, to)}
              fill="none"
              stroke="var(--border2)"
              strokeWidth={1.5}
              markerEnd="url(#arrow)"
            />
          );
        })}

        {/* Course nodes */}
        {COL_ORDER.flatMap((col, colIdx) =>
          col.map((id) => {
            const pos = nodePos(id);
            if (!pos) return null;
            const course = courseMap.get(id);
            const label = course?.name ?? id;
            const color = COL_COLORS[colIdx];
            return (
              <Link key={id} href={`/catalog/${id}`}>
                <g style={{ cursor: 'pointer' }}>
                  <rect
                    x={pos.x}
                    y={pos.y}
                    width={NODE_W}
                    height={NODE_H}
                    rx={8}
                    fill={color}
                    fillOpacity={0.1}
                    stroke={color}
                    strokeWidth={1.5}
                  />
                  <text
                    x={pos.x + NODE_W / 2}
                    y={pos.y + NODE_H / 2 + 5}
                    textAnchor="middle"
                    fontSize={11}
                    fill="var(--text)"
                  >
                    {label.length > 24 ? label.slice(0, 22) + '…' : label}
                  </text>
                </g>
              </Link>
            );
          }),
        )}
      </svg>
    </div>
  );
}
