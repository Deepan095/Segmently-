import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { cn } from '../../lib/utils';
import { useRecentProjects } from '../../hooks/useDashboard';
import type { ProjectStatus } from '../../types';

const MotionLink = motion(Link);

const STATUS_STYLES: Record<ProjectStatus, string> = {
  pending: 'bg-gray-100 text-gray-600',
  downloading: 'bg-sky-100 text-sky-700',
  transcribing: 'bg-sky-100 text-sky-700',
  segmenting: 'bg-violet-100 text-violet-700',
  rendering: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
};

function StatusPill({ status }: { status: ProjectStatus }) {
  return (
    <span
      className={cn(
        'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize',
        STATUS_STYLES[status],
      )}
    >
      {status}
    </span>
  );
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function RecentProjects() {
  const { data, isPending, isError, error, refetch } = useRecentProjects(5);
  const projects = data ?? [];

  return (
    <GlassCard className="bg-white/70">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Recent projects</h2>
        <MotionLink
          to="/projects"
          whileHover={{ x: 2 }}
          whileTap={{ scale: 0.97 }}
          className="flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-700"
        >
          View all
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </MotionLink>
      </div>

      {isPending ? (
        <ul className="flex flex-col gap-2" aria-busy="true">
          {[0, 1, 2, 3, 4].map((key) => (
            <li key={key} className="h-10 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </ul>
      ) : isError ? (
        <div className="flex flex-col items-start gap-2 py-4">
          <p className="text-sm text-gray-600">
            {error instanceof Error ? error.message : 'Could not load projects.'}
          </p>
          <motion.button
            type="button"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => void refetch()}
            className="rounded-lg bg-purple-100 px-3 py-1.5 text-xs font-medium text-purple-700"
          >
            Retry
          </motion.button>
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-start gap-2 py-6 text-sm text-gray-500">
          <p>No projects yet.</p>
          <MotionLink
            to="/projects/new"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="font-medium text-purple-600 hover:text-purple-700"
          >
            Create your first project
          </MotionLink>
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-gray-100">
          {projects.map((project) => (
            <li key={project.id}>
              <MotionLink
                to={`/projects/${project.id}`}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.99 }}
                className="flex items-center justify-between gap-3 py-2.5"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-gray-900">
                    {project.title}
                  </span>
                  <span className="text-xs text-gray-400">{formatDate(project.created_at)}</span>
                </span>
                <StatusPill status={project.status} />
              </MotionLink>
            </li>
          ))}
        </ul>
      )}
    </GlassCard>
  );
}
