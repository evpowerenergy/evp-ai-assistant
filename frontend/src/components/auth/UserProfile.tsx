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
    <div className="flex items-center gap-4">
      <div className="text-right">
        <p className="text-sm font-medium text-foreground">
          {user.email}
        </p>
        <p className="text-xs text-muted-foreground capitalize">
          {userRole || 'staff'}
        </p>
      </div>
      <button
        onClick={handleSignOut}
        className="rounded-md bg-muted px-3 py-2 text-sm font-medium text-foreground hover:opacity-90"
      >
        Sign Out
      </button>
    </div>
  )
}
