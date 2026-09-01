import { motion } from 'framer-motion';
import { Check, Loader2, X } from 'lucide-react';
import type { JobStatus, JobType, ProcessingJob } from '../../types';
import { cn } from '../../lib/utils';

interface Stage {
  type: JobType;
  label: string;
}

const STAGES: Stage[] = [
  { type: 'download', label: 'Download' },
  { type: 'transcribe', label: 'Transcribe' },
  { type: 'segment', label: 'Segment' },
  { type: 'render', label: 'Render' },
];

interface PipelineProgressProps {
  jobs: ProcessingJob[];
}

/** Horizontal stepper for the download -> transcribe -> segment -> render pipeline. */
export function PipelineProgress({ jobs }: PipelineProgressProps) {
  const latestByType = new Map<JobType, ProcessingJob>();
  for (const job of jobs) {
    const existing = latestByType.get(job.job_type);
    if (!existing || job.created_at >= existing.created_at) {
      latestByType.set(job.job_type, job);
    }
  }

  return (
    <ol className="flex w-full items-start gap-2">
      {STAGES.map((stage, index) => {
        const job = latestByType.get(stage.type);
        const status: JobStatus = job?.status ?? 'queued';
        const isRunning = status === 'running';
        const isDone = status === 'completed';
        const isFailed = status === 'failed';

        return (
          <li key={stage.type} className="flex flex-1 flex-col items-center gap-2 text-center">
            <motion.div
              initial={false}
              animate={{ scale: isRunning ? [1, 1.08, 1] : 1 }}
              transition={
                isRunning ? { repeat: Infinity, duration: 1.4 } : { duration: 0.2 }
              }
              className={cn(
                'flex h-9 w-9 items-center justify-center rounded-full border-2',
                isDone && 'border-green-500 bg-green-500 text-white',
                isRunning && 'border-purple-500 bg-purple-50 text-purple-600',
                isFailed && 'border-red-500 bg-red-500 text-white',
                !isDone && !isRunning && !isFailed && 'border-gray-300 bg-white text-gray-400',
              )}
            >
              {isDone && <Check className="h-4 w-4" />}
              {isRunning && <Loader2 className="h-4 w-4 animate-spin" />}
              {isFailed && <X className="h-4 w-4" />}
              {!isDone && !isRunning && !isFailed && (
                <span className="text-xs font-semibold">{index + 1}</span>
              )}
            </motion.div>

            <span className="text-xs font-medium text-gray-700">{stage.label}</span>

            {isRunning && (
              <div className="h-1 w-full overflow-hidden rounded-full bg-gray-200">
                <motion.div
                  className="h-full rounded-full bg-purple-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${job?.progress_pct ?? 0}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
