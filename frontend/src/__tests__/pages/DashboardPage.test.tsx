import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { UseQueryResult } from '@tanstack/react-query';

import type { Summary } from '../../types/dashboard';

vi.mock('../../hooks/useDashboard', () => ({ useSummary: vi.fn() }));
vi.mock('../../components/dashboard/UsageChart', () => ({
  UsageChart: () => <div data-testid="usage-chart" />,
}));
vi.mock('../../components/dashboard/RecentProjects', () => ({
  RecentProjects: () => <div data-testid="recent-projects" />,
}));
vi.mock('../../components/dashboard/TopClipsList', () => ({
  TopClipsList: () => <div data-testid="top-clips" />,
}));

import { useSummary } from '../../hooks/useDashboard';
import { DashboardPage } from '../../pages/DashboardPage';

const mockedUseSummary = vi.mocked(useSummary);

const asResult = (partial: Partial<UseQueryResult<Summary, Error>>) =>
  partial as UseQueryResult<Summary, Error>;

beforeEach(() => vi.clearAllMocks());

describe('DashboardPage', () => {
  it('renders formatted stat values from the summary query', () => {
    mockedUseSummary.mockReturnValue(
      asResult({
        data: {
          minutes_uploaded: 123.4,
          projects_total: 5,
          projects_completed: 3,
          clips_generated: 12,
          clips_downloaded: 9,
        },
        isPending: false,
        isError: false,
      }),
    );

    render(<DashboardPage />);

    expect(screen.getByText('Minutes uploaded')).toBeInTheDocument();
    expect(screen.getByText('123.4')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('3 completed')).toBeInTheDocument();
    expect(screen.getByTestId('usage-chart')).toBeInTheDocument();
  });

  it('renders the shell while the summary is still pending', () => {
    mockedUseSummary.mockReturnValue(asResult({ data: undefined, isPending: true, isError: false }));
    render(<DashboardPage />);
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText('Clips ready')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('surfaces a load error', () => {
    mockedUseSummary.mockReturnValue(
      asResult({
        data: undefined,
        isPending: false,
        isError: true,
        error: new Error('boom'),
      }),
    );
    render(<DashboardPage />);
    expect(screen.getByRole('alert')).toHaveTextContent('boom');
  });
});
