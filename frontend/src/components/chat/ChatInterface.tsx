'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { SessionSidebar } from './SessionSidebar'
import { ProcessStatusPanel } from './ProcessStatusPanel'
import { useChat } from '@/hooks/useChat'
import { useSession } from '@/hooks/useSession'
import { useConfig } from '@/hooks/useConfig'

function getHeaderSessionTitle(session?: { title?: string; preview?: string } | null): string {
  if (!session) return 'New Chat'
  const normalizedTitle = (session.title || '').trim()
  const isLegacyTitle = /^chat\s/i.test(normalizedTitle) || /^new chat$/i.test(normalizedTitle)
  if (isLegacyTitle && session.preview) {
    return session.preview
  }
  return normalizedTitle || session.preview || 'New Chat'
}

export function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { messages, sendMessage, loadMessages, clearMessages, loading, error, processSteps, runtime, toolResults, debugPrecompute } = useChat()
  const { currentSession, sessions, createSession, switchSession, deleteSession, renameSession, updateSessionPreview } = useSession()
  const { config: modelConfig } = useConfig()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  /** เมื่อส่งข้อความแรก (สร้าง session ใหม่) ไม่โหลดประวัติเพื่อไม่ให้ข้อความหายและ UX กระตุก */
  const sendingFirstMessageRef = useRef(false)

  // Load messages when session changes (ข้ามเมื่อเพิ่งสร้าง session จากกดส่งข้อความแรก)
  useEffect(() => {
    if (!currentSession?.id) {
      clearMessages()
      return
    }
    if (sendingFirstMessageRef.current) {
      return
    }
    setIsLoadingHistory(true)
    loadMessages(currentSession.id).finally(() => {
      setIsLoadingHistory(false)
    })
  }, [currentSession?.id, loadMessages, clearMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (content: string) => {
    try {
      if (!currentSession) {
        sendingFirstMessageRef.current = true
        const newSession = await createSession(content)
        updateSessionPreview(newSession.id, content)
        try {
          await sendMessage(content, newSession.id)
        } finally {
          sendingFirstMessageRef.current = false
        }
      } else {
        updateSessionPreview(currentSession.id, content)
        await sendMessage(content, currentSession.id)
      }
    } catch (err) {
      console.error('Failed to send message:', err)
      sendingFirstMessageRef.current = false
    }
  }

  return (
    <div className="flex h-full min-h-0 max-w-full overflow-hidden rounded-2xl border border-border/60 bg-transparent text-foreground">
      {/* Session Sidebar */}
      <SessionSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        currentSessionId={currentSession?.id}
        onSelectSession={switchSession}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
        onCreateSession={createSession}
      />

      {/* Main Chat Area - min-w-0 ให้ flex ลดขนาดได้ ไม่ดัน panel ออกจอ */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex flex-shrink-0 items-center justify-between gap-2 border-b border-border/70 bg-transparent px-4 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="shrink-0 rounded-md p-2 text-muted-foreground hover:bg-muted lg:hidden"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="truncate text-lg font-semibold text-foreground">
              {getHeaderSessionTitle(currentSession)}
            </h1>
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden shrink-0 rounded-md p-2 text-muted-foreground hover:bg-muted lg:block"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {isLoadingHistory ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <div className="mb-2 flex justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"></div>
                </div>
                <p className="text-sm text-muted-foreground">กำลังโหลดประวัติการสนทนา...</p>
              </div>
            </div>
          ) : (
            <>
              <MessageList messages={messages} loading={loading} />
              {error && (
                <div className="mx-4 mt-4 rounded-md bg-red-50/85 p-4 dark:bg-red-950/50">
                  <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <MessageInput onSend={handleSendMessage} disabled={loading} />
      </div>

      {/* Process Status Panel - Right Column */}
      <ProcessStatusPanel
        loading={loading}
        processSteps={processSteps}
        runtime={runtime}
        toolResults={toolResults}
        debugPrecompute={debugPrecompute}
        loadingHistory={isLoadingHistory}
        modelConfig={modelConfig}
      />
    </div>
  )
}
