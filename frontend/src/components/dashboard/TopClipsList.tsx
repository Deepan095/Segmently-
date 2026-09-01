import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Trophy } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { useTopClips } from '../../hooks/useDashboard';

const MotionLink = motion(Link);

function ScoreBadge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const fillClass =
    clamped >= 80 ? 'fill-emerald-500' : clamped >= 50 ? 'fill-sky-500' : 'fill-gray-400';
  return (
    <span
      className="flex shrink-0 items-center gap-2"
      role="img"
      aria-label={`Score ${clamped} out of 100`}
    >
      <svg viewBox="0 0 100 6" preserveAspectRatio="none" className="h-1.5 w-16" aria-hidden="true">
        <rect x="0" y="0" width="100" height="6" rx="3" className="fill-gray-100" />
        <rect x="0" y="0" width={clamped} height="6" rx="3" className={fillClass} />
      </svg>
      <span className="w-8 text-right text-xs font-semibold tabular-nums text-gray-700">
        {clamped}
      </span>
    </span>
  );
}

export function TopClipsList() {
  const { data, isPending, isError, error, refetch } = useTopClips();
  const clips = data ?? [];

  return (
    <GlassCard className="bg-white/70">
      <div className="mb-3 flex items-center gap-2">
        <Trophy className="h-4 w-4 text-amber-500" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-gray-900">Top clips</h2>
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
            {error instanceof Error ? error.message : 'Could not load clips.'}
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
      ) : clips.length === 0 ? (
        <p className="py-6 text-sm text-gray-500">
          No clips yet. Score-ranked clips show up here once a project finishes processing.
        </p>
      ) : (
        <ol className="flex flex-col divide-y divide-gray-100">
          {clips.map((clip, index) => (
            <li key={clip.id}>
              <MotionLink
                to={`/projects/${clip.project_id}`}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.99 }}
                className="flex items-center justify-between gap-3 py-2.5"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <span className="w-4 shrink-0 text-xs font-semibold tabular-nums text-gray-400">
                    {index + 1}
                  </span>
                  <span className="truncate text-sm font-medium text-gray-900">{clip.title}</span>
                </span>
                <ScoreBadge score={clip.score} />
              </MotionLink>
            </li>
          ))}
        </ol>
      )}
    </GlassCard>
  );
}
