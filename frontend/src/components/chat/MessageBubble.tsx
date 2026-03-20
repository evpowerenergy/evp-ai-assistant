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
        className={`max-w-3xl rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'glass-panel border-white/30 text-foreground'
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
