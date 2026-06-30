'use client'

import { useState, useEffect, useCallback } from 'react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/contexts/AuthContext'

export interface LineStatus {
  linked: boolean
  line_user_id?: string
  linked_at?: string
}

export interface LinkCodeResponse {
  success: boolean
  code: string
  expires_at: string
  instruction: string
}

export function useLineLink() {
  const { session, loading: authLoading } = useAuth()
  const [status, setStatus] = useState<LineStatus | null>(null)
  const [linkCode, setLinkCode] = useState<LinkCodeResponse | null>(null)
  const [countdown, setCountdown] = useState(0)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const authHeaders = useCallback(() => {
    if (!session?.access_token) return {}
    return { Authorization: `Bearer ${session.access_token}` }
  }, [session?.access_token])

  const loadStatus = useCallback(async () => {
    if (!session?.access_token) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get<LineStatus & { success: boolean }>(
        '/api/v1/line/status',
        { headers: authHeaders() }
      )
      setStatus({ linked: data.linked, line_user_id: data.line_user_id, linked_at: data.linked_at })
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string }
      const message =
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : 'โหลดสถานะ LINE ไม่สำเร็จ')
      setError(String(message))
      setStatus({ linked: false })
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, authHeaders])

  useEffect(() => {
    if (authLoading) return
    void loadStatus()
  }, [authLoading, loadStatus])

  useEffect(() => {
    if (!linkCode?.expires_at) {
      setCountdown(0)
      return
    }
    const tick = () => {
      const remaining = Math.max(
        0,
        Math.floor((new Date(linkCode.expires_at).getTime() - Date.now()) / 1000)
      )
      setCountdown(remaining)
      if (remaining === 0) {
        setLinkCode(null)
      }
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [linkCode])

  const generateCode = useCallback(async () => {
    if (!session?.access_token) {
      setError('กรุณา login ก่อน')
      return
    }
    setActionLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.post<LinkCodeResponse>(
        '/api/v1/line/link-code',
        {},
        { headers: authHeaders() }
      )
      setLinkCode(data)
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string }
      const message =
        ax.response?.data?.detail ||
        (err instanceof Error ? err.message : 'สร้างรหัสไม่สำเร็จ')
      setError(String(message))
    } finally {
      setActionLoading(false)
    }
  }, [session?.access_token, authHeaders])

  const unlink = useCallback(async () => {
    if (!session?.access_token) return false
    setActionLoading(true)
    setError(null)
    try {
      await apiClient.delete('/api/v1/line/unlink', { headers: authHeaders() })
      setLinkCode(null)
      await loadStatus()
      return true
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'ยกเลิกการเชื่อมต่อไม่สำเร็จ'
      setError(message)
      return false
    } finally {
      setActionLoading(false)
    }
  }, [session?.access_token, authHeaders, loadStatus])

  const linkCommand = linkCode ? `LINK ${linkCode.code}` : null

  return {
    status,
    linkCode,
    linkCommand,
    countdown,
    loading: loading || authLoading,
    actionLoading,
    error,
    generateCode,
    unlink,
    reload: loadStatus,
  }
}
