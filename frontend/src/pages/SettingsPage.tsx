import { useState } from 'react';
import type { ChangeEvent, FormEvent, ReactNode } from 'react';
import { Bell, CheckCircle2, CreditCard, XCircle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { useAuth } from '../hooks/useAuth';
import { useUpdateProfileMutation } from '../hooks/useAuthMutations';

interface ComingSoonProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function ComingSoonSection({ icon, title, description }: ComingSoonProps) {
  return (
    <GlassCard className="bg-white/60">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-purple-400">{icon}</span>
          <div>
            <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
            <p className="mt-0.5 text-sm text-gray-500">{description}</p>
          </div>
        </div>
        <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
          Coming soon
        </span>
      </div>
    </GlassCard>
  );
}

export function SettingsPage() {
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
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

        <GlassCard className="bg-white/70">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">Profile</h2>

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
                    <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" />
                    Verified
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-gray-400" aria-hidden="true" />
                    Not verified
                  </>
                )}
              </dd>
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
                Settings saved.
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

        <ComingSoonSection
          icon={<Bell className="h-5 w-5" aria-hidden="true" />}
          title="Notifications"
          description="Email and in-app alerts when your clips finish rendering."
        />
        <ComingSoonSection
          icon={<CreditCard className="h-5 w-5" aria-hidden="true" />}
          title="Billing"
          description="Plans, usage limits, and invoices."
        />
      </div>
    </PageWrapper>
  );
}
