'use client'

export type ChatMode = 'crm' | 'kb'

interface ChatModeToggleProps {
  mode: ChatMode
  onChange: (mode: ChatMode) => void
  disabled?: boolean
}

export function ChatModeToggle({ mode, onChange, disabled }: ChatModeToggleProps) {
  return (
    <div className="mx-auto mb-2 flex max-w-3xl gap-1 rounded-xl border border-neutral-200 bg-white p-1 shadow-sm dark:border-neutral-700 dark:bg-[#2f2f2f]">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('crm')}
        className={`flex-1 rounded-lg px-3 py-2 text-left text-xs transition-colors sm:text-sm ${
          mode === 'crm'
            ? 'bg-emerald-600 text-white shadow-sm'
            : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
        } disabled:cursor-not-allowed disabled:opacity-60`}
      >
        <span className="block font-medium">CRM</span>
        <span className={`block text-[10px] sm:text-[11px] ${mode === 'crm' ? 'text-emerald-50' : 'text-neutral-400'}`}>
          ลีด, ยอดขาย, นัด, Marketing
        </span>
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('kb')}
        className={`flex-1 rounded-lg px-3 py-2 text-left text-xs transition-colors sm:text-sm ${
          mode === 'kb'
            ? 'bg-emerald-600 text-white shadow-sm'
            : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
        } disabled:cursor-not-allowed disabled:opacity-60`}
      >
        <span className="block font-medium">เอกสารบริษัท</span>
        <span className={`block text-[10px] sm:text-[11px] ${mode === 'kb' ? 'text-emerald-50' : 'text-neutral-400'}`}>
          SOP, ข้อมูลอ้างอิง, Company Reference
        </span>
      </button>
    </div>
  )
}
