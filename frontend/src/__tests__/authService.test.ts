import { AxiosError } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import api from '../services/api';
import {
  extractApiError,
  getMe,
  googleLoginUrl,
  login,
  logout,
  register,
  updateProfile,
} from '../services/authService';

const mockedApi = vi.mocked(api, true);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe('register', () => {
  it('POSTs to /auth/register and returns the created user', async () => {
    mockedApi.post.mockResolvedValueOnce({ data: { id: 1, email: 'a@b.com' } });
    const user = await register({ email: 'a@b.com', password: 'password123' });
    expect(mockedApi.post).toHaveBeenCalledWith('/auth/register', {
      email: 'a@b.com',
      password: 'password123',
    });
    expect(user.email).toBe('a@b.com');
  });
});

describe('login', () => {
  it('sends a url-encoded username/password form', async () => {
    mockedApi.post.mockResolvedValueOnce({
      data: { access_token: 'a', refresh_token: 'r', token_type: 'bearer' },
    });
    const tokens = await login({ email: 'a@b.com', password: 'password123' });

    const [url, body] = mockedApi.post.mock.calls[0];
    expect(url).toBe('/auth/login');
    expect(body).toBeInstanceOf(URLSearchParams);
    expect((body as URLSearchParams).get('username')).toBe('a@b.com');
    expect((body as URLSearchParams).get('password')).toBe('password123');
    expect(tokens.access_token).toBe('a');
  });
});

describe('logout', () => {
  it('is a no-op when there is no stored refresh token', async () => {
    await logout();
    expect(mockedApi.post).not.toHaveBeenCalled();
  });

  it('revokes the stored refresh token and swallows errors', async () => {
    localStorage.setItem('refresh_token', 'r-1');
    mockedApi.post.mockRejectedValueOnce(new Error('network'));
    await expect(logout()).resolves.toBeUndefined();
    expect(mockedApi.post).toHaveBeenCalledWith('/auth/logout', { refresh_token: 'r-1' });
  });
});

describe('getMe / updateProfile', () => {
  it('getMe reads /auth/me', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: { id: 7, email: 'me@x.com' } });
    expect((await getMe()).id).toBe(7);
    expect(mockedApi.get).toHaveBeenCalledWith('/auth/me');
  });

  it('updateProfile PUTs /auth/me', async () => {
    mockedApi.put.mockResolvedValueOnce({ data: { id: 7, full_name: 'New' } });
    const user = await updateProfile({ full_name: 'New' });
    expect(mockedApi.put).toHaveBeenCalledWith('/auth/me', { full_name: 'New' });
    expect(user.full_name).toBe('New');
  });
});

describe('extractApiError', () => {
  const makeAxiosError = (data: unknown): AxiosError => {
    const err = new AxiosError('Request failed');
    // @ts-expect-error partial response is enough for the extractor
    err.response = { data };
    return err;
  };

  it('prefers the { message } field from the app error body', () => {
    expect(extractApiError(makeAxiosError({ code: 'CONFLICT', message: 'Email taken' }))).toBe(
      'Email taken',
    );
  });

  it('falls back to a string detail', () => {
    expect(extractApiError(makeAxiosError({ detail: 'Nope' }))).toBe('Nope');
  });

  it('reads the first item of a FastAPI validation detail array', () => {
    expect(extractApiError(makeAxiosError({ detail: [{ msg: 'field required' }] }))).toBe(
      'field required',
    );
  });

  it('uses the provided fallback for unknown errors', () => {
    expect(extractApiError({}, 'fallback msg')).toBe('fallback msg');
  });

  it('reads a plain Error message', () => {
    expect(extractApiError(new Error('boom'))).toBe('boom');
  });
});

describe('googleLoginUrl', () => {
  it('points at the backend google login endpoint', () => {
    expect(googleLoginUrl()).toContain('/api/v1/auth/google/login');
  });
});
