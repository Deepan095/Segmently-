import { Link } from 'react-router-dom';
import { Film, Link2, Upload } from 'lucide-react';
import type { Project } from '../../types';
import { GlassCard } from '../ui/GlassCard';
import { ProjectStatusBadge } from './ProjectStatusBadge';

interface ProjectCardProps {
  project: Project;
}

function formatDuration(totalSeconds: number): string {
  const seconds = Math.floor(totalSeconds % 60);
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (value: number): string => value.toString().padStart(2, '0');
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`;
}

/** Summary card for a single project, linking to its detail page. */
export function ProjectCard({ project }: ProjectCardProps) {
  const SourceIcon = project.source_type === 'url' ? Link2 : Upload;
  const sourceLabel = project.source_type === 'url' ? 'Imported from URL' : 'Uploaded file';

  return (
    <Link to={`/projects/${project.id}`} className="block">
      <GlassCard className="bg-white/70">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="mt-0.5 rounded-lg bg-purple-100 p-2 text-purple-600">
              <Film className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-gray-900">{project.title}</h3>
              <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
                <SourceIcon className="h-3.5 w-3.5" />
                <span>{sourceLabel}</span>
                {project.duration_seconds !== null && (
                  <span>· {formatDuration(project.duration_seconds)}</span>
                )}
              </p>
            </div>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>
        <p className="mt-3 text-xs text-gray-400">
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </GlassCard>
    </Link>
  );
}
