import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { GlassCard } from '../ui/GlassCard';
import { cn } from '../../lib/utils';
import { useUsage } from '../../hooks/useDashboard';
import type { UsageRange } from '../../types/dashboard';

/**
 * Two measures on different scales (minutes vs. clip counts) are shown as
 * synchronised small multiples - never a dual-axis chart. Colours are the
 * categorical slots 1 (blue) and 2 (orange): a CVD-safe adjacent pair.
 */
const COLOR_MINUTES = '#2a78d6';
const COLOR_CLIPS = '#eb6834';
const SWATCH_MINUTES = 'bg-[#2a78d6]';
const SWATCH_CLIPS = 'bg-[#eb6834]';
const AXIS_INK = '#898781';
const GRID_INK = '#e1e0d9';

const RANGES: readonly UsageRange[] = ['7d', '30d', '90d'] as const;
const RANGE_LABEL: Record<UsageRange, string> = {
  '7d': '7 days',
  '30d': '30 days',
  '90d': '90 days',
};

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function formatDay(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  if (!year || !month || !day) return iso;
  return `${MONTHS[month - 1]} ${day}`;
}

interface UsageTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ value?: number | string; name?: string }>;
  unit: string;
}

function UsageTooltip({ active, label, payload, unit }: UsageTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0];
  const raw = typeof point.value === 'number' ? point.value : Number(point.value ?? 0);
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-semibold text-gray-900">{formatDay(String(label))}</p>
      <p className="mt-0.5 text-gray-600">
        <span className="font-medium text-gray-900 tabular-nums">
          {raw.toLocaleString(undefined, { maximumFractionDigits: 1 })}
        </span>{' '}
        {unit}
      </p>
    </div>
  );
}

interface ChartPoint {
  date: string;
  minutes_processed: number;
  clips_generated: number;
}

interface SeriesChartProps {
  title: string;
  color: string;
  swatchClass: string;
  dataKey: 'minutes_processed' | 'clips_generated';
  unit: string;
  data: ChartPoint[];
  showXAxis: boolean;
}

function SeriesChart({ title, color, swatchClass, dataKey, unit, data, showXAxis }: SeriesChartProps) {
  const gradientId = `usage-gradient-${dataKey}`;
  return (
    <div role="img" aria-label={`${title} over time`}>
      <div className="mb-1 flex items-center gap-2">
        <span className={cn('h-2.5 w-2.5 rounded-full', swatchClass)} aria-hidden="true" />
        <span className="text-xs font-medium text-gray-600">{title}</span>
      </div>
      <ResponsiveContainer width="100%" height={showXAxis ? 150 : 128}>
        <AreaChart
          data={data}
          margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
          accessibilityLayer
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={GRID_INK} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            hide={!showXAxis}
            tickFormatter={formatDay}
            tick={{ fill: AXIS_INK, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: GRID_INK }}
            minTickGap={24}
            interval="preserveStartEnd"
          />
          <YAxis
            width={44}
            tick={{ fill: AXIS_INK, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            content={<UsageTooltip unit={unit} />}
            cursor={{ stroke: color, strokeWidth: 1, strokeOpacity: 0.4 }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            name={title}
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const rangeButtonClasses = (isActive: boolean): string =>
  cn(
    'rounded-lg px-3 py-1 text-xs font-medium transition-colors',
    isActive ? 'bg-purple-100 text-purple-700' : 'text-gray-500 hover:bg-gray-100',
  );

export function UsageChart() {
  const [range, setRange] = useState<UsageRange>('30d');
  const { data, isPending, isError, error, refetch } = useUsage(range);

  const points = useMemo<ChartPoint[]>(
    () =>
      (data?.points ?? []).map((p) => ({
        date: p.date,
        minutes_processed: p.minutes_processed,
        clips_generated: p.clips_generated,
      })),
    [data],
  );

  const isEmpty =
    points.length > 0 &&
    points.every((p) => p.minutes_processed === 0 && p.clips_generated === 0);

  return (
    <GlassCard className="bg-white/70">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Usage</h2>
          <p className="text-xs text-gray-500">Minutes processed and clips generated per day</p>
        </div>
        <div
          className="flex items-center gap-1 rounded-xl bg-gray-50 p-1"
          role="group"
          aria-label="Select time range"
        >
          {RANGES.map((option) => (
            <motion.button
              key={option}
              type="button"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.96 }}
              onClick={() => setRange(option)}
              aria-pressed={range === option}
              className={rangeButtonClasses(range === option)}
            >
              {RANGE_LABEL[option]}
            </motion.button>
          ))}
        </div>
      </div>

      {isPending ? (
        <div className="h-72 animate-pulse rounded-xl bg-gray-100" aria-busy="true" aria-label="Loading usage data" />
      ) : isError ? (
        <div className="flex h-72 flex-col items-center justify-center gap-3 text-center">
          <p className="text-sm text-gray-600">
            {error instanceof Error ? error.message : 'Could not load usage data.'}
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
      ) : isEmpty ? (
        <div className="flex h-72 items-center justify-center text-sm text-gray-500">
          No activity in the last {RANGE_LABEL[range]} yet.
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <SeriesChart
            title="Minutes processed"
            color={COLOR_MINUTES}
            swatchClass={SWATCH_MINUTES}
            dataKey="minutes_processed"
            unit="minutes"
            data={points}
            showXAxis={false}
          />
          <SeriesChart
            title="Clips generated"
            color={COLOR_CLIPS}
            swatchClass={SWATCH_CLIPS}
            dataKey="clips_generated"
            unit="clips"
            data={points}
            showXAxis
          />
        </div>
      )}
    </GlassCard>
  );
}
