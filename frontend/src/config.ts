/**
 * Frontend configuration
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const TEACHER_ACCESS_CODE = import.meta.env.VITE_TEACHER_ACCESS_CODE || 'TEACHER123';

// Phase 7: Teacher API Key (optional, for protected teacher endpoints)
// If set in env, will be sent as X-API-Key header for teacher endpoints
export const TEACHER_API_KEY = import.meta.env.VITE_TEACHER_API_KEY || '';

