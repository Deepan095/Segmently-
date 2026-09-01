import { motion } from 'framer-motion';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { LoginForm } from '../components/auth/LoginForm';
import { GoogleLoginButton } from '../components/auth/GoogleLoginButton';
import { useAuth } from '../hooks/useAuth';

const MotionLink = motion(Link);

export function LoginPage() {
  const navigate = useNavigate();
  const { user, isLoading } = useAuth();

  if (!isLoading && user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <MeshBackground />
      <GlassCard className="w-full max-w-md bg-white/70">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="mt-1 text-sm text-gray-600">Sign in to your Segmently account</p>
        </div>

        <LoginForm onSuccess={() => navigate('/dashboard')} />

        <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-wide text-gray-400">
          <span className="h-px flex-1 bg-gray-200" />
          <span>or</span>
          <span className="h-px flex-1 bg-gray-200" />
        </div>

        <GoogleLoginButton />

        <div className="mt-6 flex flex-col items-center gap-2 text-sm text-gray-600">
          <MotionLink
            to="/forgot-password"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="text-gray-500 hover:text-purple-600"
          >
            Forgot your password?
          </MotionLink>
          <span>
            New to Segmently?{' '}
            <MotionLink
              to="/register"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.97 }}
              className="inline-block font-semibold text-purple-600 hover:text-purple-700"
            >
              Create an account
            </MotionLink>
          </span>
        </div>
      </GlassCard>
    </div>
  );
}
