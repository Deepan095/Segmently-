import { Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AppShell } from '../components/layout/AppShell';
import { ProjectsListPage } from './ProjectsListPage';
import { NewProjectPage } from './NewProjectPage';
import { ProjectDetailPage } from './ProjectDetailPage';

/**
 * Projects / Uploads module route table. The orchestrator spreads this fragment
 * inside the app's top-level <Routes> element:
 *
 *   <Routes>
 *     {authRoutes}
 *     {projectRoutes}
 *     ...other module routes
 *   </Routes>
 */
export const projectRoutes = (
  <>
    <Route
      path="/projects"
      element={
        <ProtectedRoute>
          <AppShell>
            <ProjectsListPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
    <Route
      path="/projects/new"
      element={
        <ProtectedRoute>
          <AppShell>
            <NewProjectPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
    <Route
      path="/projects/:id"
      element={
        <ProtectedRoute>
          <AppShell>
            <ProjectDetailPage />
          </AppShell>
        </ProtectedRoute>
      }
    />
  </>
);
