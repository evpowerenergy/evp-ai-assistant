'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import apiClient from '@/lib/api/client'

interface AgentRun {
  id: string
  request_id: string
  request_type?: string
  primary_engine: string
  primary_status?: string
  actual_engine?: string
  model?: string
  fallback_used: boolean
  fallback_reason?: string
  response_source?: string
  timings?: { total_seconds?: number }
  total_tool_calls?: number
  total_skill_calls?: number
  error_class?: string
  created_at: string
}

const statusStyle: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  timed_out: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
}

export default function AgentRunsPage() {
  const { session, userRole } = useAuth()
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const [fallback, setFallback] = useState('')

  const loadRuns = useCallback(async () => {
    if (!session?.access_token || userRole !== 'super_admin') return
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/api/v1/admin/agent-runs', {
        headers: { Authorization: `Bearer ${session.access_token}` },
        params: {
          limit: 100,
          ...(status && { status }),
          ...(fallback && { fallback_used: fallback === 'yes' }),
        },
      })
      setRuns(response.data.runs || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'โหลด Agent Audit ไม่สำเร็จ')
    } finally {
      setLoading(false)
    }
  }, [fallback, session?.access_token, status, userRole])

  useEffect(() => { void loadRuns() }, [loadRuns])

  if (userRole && userRole !== 'super_admin') {
    return <div className="p-8 text-center text-red-500">หน้านี้สำหรับ Super Admin เท่านั้น</div>
  }

  return (
    <div className="min-h-screen bg-background p-4 text-foreground sm:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href="/admin" className="text-sm text-indigo-500 hover:underline">← Admin Console</Link>
            <h1 className="mt-2 text-2xl font-semibold">Agent Runtime Audit</h1>
            <p className="text-sm text-muted-foreground">Hermes, Skills, MCP, Timeout และ LangGraph fallback</p>
          </div>
          <button onClick={() => void loadRuns()} className="rounded-md border border-border px-3 py-2 text-sm hover:bg-muted">Refresh</button>
        </div>

        <div className="mb-4 flex flex-wrap gap-3 rounded-lg border border-border bg-card p-3">
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="">ทุกสถานะ</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="timed_out">Timed out</option>
            <option value="failed">Failed</option>
          </select>
          <select value={fallback} onChange={(e) => setFallback(e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="">Fallback ทั้งหมด</option>
            <option value="yes">ใช้ Fallback</option>
            <option value="no">ไม่ใช้ Fallback</option>
          </select>
        </div>

        {error && <div className="mb-4 rounded-md border border-red-400 bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</div>}

        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-border bg-muted/60 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">เวลา / Request</th>
                  <th className="px-4 py-3">ประเภท</th>
                  <th className="px-4 py-3">Engine</th>
                  <th className="px-4 py-3">สถานะ</th>
                  <th className="px-4 py-3">Runtime</th>
                  <th className="px-4 py-3">Tools / Skills</th>
                  <th className="px-4 py-3">Fallback</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((run) => {
                  const runStatus = run.primary_status || 'unknown'
                  return (
                    <tr key={run.id} className="hover:bg-muted/40">
                      <td className="px-4 py-3">
                        <Link href={`/admin/agent-runs/${run.id}`} className="font-mono text-xs text-indigo-500 hover:underline">{run.request_id.slice(0, 12)}</Link>
                        <div className="mt-1 text-xs text-muted-foreground">{new Date(run.created_at).toLocaleString('th-TH')}</div>
                      </td>
                      <td className="px-4 py-3">{run.request_type || '—'}</td>
                      <td className="px-4 py-3"><div>{run.primary_engine}</div><div className="text-xs text-muted-foreground">{run.model || '—'}</div></td>
                      <td className="px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs ${statusStyle[runStatus] || 'bg-muted text-muted-foreground'}`}>{runStatus}</span></td>
                      <td className="px-4 py-3">{run.timings?.total_seconds != null ? `${run.timings.total_seconds.toFixed(1)}s` : '—'}</td>
                      <td className="px-4 py-3">{run.total_tool_calls || 0} / {run.total_skill_calls || 0}</td>
                      <td className="px-4 py-3">{run.fallback_used ? <span className="text-amber-500">{run.response_source || 'Yes'}</span> : 'No'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {!loading && runs.length === 0 && <p className="p-10 text-center text-sm text-muted-foreground">ยังไม่มีข้อมูล audit หรือยังไม่ได้ apply migration</p>}
          {loading && <p className="p-10 text-center text-sm text-muted-foreground">กำลังโหลด…</p>}
        </div>
      </div>
    </div>
  )
}
