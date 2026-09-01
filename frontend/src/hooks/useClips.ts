import { useCallback } from 'react';
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import {
  deleteClip,
  extractClipError,
  getClip,
  getClipDownload,
  listProjectClips,
  rerenderClip,
  updateClip,
} from '../services/clipService';
import type {
  ClipDetail,
  ClipDownload,
  ClipListItem,
  UpdateClipPayload,
} from '../services/clipService';
import type { ClipStatus } from '../types';

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const clipKeys = {
  all: ['clips'] as const,
  list: (projectId: number) => ['clips', 'list', projectId] as const,
  detail: (clipId: number) => ['clips', 'detail', clipId] as const,
  download: (clipId: number) => ['clips', 'download', clipId] as const,
};

const IN_PROGRESS: ReadonlySet<ClipStatus> = new Set<ClipStatus>(['queued', 'rendering']);

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/** Clips for a single project (newest-first ordering is left to the caller). */
export function useProjectClips(
  projectId: number | undefined,
): UseQueryResult<ClipListItem[], Error> {
  return useQuery({
    queryKey: clipKeys.list(projectId ?? 0),
    queryFn: () => listProjectClips(projectId as number),
    enabled: typeof projectId === 'number',
    select: (page) => page.items,
  });
}

export interface AggregatedClips {
  clips: ClipListItem[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
}

/**
 * Clips across several projects, fetched in parallel and flattened.
 * Used by the library page when no single project is selected.
 */
export function useClipsForProjects(projectIds: number[]): AggregatedClips {
  const results = useQueries({
    queries: projectIds.map((projectId) => ({
      queryKey: clipKeys.list(projectId),
      queryFn: () => listProjectClips(projectId),
      select: (page: Awaited<ReturnType<typeof listProjectClips>>) => page.items,
    })),
  });

  return {
    clips: results.flatMap((result) => result.data ?? []),
    isLoading: results.some((result) => result.isLoading),
    isError: results.some((result) => result.isError),
    error: results.find((result) => result.error)?.error ?? null,
  };
}

/** Clip detail. Polls while the clip is queued or rendering. */
export function useClip(clipId: number | undefined): UseQueryResult<ClipDetail, Error> {
  return useQuery({
    queryKey: clipKeys.detail(clipId ?? 0),
    queryFn: () => getClip(clipId as number),
    enabled: typeof clipId === 'number',
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && IN_PROGRESS.has(status) ? 4000 : false;
    },
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useUpdateClip(
  clipId: number,
): UseMutationResult<ClipDetail, Error, UpdateClipPayload> {
  const queryClient = useQueryClient();
  return useMutation<ClipDetail, Error, UpdateClipPayload>({
    mutationFn: async (payload) => {
      try {
        return await updateClip(clipId, payload);
      } catch (error) {
        throw new Error(extractClipError(error, 'Could not save your changes.'));
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(clipKeys.detail(clipId), data);
      void queryClient.invalidateQueries({ queryKey: clipKeys.all });
    },
  });
}

export function useRerenderClip(clipId: number): UseMutationResult<void, Error, void> {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      try {
        await rerenderClip(clipId);
      } catch (error) {
        throw new Error(extractClipError(error, 'Could not start the re-render.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clipKeys.detail(clipId) });
    },
  });
}

export function useDeleteClip(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (clipId) => {
      try {
        await deleteClip(clipId);
      } catch (error) {
        throw new Error(extractClipError(error, 'Could not delete the clip.'));
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clipKeys.all });
    },
  });
}

// ---------------------------------------------------------------------------
// Download
// ---------------------------------------------------------------------------

export interface ClipDownloadHandle {
  url: string | null;
  expiresAt: string | null;
  isFetching: boolean;
  isError: boolean;
  error: Error | null;
  /** Lazily fetches a fresh signed URL and triggers a browser download. */
  download: () => Promise<void>;
}

/**
 * Signed MP4 download URL. When `enabled` the URL is also available up-front
 * (e.g. to feed the in-app preview player); otherwise it is fetched on demand
 * the first time `download()` is called.
 */
export function useClipDownload(clipId: number, enabled = false): ClipDownloadHandle {
  const query = useQuery<ClipDownload, Error>({
    queryKey: clipKeys.download(clipId),
    queryFn: () => getClipDownload(clipId),
    enabled,
    staleTime: 60_000,
    gcTime: 60_000,
  });

  const { data, refetch } = query;

  const download = useCallback(async () => {
    let payload = data;
    if (!payload) {
      const result = await refetch();
      payload = result.data;
    }
    if (!payload?.url) {
      return;
    }
    const link = document.createElement('a');
    link.href = payload.url;
    link.rel = 'noopener';
    link.download = '';
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, [data, refetch]);

  return {
    url: data?.url ?? null,
    expiresAt: data?.expires_at ?? null,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error,
    download,
  };
}
