'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/contexts/AuthContext'
import apiClient from '@/lib/api/client'

interface Session {
  id: string
  title: string
  preview?: string
  created_at: string
  updated_at: string
}

const DEFAULT_SESSION_TITLE = 'New Chat'
const TITLE_MAX_LENGTH = 50
const PREVIEW_MAX_LENGTH = 80

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength).trim()}...`
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

function generateSessionTitle(input?: string): string {
  const normalized = normalizeText(input || '')
  if (!normalized) return DEFAULT_SESSION_TITLE
  return truncateText(normalized, TITLE_MAX_LENGTH)
}

function generatePreview(input?: string): string | undefined {
  const normalized = normalizeText(input || '')
  if (!normalized) return undefined
  return truncateText(normalized, PREVIEW_MAX_LENGTH)
}

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSession, setCurrentSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const { user, session } = useAuth()
  const supabase = createClient()

  const setActiveSessionOnBackend = useCallback(
    async (sessionId: string) => {
      if (!session?.access_token) return
      try {
        await apiClient.patch(
          '/api/v1/chat/active-session',
          { session_id: sessionId },
          { headers: { Authorization: `Bearer ${session.access_token}` } }
        )
      } catch (error) {
        console.error('Failed to sync active session:', error)
      }
    },
    [session?.access_token]
  )

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

      const sessionsData = (data || []) as Session[]
      const sessionIds = sessionsData.map((s) => s.id)
      const previewBySessionId: Record<string, string> = {}
      const fallbackPreviewBySessionId: Record<string, string> = {}

      if (sessionIds.length > 0) {
        const { data: messageData, error: messageError } = await supabase
          .from('chat_messages')
          .select('session_id, role, content, created_at')
          .in('session_id', sessionIds)
          .order('created_at', { ascending: false })

        if (messageError) throw messageError

        for (const msg of messageData || []) {
          const messagePreview = generatePreview(msg.content) || ''
          if (!messagePreview) continue

          if (!fallbackPreviewBySessionId[msg.session_id]) {
            fallbackPreviewBySessionId[msg.session_id] = messagePreview
          }

          if (msg.role === 'user' && !previewBySessionId[msg.session_id]) {
            previewBySessionId[msg.session_id] = messagePreview
          }
        }
      }

      const withPreview = sessionsData.map((s) => ({
        ...s,
        preview: previewBySessionId[s.id] || fallbackPreviewBySessionId[s.id] || undefined,
      }))

      setSessions(withPreview)

      let activeId: string | null = null
      if (session?.access_token) {
        try {
          const { data: activeData } = await apiClient.get<{ session_id: string }>(
            '/api/v1/chat/active-session',
            { headers: { Authorization: `Bearer ${session.access_token}` } }
          )
          activeId = activeData?.session_id || null
        } catch {
          activeId = null
        }
      }

      if (activeId) {
        const active = withPreview.find((s) => s.id === activeId)
        if (active) {
          setCurrentSession(active)
          return
        }
      }

      if (withPreview.length > 0) {
        setCurrentSession(withPreview[0])
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setLoading(false)
    }
  }, [user, session?.access_token, supabase])

  useEffect(() => {
    if (user) {
      loadSessions()
    }
  }, [user, loadSessions])

  const createSession = useCallback(
    async (title?: string): Promise<Session> => {
      if (!user) throw new Error('Not authenticated')

      const sessionTitle = generateSessionTitle(title)
      const sessionPreview = generatePreview(title)

      const { data, error } = await supabase
        .from('chat_sessions')
        .insert({
          title: sessionTitle,
          user_id: user.id,
        })
        .select()
        .single()

      if (error) throw error

      const newSession = {
        ...(data as Session),
        preview: sessionPreview,
      }
      setSessions((prev) => [newSession, ...prev])
      setCurrentSession(newSession)
      await setActiveSessionOnBackend(newSession.id)

      return newSession
    },
    [user, supabase, setActiveSessionOnBackend]
  )

  const switchSession = useCallback(
    (sessionId: string) => {
      const s = sessions.find((x) => x.id === sessionId)
      if (s) {
        setCurrentSession(s)
        void setActiveSessionOnBackend(sessionId)
      }
    },
    [sessions, setActiveSessionOnBackend]
  )

  const deleteSession = useCallback(
    async (sessionId: string) => {
      if (!user) return

      try {
        const { error } = await supabase
          .from('chat_sessions')
          .delete()
          .eq('id', sessionId)
          .eq('user_id', user.id)

        if (error) throw error

        setSessions((prev) => {
          const filtered = prev.filter((s) => s.id !== sessionId)
          if (currentSession?.id === sessionId) {
            const next = filtered[0] || null
            setCurrentSession(next)
            if (next) {
              void setActiveSessionOnBackend(next.id)
            }
          }
          return filtered
        })
      } catch (error) {
        console.error('Failed to delete session:', error)
      }
    },
    [user, currentSession, supabase, setActiveSessionOnBackend]
  )

  const renameSession = useCallback(
    async (sessionId: string, nextTitle: string) => {
      if (!user) return

      const normalizedTitle = generateSessionTitle(nextTitle)
      try {
        const { error } = await supabase
          .from('chat_sessions')
          .update({ title: normalizedTitle })
          .eq('id', sessionId)
          .eq('user_id', user.id)

        if (error) throw error

        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: normalizedTitle } : s))
        )

        setCurrentSession((prev) =>
          prev?.id === sessionId ? { ...prev, title: normalizedTitle } : prev
        )
      } catch (error) {
        console.error('Failed to rename session:', error)
      }
    },
    [user, supabase]
  )

  const updateSessionPreview = useCallback((sessionId: string, messageContent: string) => {
    const preview = generatePreview(messageContent)
    const nowIso = new Date().toISOString()

    setSessions((prev) => {
      const updated = prev.map((s) =>
        s.id === sessionId ? { ...s, preview, updated_at: nowIso } : s
      )
      return [...updated].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
    })

    setCurrentSession((prev) =>
      prev?.id === sessionId ? { ...prev, preview, updated_at: nowIso } : prev
    )
  }, [])

  return {
    sessions,
    currentSession,
    loading,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    updateSessionPreview,
    loadSessions,
  }
}
