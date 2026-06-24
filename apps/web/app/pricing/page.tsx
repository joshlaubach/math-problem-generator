import Link from 'next/link'

const SESSION_PRODUCTS = [
  {
    id: '1hr',
    name: '1-Hour Session',
    price: '$20',
    unit: 'per session',
    description: 'One hour with your AI math tutor. Pick up exactly where you left off each time.',
    highlighted: true,
    badge: 'Most popular',
    ctaHref: '/credits/checkout?bundle=1hr',
    cta: 'Buy a session',
  },
  {
    id: '2hr',
    name: '2-Hour Session',
    price: '$35',
    unit: 'per session',
    description: 'Deep-dive on hard topics. Best for test prep or complex homework blocks.',
    highlighted: false,
    badge: null,
    ctaHref: '/credits/checkout?bundle=2hr',
    cta: 'Buy a session',
  },
  {
    id: '5x1hr',
    name: '5× 1-Hour Sessions',
    price: '$90',
    unit: 'saves $10',
    description: 'Stock up and save. Five 1-hour sessions. Credits never expire within 6 months.',
    highlighted: false,
    badge: 'Best value',
    ctaHref: '/credits/checkout?bundle=5x1hr',
    cta: 'Buy 5 sessions',
  },
] as const

const SUBSCRIPTION_TIERS = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    problems: '5 / day',
    hints: '2 of 4',
    honors: false,
    honorsNote: 'Standard only',
    teacher: false,
    cta: 'Get started',
    ctaHref: '/sign-up',
    highlighted: false,
  },
  {
    id: 'basic',
    name: 'Explorer',
    price: '$4',
    period: 'per month',
    problems: '30 / day',
    hints: '3 of 4',
    honors: false,
    honorsNote: 'Standard only',
    teacher: false,
    cta: 'Start Explorer',
    ctaHref: '/sign-up?plan=basic',
    highlighted: false,
  },
  {
    id: 'student',
    name: 'Student',
    price: '$9',
    period: 'per month',
    problems: '100 / day',
    hints: '4 of 4',
    honors: true,
    honorsNote: 'HS Honors included',
    teacher: false,
    cta: 'Start Student',
    ctaHref: '/sign-up?plan=student',
    highlighted: true,
  },
  {
    id: 'honors',
    name: 'Honors',
    price: '$16',
    period: 'per month',
    problems: '300 / day',
    hints: '4 of 4',
    honors: true,
    honorsNote: 'All honors topics',
    teacher: false,
    cta: 'Start Honors',
    ctaHref: '/sign-up?plan=honors',
    highlighted: false,
  },
  {
    id: 'classroom-student',
    name: 'Teacher',
    price: '$29',
    period: 'per month',
    problems: '500 / day',
    hints: '4 of 4',
    honors: true,
    honorsNote: 'All honors topics',
    teacher: true,
    cta: 'Start Teaching',
    ctaHref: '/sign-up?plan=classroom-student',
    highlighted: false,
  },
] as const

const FEATURES: Array<{ key: string; label: string; isBoolean?: boolean }> = [
  { key: 'problems',   label: 'Problems per day' },
  { key: 'hints',      label: 'Hints per problem' },
  { key: 'honorsNote', label: 'Honors topics' },
  { key: 'teacher',    label: 'Teacher mode', isBoolean: true },
]

export default function PricingPage() {
  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/">Home</Link>
          <span className="sep">/</span>
          <span className="current">Pricing</span>
        </nav>
      </div>

      <div className="page-content" style={{ maxWidth: 1100 }}>
        <h1 className="display-heading" style={{ marginBottom: 6 }}>
          Simple, <em>transparent</em> pricing
        </h1>
        <p className="page-subtitle">
          Practice with the problem generator on any plan. Buy a tutoring session when you want live guidance.
        </p>

        {/* ── Tutoring Sessions ──────────────────────────────────────────── */}
        <h2 className="section-heading" style={{ marginBottom: 16, marginTop: 8 }}>
          AI Tutoring Sessions
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 24, lineHeight: 1.65, maxWidth: 560 }}>
          Pay per session — no subscription. Credits are good for 6 months.
          Start with a{' '}
          <Link href="/tutor/demo" style={{ color: 'var(--caramel)', fontWeight: 500 }}>
            free 30-minute demo
          </Link>
          {' '}to try before you buy.
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 48,
        }}>
          {SESSION_PRODUCTS.map(p => (
            <div
              key={p.id}
              style={{
                background: p.highlighted ? 'var(--caramel-dim)' : 'var(--surface)',
                border: `1px solid ${p.highlighted ? 'var(--caramel)' : 'var(--border)'}`,
                borderRadius: 12,
                padding: '24px 22px',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
              }}
            >
              {p.badge && (
                <div style={{
                  position: 'absolute', top: -11, left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--caramel)', color: 'white',
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
                  textTransform: 'uppercase', padding: '3px 10px',
                  borderRadius: 10, whiteSpace: 'nowrap',
                }}>
                  {p.badge}
                </div>
              )}

              <div style={{
                fontFamily: 'var(--font-fraunces), Georgia, serif',
                fontSize: 17, fontWeight: 600, color: 'var(--text)', marginBottom: 4,
              }}>
                {p.name}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
                <span style={{
                  fontFamily: 'var(--font-fraunces), Georgia, serif',
                  fontSize: 34, fontWeight: 600, color: 'var(--caramel)', lineHeight: 1,
                }}>
                  {p.price}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>{p.unit}</div>
              <p style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 20, flex: 1 }}>
                {p.description}
              </p>

              <Link
                href={p.ctaHref}
                style={{
                  display: 'block', textAlign: 'center',
                  padding: '10px 12px', borderRadius: 8,
                  fontSize: 13, fontWeight: 600, textDecoration: 'none',
                  background: p.highlighted ? 'var(--caramel)' : 'transparent',
                  color: p.highlighted ? 'white' : 'var(--text-dim)',
                  border: `1px solid ${p.highlighted ? 'var(--caramel)' : 'var(--border2)'}`,
                  transition: 'all 0.2s',
                }}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Tutoring features */}
        <div className="warm-card-static" style={{ padding: '22px 28px', marginBottom: 48 }}>
          <h2 className="section-heading" style={{ marginBottom: 12 }}>What&apos;s included in every session</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {[
              { icon: '🎯', title: 'Guided, not answered', body: 'Tiered hints scaffold your thinking. You do the work — the tutor guides you there.' },
              { icon: '✓',  title: 'SymPy-graded answers', body: 'Computer algebra checks every answer. No pattern-matching guesses.' },
              { icon: '🧠', title: 'Remembers you', body: 'Tracks your accuracy and weak spots so every session picks up where you left off.' },
              { icon: '📐', title: 'Live whiteboard', body: 'The tutor writes on a shared whiteboard in real time as it teaches.' },
              { icon: '🎙️', title: 'Voice + text', body: 'Answer verbally or type. The tutor talks back. Switch anytime mid-session.' },
              { icon: '📄', title: 'Session summary', body: 'You get a summary of topics covered and problems to practice after every session.' },
            ].map(f => (
              <div key={f.title} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 2 }}>{f.icon}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{f.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{f.body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Practice Subscriptions ─────────────────────────────────────── */}
        <h2 className="section-heading" style={{ marginBottom: 8 }}>Practice Plans</h2>
        <p style={{ fontSize: 14, color: 'var(--text-dim)', marginBottom: 24, lineHeight: 1.65 }}>
          Unlimited problem practice, adaptive difficulty, and progress tracking. No tutoring included — add session credits separately.
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: 14,
          marginBottom: 48,
        }}>
          {SUBSCRIPTION_TIERS.map((tier) => (
            <div
              key={tier.id}
              style={{
                background: tier.highlighted ? 'var(--caramel-dim)' : 'var(--surface)',
                border: `1px solid ${tier.highlighted ? 'var(--caramel)' : 'var(--border)'}`,
                borderRadius: 12,
                padding: '24px 20px',
                display: 'flex',
                flexDirection: 'column',
                gap: 0,
                position: 'relative',
              }}
            >
              {tier.highlighted && (
                <div style={{
                  position: 'absolute', top: -11, left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--caramel)', color: 'white',
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
                  textTransform: 'uppercase', padding: '3px 10px',
                  borderRadius: 10, whiteSpace: 'nowrap',
                }}>
                  Most popular
                </div>
              )}

              <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 17, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
                {tier.name}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 32, fontWeight: 600, color: 'var(--caramel)', lineHeight: 1 }}>
                  {tier.price}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>{tier.period}</div>

              <Link
                href={tier.ctaHref}
                style={{
                  display: 'block', textAlign: 'center',
                  padding: '9px 12px', borderRadius: 8,
                  fontSize: 13, fontWeight: 500, textDecoration: 'none',
                  background: tier.highlighted ? 'var(--caramel)' : 'transparent',
                  color: tier.highlighted ? 'white' : 'var(--text-dim)',
                  border: `1px solid ${tier.highlighted ? 'var(--caramel)' : 'var(--border2)'}`,
                  marginBottom: 20,
                  transition: 'all 0.2s',
                }}
              >
                {tier.cta}
              </Link>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
                {FEATURES.map((f) => {
                  const val = (tier as Record<string, unknown>)[f.key]
                  return (
                    <div key={f.key} style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>
                        {f.label}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>
                        {f.isBoolean
                          ? (val ? '✓ Included' : '—')
                          : String(val)}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* What's in every plan */}
        <div className="warm-card-static" style={{ padding: '22px 28px', marginBottom: 32 }}>
          <h2 className="section-heading" style={{ marginBottom: 12 }}>What&apos;s in every plan</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {[
              { icon: '📐', title: '15 courses', body: 'Pre-Algebra through graduate-level mathematics' },
              { icon: '🔢', title: 'Rendered LaTeX', body: 'Beautiful math notation via KaTeX on every problem' },
              { icon: '🎯', title: 'Adaptive difficulty', body: '6 difficulty levels from Introductory to Expert' },
              { icon: '∫', title: 'Solution-first problems', body: 'Every answer is CAS-verified before you see it' },
              { icon: '💡', title: 'Progressive hints', body: 'Scaffolded hints that guide without spoiling' },
              { icon: '📈', title: 'Progress tracking', body: 'Streak tracking, accuracy stats, session history' },
            ].map(f => (
              <div key={f.title} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 2 }}>{f.icon}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{f.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{f.body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Teacher mode callout */}
        <div style={{
          background: 'var(--caramel-dim)',
          border: '1px solid rgba(196,151,106,0.3)',
          borderRadius: 12,
          padding: '22px 28px',
        }}>
          <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
            👨‍🏫 Teacher mode
          </div>
          <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7, maxWidth: 600 }}>
            Teacher plan includes a <strong style={{ color: 'var(--text)' }}>Reveal Solution</strong> button on every problem —
            show the full answer, worked steps, and all hints at once for classroom demonstrations and homework review.
            Includes all honors topics and 500 problems per day.
          </p>
        </div>
      </div>
    </>
  )
}
