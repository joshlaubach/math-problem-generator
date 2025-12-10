import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Header } from '../components/Header';

vi.mock('../hooks/useUserIdentity', () => ({
  useUserIdentity: () => ({
    userId: 'test-user-123',
    role: 'student',
    isTeacher: false,
    switchToTeacher: vi.fn(),
    switchToStudent: vi.fn(),
  }),
}));

describe('Header Component', () => {
  it('renders the app title', () => {
    render(<Header />);
    
    const title = screen.getByText(/Math Problem Generator/i);
    expect(title).toBeInTheDocument();
  });

  it('displays current role', () => {
    render(<Header />);
    
    const roleIndicator = screen.getByText(/student/i);
    expect(roleIndicator).toBeInTheDocument();
  });

  it('displays truncated user ID', () => {
    render(<Header />);
    
    const userId = screen.getByText(/test-user/i);
    expect(userId).toBeInTheDocument();
  });

  it('has a role switch button', () => {
    render(<Header />);
    
    const button = screen.getByRole('button', { name: /switch/i });
    expect(button).toBeInTheDocument();
  });

  it('renders without crashing', () => {
    const { container } = render(<Header />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
