// HTTP client for API communication

import {
  ApiResponse,
  AuthResponse,
  AuthTokenResponse,
  UserRegisterRequest,
  UserLoginRequest,
  ProblemResponse,
  SubmissionResponse,
  ProgressResponse,
  PaginatedResponse,
  AssignmentResponse,
  AssignmentSummary,
  AssignmentProblem,
  AssignmentStats,
} from "../types/api_types";

const API_BASE_URL = "http://localhost:8000";

class HttpClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.loadToken();
  }

  /**
   * Load stored authentication token
   */
  private loadToken(): void {
    this.token = localStorage.getItem("authToken");
  }

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    this.token = token;
    localStorage.setItem("authToken", token);
  }

  /**
   * Clear authentication token
   */
  clearToken(): void {
    this.token = null;
    localStorage.removeItem("authToken");
  }

  /**
   * Get default headers with authentication
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Make a GET request
   */
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "GET",
        headers: this.getHeaders(),
      });

      return this.handleResponse<T>(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  /**
   * Make a POST request
   */
  async post<T>(
    endpoint: string,
    data: Record<string, any>
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });

      return this.handleResponse<T>(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  /**
   * Make a PUT request
   */
  async put<T>(
    endpoint: string,
    data: Record<string, any>
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "PUT",
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      });

      return this.handleResponse<T>(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  /**
   * Make a DELETE request
   */
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "DELETE",
        headers: this.getHeaders(),
      });

      return this.handleResponse<T>(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  /**
   * Handle HTTP response
   */
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.error || "An error occurred",
        message: data.message,
      };
    }

    return {
      success: true,
      data,
      message: data.message,
    };
  }

  /**
   * Handle request error
   */
  private handleError(error: any): ApiResponse<any> {
    console.error("HTTP Client Error:", error);
    return {
      success: false,
      error: error.message || "Network error",
    };
  }
}

// Export singleton instance
export const httpClient = new HttpClient();

// ============================================================================
// Phase 10: Token Management
// ============================================================================

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (token) {
    localStorage.setItem("mpg_token", token);
  } else {
    localStorage.removeItem("mpg_token");
  }
  // Also update httpClient's token
  if (token) {
    httpClient.setToken(token);
  } else {
    httpClient.clearToken();
  }
}

export function getAuthToken(): string | null {
  if (authToken !== null) return authToken;
  const stored = localStorage.getItem("mpg_token");
  authToken = stored ?? null;
  return authToken;
}

export function clearAuthToken(): void {
  setAuthToken(null);
}

// ============================================================================
// Phase 10: Authentication API calls
// ============================================================================

export const authAPI = {
  async register(
    data: UserRegisterRequest
  ): Promise<AuthTokenResponse> {
    const response = await httpClient.post<AuthTokenResponse>(
      "/auth/register",
      data
    );

    if (response.success && response.data) {
      setAuthToken(response.data.access_token);
      // Store user info
      localStorage.setItem(
        "mpg_user_info",
        JSON.stringify({
          user_id: response.data.user_id,
          role: response.data.role,
          email: response.data.email,
          display_name: response.data.display_name,
        })
      );
      return response.data;
    }

    throw new Error(response.error || "Registration failed");
  },

  async login(data: UserLoginRequest): Promise<AuthTokenResponse> {
    const response = await httpClient.post<AuthTokenResponse>(
      "/auth/login",
      data
    );

    if (response.success && response.data) {
      setAuthToken(response.data.access_token);
      // Store user info
      localStorage.setItem(
        "mpg_user_info",
        JSON.stringify({
          user_id: response.data.user_id,
          role: response.data.role,
          email: response.data.email,
          display_name: response.data.display_name,
        })
      );
      return response.data;
    }

    throw new Error(response.error || "Login failed");
  },

  logout(): void {
    clearAuthToken();
    localStorage.removeItem("mpg_user_info");
  },
};

/**
 * Legacy Authentication API calls (backward compatible)
 */
export const legacyAuthAPI = {
  login: async (email: string, password: string): Promise<ApiResponse<AuthResponse>> => {
    return httpClient.post<AuthResponse>("/api/auth/login", {
      email,
      password,
    });
  },

  register: async (
    name: string,
    email: string,
    password: string,
    role: string = "student"
  ): Promise<ApiResponse<AuthResponse>> => {
    return httpClient.post<AuthResponse>("/api/auth/register", {
      name,
      email,
      password,
      role,
    });
  },

  logout: async (): Promise<ApiResponse<any>> => {
    httpClient.clearToken();
    return { success: true };
  },

  getCurrentUser: async (): Promise<ApiResponse<any>> => {
    return httpClient.get("/api/auth/me");
  },
};

/**
 * Problem API calls
 */
export const problemAPI = {
  getNextProblem: async (): Promise<ApiResponse<ProblemResponse>> => {
    return httpClient.get<ProblemResponse>("/api/problems/next");
  },

  getProblem: async (id: string): Promise<ApiResponse<ProblemResponse>> => {
    return httpClient.get<ProblemResponse>(`/api/problems/${id}`);
  },

  getProblems: async (
    type?: string,
    difficulty?: string
  ): Promise<PaginatedResponse<ProblemResponse>> => {
    const params = new URLSearchParams();
    if (type) params.append("type", type);
    if (difficulty) params.append("difficulty", difficulty);

    return httpClient.get<ProblemResponse[]>(
      `/api/problems?${params.toString()}`
    ) as Promise<PaginatedResponse<ProblemResponse>>;
  },
};

/**
 * Submission API calls
 */
export const submissionAPI = {
  submitAnswer: async (
    problemId: string,
    answer: number
  ): Promise<ApiResponse<SubmissionResponse>> => {
    return httpClient.post<SubmissionResponse>("/api/submissions", {
      problemId,
      answer,
    });
  },

  getSubmissions: async (
    studentId?: string
  ): Promise<PaginatedResponse<SubmissionResponse>> => {
    const endpoint = studentId
      ? `/api/submissions?studentId=${studentId}`
      : "/api/submissions";

    return httpClient.get<SubmissionResponse[]>(endpoint) as Promise<
      PaginatedResponse<SubmissionResponse>
    >;
  },
};

/**
 * Progress API calls
 */
export const progressAPI = {
  getProgress: async (): Promise<ApiResponse<ProgressResponse>> => {
    return httpClient.get<ProgressResponse>("/api/progress");
  },

  getStudentProgress: async (
    studentId: string
  ): Promise<ApiResponse<ProgressResponse>> => {
    return httpClient.get<ProgressResponse>(`/api/progress/${studentId}`);
  },
};

/**
 * Assignment API calls (Phase 8)
 */
export const assignmentAPI = {
  createAssignment: async (
    data: {
      name: string;
      description?: string;
      topicId?: string;  // Optional if conceptIds provided
      numQuestions?: number;
      minDifficulty?: number;
      maxDifficulty?: number;
      calculatorMode?: string;
      conceptIds?: string[];  // Optional: filter by concepts
    },
    apiKey?: string
  ): Promise<ApiResponse<AssignmentResponse>> => {
    const request_data: Record<string, unknown> = {
      name: data.name,
      description: data.description,
      num_questions: data.numQuestions,
      min_difficulty: data.minDifficulty,
      max_difficulty: data.maxDifficulty,
      calculator_mode: data.calculatorMode,
    };
    
    // Add either topic_id or concept_ids
    if (data.topicId) {
      request_data.topic_id = data.topicId;
    }
    if (data.conceptIds && data.conceptIds.length > 0) {
      request_data.concept_ids = data.conceptIds;
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    // Manual fetch for custom headers
    try {
      const response = await fetch(`http://localhost:8000/teacher/assignments`, {
        method: "POST",
        headers,
        body: JSON.stringify(request_data),
      });

      const result = await response.json();
      if (!response.ok) {
        return {
          success: false,
          error: result.error || "Failed to create assignment",
        };
      }

      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  },

  getAssignmentSummary: async (
    assignmentId: string
  ): Promise<ApiResponse<AssignmentSummary>> => {
    return httpClient.get<AssignmentSummary>(
      `/assignments/${assignmentId}`
    );
  },

  getAssignmentProblem: async (
    assignmentId: string,
    index: number
  ): Promise<ApiResponse<AssignmentProblem>> => {
    return httpClient.get<AssignmentProblem>(
      `/assignments/${assignmentId}/problem/${index}`
    );
  },

  getAssignmentStats: async (
    assignmentId: string,
    apiKey?: string
  ): Promise<ApiResponse<AssignmentStats>> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/teacher/assignments/${assignmentId}/stats`,
        {
          method: "GET",
          headers,
        }
      );

      const result = await response.json();
      if (!response.ok) {
        return {
          success: false,
          error: result.error || "Failed to get assignment stats",
        };
      }

      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  },
};
