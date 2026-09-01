import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CONFIRMATION =
  'If an account exists for that address, a password reset link has been sent.';

const MotionLink = motion(Link);

/**
 * UI-only password reset request. The backend email flow is post-MVP, so this
 * always shows the same neutral confirmation and never reveals whether the
 * address is registered.
 */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!EMAIL_PATTERN.test(email)) {
      setError('Enter a valid email address.');
      return;
    }
    setError(undefined);
    setSubmitted(true);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <MeshBackground />
      <GlassCard className="w-full max-w-md bg-white/70">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Reset your password</h1>
          <p className="mt-1 text-sm text-gray-600">
            Enter your email and we&apos;ll send you a reset link
          </p>
        </div>

        {submitted ? (
          <p className="rounded-xl bg-purple-50 px-4 py-3 text-sm text-purple-800" role="status">
            {CONFIRMATION}
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <AnimatedInput
              label="Email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setEmail(event.target.value)}
              error={error}
            />
            <div className="flex justify-center pt-1">
              <GradientButton type="submit">Send reset link</GradientButton>
            </div>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-gray-600">
          Remembered it?{' '}
          <MotionLink
            to="/login"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="inline-block font-semibold text-purple-600 hover:text-purple-700"
          >
            Back to sign in
          </MotionLink>
        </p>
      </GlassCard>
    </div>
  );
}
