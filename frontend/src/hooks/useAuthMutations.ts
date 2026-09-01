import { useMutation } from '@tanstack/react-query';
import type { UseMutationResult } from '@tanstack/react-query';
import { useAuth } from './useAuth';
import {
  extractApiError,
  register as registerRequest,
  updateProfile as updateProfileRequest,
} from '../services/authService';
import type { RegisterPayload, UpdateProfilePayload } from '../services/authService';
import type { User } from '../types';

export interface LoginVariables {
  email: string;
  password: string;
}

/**
 * Sign in with email + password. Delegates to the shared AuthContext so the
 * user state and stored tokens stay in sync across the app.
 */
export function useLoginMutation(): UseMutationResult<void, Error, LoginVariables> {
  const { login } = useAuth();
  return useMutation<void, Error, LoginVariables>({
    mutationFn: async ({ email, password }) => {
      try {
        await login(email, password);
      } catch (error) {
        throw new Error(extractApiError(error, 'Invalid email or password.'));
      }
    },
  });
}

/**
 * Register a new account, then immediately sign the user in with the same
 * credentials so they land in an authenticated session.
 */
export function useRegisterMutation(): UseMutationResult<void, Error, RegisterPayload> {
  const { login } = useAuth();
  return useMutation<void, Error, RegisterPayload>({
    mutationFn: async (payload) => {
      try {
        await registerRequest(payload);
        await login(payload.email, payload.password);
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not create your account.'));
      }
    },
  });
}

/** Update the current user's profile and refresh the cached user. */
export function useUpdateProfileMutation(): UseMutationResult<User, Error, UpdateProfilePayload> {
  const { refreshUser } = useAuth();
  return useMutation<User, Error, UpdateProfilePayload>({
    mutationFn: async (payload) => {
      try {
        const updated = await updateProfileRequest(payload);
        await refreshUser();
        return updated;
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not update your profile.'));
      }
    },
  });
}
