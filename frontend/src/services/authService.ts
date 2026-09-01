import { AxiosError } from 'axios';
import api from './api';
import type { TokenPair, User } from '../types';

/**
 * Typed wrappers around the backend auth endpoints (prefix: /api/v1/auth).
 */

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UpdateProfilePayload {
  full_name?: string | null;
}

interface ApiErrorBody {
  code?: string;
  message?: string;
  detail?: string | { msg?: string }[];
}

/**
 * Best-effort extraction of a human-readable message from an unknown error.
 * Handles the app's ErrorResponse shape ({ code, message }) and FastAPI's
 * default validation body ({ detail: [...] }).
 */
export function extractApiError(
  error: unknown,
  fallback = 'Something went wrong. Please try again.',
): string {
  if (error instanceof AxiosError) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body) {
      if (typeof body.message === 'string' && body.message.length > 0) {
        return body.message;
      }
      if (typeof body.detail === 'string' && body.detail.length > 0) {
        return body.detail;
      }
      if (Array.isArray(body.detail) && body.detail.length > 0) {
        const first = body.detail[0];
        if (first && typeof first.msg === 'string') {
          return first.msg;
        }
      }
    }
    if (error.message.length > 0) {
      return error.message;
    }
  }
  if (error instanceof Error && error.message.length > 0) {
    return error.message;
  }
  return fallback;
}

/** Create a new account. Returns the created user profile. */
export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/register', payload);
  return data;
}

/**
 * Exchange credentials for a token pair. The backend expects an OAuth2
 * password form ("username" + "password"), so the body is url-encoded.
 */
export async function login(payload: LoginPayload): Promise<TokenPair> {
  const form = new URLSearchParams();
  form.append('username', payload.email);
  form.append('password', payload.password);
  const { data } = await api.post<TokenPair>('/auth/login', form);
  return data;
}

/** Revoke the stored refresh token server-side. Never throws. */
export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    return;
  }
  try {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  } catch {
    /* logout is best-effort: ignore network/permission errors */
  }
}

/** Fetch the currently authenticated user. */
export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

/** Update the current user's editable profile fields. */
export async function updateProfile(payload: UpdateProfilePayload): Promise<User> {
  const { data } = await api.put<User>('/auth/me', payload);
  return data;
}

/** Absolute URL that begins the Google OAuth redirect flow. */
export function googleLoginUrl(): string {
  return `${import.meta.env.VITE_API_URL}/api/v1/auth/google/login`;
}
