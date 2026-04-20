'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'
import { UserProfile } from '@/components/auth/UserProfile'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { hasAiAssistantAccess } from '@/lib/aiAssistantAccess'
import { useConfig } from '@/hooks/useConfig'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { BrandLogo } from '@/components/ui/BrandLogo'

export default function ChatPage() {
  const { userRole } = useAuth()
  const { config: modelConfig } = useConfig()

  return (
    <div className="chat-app-shell flex h-screen flex-col bg-[#fafafa] text-foreground dark:bg-[#212121]">
      <header className="chat-app-header flex flex-shrink-0 items-center justify-between gap-3 border-b border-neutral-200/90 px-4 py-2.5 dark:border-neutral-800">
        <div className="flex min-w-0 items-center gap-3">
          <BrandLogo size="sm" />
          {hasAiAssistantAccess(userRole) && (
            <Link
              href="/admin"
              className="shrink-0 rounded-lg border border-neutral-200 bg-white px-2.5 py-1 text-xs text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900/80 dark:text-neutral-300 dark:hover:bg-neutral-800 dark:hover:text-neutral-100"
            >
              Admin
            </Link>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <span
            className="hidden max-w-[220px] truncate rounded-md border border-neutral-200 bg-neutral-50 px-2.5 py-1 font-mono text-[11px] text-neutral-600 dark:border-neutral-700 dark:bg-neutral-900/90 dark:text-neutral-400 lg:inline-flex"
            title="Model ที่ใช้สร้างคำตอบ"
          >
            {modelConfig?.openai_model ?? '…'}
          </span>
          <UserProfile />
        </div>
      </header>
      <main className="min-h-0 flex-1 overflow-hidden px-0 pb-0 pt-0 sm:px-1">
        <ChatInterface />
      </main>
    </div>
  )
}
