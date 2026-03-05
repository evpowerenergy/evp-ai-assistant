'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import apiClient from '@/lib/api/client'

interface TestCase {
  id: string
  user_message: string
  expected_intent: string | null
  expected_tool: string | null
  expected_message: string | null
  similarity_threshold: number
  notes: string | null
  created_at: string
}

interface TestResult {
  test_case_id: string
  user_message: string
  expected_intent: string | null
  expected_tool: string | null
  actual_intent: string | null
  actual_tool: string | null
  ai_message: string
  expected_message: string
  similarity_score: number | null
  pass_fail: 'pass' | 'fail' | null
}

interface RunSummary {
  id: string
  run_at: string
  total: number
  passed: number
  failed: number
}

function getAuthHeaders(session: { access_token: string } | null) {
  return session ? { Authorization: `Bearer ${session.access_token}` } : {}
}

const EXPECTED_INTENT_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '— ไม่ระบุ —' },
  { value: 'db_query', label: 'db_query (ถามข้อมูลจากระบบ)' },
  { value: 'rag_query', label: 'rag_query (ถามจาก knowledge base)' },
  { value: 'general', label: 'general (คำถามทั่วไป)' },
  { value: 'clarify', label: 'clarify (ขอคำชี้แจง)' },
]

const EXPECTED_TOOL_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '— ไม่ระบุ —' },
  { value: 'search_leads', label: 'search_leads' },
  { value: 'get_sales_closed', label: 'get_sales_closed' },
  { value: 'get_daily_summary', label: 'get_daily_summary' },
  { value: 'get_lead_status', label: 'get_lead_status' },
  { value: 'get_team_kpi', label: 'get_team_kpi' },
  { value: 'get_appointments', label: 'get_appointments' },
  { value: 'get_customer_info', label: 'get_customer_info' },
  { value: 'get_sales_team', label: 'get_sales_team' },
  { value: 'get_sales_team_list', label: 'get_sales_team_list' },
  { value: 'get_lead_detail', label: 'get_lead_detail' },
  { value: 'get_my_leads', label: 'get_my_leads' },
  { value: 'get_quotations', label: 'get_quotations' },
  { value: 'get_sales_docs', label: 'get_sales_docs' },
  { value: 'get_permit_requests', label: 'get_permit_requests' },
]

export default function PromptTestsPage() {
  const { session, userRole } = useAuth()
  const [cases, setCases] = useState<TestCase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    user_message: '',
    expected_intent: '',
    expected_tool: '',
    expected_message: '',
    similarity_threshold: 0.7,
    notes: '',
  })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<{ run_id: string; total: number; passed: number; failed: number; results: TestResult[] } | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [activeTab, setActiveTab] = useState<'cases' | 'run' | 'history'>('cases')
  const [loadingLatestRun, setLoadingLatestRun] = useState(false)

  const loadCases = useCallback(async () => {
    if (!session) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get<{ success: boolean; data: TestCase[] }>(
        '/api/v1/prompt-tests/cases',
        { headers: getAuthHeaders(session) }
      )
      setCases(data.data || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load test cases')
    } finally {
      setLoading(false)
    }
  }, [session])

  const loadRuns = useCallback(async () => {
    if (!session) return
    try {
      const { data } = await apiClient.get<{ success: boolean; data: RunSummary[] }>(
        '/api/v1/prompt-tests/runs?limit=20',
        { headers: getAuthHeaders(session) }
      )
      setRuns(data.data || [])
    } catch (e) {
      console.error('Failed to load runs', e)
    }
  }, [session])

  useEffect(() => {
    if (session) {
      loadCases()
      loadRuns()
    }
  }, [session, loadCases, loadRuns])

  // โหลดผลลัพธ์รันล่าสุดอัตโนมัติเมื่อมี runs แล้ว (เมื่อเข้าหน้านี้)
  useEffect(() => {
    if (!session || runs.length === 0 || runResult !== null) return
    let cancelled = false
    setLoadingLatestRun(true)
    const latestId = runs[0].id
    apiClient
      .get<{ success: boolean; run: RunSummary; results: TestResult[] }>(
        `/api/v1/prompt-tests/runs/${latestId}`,
        { headers: getAuthHeaders(session) }
      )
      .then(({ data }) => {
        if (!cancelled) {
          setRunResult({
            run_id: data.run.id,
            total: data.run.total,
            passed: data.run.passed,
            failed: data.run.failed,
            results: data.results || [],
          })
        }
      })
      .catch(() => { if (!cancelled) setError('โหลดผลลัพธ์ล่าสุดไม่สำเร็จ') })
      .finally(() => { if (!cancelled) setLoadingLatestRun(false) })
    return () => { cancelled = true }
  }, [session, runs, runResult])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!session || !form.user_message.trim()) return
    setError(null)
    try {
      if (editingId) {
        await apiClient.patch(
          `/api/v1/prompt-tests/cases/${editingId}`,
          {
            user_message: form.user_message,
            expected_intent: form.expected_intent || null,
            expected_tool: form.expected_tool || null,
            expected_message: form.expected_message || null,
            similarity_threshold: form.similarity_threshold,
            notes: form.notes || null,
          },
          { headers: getAuthHeaders(session) }
        )
        setEditingId(null)
      } else {
        await apiClient.post(
          '/api/v1/prompt-tests/cases',
          {
            user_message: form.user_message,
            expected_intent: form.expected_intent || null,
            expected_tool: form.expected_tool || null,
            expected_message: form.expected_message || null,
            similarity_threshold: form.similarity_threshold,
            notes: form.notes || null,
          },
          { headers: getAuthHeaders(session) }
        )
      }
      setForm({ user_message: '', expected_intent: '', expected_tool: '', expected_message: '', similarity_threshold: 0.7, notes: '' })
      loadCases()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    }
  }

  const handleEdit = (tc: TestCase) => {
    setEditingId(tc.id)
    setForm({
      user_message: tc.user_message,
      expected_intent: tc.expected_intent || '',
      expected_tool: tc.expected_tool || '',
      expected_message: tc.expected_message || '',
      similarity_threshold: tc.similarity_threshold ?? 0.7,
      notes: tc.notes || '',
    })
  }

  const handleDelete = async (id: string) => {
    if (!session || !confirm('ลบ test case นี้?')) return
    try {
      await apiClient.delete(`/api/v1/prompt-tests/cases/${id}`, { headers: getAuthHeaders(session) })
      loadCases()
      if (editingId === id) {
        setEditingId(null)
        setForm({ user_message: '', expected_intent: '', expected_tool: '', expected_message: '', similarity_threshold: 0.7, notes: '' })
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete')
    }
  }

  const handleRunTests = async () => {
    if (!session || cases.length === 0) return
    setError(null)
    setRunning(true)
    // แสดง input (ที่ user กรอก) ทันที จาก cases — โหลดเฉพาะ output จาก AI
    const skeletonResults: TestResult[] = cases.map((tc) => ({
      test_case_id: tc.id,
      user_message: tc.user_message,
      expected_intent: tc.expected_intent ?? null,
      expected_tool: tc.expected_tool ?? null,
      actual_intent: null,
      actual_tool: null,
      ai_message: '',
      expected_message: tc.expected_message ?? '',
      similarity_score: null,
      pass_fail: null,
    }))
    setRunResult({
      run_id: '',
      total: cases.length,
      passed: 0,
      failed: 0,
      results: skeletonResults,
    })
    setActiveTab('run')
    try {
      const startRes = await apiClient.post<{ success: boolean; run_id: string; total: number }>(
        '/api/v1/prompt-tests/run/start',
        { test_case_ids: null },
        { headers: getAuthHeaders(session) }
      )
      const runId = startRes.data.run_id
      setRunResult((prev) => (prev ? { ...prev, run_id: runId } : null))
      let passed = 0
      let failed = 0
      for (let i = 0; i < cases.length; i++) {
        const tc = cases[i]
        const oneRes = await apiClient.post<{
          success: boolean
          result: TestResult
          passed: number
          failed: number
        }>(
          '/api/v1/prompt-tests/run/one',
          { run_id: runId, test_case_id: tc.id },
          { headers: getAuthHeaders(session) }
        )
        passed = oneRes.data.passed
        failed = oneRes.data.failed
        setRunResult((prev) => {
          if (!prev) return null
          const next = [...prev.results]
          next[i] = oneRes.data.result
          return { ...prev, results: next, passed, failed }
        })
      }
      loadRuns()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  const loadRunDetail = async (runId: string) => {
    if (!session) return
    try {
      const { data } = await apiClient.get<{ success: boolean; run: RunSummary; results: TestResult[] }>(
        `/api/v1/prompt-tests/runs/${runId}`,
        { headers: getAuthHeaders(session) }
      )
      setRunResult({
        run_id: data.run.id,
        total: data.run.total,
        passed: data.run.passed,
        failed: data.run.failed,
        results: data.results || [],
      })
      setActiveTab('run')
    } catch (e) {
      setError('Failed to load run details')
    }
  }

  const allowedRoles = ['admin', 'manager', 'super_admin']
  const roleOk = !userRole || allowedRoles.includes(userRole.toLowerCase().trim())
  if (!roleOk) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
          <p className="mt-2 text-gray-600">You need admin/manager/super_admin role to access this page.</p>
          <p className="mt-2 text-sm text-gray-500">Your role: &quot;{userRole}&quot;</p>
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
          <h1 className="text-lg font-semibold text-white sm:text-xl">Prompt E2E Tests</h1>
          <p className="text-sm text-gray-300">Manage test cases and run regression tests with embedding similarity</p>
        </div>
      </div>

      <div className="px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-end gap-4">
        <button
          onClick={handleRunTests}
          disabled={running || cases.length === 0}
          className="min-h-[2.5rem] rounded-lg bg-indigo-600 px-4 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {running ? 'กำลังรัน...' : `Run All Tests (${cases.length})`}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium leading-relaxed text-red-900">
          {error}
        </div>
      )}

      <div className="mb-6 flex gap-1 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('cases')}
          className={`border-b-2 px-4 py-3 text-sm font-medium ${activeTab === 'cases' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
        >
          Test Cases
        </button>
        <button
          onClick={() => setActiveTab('run')}
          className={`border-b-2 px-4 py-3 text-sm font-medium ${activeTab === 'run' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
        >
          ผลลัพธ์ล่าสุด
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`border-b-2 px-4 py-3 text-sm font-medium ${activeTab === 'history' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
        >
          Run History
        </button>
      </div>

      {activeTab === 'cases' && (
        <>
          <form onSubmit={handleSubmit} className="mb-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-6 text-lg font-semibold text-gray-900">
              {editingId ? 'แก้ไข Test Case' : 'เพิ่ม Test Case'}
            </h2>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-800">User Message *</label>
                <textarea
                  value={form.user_message}
                  onChange={(e) => setForm((f) => ({ ...f, user_message: e.target.value }))}
                  rows={3}
                  className="min-h-[4.5rem] w-full resize-y rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="เดือนที่แล้วปิดการขายได้กี่ราย"
                  required
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-800">Expected Intent</label>
                <select
                  value={form.expected_intent}
                  onChange={(e) => setForm((f) => ({ ...f, expected_intent: e.target.value }))}
                  className="min-h-[2.5rem] w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {EXPECTED_INTENT_OPTIONS.map((opt) => (
                    <option key={opt.value || 'empty'} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-800">Expected Tool</label>
                <select
                  value={form.expected_tool}
                  onChange={(e) => setForm((f) => ({ ...f, expected_tool: e.target.value }))}
                  className="min-h-[2.5rem] w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {EXPECTED_TOOL_OPTIONS.map((opt) => (
                    <option key={opt.value || 'empty'} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-medium text-gray-800">Expected Message (อ้างอิงเท่านั้น — ไม่ใช้ตัด Pass/Fail)</label>
                <textarea
                  value={form.expected_message}
                  onChange={(e) => setForm((f) => ({ ...f, expected_message: e.target.value }))}
                  rows={4}
                  className="min-h-[6rem] w-full resize-y rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="ข้อความตัวอย่างที่คาดหวัง หรือสรุปหลักๆ ที่ต้องมี"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-800">Similarity Threshold (0–1)</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={form.similarity_threshold}
                  onChange={(e) => setForm((f) => ({ ...f, similarity_threshold: parseFloat(e.target.value) || 0.7 }))}
                  className="min-h-[2.5rem] w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-800">Notes</label>
                <input
                  type="text"
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  className="min-h-[2.5rem] w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm leading-normal text-gray-900 placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
            <div className="mt-6 flex gap-2">
              <button type="submit" className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                {editingId ? 'บันทึก' : 'เพิ่ม'}
              </button>
              {editingId && (
                <button type="button" onClick={() => { setEditingId(null); setForm({ user_message: '', expected_intent: '', expected_tool: '', expected_message: '', similarity_threshold: 0.7, notes: '' }); }} className="rounded border border-gray-400 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100">
                  ยกเลิก
                </button>
              )}
            </div>
          </form>

          <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-lg font-semibold leading-snug text-gray-900">Test Cases ({cases.length})</h2>
            </div>
            {loading ? (
              <div className="px-6 py-12 text-center text-sm leading-relaxed text-gray-600">Loading...</div>
            ) : cases.length === 0 ? (
              <div className="px-6 py-12 text-center text-sm leading-relaxed text-gray-600">ยังไม่มี test case</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">User Message</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected Intent</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected Tool</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected Message</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Similarity</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {cases.map((tc) => (
                      <tr key={tc.id} className="hover:bg-gray-50">
                        <td className="min-w-[12rem] max-w-none align-top px-4 py-3 text-sm leading-relaxed text-gray-900">
                          <span className="block break-words whitespace-pre-wrap">{tc.user_message}</span>
                        </td>
                        <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">{tc.expected_intent || '-'}</td>
                        <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">{tc.expected_tool || '-'}</td>
                        <td className="min-w-[12rem] max-w-none align-top px-4 py-3 text-sm leading-relaxed text-gray-900">
                          <span className="block break-words whitespace-pre-wrap">{tc.expected_message || '-'}</span>
                        </td>
                        <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">{tc.similarity_threshold ?? 0.7}</td>
                        <td className="whitespace-nowrap align-top px-4 py-3">
                          <button onClick={() => handleEdit(tc)} className="mr-2 text-sm text-indigo-600 hover:underline">Edit</button>
                          <button onClick={() => handleDelete(tc.id)} className="text-sm text-red-600 hover:underline">Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === 'run' && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          {runResult ? (
            <>
              <div className="border-b border-gray-200 px-6 py-4">
                <h2 className="text-lg font-semibold leading-snug text-gray-900">ผลลัพธ์ Run</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-800">
                  {running ? (
                    <span className="text-gray-600">กำลังรัน... (ผล Pass/Fail จะอัปเดตเมื่อเสร็จ)</span>
                  ) : (
                    <>Pass: <span className="font-medium text-green-700">{runResult.passed}</span> / Fail: <span className="font-medium text-red-700">{runResult.failed}</span> / Total: <span className="font-medium text-gray-900">{runResult.total}</span></>
                  )}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-gray-500">
                  Dynamic: Pass = ไม่ error + Intent ตรง (ถ้าระบุ) + Tool ตรง (ถ้าระบุ) — คอลัมน์ Expected / Score เป็นข้อมูลอ้างอิงเท่านั้น ไม่ใช้ตัด Pass/Fail
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">User Message</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Intent (จาก agent)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected Intent</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Tool (จาก agent)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected Tool</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">AI Message</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Expected (อ้างอิง)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Score (อ้างอิง)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-700">Pass/Fail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {runResult.results.map((r, i) => {
                      const isOutputLoading = r.pass_fail === null
                      const intentMatch = !r.expected_intent || (r.actual_intent || '').toLowerCase() === (r.expected_intent || '').toLowerCase()
                      const toolMatch = !r.expected_tool || (r.actual_tool || '').toLowerCase() === (r.expected_tool || '').toLowerCase()
                      return (
                        <tr key={i} className={r.pass_fail === 'fail' ? 'bg-red-50' : ''}>
                          <td className="min-w-[12rem] max-w-none px-4 py-3 text-sm leading-relaxed text-gray-900 align-top">
                            <span className="block break-words whitespace-pre-wrap">{r.user_message}</span>
                          </td>
                          <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">
                            {isOutputLoading ? <span className="text-gray-500 italic">กำลังรัน...</span> : (r.actual_intent || '-')}
                          </td>
                          <td className={`align-top px-4 py-3 text-sm leading-relaxed ${isOutputLoading ? 'text-gray-800' : (intentMatch ? 'text-gray-800' : 'text-amber-700')}`}>
                            {r.expected_intent || '-'}
                            {r.expected_intent && !isOutputLoading && !intentMatch && <span className="ml-1 text-amber-600" title="ไม่ตรงกับ agent">≠</span>}
                          </td>
                          <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">
                            {isOutputLoading ? <span className="text-gray-500 italic">กำลังรัน...</span> : (r.actual_tool || '-')}
                          </td>
                          <td className={`align-top px-4 py-3 text-sm leading-relaxed ${isOutputLoading ? 'text-gray-800' : (toolMatch ? 'text-gray-800' : 'text-amber-700')}`}>
                            {r.expected_tool || '-'}
                            {r.expected_tool && !isOutputLoading && !toolMatch && <span className="ml-1 text-amber-600" title="ไม่ตรงกับ agent">≠</span>}
                          </td>
                          <td className="min-w-[12rem] max-w-none px-4 py-3 text-sm leading-relaxed text-gray-900 align-top">
                            {isOutputLoading ? <span className="text-gray-500 italic">กำลังรัน...</span> : <span className="block break-words whitespace-pre-wrap">{r.ai_message || '-'}</span>}
                          </td>
                          <td className="min-w-[12rem] max-w-none px-4 py-3 text-sm leading-relaxed text-gray-900 align-top">
                            <span className="block break-words whitespace-pre-wrap">{r.expected_message || '-'}</span>
                          </td>
                          <td className="align-top px-4 py-3 text-sm leading-relaxed text-gray-800">
                            {isOutputLoading ? <span className="text-gray-500 italic">กำลังรัน...</span> : (r.similarity_score != null ? r.similarity_score.toFixed(4) : '-')}
                          </td>
                          <td className="align-top px-4 py-3">
                            {isOutputLoading ? (
                              <span className="text-gray-500 italic">กำลังรัน...</span>
                            ) : (
                              <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${r.pass_fail === 'pass' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {r.pass_fail}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : loadingLatestRun ? (
            <div className="px-6 py-12 text-center text-sm leading-relaxed text-gray-600">กำลังโหลดผลลัพธ์ล่าสุด...</div>
          ) : (
            <div className="px-6 py-12 text-center text-sm leading-relaxed text-gray-600">ยังไม่มีผลการรัน — กด Run All Tests หรือเลือกจาก Run History</div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-semibold leading-snug text-gray-900">Run History</h2>
          </div>
          {runs.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm leading-relaxed text-gray-600">ยังไม่มี run</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {runs.map((r) => (
                <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-6 py-3 hover:bg-gray-50">
                  <div className="min-w-0 text-sm leading-relaxed">
                    <span className="font-medium text-gray-900">{new Date(r.run_at).toLocaleString('th-TH')}</span>
                    <span className="ml-3 text-gray-700">Total: {r.total} | Pass: {r.passed} | Fail: {r.failed}</span>
                  </div>
                  <button onClick={() => loadRunDetail(r.id)} className="shrink-0 text-sm text-indigo-600 hover:underline">
                    ดูผล
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  )
}
