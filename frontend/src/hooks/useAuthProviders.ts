import { useQuery } from '@tanstack/react-query';
import { getAuthProviders } from '../services/authService';
import type { AuthProviders } from '../services/authService';

/**
 * Which third-party sign-in options the backend has configured. Used to hide
 * the Google button when no OAuth client is set up (otherwise it 400s).
 */
export function useAuthProviders(): AuthProviders {
  const { data } = useQuery({
    queryKey: ['auth', 'providers'],
    queryFn: getAuthProviders,
    staleTime: 5 * 60 * 1000,
  });
  return data ?? { google: false };
}
