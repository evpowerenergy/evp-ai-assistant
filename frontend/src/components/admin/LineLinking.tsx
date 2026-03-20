'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/contexts/AuthContext'

interface LineIdentity {
  id: string
  user_id: string
  line_user_id: string
  linked_at: string
}

export function LineLinking() {
  const [linkings, setLinkings] = useState<LineIdentity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { userRole } = useAuth()
  const supabase = createClient()

  useEffect(() => {
    loadLinkings()
  }, [])

  const loadLinkings = async () => {
    setLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('line_identities')
        .select('*')
        .order('linked_at', { ascending: false })
        .limit(100)

      if (fetchError) throw fetchError

      setLinkings(data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load LINE linkings')
    } finally {
      setLoading(false)
    }
  }

  const handleUnlink = async (id: string) => {
    if (!confirm('Are you sure you want to unlink this LINE account?')) {
      return
    }

    try {
      const { error: deleteError } = await supabase.from('line_identities').delete().eq('id', id)

      if (deleteError) throw deleteError

      setLinkings((prev) => prev.filter((link) => link.id !== id))
    } catch (err: any) {
      setError(err.message || 'Failed to unlink LINE account')
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
          <p className="mt-4 text-muted-foreground">Loading LINE linkings...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-card shadow-sm">
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">LINE User Linking ({linkings.length})</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage LINE user account linking for notifications
        </p>
      </div>

      {error && (
        <div className="px-6 py-4">
          <div className="rounded-md bg-red-50 p-4 dark:bg-red-950/50">
            <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
          </div>
        </div>
      )}

      {linkings.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-muted-foreground">No LINE accounts linked yet</p>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {linkings.map((link) => (
            <div key={link.id} className="px-6 py-4 hover:bg-muted/50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">User ID: {link.user_id}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    LINE User ID: {link.line_user_id}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Linked: {new Date(link.linked_at).toLocaleString('th-TH')}
                  </p>
                </div>
                <button
                  onClick={() => handleUnlink(link.id)}
                  className="ml-4 rounded-md bg-red-100 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-200"
                >
                  Unlink
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
