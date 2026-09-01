import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import {
  getRecentProjects,
  getSummary,
  getTopClips,
  getUsage,
} from '../services/dashboardService';
import type { Summary, TopClip, UsageRange, UsageResponse } from '../types/dashboard';
import type { Project } from '../types';

const STALE_TIME_MS = 60_000;

/** Lifetime totals for the dashboard stat cards. */
export function useSummary(): UseQueryResult<Summary, Error> {
  return useQuery<Summary, Error>({
    queryKey: ['dashboard', 'summary'],
    queryFn: getSummary,
    staleTime: STALE_TIME_MS,
  });
}

/** Daily usage time series for the given range (7d / 30d / 90d). */
export function useUsage(range: UsageRange): UseQueryResult<UsageResponse, Error> {
  return useQuery<UsageResponse, Error>({
    queryKey: ['dashboard', 'usage', range],
    queryFn: () => getUsage(range),
    staleTime: STALE_TIME_MS,
  });
}

/** Highest-scoring recent clips. */
export function useTopClips(): UseQueryResult<TopClip[], Error> {
  return useQuery<TopClip[], Error>({
    queryKey: ['dashboard', 'top-clips'],
    queryFn: getTopClips,
    staleTime: STALE_TIME_MS,
  });
}

/** Latest projects (first page of GET /projects), capped at `limit`. */
export function useRecentProjects(limit = 5): UseQueryResult<Project[], Error> {
  return useQuery<Project[], Error>({
    queryKey: ['dashboard', 'recent-projects', limit],
    queryFn: () => getRecentProjects(limit),
    staleTime: STALE_TIME_MS,
  });
}
