'use client'

interface CitationBadgeProps {
  citation: string
}

export function CitationBadge({ citation }: CitationBadgeProps) {
  return (
    <span className="inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300">
      {citation}
    </span>
  )
}
