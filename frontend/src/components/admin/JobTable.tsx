import { useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import { motion } from 'framer-motion';
import { Loader2, RotateCcw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAdminJobs, useRetryJob } from '../../hooks/useAdmin';
import type { AdminJobStatusFilter } from '../../types/admin';
import type { JobStatus } from '../../types';

const STATUS_FILTERS: { value: AdminJobStatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'queued', label: 'Queued' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

const STATUS_BADGE: Record<JobStatus, string> = {
  queued: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

function statusOf(error: unknown): number | undefined {
  return error instanceof AxiosError ? error.response?.status : undefined;
}

function badgeClass(status: string): string {
  return STATUS_BADGE[status as JobStatus] ?? 'bg-gray-100 text-gray-600';
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

export function JobTable() {
  const [filter, setFilter] = useState<AdminJobStatusFilter>('all');
  const [page, setPage] = useState(1);
  const [pendingJobId, setPendingJobId] = useState<number | null>(null);

  const jobsQuery = useAdminJobs(filter, page);
  const retryJob = useRetryJob();

  const rows = useMemo(() => jobsQuery.data?.items ?? [], [jobsQuery.data]);
  const totalPages = jobsQuery.data?.pages ?? 1;
  const forbidden = statusOf(jobsQuery.error) === 403;

  const handleFilter = (value: AdminJobStatusFilter) => {
    setFilter(value);
    setPage(1);
  };

  const handleRetry = (jobId: number) => {
    setPendingJobId(jobId);
    retryJob.mutate(jobId, {
      onSettled: () =>
        setPendingJobId((current) => (current === jobId ? null : current)),
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((option) => (
          <motion.button
            key={option.value}
            type="button"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleFilter(option.value)}
            aria-pressed={filter === option.value}
            className={cn(
              'rounded-full border px-3 py-1.5 text-sm font-medium transition-colors',
              filter === option.value
                ? 'border-purple-500 bg-purple-500 text-white'
                : 'border-gray-200 text-gray-600 hover:bg-gray-100',
            )}
          >
            {option.label}
          </motion.button>
        ))}
        {jobsQuery.isFetching ? (
          <Loader2 className="h-4 w-4 animate-spin text-gray-400" aria-hidden />
        ) : null}
      </div>

      {retryJob.isError ? (
        <p className="text-sm text-red-500" role="alert">
          {retryJob.error.message}
        </p>
      ) : null}
      {retryJob.isSuccess && pendingJobId === null ? (
        <p className="text-sm text-green-600" role="status">
          Job re-queued.
        </p>
      ) : null}

      {forbidden ? (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          You do not have permission to view jobs.
        </p>
      ) : jobsQuery.isError ? (
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          <p>Could not load jobs.</p>
          <button
            type="button"
            onClick={() => void jobsQuery.refetch()}
            className="mt-1 font-semibold underline"
          >
            Try again
          </button>
        </div>
      ) : jobsQuery.isLoading ? (
        <p className="px-1 py-8 text-center text-sm text-gray-500">Loading jobs...</p>
      ) : rows.length === 0 ? (
        <p className="px-1 py-8 text-center text-sm text-gray-500">
          {filter === 'all' ? 'No jobs yet.' : `No ${filter} jobs.`}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">Job</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Progress</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50/60">
                  <td className="px-4 py-3 font-medium text-gray-900">#{job.id}</td>
                  <td className="px-4 py-3 text-gray-700">#{job.project_id}</td>
                  <td className="px-4 py-3 text-gray-700">{job.job_type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2 py-0.5 text-xs font-semibold',
                        badgeClass(job.status),
                      )}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-100">
                        <motion.div
                          className="h-full rounded-full bg-purple-500"
                          initial={false}
                          animate={{
                            width: `${Math.min(100, Math.max(0, job.progress_pct))}%`,
                          }}
                          transition={{ duration: 0.4 }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{job.progress_pct}%</span>
                    </div>
                    {job.error_message ? (
                      <p className="mt-1 max-w-xs truncate text-xs text-red-500" title={job.error_message}>
                        {job.error_message}
                      </p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {formatDate(job.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {job.status === 'failed' ? (
                      <motion.button
                        type="button"
                        whileHover={{ scale: pendingJobId === job.id ? 1 : 1.05 }}
                        whileTap={{ scale: pendingJobId === job.id ? 1 : 0.95 }}
                        disabled={pendingJobId === job.id}
                        onClick={() => handleRetry(job.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                      >
                        {pendingJobId === job.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RotateCcw className="h-3.5 w-3.5" />
                        )}
                        Retry
                      </motion.button>
                    ) : (
                      <span className="text-xs text-gray-300">--</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!jobsQuery.isError && totalPages > 1 ? (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <motion.button
              type="button"
              whileHover={{ scale: page > 1 ? 1.05 : 1 }}
              whileTap={{ scale: page > 1 ? 0.95 : 1 }}
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-lg border border-gray-200 px-3 py-1.5 font-medium disabled:opacity-50"
            >
              Previous
            </motion.button>
            <motion.button
              type="button"
              whileHover={{ scale: page < totalPages ? 1.05 : 1 }}
              whileTap={{ scale: page < totalPages ? 0.95 : 1 }}
              disabled={page >= totalPages}
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              className="rounded-lg border border-gray-200 px-3 py-1.5 font-medium disabled:opacity-50"
            >
              Next
            </motion.button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
