'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'
import { UserProfile } from '@/components/auth/UserProfile'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { useConfig } from '@/hooks/useConfig'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { BrandLogo } from '@/components/ui/BrandLogo'

export default function ChatPage() {
  const { userRole } = useAuth()
  const { config: modelConfig } = useConfig()

  return (
    <div className="liquid-bg flex h-screen flex-col text-foreground">
      <header className="glass-panel-strong glass-shine mx-3 mt-3 flex flex-shrink-0 items-center justify-between gap-3 rounded-2xl px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <BrandLogo size="sm" />
          {(userRole === 'super_admin' || userRole === 'admin' || userRole === 'manager') && (
            <Link
              href="/admin"
              className="shrink-0 rounded-full border border-border/70 bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
            >
              Admin
            </Link>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <span className="hidden rounded-full border border-indigo-300/40 bg-indigo-100/60 px-2.5 py-1 text-xs font-medium text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 lg:inline-flex" title="Model ที่ใช้สร้างคำตอบ">
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
