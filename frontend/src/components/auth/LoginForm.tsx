import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useLoginMutation } from '../../hooks/useAuthMutations';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface LoginFormProps {
  /** Called after a successful sign-in (e.g. to navigate to the dashboard). */
  onSuccess: () => void;
}

interface FieldErrors {
  email?: string;
  password?: string;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const mutation = useLoginMutation();

  const validate = (): boolean => {
    const next: FieldErrors = {};
    if (!EMAIL_PATTERN.test(email)) {
      next.email = 'Enter a valid email address.';
    }
    if (password.length < 8) {
      next.password = 'Password must be at least 8 characters.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) {
      return;
    }
    mutation.mutate({ email, password }, { onSuccess });
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <AnimatedInput
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setEmail(event.target.value)}
        error={errors.email}
      />
      <AnimatedInput
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setPassword(event.target.value)}
        error={errors.password}
      />
      {mutation.isError && (
        <p className="text-sm text-red-500" role="alert">
          {mutation.error.message}
        </p>
      )}
      <div className="flex justify-center pt-1">
        <GradientButton type="submit" disabled={mutation.isPending} aria-busy={mutation.isPending}>
          {mutation.isPending ? 'Signing in...' : 'Sign in'}
        </GradientButton>
      </div>
    </form>
  );
}
