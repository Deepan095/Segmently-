import { cn } from '../../lib/utils';

interface ClipScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md';
}

/** Maps a 0-100 score onto a red -> green colour scale. */
function scoreClasses(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-700 ring-green-600/20';
  if (score >= 60) return 'bg-lime-100 text-lime-700 ring-lime-600/20';
  if (score >= 40) return 'bg-amber-100 text-amber-700 ring-amber-600/20';
  if (score >= 20) return 'bg-orange-100 text-orange-700 ring-orange-600/20';
  return 'bg-red-100 text-red-700 ring-red-600/20';
}

export function ClipScoreBadge({ score, size = 'md' }: ClipScoreBadgeProps) {
  const clamped = Math.min(100, Math.max(0, Math.round(score)));

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full font-semibold ring-1 ring-inset',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        scoreClasses(clamped),
      )}
      title={`Interest score: ${clamped} / 100`}
    >
      {clamped}
      <span className="font-normal opacity-60">/100</span>
    </span>
  );
}
