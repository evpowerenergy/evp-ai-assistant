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
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100">
            <div className="h-2 w-2 rounded-full bg-gray-400"></div>
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

  return (
    <div className="flex hidden h-full w-72 flex-shrink-0 flex-col overflow-hidden border-l bg-gray-50 lg:flex">
      {/* Header - ชื่อ + Model + Runtime แยกบรรทัด ไม่ให้บัง */}
      <div className="flex shrink-0 flex-col gap-1 border-b border-gray-200 bg-white p-3">
        <h3 className="text-sm font-semibold text-gray-900">สถานะการประมวลผล</h3>
        {modelConfig && (
          <p className="text-xs font-medium text-indigo-600">
            Model: <span className="font-mono">{modelConfig.openai_model}</span>
            <span className="ml-1 font-normal text-gray-500">({modelConfig.agents_count} agents)</span>
          </p>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-600">
          {runtime !== undefined && (
            <span className="font-medium text-gray-700">Runtime: {formatTime(runtime)}</span>
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
            <h4 className="mb-2 text-xs font-semibold text-gray-700 uppercase tracking-wide">Agents และ Model</h4>
            <div className="rounded-lg border border-indigo-100 bg-white p-2.5">
              <ul className="space-y-2">
                {modelConfig.agents.map((agent, i) => (
                  <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5 text-xs">
                    <span className="text-gray-800">{agent.name}</span>
                    <span className="shrink-0 font-mono text-indigo-600">{agent.model}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* โหลด History */}
        <div>
          <h4 className="mb-2 text-xs font-semibold text-gray-700 uppercase tracking-wide">โหลด History</h4>
          <div className="rounded-lg border bg-white p-2.5">
            <div className="flex items-center gap-2">
              {loadingHistory ? (
                <>
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-blue-600"></div>
                  </div>
                  <p className="text-xs font-medium text-gray-900">กำลังโหลดประวัติการสนทนา...</p>
                </>
              ) : (
                <>
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100">
                    <svg className="h-3 w-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-xs text-gray-600">พร้อม</p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* สถานะการทำงาน - จำกัดความสูง + scroll */}
        <div>
          <h4 className="mb-1.5 text-xs font-semibold text-gray-700 uppercase tracking-wide">สถานะการทำงาน</h4>
          {processSteps && processSteps.length > 0 ? (
            <div className="max-h-36 space-y-1.5 overflow-y-auto rounded-lg border bg-gray-50/80 p-1.5">
              {processSteps.map((step, index) => (
                <div
                  key={`${step.name}-${index}`}
                  className={`flex items-center gap-2 rounded border bg-white px-2 py-1.5 transition-all ${
                    step.status === 'processing' ? 'ring-1 ring-blue-200' : ''
                  }`}
                >
                  {getStepIcon(step.status)}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <p className="truncate text-xs font-medium text-gray-900">
                        {(step as any).display_name || getStepName(step.name)}
                      </p>
                      {step.duration !== undefined && (
                        <span className="shrink-0 text-xs text-gray-400">{formatTime(step.duration)}</span>
                      )}
                    </div>
                    {step.preview && (
                      <p className="truncate text-xs text-gray-500">{step.preview}</p>
                    )}
                    {step.status === 'error' && step.data?.error && (
                      <p className="truncate text-xs text-red-600">{step.data.error}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : loading ? (
            <div className="flex items-center gap-2 rounded-lg border bg-white px-2 py-1.5">
              <div className="h-2 w-2 animate-pulse rounded-full bg-blue-600" />
              <p className="text-xs text-gray-600">กำลังประมวลผล...</p>
            </div>
          ) : (
            <p className="py-2 text-center text-xs text-gray-500">ยังไม่มีการประมวลผล</p>
          )}
        </div>

        {/* Pre-compute (Debug) */}
        {debugPrecompute && Object.keys(debugPrecompute).length > 0 && (
          <div className="border-t pt-4">
            <h4 className="mb-3 text-xs font-semibold text-gray-700 uppercase tracking-wide">Pre-compute (Debug)</h4>
            <div className="space-y-3">
              {Object.entries(debugPrecompute).map(([toolKey, summary]) => (
                <div key={toolKey} className="rounded-lg border bg-amber-50 overflow-hidden">
                  <div className="bg-amber-100 px-3 py-2 border-b">
                    <p className="text-xs font-semibold text-gray-900">{toolKey}</p>
                  </div>
                  <div className="px-3 py-2 space-y-2">
                    {typeof summary === 'object' && summary !== null && Object.entries(summary).map(([k, v]) => (
                      <div key={k}>
                        <p className="text-xs font-medium text-gray-700 mb-0.5">{k}:</p>
                        <pre className="text-xs text-gray-600 bg-white p-2 rounded border overflow-x-auto max-h-32 overflow-y-auto whitespace-pre-wrap break-words">
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
            <h4 className="mb-3 text-xs font-semibold text-gray-700 uppercase tracking-wide">ข้อมูลที่ดึงจากฟังก์ชัน</h4>
            <div className="space-y-3">
              {toolResults.map((result, index) => (
                <div key={index} className="rounded-lg border bg-white overflow-hidden">
                  {/* Tool Name */}
                  <div className="bg-gray-50 px-3 py-2 border-b">
                    <p className="text-xs font-semibold text-gray-900">
                      Function: <span className="text-blue-600">{result.tool || 'Unknown'}</span>
                    </p>
                  </div>
                  
                  {/* Input Parameters */}
                  {result.input && Object.keys(result.input).length > 0 && (
                    <div className="px-3 py-2 border-b bg-gray-50">
                      <p className="text-xs font-medium text-gray-700 mb-1">📥 Parameters (Input):</p>
                      <pre className="text-xs text-gray-600 bg-white p-2 rounded border overflow-x-auto max-h-32 overflow-y-auto whitespace-pre-wrap break-words">
                        {formatJSON(result.input, Infinity)}
                      </pre>
                    </div>
                  )}
                  
                  {/* Output Preview */}
                  <div className="px-3 py-2">
                    <p className="text-xs font-medium text-gray-700 mb-1">📤 Raw Data (Output):</p>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded border overflow-x-auto max-h-96 overflow-y-auto font-mono whitespace-pre-wrap break-words">
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
