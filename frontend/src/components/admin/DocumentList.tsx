'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

interface Document {
  id: string
  title: string
  file_type: string
  created_at: string
  uploaded_by: string
}

export function DocumentList() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const supabase = createClient()

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    setLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('kb_documents')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100)

      if (fetchError) throw fetchError

      setDocuments(data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
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
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">Documents ({documents.length})</h2>
      </div>

      {documents.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-muted-foreground">No documents uploaded yet</p>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {documents.map((doc) => (
            <div key={doc.id} className="px-6 py-4 hover:bg-muted/50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-foreground">{doc.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {doc.file_type} • {new Date(doc.created_at).toLocaleDateString('th-TH')}
                  </p>
                </div>
                <div className="ml-4">
                  <span className="inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300">
                    {doc.file_type}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
