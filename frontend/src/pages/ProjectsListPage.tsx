import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FolderPlus, Loader2 } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { AnimatedList } from '../components/ui/AnimatedList';
import { ProjectCard } from '../components/projects/ProjectCard';
import { useProjectsQuery } from '../hooks/useProjects';

export function ProjectsListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const query = useProjectsQuery(page);

  return (
    <PageWrapper>
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <GradientButton type="button" onClick={() => navigate('/projects/new')}>
            New project
          </GradientButton>
        </div>

        {query.isLoading && (
          <div className="flex justify-center py-16 text-gray-400">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        )}

        {query.isError && (
          <GlassCard className="bg-white/70 text-center">
            <p className="text-sm text-red-500">Could not load your projects.</p>
            <div className="mt-3 flex justify-center">
              <GradientButton type="button" onClick={() => void query.refetch()}>
                Retry
              </GradientButton>
            </div>
          </GlassCard>
        )}

        {query.isSuccess && query.data.items.length === 0 && (
          <GlassCard className="bg-white/70 text-center">
            <FolderPlus className="mx-auto h-10 w-10 text-purple-400" />
            <h2 className="mt-3 text-lg font-semibold text-gray-900">No projects yet</h2>
            <p className="mt-1 text-sm text-gray-600">
              Upload a video to get your first clips.
            </p>
            <div className="mt-4 flex justify-center">
              <GradientButton type="button" onClick={() => navigate('/projects/new')}>
                Create a project
              </GradientButton>
            </div>
          </GlassCard>
        )}

        {query.isSuccess && query.data.items.length > 0 && (
          <>
            <AnimatedList>
              {query.data.items.map((project) => (
                <div key={project.id} className="mb-3">
                  <ProjectCard project={project} />
                </div>
              ))}
            </AnimatedList>

            {query.data.pages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-4">
                <motion.button
                  type="button"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1 || query.isFetching}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 disabled:opacity-40"
                >
                  Previous
                </motion.button>
                <span className="text-sm text-gray-500">
                  Page {query.data.page} of {query.data.pages}
                </span>
                <motion.button
                  type="button"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setPage((current) => current + 1)}
                  disabled={page >= query.data.pages || query.isFetching}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 disabled:opacity-40"
                >
                  Next
                </motion.button>
              </div>
            )}
          </>
        )}
      </div>
    </PageWrapper>
  );
}
