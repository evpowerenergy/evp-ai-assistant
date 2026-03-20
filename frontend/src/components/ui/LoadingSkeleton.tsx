'use client'

interface LoadingSkeletonProps {
  lines?: number
  className?: string
}

export function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="flex-1 space-y-2">
          <div className="h-4 rounded bg-gray-200 dark:bg-gray-700" style={{ width: `${100 - i * 10}%` }}></div>
        </div>
      ))}
    </div>
  )
}
