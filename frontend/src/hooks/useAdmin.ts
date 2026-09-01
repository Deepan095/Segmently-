/**
 * React Query hooks for the Admin Panel module (Module 5).
 *
 *   useAdminUsers(q, page)   - GET  /admin/users
 *   useUpdateAdminUser()     - PUT  /admin/users/{id}
 *   useAdminStats()          - GET  /admin/stats
 *   useAdminJobs(status, p)  - GET  /admin/jobs
 *   useRetryJob()            - POST /admin/jobs/{id}/retry
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import { extractApiError } from '../services/authService';
import {
  getPlatformStats,
  listAdminJobs,
  listAdminUsers,
  retryAdminJob,
  updateAdminUser,
} from '../services/adminService';
import type { Page } from '../types';
import type {
  AdminJob,
  AdminUser,
  AdminUserUpdate,
  PlatformStats,
} from '../types/admin';

const adminKeys = {
  all: ['admin'] as const,
  users: (q: string, page: number) => ['admin', 'users', { q, page }] as const,
  stats: () => ['admin', 'stats'] as const,
  jobs: (status: string, page: number) =>
    ['admin', 'jobs', { status, page }] as const,
};

/** Paginated, searchable user list. */
export function useAdminUsers(
  q = '',
  page = 1,
): UseQueryResult<Page<AdminUser>, Error> {
  return useQuery<Page<AdminUser>, Error>({
    queryKey: adminKeys.users(q, page),
    queryFn: () => listAdminUsers({ q, page }),
    placeholderData: (previous) => previous,
  });
}

export interface UpdateAdminUserVariables {
  userId: number;
  payload: AdminUserUpdate;
}

/** Toggle a user's flags; invalidates every cached admin user page + stats. */
export function useUpdateAdminUser(): UseMutationResult<
  AdminUser,
  Error,
  UpdateAdminUserVariables
> {
  const queryClient = useQueryClient();
  return useMutation<AdminUser, Error, UpdateAdminUserVariables>({
    mutationFn: async ({ userId, payload }) => {
      try {
        return await updateAdminUser(userId, payload);
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not update this user.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
    },
  });
}

/** Aggregate platform stats. */
export function useAdminStats(): UseQueryResult<PlatformStats, Error> {
  return useQuery<PlatformStats, Error>({
    queryKey: adminKeys.stats(),
    queryFn: getPlatformStats,
  });
}

/** Paginated job monitor with an optional status filter. */
export function useAdminJobs(
  status = 'all',
  page = 1,
): UseQueryResult<Page<AdminJob>, Error> {
  return useQuery<Page<AdminJob>, Error>({
    queryKey: adminKeys.jobs(status, page),
    queryFn: () => listAdminJobs({ status, page }),
    placeholderData: (previous) => previous,
  });
}

/** Retry a failed job; invalidates the job monitor + stats on success. */
export function useRetryJob(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (jobId) => {
      try {
        await retryAdminJob(jobId);
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not retry this job.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'jobs'] });
      void queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
    },
  });
}
