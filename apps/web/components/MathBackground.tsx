'use client'

// Floating math symbol background + morphing warm blobs.
// Pure CSS-animated, pointer-events none, aria-hidden.

const SYMBOLS = [
  { sym: '∑', x: '4%',  dur: 32, delay: -2,  size: 22, alpha: 0.07, r0: '-5deg',  r2: '15deg'  },
  { sym: '∫', x: '9%',  dur: 45, delay: -14, size: 36, alpha: 0.04, r0: '8deg',   r2: '-12deg' },
  { sym: 'π', x: '16%', dur: 28, delay: -5,  size: 18, alpha: 0.06, r0: '0deg',   r2: '20deg'  },
  { sym: '∂', x: '22%', dur: 55, delay: -20, size: 46, alpha: 0.03, r0: '-10deg', r2: '15deg'  },
  { sym: '√', x: '30%', dur: 38, delay: -8,  size: 26, alpha: 0.05, r0: '5deg',   r2: '-15deg' },
  { sym: 'Δ', x: '38%', dur: 42, delay: -16, size: 20, alpha: 0.06, r0: '-3deg',  r2: '18deg'  },
  { sym: 'θ', x: '45%', dur: 35, delay: -3,  size: 32, alpha: 0.04, r0: '7deg',   r2: '-10deg' },
  { sym: 'λ', x: '52%', dur: 50, delay: -25, size: 16, alpha: 0.07, r0: '0deg',   r2: '25deg'  },
  { sym: '∞', x: '58%', dur: 30, delay: -10, size: 40, alpha: 0.03, r0: '-8deg',  r2: '12deg'  },
  { sym: 'φ', x: '65%', dur: 47, delay: -18, size: 24, alpha: 0.05, r0: '4deg',   r2: '-16deg' },
  { sym: 'Ω', x: '71%', dur: 36, delay: -7,  size: 28, alpha: 0.06, r0: '-6deg',  r2: '19deg'  },
  { sym: '∇', x: '78%', dur: 52, delay: -22, size: 20, alpha: 0.04, r0: '9deg',   r2: '-14deg' },
  { sym: 'μ', x: '84%', dur: 33, delay: -1,  size: 30, alpha: 0.05, r0: '-2deg',  r2: '22deg'  },
  { sym: 'σ', x: '90%', dur: 44, delay: -12, size: 18, alpha: 0.07, r0: '6deg',   r2: '-13deg' },
  { sym: 'α', x: '95%', dur: 29, delay: -9,  size: 40, alpha: 0.03, r0: '-7deg',  r2: '10deg'  },
  { sym: 'β', x: '13%', dur: 60, delay: -30, size: 14, alpha: 0.08, r0: '3deg',   r2: '-20deg' },
  { sym: 'ψ', x: '35%', dur: 39, delay: -6,  size: 22, alpha: 0.05, r0: '-4deg',  r2: '16deg'  },
  { sym: 'ε', x: '55%', dur: 48, delay: -24, size: 34, alpha: 0.03, r0: '10deg',  r2: '-8deg'  },
  { sym: 'γ', x: '73%', dur: 31, delay: -4,  size: 20, alpha: 0.06, r0: '-1deg',  r2: '23deg'  },
  { sym: 'ζ', x: '88%', dur: 57, delay: -28, size: 16, alpha: 0.07, r0: '8deg',   r2: '-18deg' },
]

export function MathBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    >
      {/* Warm morphing blobs */}
      <div style={{
        position: 'absolute',
        width: 520, height: 520,
        background: 'radial-gradient(circle, #c4976a, #e8b98a)',
        top: -130, left: -130,
        filter: 'blur(90px)',
        opacity: 0.09,
        animation: 'blob1 20s ease-in-out infinite',
      }} />
      <div style={{
        position: 'absolute',
        width: 420, height: 420,
        background: 'radial-gradient(circle, #2d6a4f, #5a9e7a)',
        bottom: -80, right: -80,
        filter: 'blur(80px)',
        opacity: 0.07,
        animation: 'blob2 25s ease-in-out infinite',
      }} />
      <div style={{
        position: 'absolute',
        width: 300, height: 300,
        background: 'radial-gradient(circle, #c1440e, #e8845a)',
        top: '45%', left: '42%',
        filter: 'blur(70px)',
        opacity: 0.04,
        animation: 'blob3 35s ease-in-out infinite',
      }} />

      {/* Floating math symbols */}
      {SYMBOLS.map((s, i) => (
        <span
          key={i}
          style={{
            position: 'absolute',
            bottom: -80,
            left: s.x,
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: s.size,
            fontStyle: 'italic',
            color: 'var(--caramel)',
            opacity: 0,
            userSelect: 'none',
            lineHeight: 1,
            // CSS custom properties for the keyframe
            ['--alpha' as string]: s.alpha,
            ['--r0' as string]: s.r0,
            ['--r2' as string]: s.r2,
            animation: `floatSym ${s.dur}s ${s.delay}s infinite ease-in-out`,
          } as React.CSSProperties}
        >
          {s.sym}
        </span>
      ))}
    </div>
  )
}
