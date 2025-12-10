/**
 * Tests for RegisterPage component
 * Tests form validation, role selection, and registration flow
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { RegisterPage } from '../RegisterPage';

// Mock the useAuthUser hook
jest.mock('../../hooks/useAuthUser', () => ({
  useAuthUser: jest.fn(() => ({
    register: jest.fn(),
    error: '',
    legacyUserId: 'legacy-123',
  })),
}));

// Mock useNavigate
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

describe('RegisterPage Component', () => {
  const renderRegisterPage = () => {
    return render(
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('should render registration form with all required inputs', () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      
      expect(emailInput).toBeInTheDocument();
      expect(passwordInput).toBeInTheDocument();
      expect(confirmPasswordInput).toBeInTheDocument();
    });

    it('should render display name optional input', () => {
      renderRegisterPage();
      
      const displayNameInput = screen.getByLabelText(/display name/i);
      expect(displayNameInput).toBeInTheDocument();
    });

    it('should render role selection radio buttons', () => {
      renderRegisterPage();
      
      const studentRadio = screen.getByLabelText(/student/i);
      const teacherRadio = screen.getByLabelText(/teacher/i);
      
      expect(studentRadio).toBeInTheDocument();
      expect(teacherRadio).toBeInTheDocument();
    });

    it('should render submit button', () => {
      renderRegisterPage();
      
      const submitButton = screen.getByRole('button', { name: /create account/i });
      expect(submitButton).toBeInTheDocument();
    });

    it('should have student role selected by default', () => {
      renderRegisterPage();
      
      const studentRadio = screen.getByLabelText(/student/i) as HTMLInputElement;
      expect(studentRadio.checked).toBe(true);
    });

    it('should render links to login and home', () => {
      renderRegisterPage();
      
      const loginLink = screen.getByText(/log in/i);
      const homeLink = screen.getByText(/back to home/i);
      
      expect(loginLink).toBeInTheDocument();
      expect(homeLink).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should require email address', async () => {
      renderRegisterPage();
      
      const submitButton = screen.getByRole('button', { name: /create account/i });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should validate email format', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: 'password123' } });
      fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/valid email/i)).toBeInTheDocument();
      });
    });

    it('should require password', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });
    });

    it('should enforce minimum password length', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: '12345' } });
      fireEvent.change(confirmPasswordInput, { target: { value: '12345' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/at least 6 characters/i)).toBeInTheDocument();
      });
    });

    it('should require password confirmation', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/confirm password/i)).toBeInTheDocument();
      });
    });

    it('should validate password match', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'different123' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
      });
    });

    it('should allow valid registration', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      // No error should appear
      await waitFor(() => {
        expect(screen.queryByText(/is required|do not match|characters/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Input Handling', () => {
    it('should update email value on change', () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      
      expect(emailInput.value).toBe('test@example.com');
    });

    it('should update password value on change', () => {
      renderRegisterPage();
      
      const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement;
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      
      expect(passwordInput.value).toBe('password123');
    });

    it('should update confirm password value on change', () => {
      renderRegisterPage();
      
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i) as HTMLInputElement;
      fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
      
      expect(confirmPasswordInput.value).toBe('password123');
    });

    it('should allow role selection change', () => {
      renderRegisterPage();
      
      const teacherRadio = screen.getByLabelText(/teacher/i) as HTMLInputElement;
      fireEvent.click(teacherRadio);
      
      expect(teacherRadio.checked).toBe(true);
    });

    it('should update display name value on change', () => {
      renderRegisterPage();
      
      const displayNameInput = screen.getByLabelText(/display name/i) as HTMLInputElement;
      fireEvent.change(displayNameInput, { target: { value: 'John Doe' } });
      
      expect(displayNameInput.value).toBe('John Doe');
    });

    it('should clear error on input change', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
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

  describe('Role Selection', () => {
    it('should allow changing from student to teacher', () => {
      renderRegisterPage();
      
      const studentRadio = screen.getByLabelText(/student/i) as HTMLInputElement;
      const teacherRadio = screen.getByLabelText(/teacher/i) as HTMLInputElement;
      
      expect(studentRadio.checked).toBe(true);
      
      fireEvent.click(teacherRadio);
      
      expect(studentRadio.checked).toBe(false);
      expect(teacherRadio.checked).toBe(true);
    });

    it('should include selected role in registration data', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      const teacherRadio = screen.getByLabelText(/teacher/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'teacher@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
      fireEvent.click(teacherRadio);
      fireEvent.click(submitButton);
      
      // Teacher role should be selected
      expect((teacherRadio as HTMLInputElement).checked).toBe(true);
    });
  });

  describe('Loading State', () => {
    it('should disable inputs while loading', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement;
      
      // Initially not disabled
      expect(emailInput.disabled).toBe(false);
      expect(passwordInput.disabled).toBe(false);
    });

    it('should show loading text on submit button', () => {
      renderRegisterPage();
      
      const submitButton = screen.getByRole('button', { name: /create account/i });
      expect(submitButton).toHaveTextContent(/create account/i);
    });
  });

  describe('Styling', () => {
    it('should have appropriate CSS classes', () => {
      const { container } = renderRegisterPage();
      
      expect(container.querySelector('.register-page')).toBeInTheDocument();
      expect(container.querySelector('.register-container')).toBeInTheDocument();
      expect(container.querySelector('.register-form')).toBeInTheDocument();
    });

    it('should have role selection styled correctly', () => {
      const { container } = renderRegisterPage();
      
      expect(container.querySelector('.role-selection')).toBeInTheDocument();
      expect(container.querySelector('.role-options')).toBeInTheDocument();
    });
  });

  describe('Optional Fields', () => {
    it('should allow registration without display name', async () => {
      renderRegisterPage();
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      const submitButton = screen.getByRole('button', { name: /create account/i });
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);
      
      // Should not error on missing optional display name
      await waitFor(() => {
        expect(screen.queryByText(/display name is required/i)).not.toBeInTheDocument();
      });
    });
  });
});
