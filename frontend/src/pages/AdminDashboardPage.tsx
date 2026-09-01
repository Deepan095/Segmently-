import { AxiosError } from 'axios';
import type { LucideIcon } from 'lucide-react';
import { Users, UserCheck, FolderKanban, Scissors, HardDrive, AlertTriangle } from 'lucide-react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { AdminStatCard } from '../components/admin/AdminStatCard';
import { useAdminStats } from '../hooks/useAdmin';
import type { PlatformStats } from '../types/admin';

const SKELETON_KEYS = ['s1', 's2', 's3', 's4', 's5', 's6'] as const;

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(
    units.length - 1,
    Math.floor(Math.log(bytes) / Math.log(1024)),
  );
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function formatCount(value: number): string {
  return value.toLocaleString();
}

interface Tile {
  label: string;
  value: string;
  icon: LucideIcon;
  hint?: string;
}

function buildTiles(stats: PlatformStats): Tile[] {
  return [
    { label: 'Total users', value: formatCount(stats.users_total), icon: Users },
    {
      label: 'Active users',
      value: formatCount(stats.users_active),
      icon: UserCheck,
      hint: `${formatCount(stats.users_total - stats.users_active)} inactive`,
    },
    { label: 'Projects', value: formatCount(stats.projects_total), icon: FolderKanban },
    { label: 'Clips', value: formatCount(stats.clips_total), icon: Scissors },
    {
      label: 'Storage (est.)',
      value: formatBytes(stats.storage_bytes_estimate),
      icon: HardDrive,
      hint: 'Uploaded source media only',
    },
    {
      label: 'Failed jobs',
      value: formatCount(stats.jobs_failed),
      icon: AlertTriangle,
    },
  ];
}

export function AdminDashboardPage() {
  const statsQuery = useAdminStats();
  const forbidden =
    statsQuery.error instanceof AxiosError && statsQuery.error.response?.status === 403;

  return (
    <PageWrapper>
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Admin</h1>
        <p className="mb-6 text-sm text-gray-500">Platform overview</p>

        {forbidden ? (
          <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
            You do not have permission to view platform stats.
          </p>
        ) : statsQuery.isError ? (
          <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            <p>Could not load platform stats.</p>
            <button
              type="button"
              onClick={() => void statsQuery.refetch()}
              className="mt-1 font-semibold underline"
            >
              Try again
            </button>
          </div>
        ) : statsQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SKELETON_KEYS.map((key) => (
              <div
                key={key}
                className="h-28 animate-pulse rounded-2xl border border-gray-200 bg-gray-100"
              />
            ))}
          </div>
        ) : statsQuery.data ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {buildTiles(statsQuery.data).map((tile) => (
              <AdminStatCard
                key={tile.label}
                label={tile.label}
                value={tile.value}
                icon={tile.icon}
                hint={tile.hint}
              />
            ))}
          </div>
        ) : null}
      </div>
    </PageWrapper>
  );
}
