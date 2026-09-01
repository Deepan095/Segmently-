import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { useAuth } from '../hooks/useAuth';

const MotionLink = motion(Link);

/**
 * Landing route for the Google OAuth redirect. The backend sends the browser
 * back here with `access_token` / `refresh_token` in the URL hash. We persist
 * them, reload the user, then scrub the hash and continue to the dashboard.
 */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) {
      return;
    }
    processed.current = true;

    const rawHash = window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash;
    const params = new URLSearchParams(rawHash);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (!accessToken || !refreshToken) {
      setError('We could not complete your sign-in. Please try again.');
      return;
    }

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    window.history.replaceState(null, '', window.location.pathname);

    void refreshUser().then(() => {
      navigate('/dashboard', { replace: true });
    });
  }, [navigate, refreshUser]);

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <MeshBackground />
      <GlassCard className="w-full max-w-md bg-white/70 text-center">
        {error ? (
          <>
            <h1 className="text-xl font-bold text-gray-900">Sign-in failed</h1>
            <p className="mt-2 text-sm text-gray-600">{error}</p>
            <MotionLink
              to="/login"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.97 }}
              className="mt-4 inline-block font-semibold text-purple-600 hover:text-purple-700"
            >
              Back to sign in
            </MotionLink>
          </>
        ) : (
          <div className="flex flex-col items-center gap-3 py-4">
            <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
            <p className="text-sm text-gray-600">Completing sign-in...</p>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
