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
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-foreground">เริ่มสนทนา</h2>
          <p className="mt-2 text-muted-foreground">ถามอะไรก็ได้เกี่ยวกับข้อมูล business หรือเอกสาร</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/70"></div>
          <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/70" style={{ animationDelay: '0.2s' }}></div>
          <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/70" style={{ animationDelay: '0.4s' }}></div>
        </div>
      )}
    </div>
  )
}
