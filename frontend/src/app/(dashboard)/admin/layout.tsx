import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute requiredRole={['admin', 'manager', 'super_admin']}>
      {children}
    </ProtectedRoute>
  )
}
