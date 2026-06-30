'use client'

import { useEffect, useRef, useState } from 'react'
import { useLineLink } from '@/hooks/useLineLink'

interface LineLinkControlProps {
  /** header = compact button in /chat navbar; page = inline on admin page */
  variant?: 'header' | 'page'
}

export function LineLinkControl({ variant = 'header' }: LineLinkControlProps) {
  const {
    status,
    linkCommand,
    countdown,
    loading,
    actionLoading,
    error,
    generateCode,
    unlink,
  } = useLineLink()
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const linked = status?.linked === true
  const label = loading ? 'LINE…' : linked ? 'LINE ✓' : 'LINE'

  const panel = (
    <div className="w-72 space-y-3 p-1 text-left sm:w-80">
      <div>
        <p className="text-sm font-semibold text-foreground">เชื่อมต่อ LINE OA</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          สร้างรหัสแล้วพิมพ์ในแชท LINE Official Account
        </p>
      </div>

      {linked ? (
        <div className="rounded-md border border-green-200 bg-green-50/80 px-3 py-2 text-xs text-green-800 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300">
          เชื่อมต่อแล้ว
          {status?.line_user_id && (
            <p className="mt-1 truncate font-mono text-[10px] opacity-80">{status.line_user_id}</p>
          )}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">ยังไม่ได้เชื่อมต่อบัญชี LINE</p>
      )}

      {!linked && (
        <>
          <ol className="list-decimal list-inside space-y-1 text-xs text-muted-foreground">
            <li>Add Friend LINE OA</li>
            <li>กดสร้างรหัสด้านล่าง</li>
            <li>พิมพ์ LINK + รหัส 6 หลัก ใน LINE</li>
          </ol>
          <button
            type="button"
            onClick={() => void generateCode()}
            disabled={actionLoading || loading}
            className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {actionLoading ? 'กำลังสร้างรหัส…' : 'สร้างรหัสเชื่อมต่อ'}
          </button>
        </>
      )}

      {linkCommand && (
        <div className="rounded-md bg-muted px-3 py-2">
          <p className="text-xs text-muted-foreground">พิมพ์ใน LINE</p>
          <p className="mt-1 break-all font-mono text-base font-semibold text-indigo-600 dark:text-indigo-400">
            {linkCommand}
          </p>
          {countdown > 0 && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              หมดอายุใน {Math.floor(countdown / 60)}:
              {(countdown % 60).toString().padStart(2, '0')} นาที
            </p>
          )}
        </div>
      )}

      {linked && (
        <button
          type="button"
          onClick={async () => {
            if (!confirm('ยกเลิกการเชื่อมต่อ LINE?')) return
            await unlink()
          }}
          disabled={actionLoading}
          className="w-full rounded-md border border-red-200 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-950/40"
        >
          ยกเลิกการเชื่อมต่อ
        </button>
      )}

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  )

  if (variant === 'page') {
    return (
      <div className="rounded-lg border border-border bg-card shadow-sm">
        <div className="border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">เชื่อมต่อบัญชี LINE</h2>
        </div>
        <div className="px-6 py-4">{panel}</div>
      </div>
    )
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors ${
          linked
            ? 'border-green-300 bg-green-50 text-green-800 hover:bg-green-100 dark:border-green-800 dark:bg-green-950/50 dark:text-green-300 dark:hover:bg-green-950/70'
            : 'border-neutral-200 bg-neutral-50 text-neutral-700 hover:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-900/90 dark:text-neutral-300 dark:hover:bg-neutral-800'
        }`}
        title="เชื่อมต่อ LINE Official Account"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
        </svg>
        <span>{label}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 rounded-lg border border-border bg-card p-3 shadow-lg">
          {panel}
        </div>
      )}
    </div>
  )
}
