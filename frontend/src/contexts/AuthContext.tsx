'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import apiClient from '@/lib/api/client'

/** อ่าน role จาก app_metadata / user_metadata (fallback) */
function getRoleFromMetadata(user: User | null | undefined): string | null {
  if (!user) return null
  const appRole = (user as any).app_metadata?.role
  if (appRole != null && String(appRole).trim() !== '') return String(appRole).trim()
  const metaRole = user.user_metadata?.role
  if (metaRole != null && String(metaRole).trim() !== '') return String(metaRole).trim()
  return null
}

/** ดึง role ผ่าน Backend API (service role) แบบเดียวกับ CRM additional-auth-user-data */
async function fetchRoleFromMeAPI(session: Session | null): Promise<string | null> {
  if (!session?.access_token) return null
  try {
    const { data } = await apiClient.get<{ role?: string }>('/api/v1/me', {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
    const role = data?.role != null ? String(data.role).trim() : null
    return role === '' ? null : role
  } catch {
    return null
  }
}

/** ดึง role จากตาราง (frontend Supabase) — fallback เมื่อเรียก /me ไม่ได้ */
async function fetchRoleFromSupabase(
  supabase: ReturnType<typeof createClient>,
  authUserId: string
): Promise<string | null> {
  const tryTable = async (table: string): Promise<string | null> => {
    try {
      const { data, error } = await supabase
        .from(table)
        .select('role')
        .eq('auth_user_id', authUserId)
        .maybeSingle()
      if (error || !data?.role) return null
      const role = String(data.role).trim()
      return role === '' ? null : role
    } catch {
      return null
    }
  }
  const fromUsers = await tryTable('users')
  if (fromUsers) return fromUsers
  return tryTable('employees')
}

/** ลำดับ: เรียก /me (backend service role) ก่อน → fallback Supabase ตาราง → metadata */
async function resolveUserRole(
  supabase: ReturnType<typeof createClient>,
  user: User | null | undefined,
  session: Session | null
): Promise<string | null> {
  if (!user?.id) return null
  const fromApi = await fetchRoleFromMeAPI(session)
  if (fromApi) return fromApi
  const fromTable = await fetchRoleFromSupabase(supabase, user.id)
  if (fromTable) return fromTable
  return getRoleFromMetadata(user)
}

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  userRole: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [userRole, setUserRole] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    const init = async () => {
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession()

      if (error) {
        console.error('Error getting session:', error)
        setSession(null)
        setUser(null)
        setUserRole(null)
        setLoading(false)
        return
      }

      if (session) {
        const expiresAt = session.expires_at || 0
        const now = Math.floor(Date.now() / 1000)
        const timeUntilExpiry = expiresAt - now

        if (timeUntilExpiry < 300) {
          const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()

          if (refreshError) {
            console.error('Error refreshing session:', refreshError)
            setSession(null)
            setUser(null)
            setUserRole(null)
          } else if (refreshData.session) {
            setSession(refreshData.session)
            setUser(refreshData.user)
            const role = await resolveUserRole(supabase, refreshData.user, refreshData.session)
            setUserRole(role)
          }
        } else {
          setSession(session)
          setUser(session.user ?? null)
          const role = await resolveUserRole(supabase, session.user, session)
          setUserRole(role)
        }
      } else {
        setSession(null)
        setUser(null)
        setUserRole(null)
      }

      setLoading(false)
    }

    void init()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session) {
        setSession(session)
        setUser(session.user ?? null)
        const role = await resolveUserRole(supabase, session.user, session)
        setUserRole(role)
      } else {
        setSession(null)
        setUser(null)
        setUserRole(null)
      }
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [router, supabase.auth])

  const signIn = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) throw error

    setSession(data.session)
    setUser(data.user)
    const role = await resolveUserRole(supabase, data.user, data.session)
    setUserRole(role)
    router.push('/chat')
    router.refresh()
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error

    setSession(null)
    setUser(null)
    setUserRole(null)
    router.push('/login')
    router.refresh()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        signIn,
        signOut,
        userRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
