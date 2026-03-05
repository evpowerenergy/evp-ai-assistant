'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/contexts/AuthContext'

interface AuditLog {
  id: string
  user_id: string
  action: string
  resource: string
  request_data: any
  response_data: any
  created_at: string
}

export function LogViewer() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const { userRole } = useAuth()
  const supabase = createClient()

  useEffect(() => {
    loadLogs()
  }, [filter])

  const loadLogs = async () => {
    setLoading(true)
    setError(null)

    try {
      let query = supabase
        .from('audit_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100)

      // Filter by user if not admin
      if (userRole !== 'admin') {
        query = query.eq('user_id', (await supabase.auth.getUser()).data.user?.id || '')
      }

      // Filter by action if specified
      if (filter !== 'all') {
        query = query.eq('action', filter)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setLogs(data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load logs')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading logs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Audit Logs ({logs.length})</h2>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
          >
            <option value="all">All Actions</option>
            <option value="chat_request">Chat Requests</option>
            <option value="tool_call">Tool Calls</option>
            <option value="document_upload">Document Uploads</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="px-6 py-4">
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}

      {logs.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-gray-500">No logs found</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-200">
          {logs.map((log) => (
            <div key={log.id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800">
                      {log.action}
                    </span>
                    <span className="text-sm text-gray-600">{log.resource}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {new Date(log.created_at).toLocaleString('th-TH')}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
