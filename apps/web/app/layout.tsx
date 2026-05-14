import type { Metadata } from 'next'
import { STIX_Two_Text, DM_Sans } from 'next/font/google'
import { ClerkProvider } from '@clerk/nextjs'
import { Sidebar } from '@/components/Sidebar'
import { BottomNav } from '@/components/BottomNav'
import { MathBackground } from '@/components/MathBackground'
import './globals.css'

// Content layer — TeX's Computer Modern equivalent (headings, course names, lesson text)
const stixTwo = STIX_Two_Text({
  subsets: ['latin'],
  variable: '--font-fraunces',
  display: 'swap',
  weight: ['400', '500', '600', '700'],
  style: ['normal', 'italic'],
})

// UI layer — clean geometric sans (nav, metadata, badges, buttons, inputs)
const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-instrument',
  display: 'swap',
  axes: ['opsz'],
})

export const metadata: Metadata = {
  title: 'Gradient — Adaptive Math Learning',
  description: 'Master mathematics from Pre-Algebra through graduate theory with adaptive problem generation.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      {/* Prevent theme flash — reads localStorage before React hydrates */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.setAttribute('data-theme','dark')}}catch(e){}})()`,
          }}
        />
      </head>
      <body className={`${stixTwo.variable} ${dmSans.variable} font-body antialiased`}>
        <ClerkProvider>
          {/* Fixed decorative background — blobs + floating symbols */}
          <MathBackground />

          {/* App shell: sidebar + main content */}
          <div className="app-shell">
            <Sidebar />
            <main className="app-main">
              {children}
            </main>
          </div>
          <BottomNav />
        </ClerkProvider>
      </body>
    </html>
  )
}
