'use client'

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: ThemeMode
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: ThemeMode) => void
}

const THEME_STORAGE_KEY = 'evp-ai-assistant-theme'

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyThemeClass(theme: ThemeMode) {
  if (typeof document === 'undefined') return
  const isDark = theme === 'dark' || (theme === 'system' && getSystemTheme() === 'dark')
  document.documentElement.classList.toggle('dark', isDark)
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('system')
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
    const initialTheme: ThemeMode =
      storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system'
        ? storedTheme
        : 'system'

    setThemeState(initialTheme)
    const initialResolved = initialTheme === 'system' ? getSystemTheme() : initialTheme
    setResolvedTheme(initialResolved)
    applyThemeClass(initialTheme)
  }, [])

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      if (theme !== 'system') return
      const next = getSystemTheme()
      setResolvedTheme(next)
      applyThemeClass('system')
    }

    handleChange()
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [theme])

  const setTheme = (nextTheme: ThemeMode) => {
    setThemeState(nextTheme)
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
    const nextResolved = nextTheme === 'system' ? getSystemTheme() : nextTheme
    setResolvedTheme(nextResolved)
    applyThemeClass(nextTheme)
  }

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
    }),
    [theme, resolvedTheme]
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
