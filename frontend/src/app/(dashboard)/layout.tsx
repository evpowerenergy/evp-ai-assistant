import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { AI_ASSISTANT_ALLOWED_ROLES } from '@/lib/aiAssistantAccess'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ErrorBoundary>
      <ProtectedRoute requiredRole={[...AI_ASSISTANT_ALLOWED_ROLES]}>{children}</ProtectedRoute>
    </ErrorBoundary>
  )
}
