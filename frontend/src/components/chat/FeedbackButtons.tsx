'use client'

import { useState } from 'react'

interface FeedbackButtonsProps {
  messageId: string
}

export function FeedbackButtons({ messageId }: FeedbackButtonsProps) {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null)

  const handleFeedback = async (type: 'positive' | 'negative') => {
    if (feedback === type) {
      // Unset feedback
      setFeedback(null)
      // TODO: Remove feedback from backend
      return
    }

    setFeedback(type)
    // TODO: Send feedback to backend
    try {
      // await apiClient.post('/feedback', { messageId, type })
    } catch (error) {
      console.error('Failed to send feedback:', error)
      setFeedback(null)
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleFeedback('positive')}
        className={`rounded-md p-1.5 transition-colors ${
          feedback === 'positive'
            ? 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        }`}
        aria-label="Thumbs up"
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.834a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
        </svg>
      </button>
      <button
        onClick={() => handleFeedback('negative')}
        className={`rounded-md p-1.5 transition-colors ${
          feedback === 'negative'
            ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        }`}
        aria-label="Thumbs down"
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.834a2 2 0 00-.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
        </svg>
      </button>
    </div>
  )
}
