'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'

export function UserProfile() {
  const { user, userRole, signOut } = useAuth()
  const router = useRouter()

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error('Sign out error:', error)
    }
  }

  if (!user) return null

  return (
    <div className="flex items-center gap-2 rounded-xl border border-border/70 bg-muted/40 px-2 py-1.5">
      <div className="min-w-0 text-right">
        <p className="max-w-[180px] truncate text-sm font-medium text-foreground md:max-w-[240px]">
          {user.email}
        </p>
        <p className="hidden text-xs capitalize text-muted-foreground sm:block">
          {userRole || 'staff'}
        </p>
      </div>
      <button
        onClick={handleSignOut}
        className="rounded-lg bg-muted px-2.5 py-1.5 text-xs font-medium text-foreground transition hover:opacity-90"
      >
        Logout
      </button>
    </div>
  )
}
