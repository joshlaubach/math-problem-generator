// Unit tests for API types and utilities

import { describe, it, expect } from "vitest";
import { isSuccessResponse, isErrorResponse } from "../../src/types/api_types";

describe("API Types", () => {
  describe("isSuccessResponse", () => {
    it("should return true for successful responses with data", () => {
      const response = {
        success: true,
        data: { id: "test" },
      };
      expect(isSuccessResponse(response)).toBe(true);
    });

    it("should return false for error responses", () => {
      const response = {
        success: false,
        error: "Test error",
      };
      expect(isSuccessResponse(response)).toBe(false);
    });

    it("should return false for responses without data", () => {
      const response = {
        success: true,
      };
      expect(isSuccessResponse(response)).toBe(false);
    });
  });

  describe("isErrorResponse", () => {
    it("should return true for error responses", () => {
      const response = {
        success: false,
        error: "Test error",
      };
      expect(isErrorResponse(response)).toBe(true);
    });

    it("should return false for successful responses", () => {
      const response = {
        success: true,
        data: { id: "test" },
      };
      expect(isErrorResponse(response)).toBe(false);
    });
  });
});
