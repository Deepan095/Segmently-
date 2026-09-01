import type { ReactNode } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';
import { cn } from '../../lib/utils';

export type StatDeltaTrend = 'up' | 'down' | 'neutral';

export interface StatCardProps {
  label: string;
  value: string | number;
  /** Optional supporting line under the value (e.g. "3 completed"). */
  delta?: string;
  /** Controls the delta icon + tint. Defaults to "neutral". */
  deltaTrend?: StatDeltaTrend;
  icon?: ReactNode;
  isLoading?: boolean;
}

const trendIcon: Record<StatDeltaTrend, typeof ArrowRight> = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  neutral: ArrowRight,
};

const trendText: Record<StatDeltaTrend, string> = {
  up: 'text-emerald-700',
  down: 'text-rose-700',
  neutral: 'text-gray-500',
};

export function StatCard({
  label,
  value,
  delta,
  deltaTrend = 'neutral',
  icon,
  isLoading = false,
}: StatCardProps) {
  const DeltaIcon = trendIcon[deltaTrend];

  return (
    <GlassCard className="bg-white/70">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
        {icon ? <span className="text-purple-500">{icon}</span> : null}
      </div>

      {isLoading ? (
        <div className="mt-3 h-8 w-24 animate-pulse rounded-lg bg-gray-200" aria-hidden="true" />
      ) : (
        <p className="mt-2 text-3xl font-bold tabular-nums text-gray-900">{value}</p>
      )}

      {delta && !isLoading ? (
        <p className={cn('mt-1 flex items-center gap-1 text-xs font-medium', trendText[deltaTrend])}>
          <DeltaIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {delta}
        </p>
      ) : null}
    </GlassCard>
  );
}
