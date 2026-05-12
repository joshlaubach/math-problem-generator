import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface LegalPageProps {
  title: string
  subtitle?: string
  effectiveDate: string
  lastUpdated: string
  content: string
}

export function LegalPage({ title, subtitle, effectiveDate, lastUpdated, content }: LegalPageProps) {
  return (
    <>
      <div className="page-cover">
        <nav className="breadcrumb">
          <Link href="/">Home</Link>
          <span className="sep">/</span>
          <span className="current">{title}</span>
        </nav>
      </div>

      <div className="page-content" style={{ maxWidth: 760 }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 className="display-heading" style={{ marginBottom: 6 }}>{title}</h1>
          {subtitle && (
            <p style={{ fontSize: 15, color: 'var(--text-dim)', marginBottom: 12 }}>{subtitle}</p>
          )}
          <div style={{ display: 'flex', gap: 20, fontSize: 13, color: 'var(--text-muted)' }}>
            <span>Effective: {effectiveDate}</span>
            <span>Last updated: {lastUpdated}</span>
          </div>
        </div>

        {/* Disclaimer banner */}
        <div style={{
          padding: '12px 16px', marginBottom: 32,
          borderRadius: 8, border: '1px solid var(--border)',
          background: 'var(--surface2)',
          fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6,
        }}>
          <strong style={{ color: 'var(--text)' }}>Not legal advice.</strong> This document was prepared for informational purposes. Josh Laubach d/b/a Gradient recommends consulting a licensed attorney before relying on these terms for legal compliance.
        </div>

        {/* Content */}
        <div className="legal-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>

        {/* Footer nav */}
        <div style={{
          marginTop: 48, paddingTop: 24,
          borderTop: '1px solid var(--border)',
          display: 'flex', gap: 20, flexWrap: 'wrap',
          fontSize: 13, color: 'var(--text-muted)',
        }}>
          <Link href="/terms" style={{ color: 'var(--caramel)', textDecoration: 'none' }}>Terms of Service</Link>
          <Link href="/privacy" style={{ color: 'var(--caramel)', textDecoration: 'none' }}>Privacy Policy</Link>
          <Link href="/dpa" style={{ color: 'var(--caramel)', textDecoration: 'none' }}>Data Processing Agreement</Link>
          <span style={{ flex: 1 }} />
          <span>© {new Date().getFullYear()} Josh Laubach d/b/a Gradient. All rights reserved.</span>
        </div>
      </div>
    </>
  )
}
