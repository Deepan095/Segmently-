import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useRegisterMutation } from '../../hooks/useAuthMutations';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface RegisterFormProps {
  /** Called after a successful sign-up + auto sign-in. */
  onSuccess: () => void;
}

interface FieldErrors {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const mutation = useRegisterMutation();

  const validate = (): boolean => {
    const next: FieldErrors = {};
    if (!EMAIL_PATTERN.test(email)) {
      next.email = 'Enter a valid email address.';
    }
    if (password.length < 8) {
      next.password = 'Password must be at least 8 characters.';
    }
    if (confirmPassword !== password) {
      next.confirmPassword = 'Passwords do not match.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) {
      return;
    }
    mutation.mutate(
      { email, password, full_name: fullName.trim() || null },
      { onSuccess },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <AnimatedInput
        label="Full name"
        type="text"
        autoComplete="name"
        value={fullName}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setFullName(event.target.value)}
        error={errors.fullName}
      />
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
        autoComplete="new-password"
        value={password}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setPassword(event.target.value)}
        error={errors.password}
      />
      <AnimatedInput
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setConfirmPassword(event.target.value)}
        error={errors.confirmPassword}
      />
      {mutation.isError && (
        <p className="text-sm text-red-500" role="alert">
          {mutation.error.message}
        </p>
      )}
      <div className="flex justify-center pt-1">
        <GradientButton type="submit" disabled={mutation.isPending} aria-busy={mutation.isPending}>
          {mutation.isPending ? 'Creating account...' : 'Create account'}
        </GradientButton>
      </div>
    </form>
  );
}
