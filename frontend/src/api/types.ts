/**
 * API type definitions matching the FastAPI backend Pydantic models
 */

export type CalculatorMode = "none" | "scientific" | "graphing";
export type AnswerType = "numeric" | "expression";

export interface TopicMetadata {
  topic_id: string;
  course_id: string;
  topic_name: string;
  difficulty_range: {
    min: number;
    max: number;
  };
}

export interface ProblemResponse {
  id: string;
  course_id: string;
  unit_id: string;
  topic_id: string;
  difficulty: number;
  calculator_mode: CalculatorMode;
  prompt_latex: string;
  answer_type: AnswerType;
  final_answer: string | number;
}

export interface AttemptResponse {
  id: string;
  user_id: string;
  problem_id: string;
  topic_id: string;
  course_id: string;
  difficulty: number;
  is_correct: boolean;
  time_taken_seconds?: number;
  timestamp: string;
}

export interface UserStatsResponse {
  user_id: string;
  topic_id: string;
  total_attempts: number;
  correct_attempts: number;
  success_rate: number;
  average_difficulty: number;
  average_time_seconds: number;
}

export interface DifficultyRecommendationResponse {
  user_id: string;
  topic_id: string;
  recommended_difficulty: number;
  reasoning: string;
}

export interface HintRequest {
  problem_id: string;
  problem_latex: string;
  current_step_latex?: string;
  error_description?: string;
  context_tags?: string[];
}

export interface HintResponse {
  problem_id: string;
  hint: string;
  hint_type?: string;
}

// ============================================================================
// Phase 7: Teacher Analytics Types
// ============================================================================

export interface TeacherTopicStatsResponse {
  topic_id: string;
  total_attempts: number;
  correct_attempts: number;
  success_rate: number;
  average_difficulty?: number;
  average_time_seconds?: number;
  num_unique_students: number;
}

export interface UserTopicOverviewItem {
  topic_id: string;
  total_attempts: number;
  correct_attempts: number;
  success_rate: number;
  average_difficulty?: number;
}

export interface TeacherUserOverviewResponse {
  user_id: string;
  topics: UserTopicOverviewItem[];
  total_attempts: number;
  total_correct: number;
  overall_success_rate: number;
}

export interface RecentAttemptItem {
  user_id: string;
  topic_id: string;
  difficulty: number;
  is_correct: boolean;
  timestamp: string;
  time_taken_seconds?: number;
}

export interface TeacherRecentAttemptsResponse {
  attempts: RecentAttemptItem[];
  total_count: number;
  limit: number;
}

// ============================================================================
// Phase 11: Concept-Level Analytics Types
// ============================================================================

export interface ConceptStatsResponse {
  concept_id: string;
  concept_name: string;
  total_attempts: number;
  correct_attempts: number;
  success_rate: number;
  average_difficulty?: number;
  average_time_seconds?: number;
}

export interface CourseConceptHeatmapResponse {
  user_id: string;
  course_id: string;
  concept_stats: ConceptStatsResponse[];
  total_concepts: number;
  total_attempts: number;
}
