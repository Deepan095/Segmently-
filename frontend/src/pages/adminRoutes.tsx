import type { ReactNode } from 'react';
import { Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AdminGuard } from '../components/admin/AdminGuard';
import { AppShell } from '../components/layout/AppShell';
import { AdminDashboardPage } from './AdminDashboardPage';
import { AdminUsersPage } from './AdminUsersPage';
import { AdminJobsPage } from './AdminJobsPage';

/**
 * Admin module route table (Module 5). The orchestrator spreads this fragment
 * inside the app's top-level <Routes> element:
 *
 *   <Routes>
 *     {authRoutes}
 *     {adminRoutes}
 *     ...other module routes
 *   </Routes>
 *
 * Every admin route is: ProtectedRoute (must be signed in) -> AdminGuard
 * (must be is_admin, else <Navigate to="/dashboard">) -> AppShell -> page.
 */
function AdminRoute({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AdminGuard>
        <AppShell>{children}</AppShell>
      </AdminGuard>
    </ProtectedRoute>
  );
}

export const adminRoutes = (
  <>
    <Route path="/admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
    <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
    <Route path="/admin/jobs" element={<AdminRoute><AdminJobsPage /></AdminRoute>} />
  </>
);
