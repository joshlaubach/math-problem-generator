'use client'

const LABELS: Record<number, string> = {
  1: 'Intro', 2: 'Easy', 3: 'Medium', 4: 'Hard', 5: 'Advanced', 6: 'Expert',
}

interface DifficultySelectorProps {
  value: number
  min?: number
  max?: number
  recommended?: number
  onChange: (d: number) => void
}

export function DifficultySelector({ value, min = 1, max = 6, recommended, onChange }: DifficultySelectorProps) {
  const levels = Array.from({ length: max - min + 1 }, (_, i) => min + i)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <label style={{
        fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
        letterSpacing: '0.1em', color: 'var(--text-muted)',
      }}>
        Difficulty
      </label>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {levels.map(d => (
          <button
            key={d}
            type="button"
            onClick={() => onChange(d)}
            className={`diff-chip ${value === d ? 'active' : ''}`}
            style={{ position: 'relative' }}
          >
            {LABELS[d] ?? `Level ${d}`}
            {recommended === d && (
              <span style={{
                position: 'absolute', top: -6, right: -6,
                background: 'var(--forest)', color: 'white',
                fontSize: 8, padding: '1px 5px', borderRadius: 8,
                fontWeight: 700, letterSpacing: '0.05em',
              }}>
                rec
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
