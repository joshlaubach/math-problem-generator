import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/catalog(.*)',
  '/pricing(.*)',
  '/test-math(.*)',
  '/terms(.*)',
  '/privacy(.*)',
  '/dpa(.*)',
  '/tutor/wbtest(.*)',    // dev harness — remove before shipping
])

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) await auth.protect()
})

export const config = {
  matcher: [
    // tutor/wbtest is a dev-only harness; skip Clerk entirely so it loads without login
    '/((?!_next|tutor/wbtest|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
