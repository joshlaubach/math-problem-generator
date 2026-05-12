import Link from 'next/link'
import { MathText } from '@/components/MathText'

export default function HomePage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 64px' }}>

      {/* Hero */}
      <div style={{ maxWidth: 680, animation: 'viewIn 0.5s cubic-bezier(0.16,1,0.3,1) both' }}>

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '4px 12px', borderRadius: 20,
          background: 'var(--caramel-dim)',
          border: '1px solid rgba(196,151,106,0.2)',
          fontSize: 12, fontWeight: 500, color: 'var(--caramel)',
          marginBottom: 24,
          animation: 'fadeUp 0.5s 0.1s both',
        }}>
          ✦ Adaptive math learning
        </div>

        <h1 style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 'clamp(36px, 5vw, 58px)',
          fontWeight: 600,
          letterSpacing: '-0.03em',
          lineHeight: 1.1,
          color: 'var(--text)',
          marginBottom: 20,
          animation: 'headingSlide 0.6s 0.05s cubic-bezier(0.16,1,0.3,1) both',
        }}>
          The fastest path from{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--caramel)' }}>Pre-Algebra</em>{' '}
          to mastery
        </h1>

        <p style={{
          fontSize: 17, lineHeight: 1.7,
          color: 'var(--text-dim)',
          maxWidth: 540,
          marginBottom: 32,
          animation: 'fadeUp 0.5s 0.2s both',
        }}>
          Adaptive problem generation, step-by-step hints, and a curriculum that knows what you need to learn next — unlike a chat window that forgets you the moment you close it.
        </p>

        {/* Hero LaTeX */}
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '20px 28px',
          marginBottom: 36,
          display: 'inline-block',
          animation: 'fadeUp 0.5s 0.3s both',
          boxShadow: '0 4px 24px var(--caramel-dim)',
        }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--caramel)', marginBottom: 8, fontWeight: 600 }}>
            Beautifully rendered mathematics
          </div>
          <MathText latex="\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}" />
        </div>

        {/* CTAs */}
        <div style={{ display: 'flex', gap: 12, animation: 'fadeUp 0.5s 0.38s both' }}>
          <Link href="/sign-up" className="btn-caramel" style={{ textDecoration: 'none', padding: '12px 28px', fontSize: 15 }}>
            Get started free
          </Link>
          <Link href="/catalog" className="btn-ghost" style={{ textDecoration: 'none', padding: '12px 28px', fontSize: 15 }}>
            Browse courses →
          </Link>
        </div>
      </div>

      {/* Differentiators — bottom strip */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        maxWidth: 680,
        marginTop: 60,
        animation: 'fadeUp 0.6s 0.5s both',
      }}>
        {[
          { icon: '🧠', title: 'Remembers you', body: 'Tracks your streak, accuracy, and weak spots across every session.' },
          { icon: '🎯', title: 'Guides the work', body: 'Tiered hints scaffold your thinking — no answer until you earn it.' },
          { icon: '✓', title: 'CAS-verified', body: 'SymPy checks every answer. No hallucinated solutions.' },
        ].map(d => (
          <div key={d.title} className="warm-card" style={{ padding: '18px 20px', cursor: 'default' }}>
            <div style={{ fontSize: 22, marginBottom: 8 }}>{d.icon}</div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>{d.title}</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>{d.body}</div>
          </div>
        ))}
      </div>

    </div>
  )
}
