'use client'

import { LineLinking } from '@/components/admin/LineLinking'

export default function LinePage() {
  return (
    <div className="container mx-auto bg-background px-4 py-8 text-foreground">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">LINE Integration</h1>
        <p className="mt-2 text-muted-foreground">
          เชื่อมต่อบัญชี LINE เพื่อถามตอบ AI ผ่าน LINE Official Account (ประวัติแชทร่วมกับเว็บ)
        </p>
      </div>

      <LineLinking />
    </div>
  )
}
