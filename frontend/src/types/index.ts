/**
 * Shared API types for Segmently.
 * Enums are modelled as string-literal unions matching the PRP database models.
 */

// ---------------------------------------------------------------------------
// Enums (string-literal unions)
// ---------------------------------------------------------------------------

export type ProjectSourceType = 'upload' | 'url';

export type ProjectStatus =
  | 'pending'
  | 'downloading'
  | 'transcribing'
  | 'segmenting'
  | 'rendering'
  | 'completed'
  | 'failed';

export type JobType = 'download' | 'transcribe' | 'segment' | 'render';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export type ClipStatus = 'queued' | 'rendering' | 'ready' | 'failed';

// ---------------------------------------------------------------------------
// Core resources
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_admin: boolean;
  oauth_provider: string | null;
  oauth_sub: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface Project {
  id: number;
  user_id: number;
  title: string;
  source_type: ProjectSourceType;
  source_url: string | null;
  storage_key: string | null;
  duration_seconds: number | null;
  file_size_bytes: number | null;
  status: ProjectStatus;
  error_message: string | null;
  thumbnail_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface Transcript {
  id: number;
  project_id: number;
  language: string;
  full_text: string;
  segments: TranscriptSegment[];
  created_at: string;
}

export interface ProcessingJob {
  id: number;
  project_id: number;
  job_type: JobType;
  status: JobStatus;
  progress_pct: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface CaptionStyle {
  font_family?: string;
  font_size?: number;
  color?: string;
  background_color?: string;
  position?: 'top' | 'middle' | 'bottom';
  uppercase?: boolean;
}

export interface Clip {
  id: number;
  project_id: number;
  user_id: number;
  title: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  aspect_ratio: string;
  status: ClipStatus;
  score: number;
  score_reason: string;
  storage_key: string | null;
  thumbnail_key: string | null;
  caption_style: CaptionStyle;
  created_at: string;
  updated_at: string;
}

export interface ClipCaption {
  id: number;
  clip_id: number;
  segments: TranscriptSegment[];
  edited: boolean;
}

// ---------------------------------------------------------------------------
// Generic API envelopes
// ---------------------------------------------------------------------------

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
