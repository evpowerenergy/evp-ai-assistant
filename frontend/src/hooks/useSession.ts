'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/contexts/AuthContext'

interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSession, setCurrentSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()
  const supabase = createClient()

  const loadSessions = useCallback(async () => {
    if (!user) return

    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('chat_sessions')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })
        .limit(50)

      if (error) throw error

      setSessions(data || [])
      if (data && data.length > 0 && !currentSession) {
        setCurrentSession(data[0])
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setLoading(false)
    }
  }, [user, currentSession])

  useEffect(() => {
    if (user) {
      loadSessions()
    }
  }, [user, loadSessions])

  const createSession = useCallback(
    async (title?: string): Promise<Session> => {
      if (!user) throw new Error('Not authenticated')

      const sessionTitle = title || `Chat ${new Date().toLocaleString('th-TH')}`

      const { data, error } = await supabase
        .from('chat_sessions')
        .insert({
          title: sessionTitle.substring(0, 50),
          user_id: user.id,
        })
        .select()
        .single()

      if (error) throw error

      const newSession = data as Session
      setSessions((prev) => [newSession, ...prev])
      setCurrentSession(newSession)

      return newSession
    },
    [user]
  )

  const switchSession = useCallback((sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId)
    if (session) {
      setCurrentSession(session)
    }
  }, [sessions])

  const deleteSession = useCallback(
    async (sessionId: string) => {
      if (!user) return

      try {
        const { error } = await supabase.from('chat_sessions').delete().eq('id', sessionId).eq('user_id', user.id)

        if (error) throw error

        setSessions((prev) => {
          const filtered = prev.filter((s) => s.id !== sessionId)
          if (currentSession?.id === sessionId) {
            setCurrentSession(filtered[0] || null)
          }
          return filtered
        })
      } catch (error) {
        console.error('Failed to delete session:', error)
      }
    },
    [user, currentSession]
  )

  return {
    sessions,
    currentSession,
    loading,
    createSession,
    switchSession,
    deleteSession,
    loadSessions,
  }
}
