import { Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AppShell } from '../components/layout/AppShell';
import { DashboardPage } from './DashboardPage';
import { SettingsPage } from './SettingsPage';

/**
 * Analytics Dashboard module (Module 4) route table. The orchestrator spreads
 * this fragment inside the app's top-level <Routes> element:
 *
 *   <Routes>
 *     {authRoutes}
 *     {dashboardRoutes}
 *     ...other module routes
 *   </Routes>
 */
export const dashboardRoutes = (
  <>
    <Route
      path="/dashboard"
      element={
        <ProtectedRoute>
          <AppShell>
            <DashboardPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
    <Route
      path="/settings"
      element={
        <ProtectedRoute>
          <AppShell>
            <SettingsPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
  </>
);
