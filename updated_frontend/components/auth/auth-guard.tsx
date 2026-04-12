'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { getAccessToken } from '@/lib/api-client'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    if (!isAuthenticated && !getAccessToken()) {
      router.replace('/login')
    }
  }, [isAuthenticated, router])

  if (!mounted) return null
  if (!isAuthenticated && !getAccessToken()) return null
  return <>{children}</>
}
