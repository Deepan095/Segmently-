import { AxiosError } from 'axios';
import api from './api';
import type { CaptionStyle, Clip, Page, TranscriptSegment } from '../types';

/**
 * Typed wrappers around the backend clip endpoints.
 * Clip list/detail live under /api/v1 (prefix handled by the shared api client):
 *   GET    /projects/{project_id}/clips
 *   GET    /clips/{id}
 *   PUT    /clips/{id}
 *   POST   /clips/{id}/rerender
 *   GET    /clips/{id}/download
 *   DELETE /clips/{id}
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Caption/render style payload. Extends the shared CaptionStyle with the
 * horizontal crop-centre used by the reframe control (0 = far left,
 * 1 = far right, 0.5 = centred).
 */
export interface ClipStyle extends CaptionStyle {
  reframe_offset?: number;
  /** Per-clip override for automatic stock-footage B-roll. */
  broll?: boolean;
  /** "fit" (blurred fill) or "crop" (zoom). Defaults to the server setting. */
  render_mode?: 'fit' | 'crop';
}

/**
 * Optional signed asset URLs the backend may attach to a clip payload.
 * Absent while a clip is still rendering.
 */
export interface ClipAssets {
  thumbnail_url?: string | null;
  video_url?: string | null;
}

export type ClipListItem = Clip & ClipAssets;

/** Clip detail response, including the editable caption segments. */
export type ClipDetail = Clip &
  ClipAssets & {
    caption_segments: TranscriptSegment[];
  };

export interface UpdateClipPayload {
  title?: string;
  start_seconds?: number;
  end_seconds?: number;
  caption_segments?: TranscriptSegment[];
  caption_style?: ClipStyle;
}

export interface ClipDownload {
  url: string;
  expires_at: string;
}

export interface ProjectOption {
  id: number;
  title: string;
}

interface ApiErrorBody {
  code?: string;
  message?: string;
  detail?: string | { msg?: string }[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Best-effort human-readable message from an unknown error. */
export function extractClipError(
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

/** Clamp a reframe offset into the valid 0..1 range. */
export function clampOffset(value: number): number {
  if (Number.isNaN(value)) {
    return 0.5;
  }
  return Math.min(1, Math.max(0, value));
}

/** Format a duration in seconds as m:ss. */
export function formatSeconds(total: number): string {
  const safe = Math.max(0, Math.floor(total));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

export async function listProjectClips(
  projectId: number,
  page = 1,
  size = 100,
): Promise<Page<ClipListItem>> {
  const { data } = await api.get<Page<ClipListItem>>(`/projects/${projectId}/clips`, {
    params: { page, size },
  });
  return data;
}

export async function getClip(clipId: number): Promise<ClipDetail> {
  const { data } = await api.get<ClipDetail>(`/clips/${clipId}`);
  return data;
}

export async function updateClip(
  clipId: number,
  payload: UpdateClipPayload,
): Promise<ClipDetail> {
  const { data } = await api.put<ClipDetail>(`/clips/${clipId}`, payload);
  return data;
}

export async function rerenderClip(clipId: number): Promise<void> {
  await api.post(`/clips/${clipId}/rerender`);
}

export async function deleteClip(clipId: number): Promise<void> {
  await api.delete(`/clips/${clipId}`);
}

export async function getClipDownload(clipId: number): Promise<ClipDownload> {
  const { data } = await api.get<ClipDownload>(`/clips/${clipId}/download`);
  return data;
}

/**
 * Lightweight project list for the library filter. Calls GET /projects
 * directly so the clips module stays decoupled from the projects module.
 */
export async function listProjectsForFilter(): Promise<ProjectOption[]> {
  const { data } = await api.get<Page<{ id: number; title: string }>>('/projects', {
    params: { page: 1, size: 100 },
  });
  return data.items.map((project) => ({ id: project.id, title: project.title }));
}
