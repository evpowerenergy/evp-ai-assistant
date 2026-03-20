'use client'

import { useEffect, useRef, useState } from 'react'

interface Session {
  id: string
  title: string
  preview?: string
  created_at: string
  updated_at: string
}

interface SessionSidebarProps {
  open: boolean
  onClose: () => void
  sessions: Session[]
  currentSessionId?: string
  onSelectSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onRenameSession: (sessionId: string, title: string) => Promise<void> | void
  onCreateSession: (title?: string) => Promise<Session>
}

function getDisplayTitle(session: Session): string {
  const normalizedTitle = (session.title || '').trim()
  const isLegacyTitle = /^chat\s/i.test(normalizedTitle) || /^new chat$/i.test(normalizedTitle)
  if (isLegacyTitle && session.preview) {
    return session.preview
  }
  return normalizedTitle || session.preview || 'Untitled Chat'
}

function formatSessionDate(session: Session): string {
  const date = new Date(session.updated_at || session.created_at)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('th-TH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function SessionSidebar({
  open,
  onClose,
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onCreateSession,
}: SessionSidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null)
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, onClose])

  const handleNewChat = async () => {
    await onCreateSession()
    onClose()
  }

  const startRenaming = (session: Session) => {
    setEditingSessionId(session.id)
    setEditingTitle(getDisplayTitle(session))
  }

  const cancelRenaming = () => {
    setEditingSessionId(null)
    setEditingTitle('')
  }

  const saveRename = async (sessionId: string) => {
    await onRenameSession(sessionId, editingTitle)
    cancelRenaming()
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={onClose} />
      )}

      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={`glass-panel-strong fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-lg font-semibold text-foreground">Chat Sessions</h2>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-muted-foreground hover:bg-muted lg:hidden"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* New Chat Button */}
          <div className="border-b border-border px-4 py-3">
            <button
              onClick={handleNewChat}
              className="w-full rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-indigo-500/30 transition-all hover:-translate-y-0.5 hover:bg-indigo-700"
            >
              + New Chat
            </button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No chat sessions yet
              </div>
            ) : (
              <div className="space-y-1 p-2">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group flex items-start justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                      currentSessionId === session.id
                        ? 'bg-indigo-100/70 text-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-300'
                        : 'text-muted-foreground hover:bg-white/40 hover:text-foreground dark:hover:bg-white/10'
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      {editingSessionId === session.id ? (
                        <input
                          autoFocus
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onBlur={() => saveRename(session.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              void saveRename(session.id)
                            }
                            if (e.key === 'Escape') {
                              cancelRenaming()
                            }
                          }}
                          className="w-full rounded border border-indigo-300 bg-input px-2 py-1 text-sm text-foreground outline-none ring-2 ring-indigo-200"
                        />
                      ) : (
                        <button
                          onClick={() => {
                            onSelectSession(session.id)
                            onClose()
                          }}
                          className="w-full text-left"
                        >
                          <p className="truncate font-medium">{getDisplayTitle(session)}</p>
                          <p className="mt-0.5 truncate text-xs text-muted-foreground">{formatSessionDate(session)}</p>
                        </button>
                      )}
                    </div>
                    <div className="ml-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        onClick={() => startRenaming(session)}
                        className="rounded-md p-1 hover:bg-muted"
                        aria-label="Rename session"
                      >
                        <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5h2m-1-1v2m-7 9l8.586-8.586a2 2 0 112.828 2.828L7.828 17.828A4 4 0 015 19H3v-2a4 4 0 011.172-2.828z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => onDeleteSession(session.id)}
                        className="rounded-md p-1 hover:bg-red-100"
                        aria-label="Delete session"
                      >
                        <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
