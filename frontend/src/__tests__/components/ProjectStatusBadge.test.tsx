import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProjectStatusBadge } from '../../components/projects/ProjectStatusBadge';
import type { ProjectStatus } from '../../types';

describe('ProjectStatusBadge', () => {
  it.each<[ProjectStatus, string]>([
    ['pending', 'Pending'],
    ['downloading', 'Downloading'],
    ['transcribing', 'Transcribing'],
    ['segmenting', 'Segmenting'],
    ['rendering', 'Rendering'],
    ['completed', 'Completed'],
    ['failed', 'Failed'],
  ])('renders the %s status as "%s"', (status, label) => {
    render(<ProjectStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('applies a caller-supplied className', () => {
    render(<ProjectStatusBadge status="completed" className="my-custom-class" />);
    expect(screen.getByText('Completed')).toHaveClass('my-custom-class');
  });

  it('uses the failed colour tokens for a failed project', () => {
    render(<ProjectStatusBadge status="failed" />);
    expect(screen.getByText('Failed').className).toContain('text-red-700');
  });
});
