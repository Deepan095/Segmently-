/**
 * Analytics Dashboard (Module 4) API types.
 *
 * Shapes mirror `backend/app/schemas/dashboard.py`:
 *   - SummaryResponse  -> Summary
 *   - UsagePoint       -> UsagePoint
 *   - UsageResponse    -> UsageResponse
 *   - TopClip          -> TopClip
 */

/** Selectable window for the usage time series. */
export type UsageRange = '7d' | '30d' | '90d';

/** Lifetime totals for the current user (GET /dashboard/summary). */
export interface Summary {
  /** Sum of Project.duration_seconds / 60 across the user's projects. */
  minutes_uploaded: number;
  projects_total: number;
  projects_completed: number;
  clips_generated: number;
  /** MVP proxy: count of clips in status "ready". */
  clips_downloaded: number;
}

/** One calendar day of activity. `date` is an ISO date string (YYYY-MM-DD). */
export interface UsagePoint {
  date: string;
  minutes_processed: number;
  clips_generated: number;
}

/** Daily time series over the requested range, zero-filled (GET /dashboard/usage). */
export interface UsageResponse {
  range: UsageRange;
  points: UsagePoint[];
}

/** A high-scoring clip for the "Top Clips" panel (GET /dashboard/top-clips). */
export interface TopClip {
  id: number;
  title: string;
  /** 0-100 interest/virality score. */
  score: number;
  project_id: number;
  thumbnail_url: string | null;
}
