'use client'

import { CitationBadge } from './CitationBadge'
import { FeedbackButtons } from './FeedbackButtons'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: string[]
  tool_calls?: any[]
  created_at?: string
}

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[min(100%,42rem)] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${
          isUser
            ? 'border border-emerald-200/80 bg-emerald-50 text-neutral-900 shadow-sm dark:border-emerald-800/50 dark:bg-emerald-950/35 dark:text-emerald-50'
            : 'border-l-2 border-emerald-600/45 bg-transparent pl-4 text-neutral-800 dark:border-emerald-500/35 dark:text-neutral-100'
        }`}
        style={{ 
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
          wordBreak: 'break-word'
        }}
      >
        <div 
          className="whitespace-pre-wrap break-words"
          style={{
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
            wordBreak: 'break-word',
            maxWidth: '100%'
          }}
        >
          {message.content}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.citations.map((citation, index) => (
              <CitationBadge key={index} citation={citation} />
            ))}
          </div>
        )}

        {/* Tool Calls (for debugging) */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 text-xs opacity-75">
            Used {message.tool_calls.length} tool(s)
          </div>
        )}

        {/* Feedback Buttons */}
        {!isUser && (
          <div className="mt-3">
            <FeedbackButtons messageId={message.id} />
          </div>
        )}
      </div>
    </div>
  )
}
