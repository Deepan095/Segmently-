import { useMemo } from 'react';
import type { ChangeEvent } from 'react';
import { motion } from 'framer-motion';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertCircle, Scissors } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { PageWrapper } from '../components/layout/PageWrapper';
import { AnimatedList } from '../components/ui/AnimatedList';
import { ClipCard } from '../components/clips/ClipCard';
import { listProjectsForFilter } from '../services/clipService';
import { useClipsForProjects } from '../hooks/useClips';
import { cn } from '../lib/utils';

type ProjectFilter = number | 'all';
type SortKey = 'score' | 'newest';

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'score', label: 'Top score' },
  { key: 'newest', label: 'Newest' },
];

export function ClipsLibraryPage() {
  const projectsQuery = useQuery({
    queryKey: ['projects', 'filter-options'],
    queryFn: listProjectsForFilter,
  });

  const projects = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data]);

  // Filter + sort live in the URL so a project's "View clips" link deep-links
  // straight to that project's clips (`/clips?project=<id>`).
  const [searchParams, setSearchParams] = useSearchParams();
  const projectParam = searchParams.get('project');
  const projectFilter: ProjectFilter =
    projectParam && /^\d+$/.test(projectParam) ? Number(projectParam) : 'all';
  const sort: SortKey = searchParams.get('sort') === 'newest' ? 'newest' : 'score';

  const updateParams = (next: { project?: ProjectFilter; sort?: SortKey }) => {
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev);
        if (next.project !== undefined) {
          if (next.project === 'all') params.delete('project');
          else params.set('project', String(next.project));
        }
        if (next.sort !== undefined) {
          if (next.sort === 'score') params.delete('sort');
          else params.set('sort', next.sort);
        }
        return params;
      },
      { replace: true },
    );
  };

  const activeProject = useMemo(
    () => projects.find((p) => p.id === projectFilter),
    [projects, projectFilter],
  );

  const projectIds = useMemo(() => {
    if (projectFilter === 'all') {
      return projects.map((project) => project.id);
    }
    return [projectFilter];
  }, [projectFilter, projects]);

  const { clips, isLoading: clipsLoading, isError: clipsError } =
    useClipsForProjects(projectIds);

  const sortedClips = useMemo(() => {
    const copy = [...clips];
    copy.sort((a, b) =>
      sort === 'score'
        ? b.score - a.score
        : Date.parse(b.created_at) - Date.parse(a.created_at),
    );
    return copy;
  }, [clips, sort]);

  const handleProjectChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const { value } = event.target;
    updateParams({ project: value === 'all' ? 'all' : Number(value) });
  };

  const isLoading = projectsQuery.isLoading || (projectIds.length > 0 && clipsLoading);
  const isError = projectsQuery.isError || clipsError;

  return (
    <PageWrapper>
      <div className="mx-auto max-w-3xl">
        <header className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-gray-900">
            {projectFilter === 'all' ? 'Clips' : 'Project clips'}
          </h1>
        </header>
        {projectFilter !== 'all' ? (
          <p className="mb-4 text-sm text-gray-500">
            Showing clips from{' '}
            <span className="font-medium text-gray-700">
              {activeProject?.title ?? `project #${projectFilter}`}
            </span>
            .{' '}
            <button
              type="button"
              onClick={() => updateParams({ project: 'all' })}
              className="text-purple-600 hover:underline"
            >
              View all clips
            </button>
          </p>
        ) : null}

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <select
            value={projectFilter === 'all' ? 'all' : String(projectFilter)}
            onChange={handleProjectChange}
            disabled={projectsQuery.isLoading || projects.length === 0}
            className="rounded-xl border-2 border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-purple-500 disabled:bg-gray-50"
          >
            <option value="all">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.title}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1 rounded-xl bg-gray-100 p-1">
            {SORT_OPTIONS.map((option) => (
              <motion.button
                key={option.key}
                type="button"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => updateParams({ sort: option.key })}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                  sort === option.key
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700',
                )}
              >
                {option.label}
              </motion.button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((key) => (
              <div key={key} className="h-28 animate-pulse rounded-2xl bg-gray-100" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <AlertCircle className="h-4 w-4" />
            Could not load clips. Please try again.
          </div>
        ) : sortedClips.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-10 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-purple-100 text-purple-500">
              <Scissors className="h-5 w-5" />
            </div>
            <h2 className="text-sm font-semibold text-gray-900">No clips yet</h2>
            <p className="mt-1 text-sm text-gray-500">
              {projects.length === 0
                ? 'Create a project to generate your first clips.'
                : 'No clips match this filter yet.'}
            </p>
            <Link
              to="/projects/new"
              className="mt-4 inline-block rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-2 text-sm font-semibold text-white"
            >
              New project
            </Link>
          </div>
        ) : (
          <AnimatedList>
            {sortedClips.map((clip) => (
              <div key={clip.id} className="pb-3">
                <ClipCard clip={clip} />
              </div>
            ))}
          </AnimatedList>
        )}
      </div>
    </PageWrapper>
  );
}
