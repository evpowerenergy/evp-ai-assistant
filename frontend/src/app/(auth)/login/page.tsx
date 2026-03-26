'use client'

import { useMemo, useState, FormEvent, MouseEvent, CSSProperties, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { BrandLogo } from '@/components/ui/BrandLogo'
import { LoginThreeBackground } from '@/components/auth/LoginThreeBackground'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [performanceMode, setPerformanceMode] = useState<'low' | 'high'>('high')
  const [mouse, setMouse] = useState({ x: 50, y: 50, active: false })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const router = useRouter()
  const networkNodes = useMemo(
    () => [
      { x: 8, y: 18, size: 9 },
      { x: 16, y: 34, size: 12 },
      { x: 26, y: 14, size: 10 },
      { x: 31, y: 56, size: 13 },
      { x: 44, y: 28, size: 10 },
      { x: 52, y: 44, size: 12 },
      { x: 63, y: 22, size: 14 },
      { x: 71, y: 52, size: 9 },
      { x: 82, y: 30, size: 13 },
      { x: 86, y: 64, size: 10 },
      { x: 61, y: 74, size: 12 },
      { x: 38, y: 76, size: 9 },
    ],
    []
  )

  const networkLines = useMemo(
    () => [
      [0, 1], [1, 3], [0, 2], [2, 4], [4, 5], [3, 5],
      [4, 6], [6, 8], [5, 7], [7, 9], [5, 10], [10, 9],
      [3, 11], [11, 10], [6, 7], [1, 4], [2, 6],
    ],
    []
  )

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * 100
    const y = ((e.clientY - rect.top) / rect.height) * 100
    setMouse({ x, y, active: true })
  }

  const handleMouseLeave = () => {
    setMouse((prev) => ({ ...prev, active: false }))
  }

  useEffect(() => {
    if (typeof window === 'undefined') return

    const savedRememberMe = window.localStorage.getItem('auth.remember_me')
    const savedEmail = window.localStorage.getItem('auth.saved_email')

    const isRememberEnabled = savedRememberMe !== 'false'
    setRememberMe(isRememberEnabled)
    if (isRememberEnabled && savedEmail) {
      setEmail(savedEmail)
    }
  }, [])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('auth.remember_me', String(rememberMe))
        if (rememberMe) {
          window.localStorage.setItem('auth.saved_email', email)
        } else {
          window.localStorage.removeItem('auth.saved_email')
        }
      }
      await signIn(email, password)
      router.push('/chat')
    } catch (err: any) {
      setError(err.message || 'Failed to sign in')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="liquid-bg ai-login-bg relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12 text-foreground sm:px-6 lg:px-8"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={
        {
          '--mouse-x': `${mouse.x}%`,
          '--mouse-y': `${mouse.y}%`,
        } as CSSProperties
      }
    >
      <div className="ai-orb ai-orb-1" />
      <div className="ai-orb ai-orb-2" />
      <div className="ai-orb ai-orb-3" />
      <div className="ai-grid-overlay" />
      <LoginThreeBackground mode={performanceMode} />
      <div className="ai-3d-ring" />
      <div className={`ai-mouse-spotlight ${mouse.active ? 'is-active' : ''}`} />

      <div className="ai-network" aria-hidden="true">
        {networkLines.map(([from, to], idx) => {
          const a = networkNodes[from]
          const b = networkNodes[to]
          const deltaX = b.x - a.x
          const deltaY = b.y - a.y
          const length = Math.sqrt(deltaX ** 2 + deltaY ** 2)
          const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI)

          return (
            <div
              key={`line-${idx}`}
              className="ai-network-line"
              style={{
                left: `${a.x}%`,
                top: `${a.y}%`,
                width: `${length}%`,
                transform: `rotate(${angle}deg)`,
              }}
            />
          )
        })}

        {networkNodes.map((node, idx) => {
          const distance = Math.hypot(mouse.x - node.x, mouse.y - node.y)
          const influence = mouse.active ? Math.max(0, 1 - distance / 22) : 0

          return (
            <span
              key={`node-${idx}`}
              className="ai-network-node"
              style={
                {
                  left: `${node.x}%`,
                  top: `${node.y}%`,
                  width: `${node.size}px`,
                  height: `${node.size}px`,
                  '--node-scale': `${1 + influence * 1.4}`,
                  '--node-alpha': `${0.35 + influence * 0.65}`,
                } as CSSProperties
              }
            />
          )
        })}
      </div>

      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="ai-performance-panel">
        <span className="ai-panel-label">3D</span>
        <button
          type="button"
          className={`ai-mode-btn ${performanceMode === 'low' ? 'active' : ''}`}
          onClick={() => setPerformanceMode('low')}
        >
          Low
        </button>
        <button
          type="button"
          className={`ai-mode-btn ${performanceMode === 'high' ? 'active' : ''}`}
          onClick={() => setPerformanceMode('high')}
        >
          High
        </button>
      </div>

      <div className="glass-panel-strong glass-shine ai-login-card relative z-10 w-full max-w-md space-y-7 rounded-3xl border border-white/30 p-8">
        <div className="flex flex-col items-center text-center">
          <BrandLogo size="lg" className="mb-4" />
          <p className="ai-login-badge mb-2 rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.18em]">
            AI Command Center
          </p>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Welcome back
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to access EV Power internal AI assistant platform
          </p>
        </div>

        <form className="space-y-5" autoComplete="on" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
              <h3 className="text-sm font-medium text-red-700 dark:text-red-300">{error}</h3>
            </div>
          )}

          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-foreground/90">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="ai-login-input block w-full rounded-xl border border-border/70 bg-input/80 px-4 py-3 ring-0 transition-all placeholder:text-muted-foreground focus:border-indigo-500/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                placeholder="username/email"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-foreground/90">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="ai-login-input block w-full rounded-xl border border-border/70 bg-input/80 px-4 py-3 pr-12 ring-0 transition-all placeholder:text-muted-foreground focus:border-indigo-500/60 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M3 3l18 18" strokeLinecap="round" />
                      <path d="M10.58 10.58a2 2 0 102.83 2.83" strokeLinecap="round" />
                      <path d="M9.36 5.37A10.94 10.94 0 0112 5c5 0 9.27 3.11 11 7-1.02 2.29-2.74 4.15-4.86 5.35M6.23 6.23C3.95 7.6 2.13 9.62 1 12c.6 1.34 1.46 2.57 2.52 3.64" strokeLinecap="round" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M1 12c1.73-3.89 6-7 11-7s9.27 3.11 11 7c-1.73 3.89-6 7-11 7S2.73 15.89 1 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground/90">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-border text-indigo-500 focus:ring-indigo-500"
              />
              Remember me
            </label>
            <button
              type="submit"
              disabled={loading}
              className="ai-login-button group relative flex w-full items-center justify-center rounded-xl px-3 py-3 text-sm font-semibold text-white transition-transform duration-300 hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>

            <p className="text-center text-xs text-muted-foreground">
              Secure access protected by role-based permissions
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}
