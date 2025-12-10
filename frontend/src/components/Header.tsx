/**
 * Header component with authentication and role handling
 * Supports both old useUserIdentity and new useAuthUser patterns
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserRole } from '../hooks/useUserIdentity';
import { useAuthUser } from '../hooks/useAuthUser';
import { TEACHER_ACCESS_CODE } from '../config';
import './Header.css';

interface HeaderProps {
  role: UserRole;
  isTeacher: boolean;
  userId: string;
  onSwitchToTeacher: (code: string) => boolean;
  onSwitchToStudent: () => void;
}

export function Header({
  role,
  isTeacher,
  userId,
  onSwitchToTeacher,
  onSwitchToStudent,
}: HeaderProps) {
  const navigate = useNavigate();
  const { isAuthenticated, email, displayName, logout } = useAuthUser();
  const [showAccessCodeModal, setShowAccessCodeModal] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [accessError, setAccessError] = useState('');

  const handleRequestTeacherMode = () => {
    setShowAccessCodeModal(true);
    setAccessError('');
    setAccessCode('');
  };

  const handleSubmitAccessCode = () => {
    if (onSwitchToTeacher(accessCode)) {
      setShowAccessCodeModal(false);
      setAccessCode('');
    } else {
      setAccessError('Invalid access code');
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleLogin = () => {
    navigate('/login');
  };

  const handleRegister = () => {
    navigate('/register');
  };

  return (
    <>
      <header className="header">
        <div className="header-content">
          <h1 style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            Math Problem Generator
          </h1>
          <div className="header-right">
            {isAuthenticated ? (
              <>
                <div className="auth-info">
                  <span className="user-email">{email || displayName || 'User'}</span>
                  <span className="user-role">({role})</span>
                </div>
                <button onClick={handleLogout} className="btn btn-secondary">
                  Logout
                </button>
              </>
            ) : (
              <>
                <div className="auth-buttons">
                  <button onClick={handleLogin} className="btn btn-primary-outline">
                    Login
                  </button>
                  <button onClick={handleRegister} className="btn btn-primary">
                    Register
                  </button>
                </div>
              </>
            )}

            <div className="role-indicator">
              <span>Role: <strong>{role}</strong></span>
              <span className="user-id">ID: {userId.slice(0, 8)}</span>
            </div>
            <div className="role-switch">
              {isTeacher ? (
                <button onClick={onSwitchToStudent} className="btn btn-secondary">
                  Switch to Student
                </button>
              ) : (
                <button onClick={handleRequestTeacherMode} className="btn btn-secondary">
                  Switch to Teacher
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {showAccessCodeModal && (
        <div className="modal-overlay" onClick={() => setShowAccessCodeModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Teacher Access Required</h2>
            <p>Enter the teacher access code to access teacher features.</p>
            <input
              type="password"
              placeholder="Access code"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSubmitAccessCode()}
              className="input"
            />
            {accessError && <div className="error-message">{accessError}</div>}
            <div className="modal-buttons">
              <button onClick={handleSubmitAccessCode} className="btn btn-primary">
                Submit
              </button>
              <button
                onClick={() => setShowAccessCodeModal(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
