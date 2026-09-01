import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { authRoutes } from './pages/authRoutes';
import { projectRoutes } from './pages/projectRoutes';
import { clipRoutes } from './pages/clipRoutes';
import { dashboardRoutes } from './pages/dashboardRoutes';
import { adminRoutes } from './pages/adminRoutes';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Root component. Each feature module owns its own route table
 * (`src/pages/*Routes.tsx`); this file only assembles them and provides
 * the query client + auth context.
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />

            {authRoutes}
            {dashboardRoutes}
            {projectRoutes}
            {clipRoutes}
            {adminRoutes}

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
