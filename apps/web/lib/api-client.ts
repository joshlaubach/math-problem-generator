const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

// ─── Error ────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ─── Internal fetch helper ────────────────────────────────────────────────────

async function req<T>(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: 'no-store' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      (body as { detail?: string }).detail ?? res.statusText,
    );
  }
  return res.json() as Promise<T>;
}

// ─── Lesson types ─────────────────────────────────────────────────────────────

export interface LessonStep {
  expression_latex: string
  description_latex: string
  student_completes: boolean
}

export interface PracticeProblem {
  prompt_latex: string
  answer_latex: string
}

export interface TopicLesson {
  topic_id: string
  topic_name: string
  course_name: string
  generated_at: string
  hook: string
  concept: string
  anatomy: string
  worked_example: LessonStep[]
  partial_example: LessonStep[]
  practice_problems: PracticeProblem[]
  common_mistakes: string[]
  untested_variants: string[]
  _fallback?: boolean
}

export interface TopicRoadmapItem {
  topic_id: string
  topic_name: string
  description: string
}

export interface UnitIntro {
  unit_id: string
  unit_name: string
  course_name: string
  generated_at: string
  hook: string
  concept: string
  topic_roadmap: TopicRoadmapItem[]
  _fallback?: boolean
}

// ─── Curriculum types (new DB-based endpoints) ───────────────────────────────

export type CalculatorMode = 'none' | 'scientific' | 'graphing' | 'cas';
export type AnswerType = 'numeric' | 'expression';
export type UserTier = 'free' | 'basic' | 'student' | 'honors' | 'classroom-student';

export interface EducationLevelResponse {
  id: string;
  name: string;
  description: string | null;
  display_order: number;
  is_active: boolean;
}

export interface CourseResponse {
  id: string;
  name: string;
  description: string | null;
  education_level_id: string;
  display_order: number;
  is_active: boolean;
  code: string | null;
  credits: number | null;
  prerequisites: string[];
}

export interface UnitResponse {
  id: string;
  name: string;
  description: string | null;
  course_id: string;
  display_order: number;
  is_active: boolean;
}

export interface TopicResponse {
  id: string;
  name: string;
  description: string | null;
  unit_id: string;
  course_id: string;
  display_order: number;
  is_active: boolean;
  prerequisites: string[];
  difficulty_min: number;
  difficulty_max: number;
}

// ─── Legacy topic registry (used by catalog + practice) ──────────────────────

export interface LegacyTopicMetadata {
  topic_id: string;
  topic_name: string;
  unit_id: string;
  unit_name: string;
  course_id: string;
  course_name: string;
  prerequisites: string[];
  calculator_mode: CalculatorMode;
  is_honors: boolean;
}

// ─── Problem types ────────────────────────────────────────────────────────────

export interface ProblemResponse {
  id: string;
  topic_id: string;
  course_id: string;
  difficulty: number;
  prompt_latex: string;
  answer_type: AnswerType;
  final_answer: string;
  solution: Record<string, unknown> | null;
  calculator_mode: CalculatorMode;
  word_problem_prompt: string | null;
  concept_ids: string[];
  primary_concept_id: string | null;
}

export interface AttemptResponse {
  user_id: string;
  problem_id: string;
  topic_id: string;
  timestamp: string;
  is_correct: boolean;
}

export interface SubmitAttemptRequest {
  user_id: string;        // required by backend model; overridden by auth on server
  problem_id: string;
  topic_id: string;
  course_id: string;
  difficulty: number;
  is_correct: boolean;
  time_taken_seconds?: number;
}

export interface HintRequest {
  problem_id: string;
  problem_latex: string;
  hint_index?: number;
  current_step_latex?: string;
  error_description?: string;
  context_tags?: string[];
}

export interface HintResponse {
  problem_id: string;
  hint: string;
  hint_type: string | null;
}

export interface UserStatsResponse {
  user_id: string;
  topic_id: string;
  total_attempts: number;
  correct_attempts: number;
  success_rate: number;
  average_difficulty: number;
  average_time_seconds: number | null;
}

export interface DifficultyRecommendationResponse {
  user_id: string;
  topic_id: string;
  recommended_difficulty: number;
  reasoning: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  tier: UserTier;
  is_teacher: boolean;
  age_confirmed: boolean;
  created_at: string;
}

export interface GenerateProblemParams {
  topic_id: string;
  difficulty: number;         // required by backend (1–6)
  calculator_mode?: CalculatorMode;
  word_problem?: boolean;
}

export interface HealthResponse {
  status: string;
  bank_size?: number;
  bank_size_per_course?: Record<string, number>;
}

// ─── API client ───────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: (): Promise<HealthResponse> =>
    req('/health', null),

  // Legacy topic registry (flat list; used by catalog + practice)
  getTopicsLegacy: (): Promise<LegacyTopicMetadata[]> =>
    req('/topics', null),

  // New DB-based curriculum (richer metadata; used for future phases)
  getEducationLevels: (): Promise<EducationLevelResponse[]> =>
    req('/curriculum/education-levels', null),

  getCourses: (): Promise<CourseResponse[]> =>
    req('/curriculum/courses', null),

  getCourse: (courseId: string): Promise<CourseResponse> =>
    req(`/curriculum/courses/${courseId}`, null),

  getUnits: (courseId?: string): Promise<UnitResponse[]> =>
    req(
      courseId ? `/curriculum/units?course_id=${courseId}` : '/curriculum/units',
      null,
    ),

  getTopics: (unitId?: string): Promise<TopicResponse[]> =>
    req(
      unitId ? `/curriculum/topics?unit_id=${unitId}` : '/curriculum/topics',
      null,
    ),

  // Problems
  generateProblem: (
    token: string,
    params: GenerateProblemParams,
  ): Promise<ProblemResponse> => {
    const qs = new URLSearchParams();
    qs.set('topic_id', params.topic_id);
    qs.set('difficulty', String(params.difficulty));
    if (params.calculator_mode) qs.set('calculator_mode', params.calculator_mode);
    if (params.word_problem) qs.set('word_problem', 'true');
    return req(`/generate?${qs}`, token);
  },

  submitAttempt: (
    token: string,
    body: SubmitAttemptRequest,
  ): Promise<AttemptResponse> =>
    req('/attempt', token, { method: 'POST', body: JSON.stringify(body) }),

  getHint: (token: string, body: HintRequest): Promise<HintResponse> =>
    req('/hint', token, { method: 'POST', body: JSON.stringify(body) }),

  // User
  getMe: (token: string): Promise<UserResponse> =>
    req('/users/me', token),

  confirmAge: (token: string): Promise<{ ok: boolean; age_confirmed: boolean }> =>
    req('/users/me/confirm-age', token, { method: 'POST' }),

  // Lesson notes (retired — returns 410)
  getLessonNotes: (unitId: string): Promise<{ unit_id: string; unit_name: string; content: string; generated_at: string }> =>
    req(`/units/${unitId}/notes`, null),

  // Topic lessons (structured JSON)
  getTopicLesson: (topicId: string): Promise<TopicLesson> =>
    req(`/topics/${topicId}/lesson`, null),

  // Unit introductions
  getUnitIntro: (unitId: string): Promise<UnitIntro> =>
    req(`/units/${unitId}/intro`, null),

  // Stats
  getMyStats: (token: string, topicId: string): Promise<UserStatsResponse> =>
    req(`/me/stats/${topicId}`, token),

  getMyRecommendation: (
    token: string,
    topicId: string,
  ): Promise<DifficultyRecommendationResponse> =>
    req(`/me/recommend/${topicId}`, token),
};
