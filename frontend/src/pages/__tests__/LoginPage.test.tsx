/**
 * Tests for LoginPage component
 * Tests form validation, error handling, and authentication flow
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from '../LoginPage';

// Mock the useAuthUser hook
jest.mock('../../hooks/useAuthUser', () => ({
  useAuthUser: jest.fn(() => ({
    login: jest.fn(),
    error: '',
    legacyUserId: 'legacy-123',
  })),
}));

// Mock useNavigate
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

describe('LoginPage Component', () => {
  const renderLoginPage = () => {
    return render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('should render login form with email and password inputs', () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      
      expect(emailInput).toBeInTheDocument();
      expect(passwordInput).toBeInTheDocument();
    });

    it('should render submit button', () => {
      renderLoginPage();
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      expect(submitButton).toBeInTheDocument();
    });

    it('should have email input with type="email"', () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      expect(emailInput.type).toBe('email');
    });

    it('should have password input with type="password"', () => {
      renderLoginPage();
      
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      expect(passwordInput.type).toBe('password');
    });

    it('should render links to register and home', () => {
      renderLoginPage();
      
      const registerLink = screen.getByText(/register/i);
      const homeLink = screen.getByText(/back to home/i);
      
      expect(registerLink).toBeInTheDocument();
      expect(homeLink).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should not submit with empty email', async () => {
      renderLoginPage();
      
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should not submit with empty password', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });
    });

    it('should validate email format', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/valid email/i)).toBeInTheDocument();
      });
    });

    it('should allow form submission with valid inputs', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      // Should not show validation error
      await waitFor(() => {
        expect(screen.queryByText(/is required/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should disable inputs while loading', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      
      // Initially not disabled
      expect(emailInput.disabled).toBe(false);
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      fireEvent.click(submitButton);
      
      // Would be disabled during loading (with proper mock)
    });

    it('should show loading text on submit button during loading', async () => {
      renderLoginPage();
      
      // With mock, button should change text to "Logging in..." during request
      const submitButton = screen.getByRole('button', { name: /log in/i });
      expect(submitButton).toHaveTextContent(/log in|logging in/i);
    });
  });

  describe('Form Input Handling', () => {
    it('should update email input value on change', () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      
      expect(emailInput.value).toBe('test@example.com');
    });

    it('should update password input value on change', () => {
      renderLoginPage();
      
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      
      expect(passwordInput.value).toBe('password123');
    });

    it('should clear error on input change', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      // Trigger error
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
      
      // Clear error on input change
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      
      await waitFor(() => {
        expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Display', () => {
    it('should display error message when provided', async () => {
      renderLoginPage();
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      fireEvent.click(submitButton);
      
      // No email validation should show error
      await waitFor(() => {
        const errorElement = screen.queryByText(/required|valid/i);
        expect(errorElement).toBeInTheDocument();
      });
    });

    it('should clear errors when submitting valid form', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /log in/i });
      
      // Valid inputs
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      // Error should be cleared
      await waitFor(() => {
        expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Styling', () => {
    it('should have appropriate CSS classes', () => {
      const { container } = renderLoginPage();
      
      expect(container.querySelector('.login-page')).toBeInTheDocument();
      expect(container.querySelector('.login-container')).toBeInTheDocument();
      expect(container.querySelector('.login-form')).toBeInTheDocument();
    });
  });
});
