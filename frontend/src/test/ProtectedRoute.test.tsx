import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProtectedRoute from '../components/ProtectedRoute';

// Mock AuthContext
const mockUseAuth = vi.fn();
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

function TestChild() {
  return <div data-testid="protected-content">Protected Content</div>;
}

function AuthRedirectCapture() {
  return <div data-testid="auth-page">Auth Page</div>;
}

function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <TestChild />
            </ProtectedRoute>
          }
        />
        <Route path="/auth" element={<AuthRedirectCapture />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    renderWithRouter('/protected');
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('redirects to /auth when not authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    renderWithRouter('/protected');
    expect(screen.getByTestId('auth-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('shows loading state while auth is loading', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });
    renderWithRouter('/protected');
    expect(screen.getByText(/checking authentication/i)).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });
});
