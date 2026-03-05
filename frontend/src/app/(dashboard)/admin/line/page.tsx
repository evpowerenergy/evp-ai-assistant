'use client'

import { LineLinking } from '@/components/admin/LineLinking'

export default function LinePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">LINE Integration</h1>
        <p className="mt-2 text-gray-600">Manage LINE user linking and notifications</p>
      </div>

      <LineLinking />
    </div>
  )
}
