'use client'

import { useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn, user } = useUser()
  const router = useRouter()

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn || (user?.publicMetadata as { role?: string })?.role !== 'admin') {
      router.replace('/')
    }
  }, [isLoaded, isSignedIn, user, router])

  if (!isLoaded) return null
  if (!isSignedIn || (user?.publicMetadata as { role?: string })?.role !== 'admin') return null

  return <>{children}</>
}
