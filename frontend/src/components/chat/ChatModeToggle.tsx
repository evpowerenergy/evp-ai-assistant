'use client'

export type ChatMode = 'crm' | 'kb'

interface ChatModeToggleProps {
  mode: ChatMode
  onChange: (mode: ChatMode) => void
  disabled?: boolean
}

export function ChatModeToggle({ mode, onChange, disabled }: ChatModeToggleProps) {
  // `mode` and `onChange` are intentionally retained in the component API so
  // LangGraph can keep its persisted fallback preference. Hermes is the only
  // user-facing mode and routes each request to the appropriate EVP tool.
  void mode
  void onChange
  void disabled

  return (
    <div className="mx-auto mb-2 grid max-w-3xl grid-cols-1 gap-1 rounded-xl border border-neutral-200 bg-white p-1 shadow-sm sm:grid-cols-3 dark:border-neutral-700 dark:bg-[#2f2f2f]">
      <button
        type="button"
        disabled
        aria-current="true"
        className="rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-600 px-3 py-2 text-left text-xs text-white shadow-sm sm:text-sm"
      >
        <span className="flex items-center gap-1.5 font-semibold">
          <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_8px_rgba(110,231,183,0.9)]" />
          Hermes Auto
        </span>
        <span className="block text-[10px] text-indigo-50 sm:text-[11px]">
          เลือกเครื่องมือและข้อมูลให้อัตโนมัติ
        </span>
      </button>
      <button
        type="button"
        disabled
        title="โหมดสำรองสำหรับ LangGraph — Hermes Auto จะเลือก CRM tool ให้เอง"
        className="cursor-not-allowed rounded-lg border border-dashed border-neutral-200 px-3 py-2 text-left text-xs text-neutral-400 opacity-60 sm:text-sm dark:border-neutral-700 dark:text-neutral-500"
      >
        <span className="block font-medium">CRM</span>
        <span className="block text-[10px] sm:text-[11px]">
          สำรอง · Hermes เลือกให้อัตโนมัติ
        </span>
      </button>
      <button
        type="button"
        disabled
        title="โหมดสำรองสำหรับ LangGraph — Hermes Auto จะเลือก Knowledge tool ให้เอง"
        className="cursor-not-allowed rounded-lg border border-dashed border-neutral-200 px-3 py-2 text-left text-xs text-neutral-400 opacity-60 sm:text-sm dark:border-neutral-700 dark:text-neutral-500"
      >
        <span className="block font-medium">Knowledge</span>
        <span className="block text-[10px] sm:text-[11px]">
          สำรอง · Hermes เลือกให้อัตโนมัติ
        </span>
      </button>
    </div>
  )
}
