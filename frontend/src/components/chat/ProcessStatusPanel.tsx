'use client'

import { useEffect, useState } from 'react'
import type { ConfigInfo } from '@/hooks/useConfig'

interface ProcessStep {
  name: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  startTime?: number
  endTime?: number
  duration?: number
  data?: any
  preview?: string
  display_name?: string  // Display name in Thai
}

interface ProcessStatusPanelProps {
  loading: boolean
  processSteps?: ProcessStep[]
  runtime?: number
  toolResults?: any[]
  debugPrecompute?: Record<string, any> | null
  loadingHistory?: boolean
  modelConfig?: ConfigInfo | null
}

export function ProcessStatusPanel({ loading, processSteps, runtime, toolResults, debugPrecompute, loadingHistory, modelConfig }: ProcessStatusPanelProps) {
  const [elapsedTime, setElapsedTime] = useState(0)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  useEffect(() => {
    if (!loading) return

    const interval = setInterval(() => {
      setElapsedTime((prev) => prev + 0.1)
    }, 100)

    return () => clearInterval(interval)
  }, [loading])

  useEffect(() => {
    if (!loading) {
      setElapsedTime(0)
    }
  }, [loading])

  const formatTime = (seconds: number) => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`
    }
    return `${seconds.toFixed(1)}s`
  }

  const getStepIcon = (status: ProcessStep['status']) => {
    switch (status) {
      case 'completed':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100">
            <svg className="h-3 w-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )
      case 'processing':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100">
            <div className="h-2 w-2 animate-pulse rounded-full bg-blue-600"></div>
          </div>
        )
      case 'error':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-100">
            <svg className="h-3 w-3 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        )
      default:
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-muted">
            <div className="h-2 w-2 rounded-full bg-muted-foreground"></div>
          </div>
        )
    }
  }

  const getStepName = (step: string) => {
    const stepNames: Record<string, string> = {
      router: 'วิเคราะห์ Intent',
      db_query: 'ดึงข้อมูลจาก Database',
      rag_query: 'ค้นหาเอกสาร',
      result_grader: 'ตรวจสอบคุณภาพข้อมูล',
      rpc_planner: 'ปรับ Parameters',
      generate_response: 'สร้างคำตอบ',
      direct_answer: 'ตอบคำถามทั่วไป',
    }
    return stepNames[step] || step
  }

  const formatPreview = (data: any, toolName?: string): string => {
    if (!data) return 'ไม่มีข้อมูล'
    
    try {
      if (toolName === 'search_leads') {
        const leads = data?.data?.leads || []
        const count = data?.data?.stats?.returned || leads.length
        if (count > 0) {
          return `พบ ${count} leads`
        }
        return 'ไม่พบข้อมูล'
      }
      
      if (toolName === 'get_lead_status') {
        if (data?.found) {
          return `พบ lead: ${data.display_name || data.full_name || 'N/A'}`
        }
        return 'ไม่พบ lead'
      }
      
      if (toolName === 'get_daily_summary') {
        const newLeads = data?.new_leads_today || 0
        return `Lead ใหม่: ${newLeads} รายการ`
      }
      
      // Generic preview
      if (typeof data === 'object') {
        const keys = Object.keys(data)
        if (keys.length > 0) {
          return `ข้อมูล: ${keys.length} fields`
        }
      }
      
      return 'มีข้อมูล'
    } catch (e) {
      return 'กำลังประมวลผล...'
    }
  }

  const formatJSON = (obj: any, maxLength: number = Infinity): string => {
    try {
      const str = JSON.stringify(obj, null, 2)
      // If maxLength is Infinity, return full string
      if (maxLength === Infinity) {
        return str
      }
      if (str.length > maxLength) {
        return str.substring(0, maxLength) + '\n... (truncated)'
      }
      return str
    } catch {
      return String(obj)
    }
  }

  const toExportText = (value: any) => {
    if (typeof value === 'string') return value
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      window.setTimeout(() => {
        setCopiedKey((prev) => (prev === key ? null : prev))
      }, 1500)
    } catch {
      // Fallback for older browsers / blocked clipboard API
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '0'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(textarea)
      if (ok) {
        setCopiedKey(key)
        window.setTimeout(() => {
          setCopiedKey((prev) => (prev === key ? null : prev))
        }, 1500)
      }
    }
  }

  const downloadTextFile = (filename: string, text: string, mimeType: string) => {
    const blob = new Blob([text], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="hidden h-full w-72 flex-shrink-0 flex-col overflow-hidden border-l border-neutral-200 bg-[#f7f7f8] dark:border-neutral-800 dark:bg-[#171717] lg:flex">
      {/* Header - ชื่อ + Model + Runtime แยกบรรทัด ไม่ให้บัง */}
      <div className="flex shrink-0 flex-col gap-1 border-b border-neutral-200 p-3 dark:border-neutral-800">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">สถานะการประมวลผล</h3>
        {modelConfig && (
          <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
            Model: <span className="font-mono text-neutral-800 dark:text-neutral-200">{modelConfig.openai_model}</span>
            <span className="ml-1 font-normal text-muted-foreground">({modelConfig.agents_count} agents)</span>
          </p>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          {runtime !== undefined && (
            <span className="font-medium text-foreground">Runtime: {formatTime(runtime)}</span>
          )}
          {loading && (
            <span className="text-blue-600">กำลังทำงาน: {formatTime(elapsedTime)}</span>
          )}
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div className="min-h-0 flex-1 overflow-y-auto p-3 space-y-3">
        {/* Agents และ Model ที่ใช้ (แยกแต่ละตัว) */}
        {modelConfig && modelConfig.agents.length > 0 && (
          <div>
            <h4 className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Agents และ Model</h4>
            <div className="rounded-lg border border-neutral-200 bg-white p-2.5 dark:border-neutral-700 dark:bg-neutral-900/50">
              <ul className="space-y-2">
                {modelConfig.agents.map((agent, i) => (
                  <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5 text-xs">
                    <span className="text-foreground">{agent.name}</span>
                    <span className="shrink-0 font-mono text-neutral-600 dark:text-neutral-300">{agent.model}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* โหลด History */}
        <div>
          <h4 className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">โหลด History</h4>
          <div className="rounded-lg border border-neutral-200 bg-white p-2.5 dark:border-neutral-700 dark:bg-neutral-900/50">
            <div className="flex items-center gap-2">
              {loadingHistory ? (
                <>
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-blue-600"></div>
                  </div>
                  <p className="text-xs font-medium text-foreground">กำลังโหลดประวัติการสนทนา...</p>
                </>
              ) : (
                <>
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-muted">
                    <svg className="h-3 w-3 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-xs text-muted-foreground">พร้อม</p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* สถานะการทำงาน - จำกัดความสูง + scroll */}
        <div>
          <h4 className="mb-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">สถานะการทำงาน</h4>
          {processSteps && processSteps.length > 0 ? (
            <div className="max-h-36 space-y-1.5 overflow-y-auto rounded-lg border border-neutral-200 bg-neutral-100/80 p-1.5 dark:border-neutral-700 dark:bg-neutral-900/40">
              {processSteps.map((step, index) => (
                <div
                  key={`${step.name}-${index}`}
                  className={`flex items-center gap-2 rounded border border-neutral-200 bg-white px-2 py-1.5 transition-all dark:border-neutral-700 dark:bg-neutral-900/60 ${
                    step.status === 'processing' ? 'ring-1 ring-neutral-400/50 dark:ring-neutral-500/40' : ''
                  }`}
                >
                  {getStepIcon(step.status)}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <p className="truncate text-xs font-medium text-foreground">
                        {(step as any).display_name || getStepName(step.name)}
                      </p>
                      {step.duration !== undefined && (
                        <span className="shrink-0 text-xs text-muted-foreground">{formatTime(step.duration)}</span>
                      )}
                    </div>
                    {step.preview && (
                      <p className="truncate text-xs text-muted-foreground">{step.preview}</p>
                    )}
                    {step.status === 'error' && step.data?.error && (
                      <p className="truncate text-xs text-red-600">{step.data.error}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : loading ? (
            <div className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900/50">
              <div className="h-2 w-2 animate-pulse rounded-full bg-neutral-500 dark:bg-neutral-400" />
              <p className="text-xs text-muted-foreground">กำลังประมวลผล...</p>
            </div>
          ) : (
            <p className="py-2 text-center text-xs text-muted-foreground">ยังไม่มีการประมวลผล</p>
          )}
        </div>

        {/* Pre-compute (Debug) */}
        {debugPrecompute && Object.keys(debugPrecompute).length > 0 && (
          <div className="border-t pt-4">
            <h4 className="mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Pre-compute (Debug)</h4>
            <div className="space-y-3">
              {Object.entries(debugPrecompute).map(([toolKey, summary]) => (
                <div key={toolKey} className="overflow-hidden rounded-lg border border-amber-300/70 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40">
                  <div className="border-b border-amber-300/70 bg-amber-100 px-3 py-2 dark:border-amber-900 dark:bg-amber-900/60">
                    <p className="text-xs font-semibold text-foreground">{toolKey}</p>
                  </div>
                  <div className="px-3 py-2 space-y-2">
                    {typeof summary === 'object' && summary !== null && Object.entries(summary).map(([k, v]) => (
                      <div key={k}>
                        <p className="mb-0.5 text-xs font-medium text-muted-foreground">{k}:</p>
                        <pre className="max-h-32 overflow-x-auto overflow-y-auto whitespace-pre-wrap break-words rounded border border-border/70 bg-muted/30 p-2 text-xs text-muted-foreground">
                          {typeof v === 'string' ? v : JSON.stringify(v, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ด้านล่าง: ข้อมูลที่ดึงจากฟังก์ชัน */}
        {toolResults && toolResults.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">ข้อมูลที่ดึงจากฟังก์ชัน</h4>
            <div className="space-y-3">
              {toolResults.map((result, index) => (
                <div key={index} className="overflow-hidden rounded-lg border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900/50">
                  {/* Tool Name */}
                  <div className="border-b border-border bg-muted/50 px-3 py-2">
                    <p className="text-xs font-semibold text-foreground">
                      Function: <span className="text-blue-600">{result.tool || 'Unknown'}</span>
                    </p>
                  </div>
                  
                  {/* Input Parameters */}
                  {result.input && Object.keys(result.input).length > 0 && (
                    <div className="border-b border-border bg-muted/50 px-3 py-2">
                      <p className="mb-1 text-xs font-medium text-muted-foreground">📥 Parameters (Input):</p>
                      <pre className="max-h-32 overflow-x-auto overflow-y-auto whitespace-pre-wrap break-words rounded border border-border/70 bg-muted/30 p-2 text-xs text-muted-foreground">
                        {formatJSON(result.input, Infinity)}
                      </pre>
                    </div>
                  )}
                  
                  {/* Output Preview */}
                  <div className="px-3 py-2">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-muted-foreground">📤 Raw Data (Output):</p>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          className="rounded border border-border/80 bg-muted/30 px-2 py-0.5 text-[11px] font-medium text-foreground hover:bg-muted/60"
                          onClick={() => {
                            const text = toExportText(result.output)
                            void copyToClipboard(text, `out-${index}`)
                          }}
                        >
                          {copiedKey === `out-${index}` ? 'Copied' : 'Copy'}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-border/80 bg-muted/30 px-2 py-0.5 text-[11px] font-medium text-foreground hover:bg-muted/60"
                          onClick={() => {
                            const safeTool = String(result.tool || 'output').replace(/[^a-zA-Z0-9-_]+/g, '_')
                            const ts = new Date().toISOString().replace(/[:.]/g, '-')
                            const filename = `ai-assistant-${safeTool}-output-${ts}.json`
                            downloadTextFile(filename, toExportText(result.output), 'application/json;charset=utf-8')
                          }}
                        >
                          Export
                        </button>
                      </div>
                    </div>
                    <pre className="max-h-96 overflow-x-auto overflow-y-auto whitespace-pre-wrap break-words rounded border border-border/70 bg-muted/30 p-2 font-mono text-xs text-muted-foreground">
                      {formatJSON(result.output, Infinity)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
