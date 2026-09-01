import { useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Loader2, RefreshCw, Trash2 } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { ProjectStatusBadge } from '../components/projects/ProjectStatusBadge';
import { PipelineProgress } from '../components/projects/PipelineProgress';
import { TranscriptPanel } from '../components/projects/TranscriptPanel';
import {
  useDeleteProject,
  useProjectQuery,
  useReprocessProject,
} from '../hooks/useProjects';
import type { ProjectDetail } from '../services/projectService';

function formatDuration(totalSeconds: number): string {
  const seconds = Math.floor(totalSeconds % 60);
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (value: number): string => value.toString().padStart(2, '0');
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function transcriptAvailable(project: ProjectDetail): boolean {
  if (project.jobs.some((job) => job.job_type === 'transcribe' && job.status === 'completed')) {
    return true;
  }
  return ['segmenting', 'rendering', 'completed'].includes(project.status);
}

interface InfoRowProps {
  label: string;
  children: ReactNode;
}

function InfoRow({ label, children }: InfoRowProps) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="mt-1 break-words text-sm text-gray-900">{children}</dd>
    </div>
  );
}

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const navigate = useNavigate();

  const query = useProjectQuery(projectId);
  const deleteMutation = useDeleteProject();
  const reprocessMutation = useReprocessProject();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (!Number.isFinite(projectId) || projectId <= 0) {
    return (
      <PageWrapper>
        <div className="mx-auto max-w-3xl">
          <p className="text-sm text-gray-600">Invalid project reference.</p>
        </div>
      </PageWrapper>
    );
  }

  if (query.isLoading) {
    return (
      <PageWrapper>
        <div className="flex justify-center py-16 text-gray-400">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      </PageWrapper>
    );
  }

  if (query.isError || !query.data) {
    return (
      <PageWrapper>
        <div className="mx-auto max-w-3xl">
          <GlassCard className="bg-white/70 text-center">
            <p className="text-sm text-red-500">
              This project could not be found, or you do not have access to it.
            </p>
            <div className="mt-3 flex justify-center">
              <GradientButton type="button" onClick={() => navigate('/projects')}>
                Back to projects
              </GradientButton>
            </div>
          </GlassCard>
        </div>
      </PageWrapper>
    );
  }

  const project = query.data;
  const isPolling = query.isFetching && !query.isLoading;

  const handleDelete = (): void => {
    deleteMutation.mutate(projectId, {
      onSuccess: () => navigate('/projects'),
    });
  };

  return (
    <PageWrapper>
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <motion.button
          type="button"
          whileHover={{ x: -3 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate('/projects')}
          className="flex items-center gap-1.5 self-start text-sm font-medium text-gray-500 hover:text-purple-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Projects
        </motion.button>

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-bold text-gray-900">{project.title}</h1>
            <div className="mt-2 flex items-center gap-2">
              <ProjectStatusBadge status={project.status} />
              {isPolling && (
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Updating
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => reprocessMutation.mutate(projectId)}
              disabled={reprocessMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" />
              {reprocessMutation.isPending ? 'Restarting...' : 'Reprocess'}
            </motion.button>

            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setConfirmingDelete(true)}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </motion.button>
          </div>
        </div>

        {reprocessMutation.isError && (
          <p className="text-sm text-red-500" role="alert">
            {reprocessMutation.error.message}
          </p>
        )}

        {confirmingDelete && (
          <GlassCard className="bg-white/70">
            <p className="text-sm text-gray-700">
              Delete this project and all of its clips and media? This cannot be undone.
            </p>
            {deleteMutation.isError && (
              <p className="mt-2 text-sm text-red-500" role="alert">
                {deleteMutation.error.message}
              </p>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => setConfirmingDelete(false)}
                disabled={deleteMutation.isPending}
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              >
                Cancel
              </motion.button>
              <motion.button
                type="button"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete project'}
              </motion.button>
            </div>
          </GlassCard>
        )}

        <GlassCard className="bg-white/70">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">Pipeline</h2>
          <PipelineProgress jobs={project.jobs} />
          {project.status === 'failed' && project.error_message && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {project.error_message}
            </p>
          )}
        </GlassCard>

        <GlassCard className="bg-white/70">
          <h2 className="mb-4 text-sm font-semibold text-gray-900">Source</h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <InfoRow label="Type">
              {project.source_type === 'url' ? 'URL import' : 'File upload'}
            </InfoRow>
            {project.source_type === 'url' && project.source_url && (
              <InfoRow label="URL">
                <a
                  href={project.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-purple-600 hover:text-purple-700"
                >
                  {project.source_url}
                </a>
              </InfoRow>
            )}
            {project.duration_seconds !== null && (
              <InfoRow label="Duration">{formatDuration(project.duration_seconds)}</InfoRow>
            )}
            {project.file_size_bytes !== null && (
              <InfoRow label="File size">{formatBytes(project.file_size_bytes)}</InfoRow>
            )}
            <InfoRow label="Created">
              {new Date(project.created_at).toLocaleString()}
            </InfoRow>
          </dl>
        </GlassCard>

        <GlassCard className="bg-white/70">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Clips</h2>
              <p className="mt-1 text-sm text-gray-600">
                {project.clips_count} clip{project.clips_count === 1 ? '' : 's'} generated
              </p>
            </div>
            <GradientButton
              type="button"
              onClick={() => navigate(`/clips?project=${projectId}`)}
              disabled={project.clips_count === 0}
            >
              View clips
            </GradientButton>
          </div>
        </GlassCard>

        <TranscriptPanel projectId={projectId} available={transcriptAvailable(project)} />
      </div>
    </PageWrapper>
  );
}
