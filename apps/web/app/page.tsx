import Link from 'next/link'
import { DemoProblem } from '@/components/DemoProblem'
import { MathText } from '@/components/MathText'

// ── Whiteboard preview animation ───────────────────────────────────────────────

const WB_CSS = `
@keyframes wb-1{0%,8%{opacity:0;transform:translateY(5px)}14%,100%{opacity:1;transform:translateY(0)}}
@keyframes wb-2{0%,24%{opacity:0;transform:translateY(5px)}30%,100%{opacity:1;transform:translateY(0)}}
@keyframes wb-3{0%,40%{opacity:0;transform:translateY(5px)}46%,100%{opacity:1;transform:translateY(0)}}
@keyframes wb-4{0%,56%{opacity:0;transform:translateY(5px)}62%,100%{opacity:1;transform:translateY(0)}}
@keyframes wb-check{0%,64%{opacity:0;transform:scale(0.3)}72%,100%{opacity:1;transform:scale(1)}}
@keyframes wb-bar{0%,100%{transform:scaleY(0.25)}50%{transform:scaleY(1)}}
@keyframes wb-bubble{0%,58%{opacity:0;transform:translateY(4px)}65%,100%{opacity:1;transform:translateY(0)}}
.wb-panel{background:#faf8f4;border:1px solid #e5ddd0}
.wb-toolbar{background:#f2ede4;border-bottom:1px solid #e5ddd0}
.wb-toolbar-label{color:#888}
.wb-bubble{background:#fff;border:1px solid #e5ddd0;color:#555}
.wb-hint{color:#aaa}
[data-theme="dark"] .wb-panel{background:#1c2210;border:1px solid #3a4a28}
[data-theme="dark"] .wb-toolbar{background:#151c0d;border-bottom:1px solid #3a4a28}
[data-theme="dark"] .wb-toolbar-label{color:#6b7c52}
[data-theme="dark"] .wb-bubble{background:#1c2210;border:1px solid #3a4a28;color:#a8b890}
[data-theme="dark"] .wb-hint{color:#5a6e44}
[data-theme="dark"] .wb-eq{color:#d4e8b0}
`

function WhiteboardPreview() {
  const steps = [
    { latex: '2x + 5 = 13', anim: 'wb-1' },
    { latex: '2x = 13 - 5', anim: 'wb-2' },
    { latex: '2x = 8',      anim: 'wb-3' },
    { latex: 'x = 4',       anim: 'wb-4', bold: true },
  ]
  const barDurs = ['1.2s','1.5s','1.1s','1.4s','1.3s']

  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: 420 }}>
      <style>{WB_CSS}</style>

      {/* Main whiteboard/blackboard panel */}
      <div className="wb-panel" style={{
        borderRadius: 16,
        overflow: 'hidden',
        boxShadow: '0 12px 48px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.04)',
      }}>
        {/* Toolbar */}
        <div className="wb-toolbar" style={{
          height: 42,
          display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7, background: 'var(--caramel)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, color: '#fff', flexShrink: 0,
          }}>✦</div>
          <span className="wb-toolbar-label" style={{ fontSize: 12, fontWeight: 600, fontFamily: 'system-ui,sans-serif' }}>
            Whiteboard
          </span>
          {/* Speaking indicator */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 10, fontWeight: 600, color: 'var(--caramel)',
              fontFamily: 'system-ui,sans-serif', letterSpacing: '0.02em',
            }}>Tutor speaking</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 2, height: 14 }}>
              {barDurs.map((dur, i) => (
                <div key={i} style={{
                  width: 3, height: 14, background: 'var(--caramel)', borderRadius: 2, transformOrigin: 'bottom',
                  animation: `wb-bar ${dur} ease-in-out infinite`,
                  animationDelay: `${i * 0.12}s`,
                }} />
              ))}
            </div>
          </div>
        </div>

        {/* Whiteboard content */}
        <div style={{ padding: '26px 32px 32px' }}>
          <div className="wb-hint" style={{
            fontSize: 12, fontFamily: 'system-ui,sans-serif',
            marginBottom: 20, animation: 'wb-1 10s ease infinite',
          }}>
            "Let&apos;s solve this step by step."
          </div>
          {steps.map(({ latex, anim, bold }) => (
            <div key={latex} className={bold ? undefined : 'wb-eq'} style={{
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              fontSize: 28,
              color: bold ? 'var(--caramel)' : undefined,
              fontWeight: bold ? 700 : 400,
              marginBottom: 16, letterSpacing: '-0.01em',
              animation: `${anim} 10s ease infinite`,
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <MathText latex={latex} inline />
              {bold && (
                <span style={{
                  fontSize: 18, color: 'var(--sage)',
                  animation: 'wb-check 10s ease infinite',
                  display: 'inline-block',
                }}>✓</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Floating tutor comment bubble */}
      <div className="wb-bubble" style={{
        position: 'absolute', bottom: -18, right: -10,
        borderRadius: '12px 12px 2px 12px',
        padding: '9px 14px', maxWidth: 210,
        fontSize: 12, lineHeight: 1.5,
        fontFamily: 'system-ui,sans-serif',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
        animation: 'wb-bubble 10s ease infinite',
      }}>
        "Good. Now why did we subtract 5 from both sides?"
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      color: 'var(--text)',
    }}>

      {/* ── Hero ──────────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 80,
        padding: '72px 64px 56px',
        flexWrap: 'wrap',
      }}>
        {/* Left: headline + CTAs */}
        <div style={{ flex: '1 1 340px', maxWidth: 520, animation: 'viewIn 0.5s cubic-bezier(0.16,1,0.3,1) both' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '4px 12px', borderRadius: 20,
            background: 'var(--caramel-dim)',
            border: '1px solid rgba(196,151,106,0.2)',
            fontSize: 12, fontWeight: 500, color: 'var(--caramel)',
            marginBottom: 24,
            animation: 'fadeUp 0.5s 0.1s both',
          }}>
            ✦ Built by a professional math tutor
          </div>

          <h1 style={{
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 'clamp(32px, 4.5vw, 52px)',
            fontWeight: 600,
            letterSpacing: '-0.03em',
            lineHeight: 1.1,
            color: 'var(--text)',
            marginBottom: 20,
            animation: 'headingSlide 0.6s 0.05s cubic-bezier(0.16,1,0.3,1) both',
          }}>
            A real math tutor —{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--caramel)' }}>always available</em>
          </h1>

          <p style={{
            fontSize: 17, lineHeight: 1.7,
            color: 'var(--text-dim)',
            maxWidth: 460,
            marginBottom: 12,
            animation: 'fadeUp 0.5s 0.2s both',
          }}>
            Bring your homework, your textbook, your test prep — whatever you're actually working on.
            No courses to follow. No subscription.
          </p>
          <p style={{
            fontSize: 15, color: 'var(--text-muted)',
            marginBottom: 32,
            animation: 'fadeUp 0.5s 0.25s both',
          }}>
            $20 per session · never cancels · never loses patience
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', animation: 'fadeUp 0.5s 0.32s both' }}>
            <Link href="/tutor/demo" className="btn-caramel" style={{ textDecoration: 'none', padding: '13px 28px', fontSize: 15 }}>
              Try a free session
            </Link>
            <Link href="/sign-up" className="btn-ghost" style={{ textDecoration: 'none', padding: '13px 28px', fontSize: 15 }}>
              Create account →
            </Link>
          </div>
        </div>

        {/* Right: Whiteboard preview */}
        <div style={{ flex: '1 1 320px', maxWidth: 440, animation: 'fadeUp 0.6s 0.2s both' }}>
          <WhiteboardPreview />
        </div>
      </div>

      {/* ── Comparison strip ──────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 0,
        padding: '0 64px',
        maxWidth: 860,
        margin: '0 auto 56px',
        width: '100%',
        animation: 'fadeUp 0.5s 0.4s both',
      }}>
        {[
          { label: 'Human tutor', price: '$80–150 / hr', note: 'cancels, unavailable late at night', dim: true },
          { label: 'Subscription apps', price: '~$300 / year', note: 'follows their curriculum, not yours', dim: true },
          { label: 'Gradient', price: '$20 / session', note: 'your homework, your pace, no commitment', dim: false },
        ].map((col, i) => (
          <div key={col.label} style={{
            flex: 1, padding: '16px 20px',
            background: col.dim ? 'transparent' : 'var(--surface)',
            border: `1px solid ${col.dim ? 'transparent' : 'var(--caramel)'}`,
            borderRadius: i === 0 ? '12px 0 0 12px' : i === 2 ? '0 12px 12px 0' : 0,
            opacity: col.dim ? 0.55 : 1,
            position: 'relative',
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: col.dim ? 'var(--text-muted)' : 'var(--caramel)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
              {col.label}
            </div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 20, fontWeight: 700, color: col.dim ? 'var(--text-muted)' : 'var(--text)', marginBottom: 4 }}>
              {col.price}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
              {col.note}
            </div>
          </div>
        ))}
      </div>

      {/* ── How it works ──────────────────────────────────────────────────────── */}
      <div style={{
        padding: '0 64px 64px',
        maxWidth: 860,
        margin: '0 auto',
        width: '100%',
        animation: 'fadeUp 0.5s 0.45s both',
      }}>
        <div style={{
          fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 24,
        }}>
          How it works
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { n: '1', title: 'Bring your problem', body: 'Paste your homework, describe what you\'re stuck on, or type a problem directly. Your curriculum, not ours.' },
            { n: '2', title: 'Watch it on the whiteboard', body: 'Your tutor writes equations in real time and explains each step — exactly like sitting at the board with a person.' },
            { n: '3', title: 'Talk it through', body: 'Speak your answer or ask questions out loud. The tutor listens, guides, and won\'t give you the answer until you\'ve earned it.' },
          ].map(({ n, title, body }) => (
            <div key={n} className="warm-card" style={{ padding: '20px 22px' }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--caramel)',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, marginBottom: 12, flexShrink: 0,
              }}>{n}</div>
              <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>{title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.55 }}>{body}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Interactive demo ──────────────────────────────────────────────────── */}
      <div style={{
        padding: '0 64px 64px',
        maxWidth: 860,
        margin: '0 auto',
        width: '100%',
        animation: 'fadeUp 0.5s 0.5s both',
      }}>
        <div style={{
          fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 20,
        }}>
          Try a real problem
        </div>
        <DemoProblem />
      </div>

      {/* ── Pricing ───────────────────────────────────────────────────────────── */}
      <div style={{
        padding: '0 64px 64px',
        maxWidth: 860,
        margin: '0 auto',
        width: '100%',
        animation: 'fadeUp 0.5s 0.55s both',
      }}>
        <div style={{
          fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 20,
        }}>
          Pay per session — no subscription
        </div>
        <div style={{ display: 'flex', gap: 12, maxWidth: 480 }}>
          {[
            { duration: '1-hour session', price: '$20', note: 'Most popular' },
            { duration: '2-hour session', price: '$35', note: 'Best value' },
          ].map(p => (
            <div key={p.duration} className="warm-card" style={{ flex: 1, padding: '20px 22px' }}>
              <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 26, fontWeight: 700, color: 'var(--text)' }}>
                {p.price}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 2, marginBottom: 10 }}>{p.duration}</div>
              <div style={{
                display: 'inline-block',
                fontSize: 11, fontWeight: 600, color: 'var(--caramel)',
                background: 'var(--caramel-dim)', padding: '2px 8px', borderRadius: 4,
              }}>
                {p.note}
              </div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 14 }}>
          Credits never expire. Use one session a month or ten — each one is the same price.
        </p>
      </div>

      {/* ── Meet the tutor ────────────────────────────────────────────────────── */}
      <div style={{
        padding: '0 64px 72px',
        maxWidth: 860,
        margin: '0 auto',
        width: '100%',
        animation: 'fadeUp 0.5s 0.6s both',
      }}>
        <div className="warm-card" style={{ padding: '32px 36px', display: 'flex', gap: 32, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          {/* Avatar — replace src with a real photo */}
          <div style={{
            width: 80, height: 80, borderRadius: '50%', flexShrink: 0,
            background: 'var(--caramel)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--font-fraunces), Georgia, serif',
            fontSize: 32, color: '#fff', fontWeight: 700,
            overflow: 'hidden',
          }}>
            {/* Swap this div for an <img> tag once you have a photo */}
            JL
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 8 }}>
              Built by a professional math tutor
            </div>
            <div style={{ fontFamily: 'var(--font-fraunces), Georgia, serif', fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
              Josh Laubach
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 13, color: 'var(--caramel)', fontWeight: 600 }}>
                Professional Math Tutor · 10 years
              </span>
              <div style={{ display: 'flex', gap: 10 }}>
                {[
                  { label: 'joshlaubach.com', href: 'https://joshlaubach.com' },
                  { label: 'LinkedIn', href: 'https://linkedin.com/in/josh-laubach/' },
                  { label: 'GitHub', href: 'https://github.com/joshlaubach' },
                ].map(({ label, href }) => (
                  <a key={label} href={href} target="_blank" rel="noopener noreferrer" style={{
                    fontSize: 11, color: 'var(--text-muted)', textDecoration: 'none',
                    border: '1px solid var(--border)', borderRadius: 5,
                    padding: '2px 7px', fontFamily: 'system-ui, sans-serif',
                  }}>
                    {label}
                  </a>
                ))}
              </div>
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.7, maxWidth: 480 }}>
              I've been tutoring math one-on-one for over ten years. Every decision in this product — how it responds to wrong answers,
              how it guides you through steps, when it knows to back up and start fresh — comes from what actually works sitting
              across the table from a student. This is the tutoring approach I use, taught at scale.
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
