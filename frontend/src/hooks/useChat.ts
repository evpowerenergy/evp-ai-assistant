'use client'

import { useState, useCallback } from 'react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/contexts/AuthContext'
import type { ChatMode } from '@/components/chat/ChatModeToggle'

// Simple logger for frontend
const logger = {
  info: (message: string) => console.log(`[useChat] ${message}`),
  error: (message: string) => console.error(`[useChat] ${message}`),
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: string[]
  tool_calls?: any[]
  created_at?: string
}

interface ProcessStep {
  name: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  duration?: number
  preview?: string
  data?: any
}

export interface AgentRuntimeInfo {
  engine: string
  model?: string
  fallbackUsed: boolean
  requestId?: string
  logs?: RuntimeLogEvent[]
}

export interface RuntimeLogEvent {
  timestamp?: string
  type: 'tool' | 'skill' | 'summary'
  name: string
  status: 'completed' | 'error'
  duration?: number | null
  model?: string
  api_calls?: string
  tool_turns?: number
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([])
  const [runtime, setRuntime] = useState<number | undefined>(undefined)
  const [toolResults, setToolResults] = useState<any[]>([])
  const [debugPrecompute, setDebugPrecompute] = useState<Record<string, any> | null>(null)
  const [agentRuntime, setAgentRuntime] = useState<AgentRuntimeInfo | null>(null)
  const [useStreaming, setUseStreaming] = useState(true)  // Enable streaming by default
  const { session } = useAuth()

  const sendMessage = useCallback(
    async (content: string, sessionId: string, chatMode: ChatMode = 'crm') => {
      if (!session) {
        setError('Not authenticated')
        return
      }

      setLoading(true)
      setError(null)
      
      // Reset process steps
      setProcessSteps([])
      setRuntime(undefined)
      setToolResults([])
      setDebugPrecompute(null)
      setAgentRuntime({ engine: 'hermes', model: 'gpt-5.6-luna', fallbackUsed: false, logs: [] })

      // Add user message immediately (only if not already in history)
      // Check if this message is already in the messages list (from history)
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      }
      
      // Only add if not duplicate (avoid adding same message twice)
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1]
        if (lastMessage?.role === 'user' && lastMessage?.content === content) {
          // Message already exists, don't add duplicate
          return prev
        }
        return [...prev, userMessage]
      })

      try {
        // Validate session before making request
        if (!session?.access_token) {
          throw new Error('No access token available')
        }

        // Check if token is expired
        const expiresAt = session.expires_at
        if (expiresAt) {
          const now = Math.floor(Date.now() / 1000)
          if (now >= expiresAt) {
            throw new Error('Session expired. Please refresh the page and login again.')
          }
        }

        // Use streaming if enabled
        if (useStreaming) {
          await sendMessageStream(content, sessionId, session.access_token, chatMode)
        } else {
          // Fallback to non-streaming
          const response = await apiClient.post(
            '/api/v1/chat',
            {
              message: content,
              session_id: sessionId,
              chat_mode: chatMode,
            },
            {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            }
          )

          const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.data.response || 'No response',
            citations: response.data.citations,
            tool_calls: response.data.tool_calls,
            created_at: new Date().toISOString(),
          }

          setMessages((prev) => [...prev, assistantMessage])
          
          // Update process status
          if (response.data.process_steps) {
            setProcessSteps(response.data.process_steps)
          }
          if (response.data.runtime !== undefined) {
            setRuntime(response.data.runtime)
          }
          // Use tool_results if available, otherwise fallback to tool_calls
          if (response.data.tool_results) {
            setToolResults(response.data.tool_results)
          } else if (response.data.tool_calls) {
            setToolResults(response.data.tool_calls)
          }
          if (response.data.debug_precompute) {
            setDebugPrecompute(response.data.debug_precompute)
          }
          setAgentRuntime({
            engine: response.data.engine || 'unknown',
            model: response.data.model,
            fallbackUsed: Boolean(response.data.fallback_used),
            requestId: response.data.request_id,
            logs: response.data.runtime_logs || [],
          })
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to send message')
        console.error('Chat error:', err)
      } finally {
        setLoading(false)
      }
    },
    [session, useStreaming]
  )

  const sendMessageStream = async (
    content: string,
    sessionId: string,
    token: string,
    chatMode: ChatMode = 'crm'
  ) => {
    const baseURL = apiClient.defaults.baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${baseURL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: content,
        session_id: sessionId,
        chat_mode: chatMode,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    if (!reader) {
      throw new Error('No response body')
    }

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'runtime.log' && data.event) {
              const event = data.event as RuntimeLogEvent
              setAgentRuntime((previous) => {
                const current = previous || {
                  engine: 'hermes',
                  model: 'gpt-5.6-luna',
                  fallbackUsed: false,
                  logs: [],
                }
                const logs = current.logs || []
                const key = `${event.timestamp || ''}:${event.type}:${event.name}`
                const exists = logs.some(
                  (item) => `${item.timestamp || ''}:${item.type}:${item.name}` === key
                )
                return exists ? current : { ...current, logs: [...logs, event] }
              })
            } else if (data.type === 'final') {
              // Final response
              const assistantMessage: Message = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: data.response || 'No response',
                citations: data.citations,
                tool_calls: data.tool_calls,
                created_at: new Date().toISOString(),
              }
              // Only add if not duplicate
              setMessages((prev) => {
                const lastMessage = prev[prev.length - 1]
                if (lastMessage?.role === 'assistant' && lastMessage?.content === assistantMessage.content) {
                  // Message already exists, update it instead
                  return prev.map((msg, idx) => 
                    idx === prev.length - 1 ? assistantMessage : msg
                  )
                }
                return [...prev, assistantMessage]
              })
              
              if (data.runtime !== undefined) {
                setRuntime(data.runtime)
              }
              // Use tool_results if available, otherwise fallback to tool_calls
              if (data.tool_results) {
                setToolResults(data.tool_results)
              } else if (data.tool_calls) {
                setToolResults(data.tool_calls)
              }
              if (data.debug_precompute) {
                setDebugPrecompute(data.debug_precompute)
              }
              setAgentRuntime((previous) => {
                const mergedLogs = [...(previous?.logs || []), ...(data.runtime_logs || [])]
                  .filter((event, index, items) => {
                    const key = `${event.timestamp || ''}:${event.type}:${event.name}`
                    return items.findIndex(
                      (item) => `${item.timestamp || ''}:${item.type}:${item.name}` === key
                    ) === index
                  })
                return {
                  engine: data.engine || 'unknown',
                  model: data.model,
                  fallbackUsed: Boolean(data.fallback_used),
                  requestId: data.request_id,
                  logs: mergedLogs,
                }
              })
            } else if (data.type === 'error') {
              setError(data.error || 'Unknown error')
            } else {
              // Process step update
              const step: ProcessStep & { display_name?: string } = {
                name: data.node,
                status: data.status === 'completed' ? 'completed' : data.status === 'processing' ? 'processing' : 'pending',
                duration: data.elapsed_time,
                preview: data.preview,
                data: data.tool_results ? { tool_results: data.tool_results } : undefined,
                display_name: data.display_name,
              }
              
              setProcessSteps((prev) => {
                // Update existing step or add new one
                const existingIndex = prev.findIndex((s) => s.name === step.name)
                if (existingIndex >= 0) {
                  const updated = [...prev]
                  updated[existingIndex] = step
                  return updated
                }
                return [...prev, step]
              })
              
              // Update tool results if available
              if (data.tool_results) {
                setToolResults(data.tool_results)
              }
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, line)
          }
        }
      }
    }
  }

  const loadMessages = useCallback(async (sessionId: string) => {
    if (!session || !sessionId) {
      setMessages([])
      return
    }

    setError(null)

    try {
      // Validate session before making request
      if (!session?.access_token) {
        throw new Error('No access token available')
      }

      // Check if token is expired
      const expiresAt = session.expires_at
      if (expiresAt) {
        const now = Math.floor(Date.now() / 1000)
        if (now >= expiresAt) {
          throw new Error('Session expired. Please refresh the page and login again.')
        }
      }

      const response = await apiClient.get(
        `/api/v1/chat/history/${sessionId}`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      )

      if (response.data.success && response.data.messages) {
        // Format messages for display
        const formattedMessages: Message[] = response.data.messages.map((msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          citations: msg.citations,
          tool_calls: msg.tool_calls,
          created_at: msg.created_at,
        }))

        setMessages(formattedMessages)
        logger.info(`Loaded ${formattedMessages.length} messages from history`)
      } else {
        setMessages([])
      }
    } catch (err: any) {
      console.error('Failed to load messages:', err)
      // Don't show error for empty sessions, just set empty messages
      if (err.response?.status === 404 || err.response?.status === 400) {
        setMessages([])
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load messages')
        setMessages([])
      }
    }
  }, [session])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    setProcessSteps([])
    setRuntime(undefined)
    setToolResults([])
    setDebugPrecompute(null)
    setAgentRuntime(null)
  }, [])

  return {
    messages,
    sendMessage,
    loadMessages,
    clearMessages,
    loading,
    error,
    processSteps,
    runtime,
    toolResults,
    debugPrecompute,
    agentRuntime,
  }
}
