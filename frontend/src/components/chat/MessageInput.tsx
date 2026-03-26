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
    <div className="border-t border-neutral-200/90 bg-[#fafafa] px-3 py-3 dark:border-neutral-800 dark:bg-[#212121] sm:px-4 sm:pb-4">
      <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="relative flex min-h-[52px] flex-1 items-end rounded-[26px] border border-neutral-300 bg-white shadow-sm ring-emerald-500/0 transition-shadow focus-within:border-emerald-300 focus-within:ring-2 focus-within:ring-emerald-500/15 dark:border-neutral-600 dark:bg-[#2f2f2f] dark:focus-within:border-emerald-700/80 dark:focus-within:ring-emerald-400/10">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="พิมพ์คำถามถึง EV Power AI…"
            className="max-h-[200px] min-h-[48px] w-full resize-none rounded-[26px] border-0 bg-transparent px-4 py-3 pr-2 text-[15px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-60 dark:text-neutral-100 dark:placeholder:text-neutral-500"
            rows={1}
            style={{
              overflowY: 'auto',
              wordWrap: 'break-word',
              overflowWrap: 'break-word',
            }}
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white shadow-sm shadow-emerald-900/10 transition-colors hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:ring-offset-2 focus:ring-offset-[#fafafa] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-emerald-600 dark:hover:bg-emerald-500 dark:focus:ring-emerald-400/30 dark:focus:ring-offset-[#212121]"
          aria-label="Send message"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </form>
      <p className="mx-auto mt-2 max-w-3xl px-1 text-center text-[11px] text-neutral-400 dark:text-neutral-500">
        <span className="text-emerald-700/90 dark:text-emerald-500/90">EV Power</span>
        {' · '}
        Enter เพื่อส่ง · Shift+Enter ขึ้นบรรทัดใหม่
      </p>
    </div>
  )
}
