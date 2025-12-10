import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthUser } from '../hooks/useAuthUser';
import { UserRole } from '../types/api_types';
import './RegisterPage.css';

interface FormState {
  email: string;
  password: string;
  confirmPassword: string;
  displayName: string;
  role: Extract<UserRole, 'student' | 'teacher'>;
}

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register, legacyUserId, error } = useAuthUser();
  const [formData, setFormData] = useState<FormState>({
    email: '',
    password: '',
    confirmPassword: '',
    displayName: '',
    role: 'student',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string>('');

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev: FormState) => ({
      ...prev,
      [name]: value,
    }));
    setValidationError('');
  };

  const validateForm = (): boolean => {
    if (!formData.email.trim()) {
      setValidationError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setValidationError('Please enter a valid email address');
      return false;
    }
    if (!formData.password.trim()) {
      setValidationError('Password is required');
      return false;
    }
    if (formData.password.length < 6) {
      setValidationError('Password must be at least 6 characters');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setValidationError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationError('');

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const registerData = {
        email: formData.email,
        password: formData.password,
        role: formData.role,
        display_name: formData.displayName || undefined,
        legacy_user_id: legacyUserId,
      };

      await register(registerData);

      // Success - navigate to home
      navigate('/');
    } catch (err) {
      // Error is handled by useAuthUser hook and displayed
      setValidationError(
        error || 'Registration failed. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const displayError = validationError || error;

  return (
    <div className="register-page">
      <div className="register-container">
        <h1>Create Account</h1>

        {displayError && <div className="error-message">{displayError}</div>}

        <form className="register-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="At least 6 characters"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="displayName">Display Name (Optional)</label>
            <input
              id="displayName"
              type="text"
              name="displayName"
              value={formData.displayName}
              onChange={handleChange}
              placeholder="Your name (optional)"
              disabled={isLoading}
            />
          </div>

          <div className="form-group role-selection">
            <label>I am a:</label>
            <div className="role-options">
              <label className="radio-label">
                <input
                  type="radio"
                  name="role"
                  value="student"
                  checked={formData.role === 'student'}
                  onChange={handleChange}
                  disabled={isLoading}
                />
                <span>Student</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="role"
                  value="teacher"
                  checked={formData.role === 'teacher'}
                  onChange={handleChange}
                  disabled={isLoading}
                />
                <span>Teacher</span>
              </label>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="register-footer">
          <p>
            Already have an account?{' '}
            <a onClick={() => navigate('/login')}>Log in here</a>
          </p>
          <p>
            <a onClick={() => navigate('/')}>Back to Home</a>
          </p>
        </div>
      </div>
    </div>
  );
};
