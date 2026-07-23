'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import apiClient from '@/lib/api/client'

interface AuditEvent {
  id: string
  sequence_no: number
  event_type: string
  event_name: string
  status: string
  actor_id?: string
  duration_ms?: number
  model?: string
  metadata?: Record<string, unknown>
  occurred_at: string
}

export default function AgentRunDetailPage() {
  const params = useParams<{ runId: string }>()
  const { session, userRole } = useAuth()
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!session?.access_token || !params.runId || userRole !== 'super_admin') return
    apiClient.get(`/api/v1/admin/agent-runs/${params.runId}`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    }).then((response) => setData(response.data)).catch((err) => {
      setError(err.response?.data?.detail || err.message || 'โหลด audit ไม่สำเร็จ')
    })
  }, [params.runId, session?.access_token, userRole])

  if (error) return <div className="p-8 text-red-500">{error}</div>
  if (!data) return <div className="p-8 text-muted-foreground">กำลังโหลด Agent Audit…</div>

  const run = data.run
  return (
    <div className="min-h-screen bg-background p-4 text-foreground sm:p-8">
      <div className="mx-auto max-w-5xl">
        <Link href="/admin/agent-runs" className="text-sm text-indigo-500 hover:underline">← Agent Runtime Audit</Link>
        <div className="mt-4 rounded-lg border border-border bg-card p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h1 className="text-xl font-semibold">Run {String(run.request_id).slice(0, 12)}</h1><p className="font-mono text-xs text-muted-foreground">{run.id}</p></div>
            <span className="rounded-full bg-muted px-3 py-1 text-xs">{run.primary_status || run.status}</span>
          </div>
          <div className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Primary" value={`${run.primary_engine} · ${run.model || '—'}`} />
            <Metric label="Response source" value={run.response_source || run.actual_engine || '—'} />
            <Metric label="Request type" value={run.request_type || '—'} />
            <Metric label="Runtime" value={run.timings?.total_seconds != null ? `${Number(run.timings.total_seconds).toFixed(1)}s` : '—'} />
          </div>
          {run.fallback_used && <div className="mt-4 rounded-md border border-amber-400/50 bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">Fallback: {run.fallback_engine || run.actual_engine} — {run.fallback_reason || 'ไม่ระบุเหตุผล'}</div>}
        </div>

        <section className="mt-6">
          <h2 className="mb-3 text-lg font-semibold">Execution Timeline ({data.events.length})</h2>
          <div className="space-y-2">
            {(data.events as AuditEvent[]).map((event) => (
              <div key={event.id} className="grid gap-2 rounded-lg border border-border bg-card p-3 sm:grid-cols-[56px_1fr_auto]">
                <span className="font-mono text-xs text-muted-foreground">#{event.sequence_no}</span>
                <div><div className="text-sm font-medium">{event.event_name}</div><div className="text-xs text-muted-foreground">{event.event_type} · {event.actor_id || 'system'}{event.model ? ` · ${event.model}` : ''}</div></div>
                <div className="text-right text-xs"><div className={event.status === 'failed' ? 'text-red-500' : event.status === 'timed_out' ? 'text-amber-500' : 'text-emerald-500'}>{event.status}</div><div className="text-muted-foreground">{event.duration_ms != null ? `${event.duration_ms}ms` : new Date(event.occurred_at).toLocaleTimeString('th-TH')}</div></div>
              </div>
            ))}
            {data.events.length === 0 && <div className="rounded-lg border border-border p-6 text-center text-sm text-muted-foreground">ยังไม่มี structured events</div>}
          </div>
        </section>

        <section className="mt-6">
          <h2 className="mb-3 text-lg font-semibold">MCP Tools ({data.tools.length})</h2>
          <div className="overflow-x-auto rounded-lg border border-border bg-card">
            <table className="w-full min-w-[700px] text-left text-sm"><thead className="border-b border-border bg-muted/50 text-xs"><tr><th className="p-3">Tool</th><th className="p-3">Status</th><th className="p-3">Scope</th><th className="p-3">Duration</th><th className="p-3">Failure</th></tr></thead><tbody className="divide-y divide-border">{data.tools.map((tool: any) => <tr key={tool.id}><td className="p-3 font-mono text-xs">{tool.tool_name}</td><td className="p-3">{tool.status}</td><td className="p-3">{tool.scope || '—'}</td><td className="p-3">{tool.duration_ms != null ? `${tool.duration_ms}ms` : '—'}</td><td className="p-3 text-red-500">{tool.failure_code || tool.error_class || '—'}</td></tr>)}</tbody></table>
          </div>
        </section>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-muted/50 p-3"><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 break-words font-medium">{value}</div></div>
}
