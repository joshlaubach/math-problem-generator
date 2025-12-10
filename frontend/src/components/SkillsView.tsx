/**
 * SkillsView Component - Displays concept-level performance heatmap
 * 
 * Features:
 * - Color-coded skill cells (green/yellow/red) based on success rate
 * - Concept name, attempt count, success rate, and difficulty metrics
 * - Responsive grid layout for desktop and mobile
 * - Loading and error states
 */

import { useState, useEffect } from 'react';
import { ConceptStatsResponse, CourseConceptHeatmapResponse } from '../api/types';
import { apiClient } from '../api/client';
import './SkillsView.css';

interface SkillsViewProps {
  courseId: string;
  courseName?: string;
}

/**
 * Determine color for a concept cell based on success rate
 */
function getSkillColor(successRate: number): string {
  if (successRate >= 0.75) return 'skill-excellent'; // Green
  if (successRate >= 0.50) return 'skill-good';      // Yellow
  if (successRate >= 0.25) return 'skill-fair';      // Orange
  return 'skill-weak';                               // Red
}

/**
 * Format a percentage for display
 */
function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function SkillsView({ courseId, courseName }: SkillsViewProps) {
  const [data, setData] = useState<CourseConceptHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'name' | 'attempts' | 'success' | 'weakness'>('name');

  useEffect(() => {
    const fetchConceptStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getStudentConceptStats(courseId);
        setData(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load skill data');
      } finally {
        setLoading(false);
      }
    };

    fetchConceptStats();
  }, [courseId]);

  if (loading) {
    return (
      <div className="skills-view">
        <div className="skills-loading">
          <p>Loading your skills data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="skills-view">
        <div className="skills-error">
          <p>Error loading skills: {error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.concept_stats.length === 0) {
    return (
      <div className="skills-view">
        <div className="skills-empty">
          <p>No practice history yet. Start solving problems to see your skill progress!</p>
        </div>
      </div>
    );
  }

  // Sort concepts based on selected criteria
  let sortedConcepts = [...data.concept_stats];
  switch (sortBy) {
    case 'name':
      sortedConcepts.sort((a, b) => a.concept_name.localeCompare(b.concept_name));
      break;
    case 'attempts':
      sortedConcepts.sort((a, b) => b.total_attempts - a.total_attempts);
      break;
    case 'success':
      sortedConcepts.sort((a, b) => b.success_rate - a.success_rate);
      break;
    case 'weakness':
      sortedConcepts.sort((a, b) => a.success_rate - b.success_rate);
      break;
  }

  return (
    <div className="skills-view">
      <div className="skills-header">
        <h2>Skills Progress{courseName && ` - ${courseName}`}</h2>
        <p className="skills-summary">
          Total Attempts: <strong>{data.total_attempts}</strong> | 
          Concepts Practiced: <strong>{data.total_concepts}</strong>
        </p>
      </div>

      <div className="skills-controls">
        <label htmlFor="sort-select">Sort by:</label>
        <select 
          id="sort-select"
          value={sortBy} 
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="sort-select"
        >
          <option value="name">Concept Name</option>
          <option value="attempts">Most Attempts</option>
          <option value="success">Strongest Skills</option>
          <option value="weakness">Weakest Skills</option>
        </select>
      </div>

      {/* Legend */}
      <div className="skills-legend">
        <div className="legend-item skill-excellent"><span>Excellent (75%+)</span></div>
        <div className="legend-item skill-good"><span>Good (50-74%)</span></div>
        <div className="legend-item skill-fair"><span>Fair (25-49%)</span></div>
        <div className="legend-item skill-weak"><span>Weak (&lt;25%)</span></div>
      </div>

      {/* Table view for better data display */}
      <div className="skills-table-container">
        <table className="skills-table">
          <thead>
            <tr>
              <th>Concept</th>
              <th>Attempts</th>
              <th>Success Rate</th>
              <th>Avg Difficulty</th>
              <th>Avg Time (sec)</th>
            </tr>
          </thead>
          <tbody>
            {sortedConcepts.map((concept) => (
              <tr
                key={concept.concept_id}
                className={`skill-row ${getSkillColor(concept.success_rate)}`}
              >
                <td className="concept-name">{concept.concept_name}</td>
                <td className="metric-attempts">{concept.total_attempts}</td>
                <td className="metric-success">
                  <div className="success-bar">
                    <div
                      className="success-fill"
                      style={{ width: `${concept.success_rate * 100}%` }}
                    ></div>
                    <span className="success-text">{formatPercent(concept.success_rate)}</span>
                  </div>
                </td>
                <td className="metric-difficulty">
                  {concept.average_difficulty?.toFixed(1) || '—'}
                </td>
                <td className="metric-time">
                  {concept.average_time_seconds?.toFixed(1) || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Grid card view for visual heatmap */}
      <div className="skills-grid-container">
        <h3>Visual Heatmap</h3>
        <div className="skills-grid">
          {sortedConcepts.map((concept) => (
            <div
              key={concept.concept_id}
              className={`skill-card ${getSkillColor(concept.success_rate)}`}
              title={`${concept.concept_name}: ${formatPercent(concept.success_rate)} success rate`}
            >
              <div className="card-name">{concept.concept_name}</div>
              <div className="card-success">{formatPercent(concept.success_rate)}</div>
              <div className="card-attempts">{concept.total_attempts} attempts</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
