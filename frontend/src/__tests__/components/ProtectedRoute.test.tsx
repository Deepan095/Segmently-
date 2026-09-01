import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../hooks/useAuth', () => ({ useAuth: vi.fn() }));

import { useAuth } from '../../hooks/useAuth';
import { ProtectedRoute } from '../../components/auth/ProtectedRoute';

const mockedUseAuth = vi.mocked(useAuth);

function renderAt(path = '/private') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/private"
          element={
            <ProtectedRoute>
              <div>secret content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('ProtectedRoute', () => {
  it('shows a loading state while auth is resolving', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true } as ReturnType<typeof useAuth>);
    renderAt();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('redirects to /login when there is no user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false } as ReturnType<typeof useAuth>);
    renderAt();
    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('secret content')).not.toBeInTheDocument();
  });

  it('renders children when a user is present', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, email: 'a@b.com' },
      isLoading: false,
    } as ReturnType<typeof useAuth>);
    renderAt();
    expect(screen.getByText('secret content')).toBeInTheDocument();
  });
});
