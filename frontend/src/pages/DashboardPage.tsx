import { Clapperboard, Clock, FolderKanban, Download } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { StatCard } from '../components/dashboard/StatCard';
import { UsageChart } from '../components/dashboard/UsageChart';
import { RecentProjects } from '../components/dashboard/RecentProjects';
import { TopClipsList } from '../components/dashboard/TopClipsList';
import { useSummary } from '../hooks/useDashboard';

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function DashboardPage() {
  const { data: summary, isPending, isError, error } = useSummary();

  const minutes = summary
    ? `${summary.minutes_uploaded.toLocaleString(undefined, { maximumFractionDigits: 1 })}`
    : '0';

  return (
    <PageWrapper>
      <div className="mx-auto max-w-6xl">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">Dashboard</h1>

        {isError ? (
          <p className="mb-6 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
            {error instanceof Error ? error.message : 'Could not load your summary.'}
          </p>
        ) : null}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Minutes uploaded"
            value={minutes}
            icon={<Clock className="h-4 w-4" />}
            isLoading={isPending}
          />
          <StatCard
            label="Projects"
            value={summary ? formatNumber(summary.projects_total) : '0'}
            delta={summary ? `${formatNumber(summary.projects_completed)} completed` : undefined}
            deltaTrend="neutral"
            icon={<FolderKanban className="h-4 w-4" />}
            isLoading={isPending}
          />
          <StatCard
            label="Clips generated"
            value={summary ? formatNumber(summary.clips_generated) : '0'}
            icon={<Clapperboard className="h-4 w-4" />}
            isLoading={isPending}
          />
          <StatCard
            label="Clips ready"
            value={summary ? formatNumber(summary.clips_downloaded) : '0'}
            icon={<Download className="h-4 w-4" />}
            isLoading={isPending}
          />
        </div>

        <div className="mt-6">
          <UsageChart />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RecentProjects />
          <TopClipsList />
        </div>
      </div>
    </PageWrapper>
  );
}
