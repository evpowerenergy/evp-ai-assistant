'use client'

import { useTheme, type ThemeMode } from '@/contexts/ThemeContext'

const OPTIONS: Array<{ value: ThemeMode; label: string }> = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
]

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme()

  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-xs text-muted-foreground sm:inline">
        Theme: {resolvedTheme}
      </span>
      <select
        value={theme}
        onChange={(e) => setTheme(e.target.value as ThemeMode)}
        className="rounded-md border border-border bg-input px-2 py-1.5 text-xs text-foreground focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label="Select theme mode"
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
