/*
Frontend Tests for Assignment Features

Tests for TeacherAssignments and AssignmentRunner components.
Uses vitest + @testing-library/react for testing.

To run: npm test -- TeacherAssignments.test.tsx
*/

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TeacherAssignments from "../components/TeacherAssignments";
import AssignmentRunner from "../pages/AssignmentRunner";
import * as httpClient from "../services/http_client";

// Mock the HTTP client
vi.mock("../services/http_client");

// ============================================================================
// TeacherAssignments Component Tests
// ============================================================================

describe("TeacherAssignments Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Create Assignment Tab", () => {
    it("renders assignment creation form", () => {
      render(<TeacherAssignments />);

      expect(screen.getByText("Create Assignment")).toBeInTheDocument();
      expect(screen.getByLabelText("Assignment Name *")).toBeInTheDocument();
      expect(screen.getByLabelText("Description")).toBeInTheDocument();
      expect(screen.getByLabelText("Topic *")).toBeInTheDocument();
      expect(screen.getByLabelText("Number of Questions")).toBeInTheDocument();
      expect(screen.getByLabelText("Min Difficulty")).toBeInTheDocument();
      expect(screen.getByLabelText("Max Difficulty")).toBeInTheDocument();
      expect(screen.getByLabelText("Calculator Mode")).toBeInTheDocument();
    });

    it("handles form input changes", async () => {
      const user = userEvent.setup();
      render(<TeacherAssignments />);

      const nameInput = screen.getByLabelText(
        "Assignment Name *"
      ) as HTMLInputElement;
      await user.type(nameInput, "Algebra Quiz 1");

      expect(nameInput.value).toBe("Algebra Quiz 1");
    });

    it("submits assignment creation form successfully", async () => {
      const mockCreateAssignment = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Algebra Quiz 1",
          topicId: "algebra",
          numQuestions: 10,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
          status: "active",
          teacherId: "teacher1",
          createdAt: new Date(),
        },
      });

      vi.mocked(httpClient.assignmentAPI.createAssignment).mockImplementation(
        mockCreateAssignment
      );

      const user = userEvent.setup();
      render(<TeacherAssignments />);

      // Fill form
      await user.type(
        screen.getByLabelText("Assignment Name *"),
        "Algebra Quiz 1"
      );
      await user.type(
        screen.getByLabelText("Number of Questions"),
        "10"
      );

      // Submit
      await user.click(screen.getByText("Create Assignment"));

      await waitFor(() => {
        expect(mockCreateAssignment).toHaveBeenCalled();
      });

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText("✓ Assignment Created")).toBeInTheDocument();
        expect(screen.getByText("ALG1-XYZ123")).toBeInTheDocument();
      });
    });

    it("displays error message on creation failure", async () => {
      const mockCreateAssignment = vi.fn().mockResolvedValue({
        success: false,
        error: "Teacher API key required",
      });

      vi.mocked(httpClient.assignmentAPI.createAssignment).mockImplementation(
        mockCreateAssignment
      );

      const user = userEvent.setup();
      render(<TeacherAssignments />);

      // Fill form with just name
      await user.type(
        screen.getByLabelText("Assignment Name *"),
        "Test Assignment"
      );

      // Submit
      await user.click(screen.getByText("Create Assignment"));

      await waitFor(() => {
        expect(
          screen.getByText("Teacher API key required")
        ).toBeInTheDocument();
      });
    });

    it("disables submit button when name is empty", () => {
      render(<TeacherAssignments />);

      const submitButton = screen.getByText(
        "Create Assignment"
      ) as HTMLButtonElement;

      expect(submitButton.disabled).toBe(true);
    });

    it("allows copying assignment code", async () => {
      const user = userEvent.setup();

      // Mock clipboard API
      const mockClipboard = vi.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: mockClipboard,
        },
      });

      const mockCreateAssignment = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Test Assignment",
          topicId: "algebra",
          numQuestions: 10,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
          status: "active",
          teacherId: "teacher1",
          createdAt: new Date(),
        },
      });

      vi.mocked(httpClient.assignmentAPI.createAssignment).mockImplementation(
        mockCreateAssignment
      );

      render(<TeacherAssignments />);

      // Create assignment
      await user.type(
        screen.getByLabelText("Assignment Name *"),
        "Test Assignment"
      );
      await user.click(screen.getByText("Create Assignment"));

      // Wait for success card
      await waitFor(() => {
        expect(screen.getByText("Copy Code")).toBeInTheDocument();
      });

      // Click copy button
      await user.click(screen.getByText("Copy Code"));

      expect(mockClipboard).toHaveBeenCalledWith("ALG1-XYZ123");
    });
  });

  describe("Stats Tab", () => {
    it("renders stats form", () => {
      render(<TeacherAssignments />);

      // Click stats tab
      fireEvent.click(screen.getByText("View Stats"));

      expect(screen.getByLabelText("Assignment Code")).toBeInTheDocument();
      expect(screen.getByText("Load Stats")).toBeInTheDocument();
    });

    it("loads and displays assignment stats", async () => {
      const mockGetStats = vi.fn().mockResolvedValue({
        success: true,
        data: {
          assignmentId: "ALG1-XYZ123",
          totalStudents: 25,
          totalAttempts: 30,
          avgScore: 0.82,
          avgTimeSeconds: 1200,
          numQuestions: 10,
        },
      });

      vi.mocked(httpClient.assignmentAPI.getAssignmentStats).mockImplementation(
        mockGetStats
      );

      const user = userEvent.setup();
      render(<TeacherAssignments />);

      // Switch to stats tab
      await user.click(screen.getByText("View Stats"));

      // Enter assignment code
      const codeInput = screen.getByLabelText("Assignment Code");
      await user.type(codeInput, "alg1-xyz123");

      // Submit
      await user.click(screen.getByText("Load Stats"));

      await waitFor(() => {
        expect(mockGetStats).toHaveBeenCalledWith("ALG1-XYZ123", "");
      });

      // Should display stats
      await waitFor(() => {
        expect(screen.getByText("Assignment Statistics")).toBeInTheDocument();
        expect(screen.getByText("25")).toBeInTheDocument(); // Total students
        expect(screen.getByText("82.0%")).toBeInTheDocument(); // Average score
        expect(screen.getByText("1200")).toBeInTheDocument(); // Avg time
      });
    });

    it("displays error when stats fail to load", async () => {
      const mockGetStats = vi.fn().mockResolvedValue({
        success: false,
        error: "Assignment not found",
      });

      vi.mocked(httpClient.assignmentAPI.getAssignmentStats).mockImplementation(
        mockGetStats
      );

      const user = userEvent.setup();
      render(<TeacherAssignments />);

      // Switch to stats tab
      await user.click(screen.getByText("View Stats"));

      // Enter assignment code
      await user.type(
        screen.getByLabelText("Assignment Code"),
        "INVALID-CODE"
      );

      // Submit
      await user.click(screen.getByText("Load Stats"));

      await waitFor(() => {
        expect(screen.getByText("Assignment not found")).toBeInTheDocument();
      });
    });

    it("disables load stats button when code is empty", () => {
      render(<TeacherAssignments />);

      fireEvent.click(screen.getByText("View Stats"));

      const loadButton = screen.getByText("Load Stats") as HTMLButtonElement;

      expect(loadButton.disabled).toBe(true);
    });
  });

  describe("Tab Navigation", () => {
    it("switches between tabs", async () => {
      const user = userEvent.setup();
      render(<TeacherAssignments />);

      // Should start on create tab
      expect(screen.getByLabelText("Assignment Name *")).toBeInTheDocument();

      // Switch to stats tab
      await user.click(screen.getByText("View Stats"));

      // Should show stats form
      expect(screen.getByLabelText("Assignment Code")).toBeInTheDocument();
      expect(
        screen.queryByLabelText("Assignment Name *")
      ).not.toBeInTheDocument();

      // Switch back to create tab
      await user.click(screen.getByText("Create Assignment"));

      // Should show create form again
      expect(screen.getByLabelText("Assignment Name *")).toBeInTheDocument();
    });
  });
});

// ============================================================================
// AssignmentRunner Component Tests
// ============================================================================

describe("AssignmentRunner Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Code Entry State", () => {
    it("renders assignment code input", () => {
      render(<AssignmentRunner />);

      expect(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123")
      ).toBeInTheDocument();
      expect(screen.getByText("Enter Assignment Code")).toBeInTheDocument();
    });

    it("handles code submission", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Algebra Quiz",
          description: "Basic algebra problems",
          numQuestions: 10,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Enter code
      const codeInput = screen.getByPlaceholderText(
        "e.g., ALG1-XYZ123"
      ) as HTMLInputElement;
      await user.type(codeInput, "ALG1-XYZ123");

      // Submit
      const submitButton = screen.getByText("Enter Assignment");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockGetSummary).toHaveBeenCalledWith("ALG1-XYZ123");
      });

      // Should show summary
      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });
    });

    it("displays error for invalid code", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: false,
        error: "Assignment not found",
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Enter invalid code
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "INVALID"
      );

      // Submit
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Assignment not found")).toBeInTheDocument();
      });
    });
  });

  describe("Assignment Summary", () => {
    it("displays assignment summary before starting", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Algebra Quiz",
          description: "Basic algebra problems",
          numQuestions: 10,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Enter code and submit
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      // Should show summary
      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
        expect(screen.getByText("Basic algebra problems")).toBeInTheDocument();
        expect(screen.getByText(/10 questions/i)).toBeInTheDocument();
      });
    });

    it("allows starting assignment from summary", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Algebra Quiz",
          description: "Basic algebra",
          numQuestions: 10,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "p1",
          question: "What is 2 + 2?",
          answerChoices: ["3", "4", "5"],
          correctAnswerIndex: 1,
          difficulty: 1,
          topicId: "algebra",
          calculatorMode: "none",
          index: 1,
          totalInAssignment: 10,
          assignmentId: "ALG1-XYZ123",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Enter code
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      // Wait for summary
      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      // Click Start Assignment
      const startButton = screen.getByText("Start Assignment");
      await user.click(startButton);

      // Should load first problem
      await waitFor(() => {
        expect(mockGetProblem).toHaveBeenCalledWith("ALG1-XYZ123", 1);
      });
    });
  });

  describe("Problem Solving", () => {
    it("displays problem with answer choices", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 2,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "p1",
          question: "What is 2 + 2?",
          answerChoices: ["3", "4", "5"],
          correctAnswerIndex: 1,
          difficulty: 1,
          topicId: "algebra",
          calculatorMode: "none",
          index: 1,
          totalInAssignment: 2,
          assignmentId: "ALG1-XYZ123",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Setup: Enter code and start
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      // Should show problem
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
        expect(screen.getByText("4")).toBeInTheDocument();
        expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();
      });
    });

    it("advances to next problem on submission", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 2,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi
        .fn()
        .mockResolvedValueOnce({
          success: true,
          data: {
            id: "p1",
            question: "What is 2 + 2?",
            answerChoices: ["3", "4", "5"],
            correctAnswerIndex: 1,
            difficulty: 1,
            topicId: "algebra",
            calculatorMode: "none",
            index: 1,
            totalInAssignment: 2,
            assignmentId: "ALG1-XYZ123",
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: {
            id: "p2",
            question: "What is 5 + 3?",
            answerChoices: ["8", "6", "7"],
            correctAnswerIndex: 0,
            difficulty: 2,
            topicId: "algebra",
            calculatorMode: "none",
            index: 2,
            totalInAssignment: 2,
            assignmentId: "ALG1-XYZ123",
          },
        });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Setup: Enter code and start
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      // First problem should show
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
      });

      // Select an answer and submit
      const answerButtons = screen.getAllByRole("button").filter((btn) =>
        ["3", "4", "5"].includes(btn.textContent || "")
      );
      await user.click(answerButtons[1]); // Click "4" (correct answer)

      // Should advance to next problem
      await waitFor(() => {
        expect(screen.getByText("What is 5 + 3?")).toBeInTheDocument();
        expect(screen.getByText("Question 2 of 2")).toBeInTheDocument();
      });
    });
  });

  describe("Completion", () => {
    it("shows completion summary after last problem", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 1,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "p1",
          question: "What is 2 + 2?",
          answerChoices: ["3", "4", "5"],
          correctAnswerIndex: 1,
          difficulty: 1,
          topicId: "algebra",
          calculatorMode: "none",
          index: 1,
          totalInAssignment: 1,
          assignmentId: "ALG1-XYZ123",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Setup: Enter code and start
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      // Wait for problem
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
      });

      // Answer and submit
      const answerButtons = screen.getAllByRole("button").filter((btn) =>
        ["3", "4", "5"].includes(btn.textContent || "")
      );
      await user.click(answerButtons[1]); // Correct answer

      // Should show completion screen
      await waitFor(() => {
        expect(
          screen.getByText(/assignment complete/i)
        ).toBeInTheDocument();
        expect(screen.getByText("100%")).toBeInTheDocument(); // Perfect score
      });
    });

    it("calculates and displays correct score", async () => {
      // Setup similar to above but with 2 problems, answering 1 correctly
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 2,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi
        .fn()
        .mockResolvedValueOnce({
          success: true,
          data: {
            id: "p1",
            question: "What is 2 + 2?",
            answerChoices: ["3", "4", "5"],
            correctAnswerIndex: 1,
            difficulty: 1,
            topicId: "algebra",
            calculatorMode: "none",
            index: 1,
            totalInAssignment: 2,
            assignmentId: "ALG1-XYZ123",
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: {
            id: "p2",
            question: "What is 5 + 3?",
            answerChoices: ["8", "6", "7"],
            correctAnswerIndex: 0,
            difficulty: 2,
            topicId: "algebra",
            calculatorMode: "none",
            index: 2,
            totalInAssignment: 2,
            assignmentId: "ALG1-XYZ123",
          },
        });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Setup
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      // First problem - answer correctly
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
      });

      let answerButtons = screen.getAllByRole("button").filter((btn) =>
        ["3", "4", "5"].includes(btn.textContent || "")
      );
      await user.click(answerButtons[1]); // Correct

      // Second problem - answer incorrectly
      await waitFor(() => {
        expect(screen.getByText("What is 5 + 3?")).toBeInTheDocument();
      });

      answerButtons = screen.getAllByRole("button").filter((btn) =>
        ["8", "6", "7"].includes(btn.textContent || "")
      );
      await user.click(answerButtons[1]); // Wrong (should be "8")

      // Should show 50% score
      await waitFor(() => {
        expect(screen.getByText("50%")).toBeInTheDocument();
      });
    });

    it("allows restarting assignment", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 1,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "p1",
          question: "What is 2 + 2?",
          answerChoices: ["3", "4", "5"],
          correctAnswerIndex: 1,
          difficulty: 1,
          topicId: "algebra",
          calculatorMode: "none",
          index: 1,
          totalInAssignment: 1,
          assignmentId: "ALG1-XYZ123",
        },
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Complete assignment
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument();
      });

      const answerButtons = screen.getAllByRole("button").filter((btn) =>
        ["3", "4", "5"].includes(btn.textContent || "")
      );
      await user.click(answerButtons[1]);

      // Show completion
      await waitFor(() => {
        expect(
          screen.getByText(/assignment complete/i)
        ).toBeInTheDocument();
      });

      // Click retry
      const retryButton = screen.getByText("Try Again");
      await user.click(retryButton);

      // Should return to code entry
      await waitFor(() => {
        expect(
          screen.getByPlaceholderText("e.g., ALG1-XYZ123")
        ).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("displays error when problem fetch fails", async () => {
      const mockGetSummary = vi.fn().mockResolvedValue({
        success: true,
        data: {
          id: "ALG1-XYZ123",
          name: "Quiz",
          description: "",
          numQuestions: 1,
          minDifficulty: 1,
          maxDifficulty: 4,
          calculatorMode: "none",
        },
      });

      const mockGetProblem = vi.fn().mockResolvedValue({
        success: false,
        error: "Problem not found",
      });

      vi.mocked(
        httpClient.assignmentAPI.getAssignmentSummary
      ).mockImplementation(mockGetSummary);
      vi.mocked(
        httpClient.assignmentAPI.getAssignmentProblem
      ).mockImplementation(mockGetProblem);

      const user = userEvent.setup();
      render(<AssignmentRunner />);

      // Setup
      await user.type(
        screen.getByPlaceholderText("e.g., ALG1-XYZ123"),
        "ALG1-XYZ123"
      );
      await user.click(screen.getByText("Enter Assignment"));

      await waitFor(() => {
        expect(screen.getByText("Algebra Quiz")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Start Assignment"));

      // Should show error
      await waitFor(() => {
        expect(screen.getByText("Problem not found")).toBeInTheDocument();
      });
    });
  });
});
