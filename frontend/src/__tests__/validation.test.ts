// Unit tests for validation utilities

import { describe, it, expect } from "vitest";
import {
  compareAnswers,
  isAnswerCorrect,
  parseAnswerInput,
  formatNumber,
  isValidNumberInput,
} from "../../src/utils/test_validation";

describe("Validation Utilities", () => {
  describe("compareAnswers", () => {
    it("should return correct result when answer is within tolerance", () => {
      const result = compareAnswers(10, 10.005, 0.01);
      expect(result.correct).toBe(true);
      expect(result.difference).toBeLessThan(0.01);
    });

    it("should return incorrect result when answer exceeds tolerance", () => {
      const result = compareAnswers(10, 10.1, 0.01);
      expect(result.correct).toBe(false);
      expect(result.difference).toBeGreaterThan(0.01);
    });

    it("should calculate correct difference", () => {
      const result = compareAnswers(5, 7, 1);
      expect(result.difference).toBe(2);
    });
  });

  describe("isAnswerCorrect", () => {
    it("should return true for correct answers", () => {
      expect(isAnswerCorrect(5, 5)).toBe(true);
    });

    it("should return true within default tolerance", () => {
      expect(isAnswerCorrect(5, 5.005)).toBe(true);
    });

    it("should return false for incorrect answers", () => {
      expect(isAnswerCorrect(5, 6)).toBe(false);
    });
  });

  describe("parseAnswerInput", () => {
    it("should parse valid number strings", () => {
      expect(parseAnswerInput("42")).toBe(42);
      expect(parseAnswerInput("3.14")).toBe(3.14);
      expect(parseAnswerInput("-5")).toBe(-5);
    });

    it("should handle whitespace", () => {
      expect(parseAnswerInput("  42  ")).toBe(42);
    });

    it("should return null for invalid input", () => {
      expect(parseAnswerInput("")).toBeNull();
      expect(parseAnswerInput("abc")).toBeNull();
      expect(parseAnswerInput("   ")).toBeNull();
    });
  });

  describe("formatNumber", () => {
    it("should format numbers to 2 decimal places by default", () => {
      expect(formatNumber(3.14159)).toBe("3.14");
      expect(formatNumber(5)).toBe("5");
    });

    it("should format to specified decimal places", () => {
      expect(formatNumber(3.14159, 3)).toBe("3.142");
      expect(formatNumber(3.14159, 1)).toBe("3.1");
    });
  });

  describe("isValidNumberInput", () => {
    it("should return true for valid number inputs", () => {
      expect(isValidNumberInput("42")).toBe(true);
      expect(isValidNumberInput("3.14")).toBe(true);
      expect(isValidNumberInput("-5")).toBe(true);
    });

    it("should return false for invalid inputs", () => {
      expect(isValidNumberInput("abc")).toBe(false);
      expect(isValidNumberInput("")).toBe(false);
      expect(isValidNumberInput("12.34.56")).toBe(false);
    });
  });
});
