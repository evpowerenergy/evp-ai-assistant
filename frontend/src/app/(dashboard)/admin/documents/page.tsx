'use client'

import { useState, FormEvent } from 'react'
import { DocumentUpload } from '@/components/admin/DocumentUpload'
import { DocumentList } from '@/components/admin/DocumentList'
import { useAuth } from '@/contexts/AuthContext'

export default function DocumentsPage() {
  const { userRole } = useAuth()
  const [refreshKey, setRefreshKey] = useState(0)

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1)
  }

  return (
    <div className="container mx-auto bg-background px-4 py-8 text-foreground">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Document Management</h1>
        <p className="mt-2 text-muted-foreground">Upload and manage knowledge base documents</p>
      </div>

      {userRole === 'admin' && (
        <div className="mb-8">
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />
        </div>
      )}

      <DocumentList key={refreshKey} />
    </div>
  )
}
