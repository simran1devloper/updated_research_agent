'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { setTokens } from '@/lib/api-client'
import { Loader } from 'lucide-react'

/**
 * Landing page for OAuth redirects.
 * Auth service redirects here after OAuth callback with:
 *   /auth/callback?access_token=...&refresh_token=...
 * We store the tokens and redirect to the main app.
 */
export default function AuthCallbackPage() {
  const router = useRouter()
  const { setUser } = useAuthStore()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token')

    if (!accessToken || !refreshToken) {
      router.replace('/login?error=oauth_failed')
      return
    }

    try {
      setTokens(accessToken, refreshToken)
      const payload = JSON.parse(atob(accessToken.split('.')[1]))
      setUser({
        id: payload.sub,
        email: payload.email,
        username: payload.username ?? payload.email.split('@')[0],
        role: payload.role,
        is_active: true,
      })
      router.replace('/')
    } catch {
      router.replace('/login?error=oauth_failed')
    }
  }, [router, setUser])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader size={24} className="animate-spin" />
        <p className="text-sm">Completing sign-in…</p>
      </div>
    </div>
  )
}
