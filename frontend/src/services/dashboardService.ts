import api from './api';
import type { Page, Project } from '../types';
import type { Summary, TopClip, UsageRange, UsageResponse } from '../types/dashboard';

/**
 * Typed wrappers around the analytics dashboard endpoints
 * (prefix: /api/v1/dashboard, bearer auth via the shared axios client).
 */

/** Lifetime totals for the current user. */
export async function getSummary(): Promise<Summary> {
  const { data } = await api.get<Summary>('/dashboard/summary');
  return data;
}

/** Daily usage time series for the trailing window. */
export async function getUsage(range: UsageRange): Promise<UsageResponse> {
  const { data } = await api.get<UsageResponse>('/dashboard/usage', {
    params: { range },
  });
  return data;
}

/**
 * Highest-scoring recent clips.
 *
 * Contract assumption: the endpoint returns a bare JSON array (matching the
 * service's `list[TopClip]` return type). A `{ items: [...] }` envelope is also
 * tolerated in case the router wraps it.
 */
export async function getTopClips(): Promise<TopClip[]> {
  const { data } = await api.get<TopClip[] | { items: TopClip[] }>('/dashboard/top-clips');
  return Array.isArray(data) ? data : data.items;
}

/**
 * Latest projects for the dashboard's "Recent projects" panel.
 *
 * Reads the first page of GET /projects (owned by the Projects module). Handles
 * both the paginated `Page<Project>` envelope and a bare array response.
 */
export async function getRecentProjects(limit = 5): Promise<Project[]> {
  const { data } = await api.get<Page<Project> | Project[]>('/projects', {
    params: { page: 1 },
  });
  const items = Array.isArray(data) ? data : data.items;
  return items.slice(0, limit);
}
