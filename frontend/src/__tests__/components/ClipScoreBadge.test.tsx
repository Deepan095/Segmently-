import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ClipScoreBadge } from '../../components/clips/ClipScoreBadge';

describe('ClipScoreBadge', () => {
  it('renders the score with a /100 suffix', () => {
    render(<ClipScoreBadge score={72} />);
    expect(screen.getByText('72')).toBeInTheDocument();
    expect(screen.getByText('/100')).toBeInTheDocument();
  });

  it('clamps values above 100', () => {
    render(<ClipScoreBadge score={150} />);
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByTitle('Interest score: 100 / 100')).toBeInTheDocument();
  });

  it('clamps negative values to 0 and uses the red scale', () => {
    render(<ClipScoreBadge score={-10} />);
    const badge = screen.getByTitle('Interest score: 0 / 100');
    expect(badge).toHaveTextContent('0');
    expect(badge.className).toContain('bg-red-100');
  });

  it('uses the green scale for high scores', () => {
    render(<ClipScoreBadge score={90} />);
    expect(screen.getByTitle('Interest score: 90 / 100').className).toContain('bg-green-100');
  });

  it('rounds fractional scores', () => {
    render(<ClipScoreBadge score={44.6} />);
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('supports the small size variant', () => {
    render(<ClipScoreBadge score={50} size="sm" />);
    expect(screen.getByTitle('Interest score: 50 / 100').className).toContain('text-xs');
  });
});
