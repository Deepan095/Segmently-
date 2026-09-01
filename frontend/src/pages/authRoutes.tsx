import { Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AppShell } from '../components/layout/AppShell';
import { LoginPage } from './LoginPage';
import { RegisterPage } from './RegisterPage';
import { ForgotPasswordPage } from './ForgotPasswordPage';
import { AuthCallbackPage } from './AuthCallbackPage';
import { ProfilePage } from './ProfilePage';

/**
 * Auth module route table. The orchestrator spreads this fragment inside the
 * app's top-level <Routes> element:
 *
 *   <Routes>
 *     {authRoutes}
 *     ...other module routes
 *   </Routes>
 */
export const authRoutes = (
  <>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/auth/callback" element={<AuthCallbackPage />} />
    <Route
      path="/profile"
      element={
        <ProtectedRoute>
          <AppShell>
            <ProfilePage />
          </AppShell>
        </ProtectedRoute>
      }
    />
  </>
);
