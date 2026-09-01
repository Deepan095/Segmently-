import { motion } from 'framer-motion';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { RegisterForm } from '../components/auth/RegisterForm';
import { GoogleLoginButton } from '../components/auth/GoogleLoginButton';
import { useAuth } from '../hooks/useAuth';

const MotionLink = motion(Link);

export function RegisterPage() {
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
          <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
          <p className="mt-1 text-sm text-gray-600">Start turning long videos into short clips</p>
        </div>

        <RegisterForm onSuccess={() => navigate('/dashboard')} />

        <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-wide text-gray-400">
          <span className="h-px flex-1 bg-gray-200" />
          <span>or</span>
          <span className="h-px flex-1 bg-gray-200" />
        </div>

        <GoogleLoginButton label="Sign up with Google" />

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <MotionLink
            to="/login"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="inline-block font-semibold text-purple-600 hover:text-purple-700"
          >
            Sign in
          </MotionLink>
        </p>
      </GlassCard>
    </div>
  );
}
