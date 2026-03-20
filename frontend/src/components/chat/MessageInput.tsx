'use client'

import { useState, FormEvent, KeyboardEvent } from 'react'

interface MessageInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (message.trim() && !disabled) {
        onSend(message.trim())
        setMessage('')
      }
    }
  }

  return (
    <div className="border-t border-border/70 bg-transparent px-4 py-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
          className="glass-panel flex-1 resize-none rounded-2xl border border-white/30 px-4 py-2 text-foreground placeholder:text-muted-foreground focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-70"
          rows={1}
          style={{ 
            minHeight: '44px', 
            maxHeight: '200px',
            overflowY: 'auto',
            wordWrap: 'break-word',
            overflowWrap: 'break-word'
          }}
        />
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="rounded-2xl bg-indigo-600 px-6 py-2 text-white shadow-sm shadow-indigo-500/35 transition-all hover:-translate-y-0.5 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
