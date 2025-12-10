/**
 * Hook for managing user identity and role
 */

import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

export type UserRole = 'student' | 'teacher';

interface UseUserIdentityReturn {
  userId: string;
  role: UserRole;
  isTeacher: boolean;
  setRole: (role: UserRole) => void;
  switchToTeacher: (accessCode: string) => boolean;
  switchToStudent: () => void;
}

const STORAGE_USER_ID_KEY = 'mpg_user_id';
const STORAGE_ROLE_KEY = 'mpg_role';
const TEACHER_ACCESS_CODE = import.meta.env.VITE_TEACHER_ACCESS_CODE || 'TEACHER123';

export function useUserIdentity(): UseUserIdentityReturn {
  const [userId, setUserId] = useState<string>(() => {
    const stored = localStorage.getItem(STORAGE_USER_ID_KEY);
    if (stored) {
      return stored;
    }
    const newId = uuidv4();
    localStorage.setItem(STORAGE_USER_ID_KEY, newId);
    return newId;
  });

  const [role, setRoleState] = useState<UserRole>(() => {
    const stored = localStorage.getItem(STORAGE_ROLE_KEY);
    return (stored as UserRole) || 'student';
  });

  const setRole = (newRole: UserRole) => {
    setRoleState(newRole);
    localStorage.setItem(STORAGE_ROLE_KEY, newRole);
  };

  const switchToTeacher = (accessCode: string): boolean => {
    if (accessCode === TEACHER_ACCESS_CODE) {
      setRole('teacher');
      return true;
    }
    return false;
  };

  const switchToStudent = () => {
    setRole('student');
  };

  return {
    userId,
    role,
    isTeacher: role === 'teacher',
    setRole,
    switchToTeacher,
    switchToStudent,
  };
}
