'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

const ADMIN_ROLES = ['admin', 'manager', 'super_admin']

export default function AdminPage() {
  const { userRole } = useAuth()
  const allowed = userRole != null && ADMIN_ROLES.includes(userRole.toLowerCase().trim())

  if (!allowed) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
          <p className="mt-2 text-gray-600">You don't have permission to access this page.</p>
          {userRole != null && (
            <p className="mt-2 text-sm text-gray-500">Your role: &quot;{userRole}&quot;</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-full">
      {/* แถบด้านบน: ปุ่มกลับไปแชท + หัวข้อ — พื้นหลังเข้ม ข้อความสีอ่อน */}
      <div className="flex flex-wrap items-center gap-4 border-b border-gray-700 bg-gray-800 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-100 transition-colors hover:bg-gray-700 hover:text-white"
        >
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          กลับไปแชท
        </Link>
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-white sm:text-xl">Admin Console</h1>
          <p className="text-sm text-gray-300">Manage system settings and content</p>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Link
          href="/admin/documents"
          className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
          <p className="mt-2 text-sm text-gray-600">Upload and manage knowledge base documents</p>
        </Link>

        <Link
          href="/admin/logs"
          className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-gray-900">Audit Logs</h2>
          <p className="mt-2 text-sm text-gray-600">View system audit logs and activity</p>
        </Link>

        <Link
          href="/admin/line"
          className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-gray-900">LINE Integration</h2>
          <p className="mt-2 text-sm text-gray-600">Manage LINE user linking and notifications</p>
        </Link>

        <Link
          href="/admin/prompt-tests"
          className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-gray-900">Prompt E2E Tests</h2>
          <p className="mt-2 text-sm text-gray-600">Manage test cases and run regression tests with embedding similarity</p>
        </Link>
      </div>
      </div>
    </div>
  )
}
