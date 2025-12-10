/*
Teacher Assignments UI Component

This component should be integrated into TeacherDashboard.
It handles assignment creation and stats viewing for teachers.
*/

import React, { useState } from "react";
import { assignmentAPI } from "../services/http_client";
import { AssignmentResponse, AssignmentStats } from "../types/api_types";
import "./TeacherAssignments.css";

interface TeacherAssignmentsProps {
  teacherApiKey?: string;
}

interface CreateFormState {
  name: string;
  description: string;
  topicId: string;
  numQuestions: number;
  minDifficulty: number;
  maxDifficulty: number;
  calculatorMode: string;
}

interface StatsFormState {
  assignmentId: string;
  stats: AssignmentStats | null;
}

const TeacherAssignments: React.FC<TeacherAssignmentsProps> = ({
  teacherApiKey = "",
}) => {
  const [activeTab, setActiveTab] = useState<"create" | "stats">("create");

  const [createForm, setCreateForm] = useState<CreateFormState>({
    name: "",
    description: "",
    topicId: "algebra",
    numQuestions: 10,
    minDifficulty: 1,
    maxDifficulty: 4,
    calculatorMode: "none",
  });

  const [statsForm, setStatsForm] = useState<StatsFormState>({
    assignmentId: "",
    stats: null,
  });

  const [createdAssignment, setCreatedAssignment] =
    useState<AssignmentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ============================================================================
  // Create Assignment Handlers
  // ============================================================================

  const handleCreateChange = (
    field: keyof CreateFormState,
    value: unknown
  ) => {
    setCreateForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const result = await assignmentAPI.createAssignment(
      {
        name: createForm.name,
        description: createForm.description,
        topicId: createForm.topicId,
        numQuestions: createForm.numQuestions,
        minDifficulty: createForm.minDifficulty,
        maxDifficulty: createForm.maxDifficulty,
        calculatorMode: createForm.calculatorMode,
      },
      teacherApiKey
    );

    setLoading(false);

    if (result.success && result.data) {
      setCreatedAssignment(result.data);
      // Reset form
      setCreateForm({
        name: "",
        description: "",
        topicId: "algebra",
        numQuestions: 10,
        minDifficulty: 1,
        maxDifficulty: 4,
        calculatorMode: "none",
      });
    } else {
      setError(result.error || "Failed to create assignment");
    }
  };

  const copyAssignmentCode = () => {
    if (createdAssignment) {
      navigator.clipboard.writeText(createdAssignment.id);
    }
  };

  // ============================================================================
  // Stats Handlers
  // ============================================================================

  const handleStatsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const result = await assignmentAPI.getAssignmentStats(
      statsForm.assignmentId,
      teacherApiKey
    );

    setLoading(false);

    if (result.success && result.data) {
      setStatsForm((prev) => ({
        ...prev,
        stats: result.data || null,
      }));
    } else {
      setError(result.error || "Failed to load stats");
    }
  };

  return (
    <div className="teacher-assignments">
      <div className="tabs">
        <button
          className={`tab-button ${activeTab === "create" ? "active" : ""}`}
          onClick={() => setActiveTab("create")}
        >
          Create Assignment
        </button>
        <button
          className={`tab-button ${activeTab === "stats" ? "active" : ""}`}
          onClick={() => setActiveTab("stats")}
        >
          View Stats
        </button>
      </div>

      {/* Create Assignment Tab */}
      {activeTab === "create" && (
        <div className="tab-content">
          {createdAssignment ? (
            <div className="success-card">
              <h3>✓ Assignment Created</h3>
              <div className="created-assignment">
                <p className="assignment-name">{createdAssignment.name}</p>
                <div className="code-display">
                  <div className="code-box">
                    <code>{createdAssignment.id}</code>
                  </div>
                  <button
                    className="copy-button"
                    onClick={copyAssignmentCode}
                    title="Copy code to clipboard"
                  >
                    Copy Code
                  </button>
                </div>
                <div className="assignment-details">
                  <div className="detail-row">
                    <span>Topic:</span>
                    <strong>{createdAssignment.topicId}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Questions:</span>
                    <strong>{createdAssignment.numQuestions}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Difficulty Range:</span>
                    <strong>
                      {createdAssignment.minDifficulty} -{" "}
                      {createdAssignment.maxDifficulty}
                    </strong>
                  </div>
                </div>
                <button
                  className="btn-secondary"
                  onClick={() => setCreatedAssignment(null)}
                >
                  Create Another
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateSubmit} className="create-form">
              <div className="form-group">
                <label htmlFor="name">Assignment Name *</label>
                <input
                  id="name"
                  type="text"
                  required
                  placeholder="e.g., Algebra Quiz 1"
                  value={createForm.name}
                  onChange={(e) =>
                    handleCreateChange("name", e.target.value)
                  }
                />
              </div>

              <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  placeholder="Optional description for students"
                  value={createForm.description}
                  onChange={(e) =>
                    handleCreateChange("description", e.target.value)
                  }
                  rows={3}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="topic">Topic *</label>
                  <select
                    id="topic"
                    value={createForm.topicId}
                    onChange={(e) =>
                      handleCreateChange("topicId", e.target.value)
                    }
                  >
                    <option value="algebra">Algebra</option>
                    <option value="geometry">Geometry</option>
                    <option value="calculus">Calculus</option>
                    <option value="statistics">Statistics</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="numQuestions">Number of Questions</label>
                  <input
                    id="numQuestions"
                    type="number"
                    min="1"
                    max="50"
                    value={createForm.numQuestions}
                    onChange={(e) =>
                      handleCreateChange(
                        "numQuestions",
                        parseInt(e.target.value)
                      )
                    }
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="minDifficulty">Min Difficulty</label>
                  <input
                    id="minDifficulty"
                    type="number"
                    min="1"
                    max="4"
                    value={createForm.minDifficulty}
                    onChange={(e) =>
                      handleCreateChange(
                        "minDifficulty",
                        parseInt(e.target.value)
                      )
                    }
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="maxDifficulty">Max Difficulty</label>
                  <input
                    id="maxDifficulty"
                    type="number"
                    min="1"
                    max="4"
                    value={createForm.maxDifficulty}
                    onChange={(e) =>
                      handleCreateChange(
                        "maxDifficulty",
                        parseInt(e.target.value)
                      )
                    }
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="calculator">Calculator Mode</label>
                <select
                  id="calculator"
                  value={createForm.calculatorMode}
                  onChange={(e) =>
                    handleCreateChange("calculatorMode", e.target.value)
                  }
                >
                  <option value="none">None</option>
                  <option value="scientific">Scientific</option>
                  <option value="graphing">Graphing</option>
                </select>
              </div>

              {error && <div className="error-message">{error}</div>}

              <button
                type="submit"
                className="btn-primary btn-large"
                disabled={loading || !createForm.name}
              >
                {loading ? "Creating..." : "Create Assignment"}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === "stats" && (
        <div className="tab-content">
          <form onSubmit={handleStatsSubmit} className="stats-form">
            <div className="form-group">
              <label htmlFor="statsAssignmentId">Assignment Code</label>
              <input
                id="statsAssignmentId"
                type="text"
                placeholder="e.g., ALG1-XYZ123"
                value={statsForm.assignmentId}
                onChange={(e) =>
                  setStatsForm((prev) => ({
                    ...prev,
                    assignmentId: e.target.value.toUpperCase(),
                  }))
                }
                disabled={loading}
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !statsForm.assignmentId}
            >
              {loading ? "Loading..." : "Load Stats"}
            </button>
          </form>

          {statsForm.stats && (
            <div className="stats-display">
              <h3>Assignment Statistics</h3>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Assignment ID</div>
                  <div className="stat-value">{statsForm.stats.assignmentId}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Total Students</div>
                  <div className="stat-value">{statsForm.stats.totalStudents}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Total Attempts</div>
                  <div className="stat-value">{statsForm.stats.totalAttempts}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Average Score</div>
                  <div className="stat-value">
                    {statsForm.stats.avgScore
                      ? (statsForm.stats.avgScore * 100).toFixed(1) + "%"
                      : "N/A"}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Avg Time (sec)</div>
                  <div className="stat-value">
                    {statsForm.stats.avgTimeSeconds
                      ? statsForm.stats.avgTimeSeconds.toFixed(0)
                      : "N/A"}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Questions</div>
                  <div className="stat-value">{statsForm.stats.numQuestions}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TeacherAssignments;
