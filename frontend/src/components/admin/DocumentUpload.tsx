'use client'

import { useState, FormEvent } from 'react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/contexts/AuthContext'

interface DocumentUploadProps {
  onUploadSuccess?: () => void
}

const CATEGORIES = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'sop', label: 'SOP' },
  { value: 'policy', label: 'นโยบาย' },
  { value: 'manual', label: 'คู่มือ' },
  { value: 'hr', label: 'HR' },
]

export function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [jobInfo, setJobInfo] = useState<string | null>(null)
  const { session } = useAuth()

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!file || !title.trim()) {
      setError('กรุณาเลือกไฟล์และใส่ชื่อเอกสาร')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(false)
    setJobInfo(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title)
      if (category) formData.append('category', category)

      const { data } = await apiClient.post<{
        document_id: string
        job_id: string
        message: string
      }>('/api/v1/ingest', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${session?.access_token}`,
        },
      })

      setSuccess(true)
      setJobInfo(`กำลังประมวลผล (document: ${data.document_id.slice(0, 8)}…)`)
      setFile(null)
      setTitle('')
      setCategory('')
      onUploadSuccess?.()

      setTimeout(() => {
        setSuccess(false)
        setJobInfo(null)
      }, 8000)
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string | object } } }
      const detail = ax.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'message' in detail) {
        setError(String((detail as { message: string }).message))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError(err instanceof Error ? err.message : 'Failed to upload document')
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-foreground">Upload Document</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-muted-foreground">
            Document Title
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="mt-1 block w-full rounded-md border border-border bg-input px-3 py-2 text-foreground shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
            placeholder="เช่น SOP การขอลา"
          />
        </div>

        <div>
          <label htmlFor="category" className="block text-sm font-medium text-muted-foreground">
            Category
          </label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 block w-full rounded-md border border-border bg-input px-3 py-2 text-foreground"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="file" className="block text-sm font-medium text-muted-foreground">
            File
          </label>
          <input
            id="file"
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            className="mt-1 block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-indigo-100 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-indigo-800 hover:file:bg-indigo-200 dark:file:bg-indigo-950/60 dark:file:text-indigo-300 dark:hover:file:bg-indigo-900/70"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            รองรับ: PDF, DOCX, TXT, MD (สูงสุด 20MB)
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4 dark:bg-red-950/50">
            <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
          </div>
        )}

        {success && (
          <div className="rounded-md bg-green-50 p-4 dark:bg-green-950/50">
            <p className="text-sm text-green-800 dark:text-green-300">
              อัปโหลดสำเร็จ — ระบบกำลังประมวลผลในพื้นหลัง
            </p>
            {jobInfo && (
              <p className="mt-1 text-xs text-green-700 dark:text-green-400">{jobInfo}</p>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={uploading || !file || !title.trim()}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
      </form>
    </div>
  )
}
