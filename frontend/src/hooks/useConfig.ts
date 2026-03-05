'use client'

import { useState, useEffect, useCallback } from 'react'
import apiClient from '@/lib/api/client'

export interface AgentInfo {
  name: string
  role: string
  model: string
}

export interface ConfigInfo {
  openai_model: string
  agents: AgentInfo[]
  agents_count: number
}

/** ดึง config (model, agents) — ไม่ต้อง login เพราะ GET /config ไม่ต้อง auth */
export function useConfig() {
  const [config, setConfig] = useState<ConfigInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConfig = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get<ConfigInfo>('/api/v1/config')
      setConfig(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load config')
      setConfig(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  return { config, loading, error, refetch: fetchConfig }
}
