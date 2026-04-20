'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: string[]
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { user, loading, userRole } = useAuth()
  const router = useRouter()

  const allowedRoles = requiredRole?.map((r) => r.toLowerCase()) ?? []
  const userRoleLower = (userRole ?? '').toLowerCase().trim()
  const requiresRoleCheck = (requiredRole?.length ?? 0) > 0
  /** Strict: empty role or role not in list => no access */
  const hasRole =
    !requiresRoleCheck || (userRoleLower !== '' && allowedRoles.includes(userRoleLower))

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (requiresRoleCheck && !hasRole) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
          <p className="mt-2 text-muted-foreground">
            Your account does not have permission to use the AI Assistant.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Your role: &quot;{userRole ?? '—'}&quot; — required: {requiredRole?.join(', ')}
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
