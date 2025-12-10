// Unit tests for HTTP client and API functions

import { describe, it, beforeEach, expect, vi } from "vitest";
import { httpClient, authAPI, problemAPI, submissionAPI, progressAPI } from "../../src/services/http_client";

// Mock fetch
global.fetch = vi.fn();

describe("HTTP Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe("Authentication", () => {
    it("should save token after login", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          token: "test-token",
          user: { id: "1", name: "Test User", email: "test@example.com", role: "student" },
        }),
      });

      httpClient.setToken("test-token");
      expect(localStorage.getItem("authToken")).toBe("test-token");
    });

    it("should clear token on logout", () => {
      httpClient.setToken("test-token");
      httpClient.clearToken();
      expect(localStorage.getItem("authToken")).toBeNull();
    });
  });

  describe("Request Methods", () => {
    it("should add Authorization header when token is set", async () => {
      httpClient.setToken("test-token");

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: {} }),
      });

      await httpClient.get("/api/test");

      const calls = (global.fetch as any).mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      // Check if Authorization header was included
      const lastCall = calls[calls.length - 1];
      expect(lastCall[1].headers["Authorization"]).toContain("Bearer");
    });

    it("should handle network errors", async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error("Network error"));

      const result = await httpClient.get("/api/test");
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe("API Endpoints", () => {
    beforeEach(() => {
      (global.fetch as any).mockClear();
    });

    it("authAPI.login should call correct endpoint", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          token: "test-token",
          user: { id: "1", name: "Test", email: "test@example.com", role: "student" },
        }),
      });

      await authAPI.login("test@example.com", "password");
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/auth/login"),
        expect.any(Object)
      );
    });

    it("problemAPI.getNextProblem should call correct endpoint", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "prob_001",
          type: "algebra",
          difficulty: "easy",
          title: "Test",
          description: "Test problem",
        }),
      });

      await problemAPI.getNextProblem();
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/problems/next"),
        expect.any(Object)
      );
    });

    it("submissionAPI.submitAnswer should call correct endpoint", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          submissionId: "sub_001",
          problemId: "prob_001",
          studentId: "stud_001",
          answer: 42,
          isCorrect: true,
          feedback: "Correct!",
          score: 100,
          attemptNumber: 1,
          timestamp: new Date().toISOString(),
        }),
      });

      await submissionAPI.submitAnswer("prob_001", 42);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/submissions"),
        expect.any(Object)
      );
    });

    it("progressAPI.getProgress should call correct endpoint", async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          studentId: "stud_001",
          totalProblems: 150,
          problemsSolved: 89,
          averageScore: 85.5,
          scoresByType: { algebra: 85, geometry: 90 },
          recentSubmissions: [],
        }),
      });

      await progressAPI.getProgress();
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/progress"),
        expect.any(Object)
      );
    });
  });
});
