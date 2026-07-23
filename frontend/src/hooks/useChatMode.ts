'use client'

import { useCallback, useEffect, useState } from 'react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/contexts/AuthContext'
import type { ChatMode } from '@/components/chat/ChatModeToggle'

const STORAGE_KEY = 'chat_mode'

function readCachedMode(): ChatMode {
  if (typeof window === 'undefined') return 'crm'
  const cached = localStorage.getItem(STORAGE_KEY)
  return cached === 'kb' ? 'kb' : 'crm'
}

export function useChatMode() {
  const { session } = useAuth()
  const [mode, setModeState] = useState<ChatMode>(readCachedMode)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session?.access_token) {
      setLoading(false)
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        const response = await apiClient.get('/api/v1/chat/mode', {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        const serverMode = response.data?.chat_mode === 'kb' ? 'kb' : 'crm'
        if (!cancelled) {
          setModeState(serverMode)
          localStorage.setItem(STORAGE_KEY, serverMode)
        }
      } catch {
        if (!cancelled) {
          setModeState(readCachedMode())
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [session?.access_token])

  const setMode = useCallback(
    async (next: ChatMode) => {
      setModeState(next)
      localStorage.setItem(STORAGE_KEY, next)

      if (!session?.access_token) return

      try {
        await apiClient.patch(
          '/api/v1/chat/mode',
          { chat_mode: next },
          { headers: { Authorization: `Bearer ${session.access_token}` } }
        )
      } catch (err) {
        console.error('Failed to persist chat mode:', err)
      }
    },
    [session?.access_token]
  )

  // CRM/KB remains an internal LangGraph fallback preference. The only
  // user-facing routing mode is Hermes Auto.
  const modeLabel = 'Hermes Auto'

  return { mode, setMode, modeLabel, loading }
}
