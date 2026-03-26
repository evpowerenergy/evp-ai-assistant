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
    <div className="flex h-full min-h-0 max-w-full overflow-hidden border-t-0 border-neutral-200/80 bg-transparent text-foreground dark:border-neutral-800">
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
        <header className="chat-thread-header flex flex-shrink-0 items-center justify-between gap-2 border-b border-neutral-200/90 bg-[#fafafa]/95 px-3 py-2 backdrop-blur-sm dark:border-neutral-800 dark:bg-[#212121]/95">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="shrink-0 rounded-lg p-2 text-neutral-500 hover:bg-neutral-200/80 dark:text-neutral-400 dark:hover:bg-neutral-800/80 lg:hidden"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="truncate text-[15px] font-medium text-neutral-800 dark:text-neutral-100">
              {getHeaderSessionTitle(currentSession)}
            </h1>
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden shrink-0 rounded-lg p-2 text-neutral-500 hover:bg-neutral-200/80 dark:text-neutral-400 dark:hover:bg-neutral-800/80 lg:block"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </header>

        {/* Messages */}
        <div className="chat-messages-scroll flex-1 overflow-y-auto bg-[#fafafa] dark:bg-[#212121]">
          {isLoadingHistory ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <div className="mb-2 flex justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-600 dark:border-neutral-700 dark:border-t-neutral-300"></div>
                </div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">กำลังโหลดประวัติการสนทนา...</p>
              </div>
            </div>
          ) : (
            <>
              <MessageList messages={messages} loading={loading} />
              {error && (
                <div className="mx-auto mt-4 max-w-3xl rounded-xl border border-red-200/80 bg-red-50/90 px-4 py-3 dark:border-red-900/60 dark:bg-red-950/40">
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
