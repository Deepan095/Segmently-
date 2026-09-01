import type { AxiosProgressEvent } from 'axios';
import api from './api';
import type { Page, ProcessingJob, Project, Transcript } from '../types';

/**
 * Typed wrappers around the backend projects endpoints (prefix: /api/v1).
 */

/** Project detail payload: the base project plus its pipeline jobs and clip count. */
export interface ProjectDetail extends Project {
  jobs: ProcessingJob[];
  clips_count: number;
  has_transcript: boolean;
}

export interface CreateProjectFromUrlPayload {
  url: string;
}

export interface UploadProjectArgs {
  file: File;
  /** Receives an integer 0-100 as the multipart body is sent. */
  onUploadProgress?: (percent: number) => void;
}

/** List the current user's projects (paginated, 1-based page index). */
export async function listProjects(page = 1): Promise<Page<Project>> {
  const { data } = await api.get<Page<Project>>('/projects', { params: { page } });
  return data;
}

/** Fetch a single project with its jobs + clip count. */
export async function getProject(id: number): Promise<ProjectDetail> {
  const { data } = await api.get<ProjectDetail>(`/projects/${id}`);
  return data;
}

/** Create a project from a pasted URL. Backend responds 202 with the new project. */
export async function createProjectFromUrl(
  payload: CreateProjectFromUrlPayload,
): Promise<Project> {
  const { data } = await api.post<Project>('/projects', payload);
  return data;
}

/** Create a project by uploading a video file. Backend responds 202. */
export async function uploadProject({
  file,
  onUploadProgress,
}: UploadProjectArgs): Promise<Project> {
  const form = new FormData();
  form.append('file', file);

  const { data } = await api.post<Project>('/projects/upload', form, {
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (!onUploadProgress) {
        return;
      }
      const total = event.total ?? 0;
      if (total > 0) {
        onUploadProgress(Math.min(100, Math.round((event.loaded * 100) / total)));
      }
    },
  });
  return data;
}

/** Delete a project along with its clips and stored media. */
export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/projects/${id}`);
}

/** Re-run the processing pipeline for a project. Backend responds 202. */
export async function reprocessProject(id: number): Promise<void> {
  await api.post(`/projects/${id}/reprocess`);
}

/** Fetch the transcript for a project (404 until transcription completes). */
export async function getProjectTranscript(id: number): Promise<Transcript> {
  const { data } = await api.get<Transcript>(`/projects/${id}/transcript`);
  return data;
}
