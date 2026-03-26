'use client'

import { MessageBubble } from './MessageBubble'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: string[]
  tool_calls?: any[]
  created_at?: string
}

interface MessageListProps {
  messages: Message[]
  loading: boolean
}

export function MessageList({ messages, loading }: MessageListProps) {
  if (messages.length === 0 && !loading) {
    return (
      <div className="flex h-full min-h-[50vh] items-center justify-center px-4">
        <div className="max-w-md text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700 dark:text-emerald-400">
            EV Power
          </p>
          <h2 className="text-2xl font-semibold tracking-tight text-neutral-800 dark:text-neutral-100">
            เริ่มสนทนากับผู้ช่วย AI
          </h2>
          <p className="mt-2 text-[15px] leading-relaxed text-neutral-500 dark:text-neutral-400">
            ถามข้อมูลธุรกิจ เอกสาร หรือสิ่งที่เกี่ยวกับองค์กร — ผู้ช่วยนี้ใช้งานภายใน EV Power เท่านั้น
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {loading && (
        <div className="flex items-center gap-1.5 text-emerald-600/70 dark:text-emerald-400/70">
          <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-current"></div>
          <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" style={{ animationDelay: '0.2s' }}></div>
          <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" style={{ animationDelay: '0.4s' }}></div>
        </div>
      )}
    </div>
  )
}
