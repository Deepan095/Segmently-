/**
 * Admin Panel (Module 5) API types.
 *
 * These mirror `backend/app/schemas/admin.py`:
 *   - AdminUserResponse   -> AdminUser
 *   - AdminUserUpdateRequest -> AdminUserUpdate
 *   - PlatformStats       -> PlatformStats
 *   - AdminJobResponse    -> AdminJob
 *
 * All `/api/v1/admin/*` endpoints require `is_admin` and return 403 otherwise.
 */

import type { JobStatus, JobType } from './index';

/** Admin-facing view of a user account, with owned-resource counts. */
export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_admin: boolean;
  oauth_provider: string | null;
  created_at: string;
  projects_count: number;
  clips_count: number;
}

/** Partial update for a user account. Only provided fields are applied. */
export interface AdminUserUpdate {
  is_active?: boolean;
  is_admin?: boolean;
  is_verified?: boolean;
}

/** The three independently toggleable boolean flags on a user. */
export type AdminUserFlag = 'is_active' | 'is_admin' | 'is_verified';

/** Aggregate platform metrics for the admin dashboard. */
export interface PlatformStats {
  users_total: number;
  users_active: number;
  projects_total: number;
  clips_total: number;
  /**
   * SUM of `Project.file_size_bytes` across every project. An estimate: it only
   * counts uploaded source media that reported a size, and excludes rendered
   * clip / thumbnail objects in object storage.
   */
  storage_bytes_estimate: number;
  jobs_failed: number;
}

/** Admin-facing view of a single processing job. */
export interface AdminJob {
  id: number;
  project_id: number;
  job_type: JobType | string;
  status: JobStatus | string;
  progress_pct: number;
  error_message: string | null;
  created_at: string;
}

/** Optional status filter for the job monitor. */
export type AdminJobStatusFilter = JobStatus | 'all';
