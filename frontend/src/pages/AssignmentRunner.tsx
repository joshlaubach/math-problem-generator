import React, { useState, useEffect } from "react";
import { assignmentAPI } from "../services/http_client";
import { AssignmentSummary, AssignmentProblem } from "../types/api_types";
import "./AssignmentRunner.css";

interface AssignmentRunnerState {
  assignmentId: string;
  summary: AssignmentSummary | null;
  currentIndex: number;
  currentProblem: AssignmentProblem | null;
  started: boolean;
  completed: boolean;
  loading: boolean;
  error: string | null;
  correctCount: number;
  startTime: number | null;
}

const AssignmentRunner: React.FC = () => {
  const [state, setState] = useState<AssignmentRunnerState>({
    assignmentId: "",
    summary: null,
    currentIndex: 0,
    currentProblem: null,
    started: false,
    completed: false,
    loading: false,
    error: null,
    correctCount: 0,
    startTime: null,
  });

  const handleCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setState((prev) => ({ ...prev, loading: true, error: null }));

    const result = await assignmentAPI.getAssignmentSummary(state.assignmentId);

    if (result.success && result.data) {
      setState((prev) => ({
        ...prev,
        summary: result.data,
        loading: false,
      }));
    } else {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: result.error || "Assignment not found",
      }));
    }
  };

  const handleStartAssignment = async () => {
    setState((prev) => ({
      ...prev,
      started: true,
      currentIndex: 1,
      startTime: Date.now(),
      loading: true,
    }));

    // Fetch first problem
    const result = await assignmentAPI.getAssignmentProblem(
      state.assignmentId,
      1
    );

    if (result.success && result.data) {
      setState((prev) => ({
        ...prev,
        currentProblem: result.data,
        loading: false,
      }));
    } else {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: result.error || "Failed to load problem",
      }));
    }
  };

  const handleProblemSubmit = async (isCorrect: boolean) => {
    if (isCorrect) {
      setState((prev) => ({
        ...prev,
        correctCount: prev.correctCount + 1,
      }));
    }

    const nextIndex = state.currentIndex + 1;

    if (state.summary && nextIndex > state.summary.numQuestions) {
      // Assignment complete
      setState((prev) => ({
        ...prev,
        completed: true,
      }));
    } else {
      // Load next problem
      setState((prev) => ({
        ...prev,
        currentIndex: nextIndex,
        loading: true,
      }));

      const result = await assignmentAPI.getAssignmentProblem(
        state.assignmentId,
        nextIndex
      );

      if (result.success && result.data) {
        setState((prev) => ({
          ...prev,
          currentProblem: result.data,
          loading: false,
        }));
      } else {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: result.error || "Failed to load problem",
        }));
      }
    }
  };

  const handleReset = () => {
    setState({
      assignmentId: "",
      summary: null,
      currentIndex: 0,
      currentProblem: null,
      started: false,
      completed: false,
      loading: false,
      error: null,
      correctCount: 0,
      startTime: null,
    });
  };

  if (!state.started && !state.summary) {
    return (
      <div className="assignment-runner">
        <div className="assignment-code-entry">
          <h2>Enter Assignment Code</h2>
          <form onSubmit={handleCodeSubmit}>
            <input
              type="text"
              placeholder="e.g., ALG1-XYZ123"
              value={state.assignmentId}
              onChange={(e) =>
                setState((prev) => ({
                  ...prev,
                  assignmentId: e.target.value.toUpperCase(),
                }))
              }
              disabled={state.loading}
            />
            <button type="submit" disabled={state.loading || !state.assignmentId}>
              {state.loading ? "Loading..." : "Look Up Assignment"}
            </button>
          </form>
          {state.error && <div className="error-message">{state.error}</div>}
        </div>
      </div>
    );
  }

  if (state.summary && !state.started) {
    return (
      <div className="assignment-runner">
        <div className="assignment-summary">
          <h2>{state.summary.name}</h2>
          {state.summary.description && (
            <p className="description">{state.summary.description}</p>
          )}
          <div className="assignment-info">
            <div className="info-item">
              <span className="label">Topic:</span>
              <span className="value">{state.summary.topicId}</span>
            </div>
            <div className="info-item">
              <span className="label">Questions:</span>
              <span className="value">{state.summary.numQuestions}</span>
            </div>
          </div>
          <button
            className="btn-primary btn-large"
            onClick={handleStartAssignment}
            disabled={state.loading}
          >
            {state.loading ? "Loading..." : "Start Assignment"}
          </button>
          <button
            className="btn-secondary btn-large"
            onClick={handleReset}
            disabled={state.loading}
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  if (state.completed) {
    const percentage =
      state.summary && state.summary.numQuestions > 0
        ? Math.round((state.correctCount / state.summary.numQuestions) * 100)
        : 0;

    return (
      <div className="assignment-runner">
        <div className="assignment-complete">
          <h2>Assignment Complete!</h2>
          <div className="completion-stats">
            <div className="stat">
              <span className="label">Score:</span>
              <span className="value">
                {state.correctCount}/{state.summary?.numQuestions}
              </span>
            </div>
            <div className="stat">
              <span className="label">Percentage:</span>
              <span className="value">{percentage}%</span>
            </div>
          </div>
          <button className="btn-primary btn-large" onClick={handleReset}>
            Try Another Assignment
          </button>
        </div>
      </div>
    );
  }

  if (state.currentProblem && state.started) {
    return (
      <div className="assignment-runner">
        <div className="assignment-progress">
          <h3>
            {state.summary?.name} - Question {state.currentIndex} of{" "}
            {state.summary?.numQuestions}
          </h3>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${((state.currentIndex - 1) / (state.summary?.numQuestions || 1)) * 100}%`,
              }}
            />
          </div>
        </div>

        <div className="problem-container">
          <div className="problem-latex">
            {state.currentProblem.problem.prompt_latex}
          </div>

          <div className="answer-section">
            <input
              type="text"
              placeholder="Enter your answer"
              className="answer-input"
            />
            <div className="button-group">
              <button className="btn-success" onClick={() => handleProblemSubmit(true)}>
                Submit Answer
              </button>
              <button className="btn-secondary" onClick={() => handleProblemSubmit(false)}>
                Skip
              </button>
            </div>
          </div>
        </div>

        {state.error && <div className="error-message">{state.error}</div>}
      </div>
    );
  }

  return (
    <div className="assignment-runner">
      <div className="loading">Loading...</div>
    </div>
  );
};

export default AssignmentRunner;
