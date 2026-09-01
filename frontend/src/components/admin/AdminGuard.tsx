import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

/**
 * Gate that only renders its children for an authenticated admin.
 *
 * Assumes it is nested inside <ProtectedRoute>, which already handles the
 * unauthenticated + still-loading cases. A signed-in non-admin is bounced to
 * the dashboard rather than shown a 403.
 */
export function AdminGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="p-6 text-sm text-gray-500">Loading...</div>;
  }

  if (!user || !user.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
