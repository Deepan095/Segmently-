/**
 * Typed wrappers around the backend admin endpoints (prefix: /api/v1/admin).
 *
 * Every endpoint is gated by `is_admin` server-side and returns 403 for a
 * non-admin caller. The UI keeps these behind <AdminGuard>, so a 403 here is
 * an unexpected edge (e.g. admin flag revoked mid-session).
 */

import api from './api';
import type { Page } from '../types';
import type {
  AdminJob,
  AdminUser,
  AdminUserUpdate,
  PlatformStats,
} from '../types/admin';

export interface ListAdminUsersParams {
  q?: string;
  page?: number;
}

export interface ListAdminJobsParams {
  status?: string;
  page?: number;
}

/** List all users, optionally filtered by a search string, paginated. */
export async function listAdminUsers(
  params: ListAdminUsersParams = {},
): Promise<Page<AdminUser>> {
  const { data } = await api.get<Page<AdminUser>>('/admin/users', {
    params: {
      q: params.q?.trim() ? params.q.trim() : undefined,
      page: params.page ?? 1,
    },
  });
  return data;
}

/** Update `is_active` / `is_admin` / `is_verified` on a single user. */
export async function updateAdminUser(
  userId: number,
  payload: AdminUserUpdate,
): Promise<AdminUser> {
  const { data } = await api.put<AdminUser>(`/admin/users/${userId}`, payload);
  return data;
}

/** Aggregate platform stats for the admin dashboard. */
export async function getPlatformStats(): Promise<PlatformStats> {
  const { data } = await api.get<PlatformStats>('/admin/stats');
  return data;
}

/** Monitor processing jobs, optionally filtered by status, paginated. */
export async function listAdminJobs(
  params: ListAdminJobsParams = {},
): Promise<Page<AdminJob>> {
  const { data } = await api.get<Page<AdminJob>>('/admin/jobs', {
    params: {
      status: params.status && params.status !== 'all' ? params.status : undefined,
      page: params.page ?? 1,
    },
  });
  return data;
}

/** Retry a failed job. Backend responds 202 (accepted, re-queued). */
export async function retryAdminJob(jobId: number): Promise<void> {
  await api.post(`/admin/jobs/${jobId}/retry`);
}
