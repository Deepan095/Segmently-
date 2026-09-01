import { Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AppShell } from '../components/layout/AppShell';
import { ClipsLibraryPage } from './ClipsLibraryPage';
import { ClipDetailPage } from './ClipDetailPage';

/**
 * Clips module route table. The orchestrator spreads this fragment inside the
 * app's top-level <Routes> element:
 *
 *   <Routes>
 *     {authRoutes}
 *     {clipRoutes}
 *     ...other module routes
 *   </Routes>
 */
export const clipRoutes = (
  <>
    <Route
      path="/clips"
      element={
        <ProtectedRoute>
          <AppShell>
            <ClipsLibraryPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
    <Route
      path="/clips/:id"
      element={
        <ProtectedRoute>
          <AppShell>
            <ClipDetailPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
  </>
);
