'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function Home() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
      if (user) {
        router.push('/chat')
      } else {
        router.push('/login')
      }
    }
  }, [user, loading, router])

  return (
    <main className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </div>
    </main>
  )
}
