'use client'

import { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

type State = 'form' | 'loading' | 'success' | 'expired' | 'error' | 'unauthenticated'

function ParentConsentContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code') ?? ''
  const { isSignedIn, isLoaded, getToken } = useAuth()

  const [parentName, setParentName] = useState('')
  const [state, setState] = useState<State>(isLoaded && !isSignedIn ? 'unauthenticated' : 'form')
  const [errorMsg, setErrorMsg] = useState('')

  if (!isLoaded) {
    return <Card><p style={{ color: 'var(--text-dim)', textAlign: 'center' }}>Loading…</p></Card>
  }

  if (!code) {
    return (
      <Card>
        <Logo />
        <h1 style={headingStyle}>Invalid link</h1>
        <p style={bodyStyle}>
          This link is missing the consent code. Ask your child to generate a new one from their
          onboarding page.
        </p>
      </Card>
    )
  }

  if (!isSignedIn || state === 'unauthenticated') {
    return (
      <Card>
        <Logo />
        <h1 style={headingStyle}>Parent consent</h1>
        <p style={bodyStyle}>
          To activate your child&apos;s account, you&apos;ll need to sign in or create a free
          Gradient account first.
        </p>
        <a
          href={`/sign-in?redirect_url=/parent-consent?code=${encodeURIComponent(code)}`}
          style={buttonStyle}
        >
          Sign in to continue
        </a>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12, textAlign: 'center' }}>
          Don&apos;t have an account?{' '}
          <a
            href={`/sign-up?redirect_url=/parent-consent?code=${encodeURIComponent(code)}`}
            style={{ color: 'var(--caramel)' }}
          >
            Create one free
          </a>
        </p>
      </Card>
    )
  }

  if (state === 'success') {
    return (
      <Card>
        <Logo />
        <h1 style={headingStyle}>All set!</h1>
        <p style={bodyStyle}>
          Your child&apos;s account is now active. They can sign in and start their first session.
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>
          You may close this tab.
        </p>
      </Card>
    )
  }

  if (state === 'expired') {
    return (
      <Card>
        <Logo />
        <h1 style={headingStyle}>Link expired</h1>
        <p style={bodyStyle}>
          This consent link has expired or has already been used. Ask your child to generate a new
          one from their onboarding page.
        </p>
      </Card>
    )
  }

  async function handleConfirm() {
    if (!parentName.trim()) return
    setState('loading')
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/parent/link/${encodeURIComponent(code)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ parent_name: parentName.trim() }),
      })
      if (res.status === 404) {
        setState('expired')
      } else if (res.ok) {
        setState('success')
      } else {
        const data = await res.json().catch(() => ({}))
        setErrorMsg(data?.detail ?? 'Something went wrong. Please try again.')
        setState('error')
      }
    } catch {
      setErrorMsg('Network error. Please check your connection and try again.')
      setState('error')
    }
  }

  return (
    <Card>
      <Logo />
      <h1 style={headingStyle}>Parent consent</h1>
      <p style={bodyStyle}>
        By confirming below, you authorise your child to use Gradient and agree that you are their
        parent or legal guardian.
      </p>

      <label style={{ display: 'block', fontSize: 13, color: 'var(--text-dim)', marginBottom: 6 }}>
        Your name
      </label>
      <input
        type="text"
        value={parentName}
        onChange={e => { setParentName(e.target.value); if (state === 'error') setState('form') }}
        placeholder="Enter your full name"
        style={inputStyle}
        disabled={state === 'loading'}
        onKeyDown={e => { if (e.key === 'Enter') handleConfirm() }}
      />

      {state === 'error' && (
        <p style={{ fontSize: 13, color: '#a03535', marginTop: 8 }}>{errorMsg}</p>
      )}

      <button
        onClick={handleConfirm}
        disabled={state === 'loading' || !parentName.trim()}
        style={{
          ...buttonStyle,
          opacity: state === 'loading' || !parentName.trim() ? 0.6 : 1,
          cursor: state === 'loading' || !parentName.trim() ? 'not-allowed' : 'pointer',
          marginTop: 16,
        }}
      >
        {state === 'loading' ? 'Confirming…' : 'Confirm & activate account'}
      </button>
    </Card>
  )
}

export default function ParentConsentPage() {
  return (
    <Suspense>
      <ParentConsentContent />
    </Suspense>
  )
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: '24px 16px',
    }}>
      <div style={{
        width: '100%', maxWidth: 420,
        background: 'var(--surface)', borderRadius: 16,
        padding: '36px 32px', boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        display: 'flex', flexDirection: 'column', gap: 0,
      }}>
        {children}
      </div>
    </div>
  )
}

function Logo() {
  return (
    <div style={{ textAlign: 'center', marginBottom: 24 }}>
      <span style={{
        fontFamily: 'var(--font-fraunces), Georgia, serif',
        fontSize: 26, fontWeight: 700, color: 'var(--text)',
        letterSpacing: '-0.5px',
      }}>
        gradient
      </span>
    </div>
  )
}

const headingStyle: React.CSSProperties = {
  fontFamily: 'var(--font-fraunces), Georgia, serif',
  fontSize: 22, fontWeight: 700, color: 'var(--text)',
  marginBottom: 12, textAlign: 'center',
}

const bodyStyle: React.CSSProperties = {
  fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.65, marginBottom: 20,
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 14px', fontSize: 14,
  background: 'var(--input-bg, var(--surface))',
  border: '1px solid var(--border)',
  borderRadius: 8, color: 'var(--text)', outline: 'none',
  boxSizing: 'border-box',
}

const buttonStyle: React.CSSProperties = {
  display: 'block', width: '100%', padding: '12px 20px',
  background: 'var(--caramel)', color: '#fff',
  fontWeight: 600, fontSize: 14, textAlign: 'center',
  borderRadius: 10, border: 'none', cursor: 'pointer',
  textDecoration: 'none',
}
