import Link from 'next/link'

const TIERS = [
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
          Every plan includes full curriculum access, rendered LaTeX, and adaptive difficulty.
          Upgrade for more daily practice and honors content.
        </p>

        {/* Tier cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: 14,
          marginBottom: 48,
        }}>
          {TIERS.map((tier) => (
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
                  position: 'absolute',
                  top: -11,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--caramel)',
                  color: 'white',
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  padding: '3px 10px',
                  borderRadius: 10,
                  whiteSpace: 'nowrap',
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
                  display: 'block',
                  textAlign: 'center',
                  padding: '9px 12px',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 500,
                  textDecoration: 'none',
                  background: tier.highlighted ? 'var(--caramel)' : 'transparent',
                  color: tier.highlighted ? 'white' : 'var(--caramel)',
                  border: `1px solid var(--caramel)`,
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

        {/* Feature comparison note */}
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
