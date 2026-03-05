'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'
import { UserProfile } from '@/components/auth/UserProfile'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { useConfig } from '@/hooks/useConfig'

export default function ChatPage() {
  const { userRole } = useAuth()
  const { config: modelConfig } = useConfig()

  return (
    <div className="flex h-screen flex-col">
      <header className="flex flex-shrink-0 items-center justify-between gap-3 border-b bg-white px-4 py-3">
        <div className="flex min-w-0 items-center gap-4">
          <h1 className="text-xl font-semibold text-gray-900">AI Assistant</h1>
          {(userRole === 'super_admin' || userRole === 'admin' || userRole === 'manager') && (
            <Link
              href="/admin"
              className="shrink-0 text-sm text-gray-600 hover:text-gray-900"
            >
              Admin
            </Link>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span className="rounded bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700" title="Model ที่ใช้สร้างคำตอบ">
            Model: {modelConfig?.openai_model ?? '…'}
          </span>
          <UserProfile />
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  )
}
