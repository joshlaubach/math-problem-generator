// API response types and structures

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// ============================================================================
// Phase 10: Authentication Types
// ============================================================================

export type UserRole = "anonymous" | "student" | "teacher" | "admin";

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: "student" | "teacher" | "admin";
  email?: string;
  display_name?: string;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
  role?: "student" | "teacher";
  display_name?: string;
  legacy_user_id?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: "student" | "teacher" | "admin";
  grade?: string;
  createdAt: string;
}

export interface ProblemResponse {
  id: string;
  type: string;
  difficulty: string;
  title: string;
  description: string;
  parameters?: Record<string, number>;
  hints?: string[];
  maxAttempts?: number;
}

export interface SubmissionResponse {
  submissionId: string;
  problemId: string;
  studentId: string;
  answer: number;
  isCorrect: boolean;
  feedback: string;
  score: number;
  attemptNumber: number;
  timestamp: string;
}

export interface ProgressResponse {
  studentId: string;
  totalProblems: number;
  problemsSolved: number;
  averageScore: number;
  scoresByType: Record<string, number>;
  recentSubmissions: SubmissionResponse[];
}

// ============================================================================
// Assignment Types (Phase 8)
// ============================================================================

export interface AssignmentCreateRequest {
  name: string;
  description?: string;
  topicId?: string;  // Optional if conceptIds provided
  numQuestions?: number;
  minDifficulty?: number;
  maxDifficulty?: number;
  calculatorMode?: string;
  conceptIds?: string[];  // Optional: filter by concepts (Phase 11)
}

export interface AssignmentResponse {
  id: string;
  name: string;
  description?: string;
  topicId: string;
  numQuestions: number;
  minDifficulty: number;
  maxDifficulty: number;
  calculatorMode: string;
  status: string;
  teacherId?: string;
  createdAt: string;
}

export interface AssignmentSummary {
  id: string;
  name: string;
  description?: string;
  topicId: string;
  numQuestions: number;
  status: string;
}

export interface AssignmentProblem {
  assignmentId: string;
  index: number;
  total: number;
  problem: ProblemResponse;
}

export interface AssignmentStats {
  assignmentId: string;
  topicId: string;
  numQuestions: number;
  totalStudents: number;
  totalAttempts: number;
  avgScore?: number;
  avgTimeSeconds?: number;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: PaginationMeta;
}

/**
 * Type guard to check if response is successful
 */
export function isSuccessResponse<T>(
  response: ApiResponse<T>
): response is Required<Pick<ApiResponse<T>, "success" | "data">> {
  return response.success === true && response.data !== undefined;
}

/**
 * Type guard to check if response is an error
 */
export function isErrorResponse(response: ApiResponse<any>): boolean {
  return response.success === false || response.error !== undefined;
}
