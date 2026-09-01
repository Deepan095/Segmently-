import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { useAuth } from '../hooks/useAuth';
import { useUpdateProfileMutation } from '../hooks/useAuthMutations';

export function ProfilePage() {
  const { user } = useAuth();
  const mutation = useUpdateProfileMutation();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [saved, setSaved] = useState(false);

  // ProtectedRoute guarantees an authenticated user before this renders.
  if (!user) {
    return null;
  }

  const trimmed = fullName.trim();
  const isDirty = trimmed !== (user.full_name ?? '');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaved(false);
    mutation.mutate(
      { full_name: trimmed || null },
      { onSuccess: () => setSaved(true) },
    );
  };

  return (
    <PageWrapper>
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">Profile</h1>

        <GlassCard className="bg-white/70">
          <dl className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Email</dt>
              <dd className="mt-1 text-sm text-gray-900">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Email verified
              </dt>
              <dd className="mt-1 flex items-center gap-1.5 text-sm text-gray-900">
                {user.is_verified ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    Verified
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-gray-400" />
                    Not verified
                  </>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Plan</dt>
              <dd className="mt-1 text-sm text-gray-900">Free</dd>
            </div>
          </dl>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <AnimatedInput
              label="Full name"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                setFullName(event.target.value);
                setSaved(false);
              }}
            />

            {mutation.isError && (
              <p className="text-sm text-red-500" role="alert">
                {mutation.error.message}
              </p>
            )}
            {saved && !mutation.isError && (
              <p className="text-sm text-green-600" role="status">
                Profile updated.
              </p>
            )}

            <div className="flex justify-end pt-1">
              <GradientButton
                type="submit"
                disabled={mutation.isPending || !isDirty}
                aria-busy={mutation.isPending}
              >
                {mutation.isPending ? 'Saving...' : 'Save changes'}
              </GradientButton>
            </div>
          </form>
        </GlassCard>
      </div>
    </PageWrapper>
  );
}
