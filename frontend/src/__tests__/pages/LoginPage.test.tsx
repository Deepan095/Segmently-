import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../../components/auth/LoginForm', () => ({
  LoginForm: () => <div data-testid="login-form" />,
}));
vi.mock('../../components/auth/GoogleLoginButton', () => ({
  GoogleLoginButton: () => <button type="button">Continue with Google</button>,
}));
vi.mock('../../components/layout/MeshBackground', () => ({
  MeshBackground: () => <div data-testid="mesh-bg" />,
}));

import { useAuth } from '../../hooks/useAuth';
import { LoginPage } from '../../pages/LoginPage';

const mockedUseAuth = vi.mocked(useAuth);

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<div>dashboard page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('LoginPage', () => {
  it('renders the sign-in card and form when unauthenticated', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false } as ReturnType<typeof useAuth>);
    renderPage();
    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    expect(screen.getByText(/continue with google/i)).toBeInTheDocument();
  });

  it('redirects an already-authenticated user to the dashboard', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, email: 'a@b.com' },
      isLoading: false,
    } as ReturnType<typeof useAuth>);
    renderPage();
    expect(screen.getByText('dashboard page')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /welcome back/i })).not.toBeInTheDocument();
  });

  it('does not redirect while auth state is still loading', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true } as ReturnType<typeof useAuth>);
    renderPage();
    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
  });
});
