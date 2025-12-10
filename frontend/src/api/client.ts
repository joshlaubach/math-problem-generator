/**
 * API client layer for the math problem generator backend
 */

import axios, { AxiosInstance } from 'axios';
import {
  TopicMetadata,
  ProblemResponse,
  AttemptResponse,
  UserStatsResponse,
  DifficultyRecommendationResponse,
  HintResponse,
  HintRequest,
  CalculatorMode,
  TeacherTopicStatsResponse,
  TeacherUserOverviewResponse,
  TeacherRecentAttemptsResponse,
  ConceptStatsResponse,
  CourseConceptHeatmapResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Fetch all available topics
   */
  async getTopics(): Promise<TopicMetadata[]> {
    const response = await this.client.get<TopicMetadata[]>('/topics');
    return response.data;
  }

  /**
   * Generate a new problem
   */
  async generateProblem(params: {
    topicId: string;
    difficulty: number;
    calculatorMode?: CalculatorMode;
    wordProblem?: boolean;
    readingLevel?: string;
    contextTags?: string[];
  }): Promise<ProblemResponse> {
    const queryParams = new URLSearchParams();
    queryParams.append('topic_id', params.topicId);
    queryParams.append('difficulty', params.difficulty.toString());
    if (params.calculatorMode) {
      queryParams.append('calculator_mode', params.calculatorMode);
    }
    if (params.wordProblem !== undefined) {
      queryParams.append('word_problem', params.wordProblem.toString());
    }
    if (params.readingLevel) {
      queryParams.append('reading_level', params.readingLevel);
    }
    if (params.contextTags && params.contextTags.length > 0) {
      params.contextTags.forEach(tag => queryParams.append('context_tags', tag));
    }

    const response = await this.client.get<ProblemResponse>(
      `/generate?${queryParams.toString()}`
    );
    return response.data;
  }

  /**
   * Submit an attempt
   */
  async submitAttempt(data: {
    userId: string;
    problemId: string;
    topicId: string;
    courseId: string;
    difficulty: number;
    isCorrect: boolean;
    timeTakenSeconds?: number;
  }): Promise<AttemptResponse> {
    const response = await this.client.post<AttemptResponse>('/attempt', {
      user_id: data.userId,
      problem_id: data.problemId,
      topic_id: data.topicId,
      course_id: data.courseId,
      difficulty: data.difficulty,
      is_correct: data.isCorrect,
      time_taken_seconds: data.timeTakenSeconds,
    });
    return response.data;
  }

  /**
   * Get user stats for a topic
   */
  async getUserStats(userId: string, topicId: string): Promise<UserStatsResponse> {
    const response = await this.client.get<UserStatsResponse>(
      `/user/${userId}/stats/${topicId}`
    );
    return response.data;
  }

  /**
   * Get difficulty recommendation for a user on a topic
   */
  async getDifficultyRecommendation(
    userId: string,
    topicId: string
  ): Promise<DifficultyRecommendationResponse> {
    const response = await this.client.get<DifficultyRecommendationResponse>(
      `/user/${userId}/recommend/${topicId}`
    );
    return response.data;
  }

  /**
   * Request a hint for a problem
   */
  async requestHint(data: HintRequest): Promise<HintResponse> {
    const response = await this.client.post<HintResponse>('/hint', {
      problem_id: data.problem_id,
      problem_latex: data.problem_latex,
      current_step_latex: data.current_step_latex,
      error_description: data.error_description,
      context_tags: data.context_tags,
    });
    return response.data;
  }

  /**
   * Health check
   */
  async getHealth(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }

  // ========================================================================
  // Phase 7: Teacher Analytics Methods
  // ========================================================================

  /**
   * Get aggregated statistics for a topic across all users (teacher-only)
   */
  async getTeacherTopicStats(
    topicId: string,
    apiKey?: string
  ): Promise<TeacherTopicStatsResponse> {
    const headers = apiKey ? { 'X-API-Key': apiKey } : {};
    
    const response = await this.client.get<TeacherTopicStatsResponse>(
      '/teacher/topic_stats',
      {
        params: { topic_id: topicId },
        headers,
      }
    );
    return response.data;
  }

  /**
   * Get statistics for a user across all topics (teacher-only)
   */
  async getTeacherUserOverview(
    userId: string,
    apiKey?: string
  ): Promise<TeacherUserOverviewResponse> {
    const headers = apiKey ? { 'X-API-Key': apiKey } : {};
    
    const response = await this.client.get<TeacherUserOverviewResponse>(
      '/teacher/user_overview',
      {
        params: { user_id: userId },
        headers,
      }
    );
    return response.data;
  }

  /**
   * Get recent attempts across all users (teacher-only)
   */
  async getTeacherRecentAttempts(
    limit: number = 50,
    apiKey?: string
  ): Promise<TeacherRecentAttemptsResponse> {
    const headers = apiKey ? { 'X-API-Key': apiKey } : {};
    
    const response = await this.client.get<TeacherRecentAttemptsResponse>(
      '/teacher/recent_attempts',
      {
        params: { limit },
        headers,
      }
    );
    return response.data;
  }

  // ========================================================================
  // Phase 11: Concept-Level Analytics Methods
  // ========================================================================

  /**
   * Get concept-level statistics for authenticated student on a course
   */
  async getStudentConceptStats(courseId: string): Promise<CourseConceptHeatmapResponse> {
    const response = await this.client.get<CourseConceptHeatmapResponse>(
      `/me/concept_stats/${courseId}`
    );
    return response.data;
  }

  /**
   * Get concept-level statistics for a student on a course (teacher-only)
   */
  async getTeacherConceptStats(
    courseId: string,
    userId: string,
    apiKey?: string
  ): Promise<CourseConceptHeatmapResponse> {
    const headers = apiKey ? { 'X-API-Key': apiKey } : {};
    
    const response = await this.client.get<CourseConceptHeatmapResponse>(
      '/teacher/concept_stats',
      {
        params: { course_id: courseId, user_id: userId },
        headers,
      }
    );
    return response.data;
  }
}

// Singleton instance
export const apiClient = new APIClient();

