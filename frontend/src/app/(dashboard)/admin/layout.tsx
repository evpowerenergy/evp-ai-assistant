import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AI_ASSISTANT_ALLOWED_ROLES } from '@/lib/aiAssistantAccess'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute requiredRole={[...AI_ASSISTANT_ALLOWED_ROLES]}>
      {children}
    </ProtectedRoute>
  )
}
