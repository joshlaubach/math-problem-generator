// Unit tests for mock data utilities

import { describe, it, expect } from "vitest";
import {
  getMockProblem,
  getMockProblemsByType,
  getMockProblemsByDifficulty,
  getRandomMockProblem,
  updateMockStudentProgress,
  mockProblems,
  mockStudent,
} from "../../src/utils/mock_data";

describe("Mock Data Utilities", () => {
  describe("getMockProblem", () => {
    it("should return problem by ID", () => {
      const problem = getMockProblem("prob_001");
      expect(problem).toBeDefined();
      expect(problem?.id).toBe("prob_001");
    });

    it("should return undefined for non-existent ID", () => {
      const problem = getMockProblem("non_existent");
      expect(problem).toBeUndefined();
    });
  });

  describe("getMockProblemsByType", () => {
    it("should return problems of specific type", () => {
      const algebra = getMockProblemsByType("algebra");
      expect(algebra.length).toBeGreaterThan(0);
      expect(algebra.every((p) => p.type === "algebra")).toBe(true);
    });

    it("should return empty array for non-existent type", () => {
      const problems = getMockProblemsByType("non_existent");
      expect(problems).toEqual([]);
    });
  });

  describe("getMockProblemsByDifficulty", () => {
    it("should return problems of specific difficulty", () => {
      const easy = getMockProblemsByDifficulty("easy");
      expect(easy.length).toBeGreaterThan(0);
      expect(easy.every((p) => p.difficulty === "easy")).toBe(true);
    });

    it("should return empty array for non-existent difficulty", () => {
      const problems = getMockProblemsByDifficulty("non_existent");
      expect(problems).toEqual([]);
    });
  });

  describe("getRandomMockProblem", () => {
    it("should return a problem from mock data", () => {
      const problem = getRandomMockProblem();
      expect(mockProblems).toContainEqual(problem);
    });

    it("should have all required properties", () => {
      const problem = getRandomMockProblem();
      expect(problem).toHaveProperty("id");
      expect(problem).toHaveProperty("type");
      expect(problem).toHaveProperty("difficulty");
      expect(problem).toHaveProperty("title");
      expect(problem).toHaveProperty("description");
      expect(problem).toHaveProperty("expectedAnswer");
    });
  });

  describe("updateMockStudentProgress", () => {
    it("should update student progress", () => {
      const updated = updateMockStudentProgress(100, 90);
      expect(updated.problemsSolved).toBe(100);
      expect(updated.averageScore).toBe(90);
    });

    it("should preserve other student properties", () => {
      const updated = updateMockStudentProgress(100, 90);
      expect(updated.id).toBe(mockStudent.id);
      expect(updated.name).toBe(mockStudent.name);
      expect(updated.email).toBe(mockStudent.email);
    });
  });

  describe("Mock Data Content", () => {
    it("should have mock problems", () => {
      expect(mockProblems.length).toBeGreaterThan(0);
    });

    it("should have mock student data", () => {
      expect(mockStudent).toHaveProperty("id");
      expect(mockStudent).toHaveProperty("name");
      expect(mockStudent).toHaveProperty("email");
    });
  });
});
