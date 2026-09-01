import type { ProjectStatus } from '../../types';
import { cn } from '../../lib/utils';

interface StatusConfig {
  label: string;
  className: string;
}

const STATUS_CONFIG: Record<ProjectStatus, StatusConfig> = {
  pending: { label: 'Pending', className: 'bg-gray-100 text-gray-700' },
  downloading: { label: 'Downloading', className: 'bg-blue-100 text-blue-700' },
  transcribing: { label: 'Transcribing', className: 'bg-indigo-100 text-indigo-700' },
  segmenting: { label: 'Segmenting', className: 'bg-violet-100 text-violet-700' },
  rendering: { label: 'Rendering', className: 'bg-amber-100 text-amber-700' },
  completed: { label: 'Completed', className: 'bg-green-100 text-green-700' },
  failed: { label: 'Failed', className: 'bg-red-100 text-red-700' },
};

interface ProjectStatusBadgeProps {
  status: ProjectStatus;
  className?: string;
}

/** Colored pill communicating the current project pipeline status. */
export function ProjectStatusBadge({ status, className }: ProjectStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.className,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
