'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'
import { UserProfile } from '@/components/auth/UserProfile'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { useConfig } from '@/hooks/useConfig'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

export default function ChatPage() {
  const { userRole } = useAuth()
  const { config: modelConfig } = useConfig()

  return (
    <div className="liquid-bg flex h-screen flex-col text-foreground">
      <header className="glass-panel-strong glass-shine mx-3 mt-3 flex flex-shrink-0 items-center justify-between gap-3 rounded-2xl px-4 py-3">
        <div className="flex min-w-0 items-center gap-4">
          <h1 className="text-xl font-semibold text-foreground">AI Assistant</h1>
          {(userRole === 'super_admin' || userRole === 'admin' || userRole === 'manager') && (
            <Link
              href="/admin"
              className="shrink-0 text-sm text-muted-foreground hover:text-foreground"
            >
              Admin
            </Link>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <ThemeToggle />
          <span className="rounded-full border border-indigo-300/40 bg-indigo-100/60 px-2.5 py-1 text-xs font-medium text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300" title="Model ที่ใช้สร้างคำตอบ">
            Model: {modelConfig?.openai_model ?? '…'}
          </span>
          <UserProfile />
        </div>
      </header>
      <main className="flex-1 overflow-hidden p-3 pt-2">
        <ChatInterface />
      </main>
    </div>
  )
}
