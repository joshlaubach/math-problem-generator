/**
 * TeacherConceptStatsView Component - Teacher skill reports for students
 * 
 * Features:
 * - View student concept performance across a course
 * - Identify weakest concepts
 * - Generate targeted practice assignments for weak skills
 * - Color-coded skill visualization
 */

import { useState, useEffect } from 'react';
import { CourseConceptHeatmapResponse, TopicMetadata } from '../api/types';
import { apiClient } from '../api/client';
import './TeacherConceptStatsView.css';

interface TeacherConceptStatsViewProps {
  studentId: string;
  courseId: string;
  courseName: string;
  topics: TopicMetadata[];
  apiKey?: string;
  onGeneratePractice?: (conceptId: string, topicIds: string[]) => void;
}

/**
 * Determine color for a concept cell based on success rate
 */
function getSkillColor(successRate: number): string {
  if (successRate >= 0.75) return 'skill-excellent';
  if (successRate >= 0.50) return 'skill-good';
  if (successRate >= 0.25) return 'skill-fair';
  return 'skill-weak';
}

/**
 * Format a percentage for display
 */
function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function TeacherConceptStatsView({
  studentId,
  courseId,
  courseName,
  topics,
  apiKey,
  onGeneratePractice,
}: TeacherConceptStatsViewProps) {
  const [data, setData] = useState<CourseConceptHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);

  // Load data on mount and when props change
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getTeacherConceptStats(courseId, studentId, apiKey);
        setData(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load concept stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [courseId, studentId, apiKey]);

  if (loading) {
    return (
      <div className="teacher-concept-stats">
        <div className="loading-state">Loading concept stats...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="teacher-concept-stats">
        <div className="error-state">Error: {error}</div>
      </div>
    );
  }

  if (!data || data.concept_stats.length === 0) {
    return (
      <div className="teacher-concept-stats">
        <div className="empty-state">
          <p>No practice history for {studentId} in {courseName}</p>
        </div>
      </div>
    );
  }

  // Sort by success rate (weak first)
  const sortedConcepts = [...data.concept_stats].sort(
    (a, b) => a.success_rate - b.success_rate
  );

  // Get weakest concepts (success rate < 75%)
  const weakConcepts = sortedConcepts.filter((c) => c.success_rate < 0.75);

  const handleGeneratePractice = (conceptId: string) => {
    if (!onGeneratePractice) return;

    setGeneratingFor(conceptId);
    try {
      // Find topics related to this concept (simplified - match by course)
      const relatedTopicIds = topics.filter((t) => t.course_id === courseId).map((t) => t.topic_id);
      onGeneratePractice(conceptId, relatedTopicIds);
    } finally {
      setGeneratingFor(null);
    }
  };

  return (
    <div className="teacher-concept-stats">
      <div className="stats-header">
        <h3>
          Concept Performance: <strong>{studentId}</strong>
        </h3>
        <p className="stats-meta">
          Course: <strong>{courseName}</strong> | Total Attempts:{' '}
          <strong>{data.total_attempts}</strong>
        </p>
      </div>

      {/* Weak Concepts Alert */}
      {weakConcepts.length > 0 && (
        <div className="weak-concepts-alert">
          <h4>⚠️ Skills to Focus On</h4>
          <p>
            {studentId} needs help with <strong>{weakConcepts.length}</strong> concept
            {weakConcepts.length !== 1 ? 's' : ''}.
          </p>
        </div>
      )}

      {/* Weak Concepts Cards */}
      {weakConcepts.length > 0 && (
        <div className="weak-concepts-section">
          <h4>Recommended Practice Areas</h4>
          <div className="weak-concepts-grid">
            {weakConcepts.map((concept) => (
              <div
                key={concept.concept_id}
                className={`weak-concept-card ${getSkillColor(concept.success_rate)}`}
              >
                <div className="card-top">
                  <div className="concept-info">
                    <div className="concept-name">{concept.concept_name}</div>
                    <div className="success-metrics">
                      <span className="metric">
                        Success: {formatPercent(concept.success_rate)}
                      </span>
                      <span className="metric">
                        {concept.total_attempts} attempt{concept.total_attempts !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                  <div className="success-circle">
                    <svg viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="45" className="bg" />
                      <circle
                        cx="50"
                        cy="50"
                        r="45"
                        className="progress"
                        style={{
                          strokeDasharray: `${concept.success_rate * 283} 283`,
                        }}
                      />
                    </svg>
                    <div className="percent">{formatPercent(concept.success_rate)}</div>
                  </div>
                </div>
                <button
                  className="btn-practice"
                  onClick={() => handleGeneratePractice(concept.concept_id)}
                  disabled={generatingFor === concept.concept_id}
                >
                  {generatingFor === concept.concept_id
                    ? 'Generating...'
                    : '📝 Generate Practice'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Concepts Table */}
      <div className="all-concepts-section">
        <h4>All Concepts Progress</h4>
        <div className="table-container">
          <table className="concepts-table">
            <thead>
              <tr>
                <th>Concept</th>
                <th>Success Rate</th>
                <th>Attempts</th>
                <th>Avg Difficulty</th>
                <th>Avg Time</th>
              </tr>
            </thead>
            <tbody>
              {sortedConcepts.map((concept) => (
                <tr key={concept.concept_id} className={`row-${getSkillColor(concept.success_rate)}`}>
                  <td className="concept-col">
                    <span className="concept-label">{concept.concept_name}</span>
                  </td>
                  <td className="success-col">
                    <div className="success-bar-mini">
                      <div
                        className="fill"
                        style={{ width: `${concept.success_rate * 100}%` }}
                      ></div>
                    </div>
                    <span>{formatPercent(concept.success_rate)}</span>
                  </td>
                  <td className="attempts-col">{concept.total_attempts}</td>
                  <td className="difficulty-col">
                    {concept.average_difficulty?.toFixed(1) || '—'}
                  </td>
                  <td className="time-col">
                    {concept.average_time_seconds?.toFixed(0) || '—'}s
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
