'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { House, Books, PencilSimple } from '@phosphor-icons/react'
import { useUser, UserButton } from '@clerk/nextjs'

export function BottomNav() {
  const pathname = usePathname()
  const { isSignedIn, isLoaded } = useUser()

  if (!isLoaded || !isSignedIn) return null

  const items = [
    { href: '/dashboard',  activePrefix: '/dashboard',  icon: House,          label: 'Home'     },
    { href: '/catalog',    activePrefix: '/catalog',    icon: Books,          label: 'Catalog'  },
    { href: '/catalog',    activePrefix: '/practice',   icon: PencilSimple,   label: 'Practice' },
  ]

  function isActive(prefix: string) {
    if (prefix === '/dashboard') return pathname === '/dashboard' || pathname === '/'
    return pathname.startsWith(prefix)
  }

  return (
    <nav className="bottom-nav">
      {items.map(({ href, activePrefix, icon: Icon, label }) => {
        const active = isActive(activePrefix)
        return (
          <Link key={label} href={href} className={`bottom-nav-item ${active ? 'active' : ''}`}>
            <Icon size={22} weight={active ? 'fill' : 'regular'} />
            {label}
          </Link>
        )
      })}
      <div className="bottom-nav-item">
        <UserButton />
        <span style={{ fontSize: 10 }}>Profile</span>
      </div>
    </nav>
  )
}
