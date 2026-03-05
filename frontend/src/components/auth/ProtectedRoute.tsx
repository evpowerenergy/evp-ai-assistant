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
  const hasRole =
    allowedRoles.length === 0 ||
    !userRoleLower ||
    allowedRoles.includes(userRoleLower)

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push('/login')
        return
      }

      if (requiredRole && userRole && !allowedRoles.includes(userRoleLower)) {
        router.push('/chat')
        return
      }
    }
  }, [user, loading, userRole, requiredRole, router, userRoleLower, allowedRoles])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (requiredRole && userRole && !hasRole) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
          <p className="mt-2 text-gray-600">You don't have permission to access this page.</p>
          <p className="mt-2 text-sm text-gray-500">Your role: &quot;{userRole}&quot; — required: {requiredRole.join(', ')}</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
