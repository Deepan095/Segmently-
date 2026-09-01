import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import { extractApiError } from '../services/authService';
import {
  createProjectFromUrl,
  deleteProject,
  getProject,
  getProjectTranscript,
  listProjects,
  reprocessProject,
  uploadProject,
} from '../services/projectService';
import type { ProjectDetail, UploadProjectArgs } from '../services/projectService';
import type { Page, Project, ProjectStatus, Transcript } from '../types';

const IN_PROGRESS_STATUSES: readonly ProjectStatus[] = [
  'pending',
  'downloading',
  'transcribing',
  'segmenting',
  'rendering',
];

/** True while the pipeline is still working on a project. */
export function isProjectInProgress(status: ProjectStatus): boolean {
  return IN_PROGRESS_STATUSES.includes(status);
}

export const projectKeys = {
  all: ['projects'] as const,
  list: (page: number) => ['projects', 'list', page] as const,
  detail: (id: number) => ['projects', 'detail', id] as const,
  transcript: (id: number) => ['projects', 'transcript', id] as const,
};

const LIST_POLL_MS = 5000;
const DETAIL_POLL_MS = 4000;

/** Paginated list of the current user's projects. Polls while any item is processing. */
export function useProjectsQuery(page = 1): UseQueryResult<Page<Project>, Error> {
  return useQuery({
    queryKey: projectKeys.list(page),
    queryFn: () => listProjects(page),
    placeholderData: (previous) => previous,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.items.some((project) => isProjectInProgress(project.status))) {
        return LIST_POLL_MS;
      }
      return false;
    },
  });
}

/** Single project detail. Polls while the pipeline status is in progress. */
export function useProjectQuery(id: number): UseQueryResult<ProjectDetail, Error> {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => getProject(id),
    enabled: Number.isFinite(id) && id > 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && isProjectInProgress(data.status)) {
        return DETAIL_POLL_MS;
      }
      return false;
    },
  });
}

/** Lazily fetch a project transcript (enable only when the panel is open + ready). */
export function useProjectTranscriptQuery(
  id: number,
  enabled: boolean,
): UseQueryResult<Transcript, Error> {
  return useQuery({
    queryKey: projectKeys.transcript(id),
    queryFn: () => getProjectTranscript(id),
    enabled: enabled && Number.isFinite(id) && id > 0,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useCreateProjectFromUrl(): UseMutationResult<Project, Error, string> {
  const queryClient = useQueryClient();
  return useMutation<Project, Error, string>({
    mutationFn: async (url) => {
      try {
        return await createProjectFromUrl({ url });
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not import that URL.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUploadProject(): UseMutationResult<Project, Error, UploadProjectArgs> {
  const queryClient = useQueryClient();
  return useMutation<Project, Error, UploadProjectArgs>({
    mutationFn: async (args) => {
      try {
        return await uploadProject(args);
      } catch (error) {
        throw new Error(extractApiError(error, 'Upload failed. Please try again.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useDeleteProject(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      try {
        await deleteProject(id);
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not delete the project.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useReprocessProject(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      try {
        await reprocessProject(id);
      } catch (error) {
        throw new Error(extractApiError(error, 'Could not restart processing.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}
