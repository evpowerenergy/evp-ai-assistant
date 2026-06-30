'use client'

import { useState, useEffect, useCallback } from 'react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/contexts/AuthContext'

interface Document {
  id: string
  title: string
  file_type: string | null
  file_path: string | null
  file_size: number | null
  status: string
  chunk_count: number | null
  category: string | null
  created_at: string
  indexed_at: string | null
  error_message: string | null
}

interface DocumentListProps {
  onRefresh?: () => void
}

const STATUS_LABELS: Record<string, string> = {
  queued: 'รอคิว',
  processing: 'กำลังประมวลผล',
  ready: 'พร้อมใช้งาน',
  failed: 'ล้มเหลว',
}

export function DocumentList({ onRefresh }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionId, setActionId] = useState<string | null>(null)
  const { session, userRole } = useAuth()
  const isSuperAdmin = userRole === 'super_admin'

  const loadDocuments = useCallback(async () => {
    if (!session?.access_token) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get<{ documents: Document[] }>('/api/v1/documents', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      setDocuments(data.documents || [])
      onRefresh?.()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load documents'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, onRefresh])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === 'queued' || d.status === 'processing'
    )
    if (!hasProcessing) return
    const interval = setInterval(() => void loadDocuments(), 5000)
    return () => clearInterval(interval)
  }, [documents, loadDocuments])

  const handleDelete = async (id: string, title: string) => {
    if (!session?.access_token) return
    if (!confirm(`ลบเอกสาร "${title}" และ chunks ทั้งหมด?`)) return
    setActionId(id)
    try {
      await apiClient.delete(`/api/v1/documents/${id}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      await loadDocuments()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setActionId(null)
    }
  }

  const handleDownload = async (id: string) => {
    if (!session?.access_token) return
    setActionId(id)
    try {
      const { data } = await apiClient.get<{ download_url: string }>(
        `/api/v1/documents/${id}/download`,
        { headers: { Authorization: `Bearer ${session.access_token}` } }
      )
      if (data.download_url) window.open(data.download_url, '_blank')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setActionId(null)
    }
  }

  const handleReindex = async (id: string) => {
    if (!session?.access_token) return
    setActionId(id)
    try {
      await apiClient.post(
        `/api/v1/documents/${id}/reindex`,
        {},
        { headers: { Authorization: `Bearer ${session.access_token}` } }
      )
      await loadDocuments()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Reindex failed')
    } finally {
      setActionId(null)
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
          <p className="mt-4 text-muted-foreground">Loading documents...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/50">
        <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">Documents ({documents.length})</h2>
        <button
          type="button"
          onClick={() => void loadDocuments()}
          className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
        >
          Refresh
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-muted-foreground">No documents uploaded yet</p>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {documents.map((doc) => (
            <div key={doc.id} className="px-6 py-4 hover:bg-muted/50">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-foreground">{doc.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {doc.file_type || doc.file_path} •{' '}
                    {new Date(doc.created_at).toLocaleDateString('th-TH')}
                    {doc.chunk_count != null ? ` • ${doc.chunk_count} chunks` : ''}
                    {doc.file_size ? ` • ${(doc.file_size / 1024).toFixed(1)} KB` : ''}
                  </p>
                  {doc.error_message && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{doc.error_message}</p>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      doc.status === 'ready'
                        ? 'bg-green-100 text-green-800 dark:bg-green-950/60 dark:text-green-300'
                        : doc.status === 'failed'
                          ? 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                    }`}
                  >
                    {STATUS_LABELS[doc.status] || doc.status}
                  </span>
                  {isSuperAdmin && (
                    <>
                      <button
                        type="button"
                        disabled={actionId === doc.id}
                        onClick={() => void handleDownload(doc.id)}
                        className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                      >
                        Download
                      </button>
                      <button
                        type="button"
                        disabled={actionId === doc.id || doc.status === 'queued'}
                        onClick={() => void handleReindex(doc.id)}
                        className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                      >
                        Reindex
                      </button>
                      <button
                        type="button"
                        disabled={actionId === doc.id}
                        onClick={() => void handleDelete(doc.id, doc.title)}
                        className="text-xs text-red-600 hover:underline disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
