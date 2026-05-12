'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useUser, UserButton, SignInButton, SignUpButton } from '@clerk/nextjs'
import Link from 'next/link'
import {
  House, Books, PencilSimple, ChartLineUp,
  Users, Flag, ChartBar, Timer, Sun, Moon,
} from '@phosphor-icons/react'

function ThemeToggle() {
  const [dark, setDark] = useState(false)

  useEffect(() => {
    setDark(document.documentElement.getAttribute('data-theme') === 'dark')
  }, [])

  function toggle() {
    const next = dark ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    localStorage.setItem('theme', next)
    setDark(!dark)
  }

  return (
    <button
      onClick={toggle}
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        width: 26, height: 26,
        borderRadius: 5,
        background: 'none',
        border: '1px solid var(--border)',
        cursor: 'pointer',
        color: 'var(--text-dim)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.25s',
        flexShrink: 0,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--caramel)'
        ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--caramel)'
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'
        ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-dim)'
      }}
    >
      {dark ? <Sun size={13} weight="bold" /> : <Moon size={13} weight="bold" />}
    </button>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const { isSignedIn, isLoaded, user } = useUser()

  function isActive(href: string) {
    if (href === '/') return pathname === '/'
    return pathname === href || pathname.startsWith(href + '/')
  }

  const isAdmin = (user?.publicMetadata as { role?: string })?.role === 'admin'

  return (
    <aside className="app-sidebar">
      {/* Logo + theme toggle */}
      <div style={{
        padding: '16px 14px 12px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: 6,
          background: 'var(--caramel)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, flexShrink: 0,
        }}>
          ✦
        </div>
        <span style={{
          fontFamily: 'var(--font-fraunces), Georgia, serif',
          fontSize: 15, fontWeight: 600,
          color: 'var(--text)',
          letterSpacing: '-0.01em',
          flex: 1,
        }}>
          Gradient
        </span>
        <ThemeToggle />
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '8px 0', overflowY: 'auto' }}>
        {isLoaded && isSignedIn && (
          <>
            <div className="nav-section-label">Workspace</div>
            <Link href="/dashboard" className={`nav-item ${isActive('/dashboard') ? 'active' : ''}`}>
              <span className="nav-icon"><House size={15} weight={isActive('/dashboard') ? 'fill' : 'regular'} /></span>
              Dashboard
            </Link>

            <div className="nav-section-label" style={{ marginTop: 10 }}>Courses</div>
            <Link href="/catalog" className={`nav-item ${isActive('/catalog') ? 'active' : ''}`}>
              <span className="nav-icon"><Books size={15} weight={isActive('/catalog') ? 'fill' : 'regular'} /></span>
              Course Catalog
            </Link>

            <div className="nav-section-label" style={{ marginTop: 10 }}>Practice</div>
            <Link
              href="/catalog"
              className={`nav-item ${pathname.startsWith('/practice') ? 'active' : ''}`}
            >
              <span className="nav-icon"><PencilSimple size={15} weight={pathname.startsWith('/practice') ? 'fill' : 'regular'} /></span>
              Practice Session
            </Link>
            <Link href="/dashboard" className="nav-item">
              <span className="nav-icon"><ChartLineUp size={15} /></span>
              My Progress
            </Link>

            {isAdmin && (
              <>
                <div className="nav-section-label" style={{ marginTop: 10 }}>Admin</div>
                <Link href="/admin/users" className={`nav-item ${isActive('/admin/users') ? 'active' : ''}`}>
                  <span className="nav-icon"><Users size={15} weight={isActive('/admin/users') ? 'fill' : 'regular'} /></span>
                  Users
                </Link>
                <Link href="/admin/flagged" className={`nav-item ${isActive('/admin/flagged') ? 'active' : ''}`}>
                  <span className="nav-icon"><Flag size={15} weight={isActive('/admin/flagged') ? 'fill' : 'regular'} /></span>
                  Flagged Problems
                </Link>
                <Link href="/admin/analytics" className={`nav-item ${isActive('/admin/analytics') ? 'active' : ''}`}>
                  <span className="nav-icon"><ChartBar size={15} weight={isActive('/admin/analytics') ? 'fill' : 'regular'} /></span>
                  Analytics
                </Link>
                <Link href="/admin/quotas" className={`nav-item ${isActive('/admin/quotas') ? 'active' : ''}`}>
                  <span className="nav-icon"><Timer size={15} weight={isActive('/admin/quotas') ? 'fill' : 'regular'} /></span>
                  Quotas
                </Link>
              </>
            )}
          </>
        )}

        {isLoaded && !isSignedIn && (
          <>
            <div className="nav-section-label">Explore</div>
            <Link href="/" className={`nav-item ${pathname === '/' ? 'active' : ''}`}>
              <span className="nav-icon"><House size={15} /></span> Home
            </Link>
            <Link href="/catalog" className={`nav-item ${isActive('/catalog') ? 'active' : ''}`}>
              <span className="nav-icon"><Books size={15} /></span> Course Catalog
            </Link>
          </>
        )}
      </nav>

      {/* Legal links */}
      <div style={{
        padding: '6px 14px',
        display: 'flex', gap: 10, flexWrap: 'wrap',
        borderTop: '1px solid var(--border)',
      }}>
        {[
          { label: 'Terms', href: '/terms' },
          { label: 'Privacy', href: '/privacy' },
          { label: 'DPA', href: '/dpa' },
        ].map(l => (
          <a key={l.href} href={l.href}
            style={{ fontSize: 11, color: 'var(--text-muted)', textDecoration: 'none' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--caramel)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            {l.label}
          </a>
        ))}
      </div>

      {/* User / auth footer */}
      <div style={{
        padding: '10px 14px 14px',
        borderTop: isSignedIn ? 'none' : '1px solid var(--border)',
      }}>
        {isLoaded && isSignedIn ? (
          <div
            role="button"
            tabIndex={0}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 8px', borderRadius: 7, cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onClick={e => {
              const btn = (e.currentTarget as HTMLElement).querySelector('button')
              if (btn && !btn.contains(e.target as Node)) btn.click()
            }}
            onKeyDown={e => {
              if (e.key === 'Enter' || e.key === ' ') {
                const btn = (e.currentTarget as HTMLElement).querySelector('button')
                btn?.click()
              }
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface3)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <UserButton />
            <span style={{
              fontSize: 13, fontWeight: 500, color: 'var(--text-dim)',
              flex: 1, minWidth: 0, overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {user?.fullName ?? user?.firstName ?? 'Student'}
            </span>
          </div>
        ) : isLoaded ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <SignInButton>
              <button className="btn-ghost" style={{ width: '100%', justifyContent: 'center', padding: '8px 16px' }}>
                Sign in
              </button>
            </SignInButton>
            <SignUpButton>
              <button className="btn-caramel" style={{ width: '100%', justifyContent: 'center', padding: '8px 16px' }}>
                Get started
              </button>
            </SignUpButton>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
