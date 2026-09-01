import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import api from '../services/api';
import { AuthProvider } from '../context/AuthContext';
import { useAuth } from '../hooks/useAuth';

const mockedApi = vi.mocked(api, true);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('useAuth', () => {
  it('throws when used outside an <AuthProvider>', () => {
    expect(() => renderHook(() => useAuth())).toThrow(/AuthProvider/);
  });

  it('starts unauthenticated and finishes loading when no token is stored', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(mockedApi.get).not.toHaveBeenCalled();
  });

  it('hydrates the user from /auth/me when an access token exists', async () => {
    localStorage.setItem('access_token', 'tok');
    mockedApi.get.mockResolvedValueOnce({ data: { id: 1, email: 'me@x.com' } });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user?.email).toBe('me@x.com');
  });

  it('login stores the token pair and refreshes the user', async () => {
    mockedApi.post.mockResolvedValueOnce({
      data: { access_token: 'a-1', refresh_token: 'r-1', token_type: 'bearer' },
    });
    mockedApi.get.mockResolvedValueOnce({ data: { id: 2, email: 'user@x.com' } });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('user@x.com', 'password123');
    });

    expect(localStorage.getItem('access_token')).toBe('a-1');
    expect(localStorage.getItem('refresh_token')).toBe('r-1');
    expect(result.current.user?.email).toBe('user@x.com');
  });

  it('logout clears tokens and user', async () => {
    localStorage.setItem('access_token', 'tok');
    localStorage.setItem('refresh_token', 'r');
    mockedApi.get.mockResolvedValueOnce({ data: { id: 1, email: 'me@x.com' } });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).not.toBeNull());

    act(() => result.current.logout());

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(result.current.user).toBeNull();
  });
});
