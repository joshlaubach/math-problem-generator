/**
 * Teacher dashboard - view student stats and analytics
 * 
 * Features:
 * - Per-User Analytics: View individual student performance across topics
 * - Per-Topic Analytics: View aggregated class performance for a specific topic
 * - Concept Stats: View and manage student skill development by concept
 * - Both modes support optional API key authentication for protected endpoints
 */

import { useState } from 'react';
import { useAuthUser } from '../hooks/useAuthUser';
import { apiClient } from '../api/client';
import { TopicMetadata, UserStatsResponse, DifficultyRecommendationResponse, TeacherTopicStatsResponse } from '../api/types';
import { TeacherConceptStatsView } from '../components/TeacherConceptStatsView';
import { TEACHER_API_KEY } from '../config';
import './TeacherDashboard.css';

interface TeacherDashboardProps {
  topics: TopicMetadata[];
}

interface StudentStats {
  userId: string;
  topicId: string;
  stats: UserStatsResponse;
  recommendation?: DifficultyRecommendationResponse;
}

interface TopicStats {
  topicId: string;
  stats: TeacherTopicStatsResponse;
}

type ViewMode = 'perUser' | 'perTopic' | 'conceptStats';

export function TeacherDashboard({ topics }: TeacherDashboardProps) {
  const { isTeacher, isAuthenticated } = useAuthUser();

  // Show auth guard message if not authorized
  if (!isAuthenticated || !isTeacher) {
    return (
      <div className="auth-guard-message">
        <div className="guard-container">
          <h2>Teacher Access Required</h2>
          <p>You must be logged in as a teacher to access this dashboard.</p>
          <p>
            If you have a teacher account,{' '}
            <a href="/login" style={{ color: '#667eea', textDecoration: 'underline' }}>
              please log in
            </a>
            . If you don't have an account,{' '}
            <a href="/register" style={{ color: '#667eea', textDecoration: 'underline' }}>
              register here
            </a>
            .
          </p>
        </div>
      </div>
    );
  }

  // View mode selection (tabs)
  const [viewMode, setViewMode] = useState<ViewMode>('perUser');

  // Shared API key state
  const [teacherApiKey, setTeacherApiKey] = useState<string>(TEACHER_API_KEY || '');

  // Per-User Analytics state
  const [studentId, setStudentId] = useState('');
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [studentStats, setStudentStats] = useState<StudentStats | null>(null);

  // Per-Topic Analytics state
  const [selectedTopicIdForStats, setSelectedTopicIdForStats] = useState<string | null>(null);
  const [topicStats, setTopicStats] = useState<TopicStats | null>(null);

  // Concept Stats state
  const [conceptStudentId, setConceptStudentId] = useState('');
  const [conceptCourseId, setConceptCourseId] = useState('sat_math');

  // Shared loading and error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Per-User Analytics: Load student statistics
  const handleLoadStudentStats = async () => {
    if (!studentId.trim() || !selectedTopicId) {
      setError('Please enter a student ID and select a topic');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const stats = await apiClient.getUserStats(studentId, selectedTopicId);
      let recommendation: DifficultyRecommendationResponse | undefined;
      try {
        recommendation = await apiClient.getDifficultyRecommendation(studentId, selectedTopicId);
      } catch {
        // Recommendation is optional
      }

      setStudentStats({
        userId: studentId,
        topicId: selectedTopicId,
        stats,
        recommendation,
      });
    } catch (err) {
      setError('Failed to load student stats');
      setStudentStats(null);
    } finally {
      setLoading(false);
    }
  };

  // Per-Topic Analytics: Load topic statistics for entire class
  const handleLoadTopicStats = async () => {
    if (!selectedTopicIdForStats) {
      setError('Please select a topic');
      return;
    }

    if (!teacherApiKey) {
      setError('Teacher API key is required for topic analytics');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const stats = await apiClient.getTeacherTopicStats(selectedTopicIdForStats, teacherApiKey);
      setTopicStats({
        topicId: selectedTopicIdForStats,
        stats,
      });
    } catch (err) {
      setError('Failed to load topic stats. Check your API key and try again.');
      setTopicStats(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="teacher-dashboard">
      {/* API Key Input Section */}
      <div className="api-key-section">
        <label htmlFor="teacher-api-key">Teacher API Key:</label>
        <input
          id="teacher-api-key"
          type="password"
          value={teacherApiKey}
          onChange={(e) => setTeacherApiKey(e.target.value)}
          placeholder="Enter your teacher API key (optional for dev)"
          className="input api-key-input"
        />
        <small>
          {teacherApiKey ? '✓ API key set' : 'ℹ️ Leave empty for development mode'}
        </small>
      </div>

      {/* Tab Navigation */}
      <div className="view-tabs">
        <button
          className={`tab-button ${viewMode === 'perUser' ? 'active' : ''}`}
          onClick={() => setViewMode('perUser')}
        >
          Per User Analytics
        </button>
        <button
          className={`tab-button ${viewMode === 'perTopic' ? 'active' : ''}`}
          onClick={() => setViewMode('perTopic')}
        >
          Per Topic Analytics
        </button>
        <button
          className={`tab-button ${viewMode === 'conceptStats' ? 'active' : ''}`}
          onClick={() => setViewMode('conceptStats')}
        >
          Student Skill Report
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {viewMode === 'perUser' ? (
        <PerUserAnalyticsView
          topics={topics}
          studentId={studentId}
          selectedTopicId={selectedTopicId}
          studentStats={studentStats}
          loading={loading}
          onStudentIdChange={setStudentId}
          onTopicChange={setSelectedTopicId}
          onLoadStats={handleLoadStudentStats}
        />
      ) : viewMode === 'perTopic' ? (
        <PerTopicAnalyticsView
          topics={topics}
          selectedTopicId={selectedTopicIdForStats}
          topicStats={topicStats}
          loading={loading}
          onTopicChange={setSelectedTopicIdForStats}
          onLoadStats={handleLoadTopicStats}
        />
      ) : (
        <ConceptStatsPanel
          topics={topics}
          studentId={conceptStudentId}
          courseId={conceptCourseId}
          onStudentIdChange={setConceptStudentId}
          onCourseChange={setConceptCourseId}
          apiKey={teacherApiKey}
        />
      )}
    </div>
  );
}

/**
 * Concept Stats Panel - for viewing student skill development by concept
 */
interface ConceptStatsPanelProps {
  topics: TopicMetadata[];
  studentId: string;
  courseId: string;
  onStudentIdChange: (id: string) => void;
  onCourseChange: (id: string) => void;
  apiKey?: string;
}

function ConceptStatsPanel({
  topics,
  studentId,
  courseId,
  onStudentIdChange,
  onCourseChange,
  apiKey,
}: ConceptStatsPanelProps) {
  // Get unique courses from topics
  const courses = Array.from(new Set(topics.map((t) => t.course_id))).map((cid) => ({
    id: cid,
    name: topics.find((t) => t.course_id === cid)?.course_id.replace(/_/g, ' ') || cid,
  }));

  return (
    <div className="concept-stats-panel">
      <div className="query-panel">
        <h2>Student Skill Development Report</h2>
        <p className="view-description">View student concept mastery and generate targeted practice</p>

        <div className="query-section">
          <label>Student ID:</label>
          <input
            type="text"
            value={studentId}
            onChange={(e) => onStudentIdChange(e.target.value)}
            placeholder="Enter student ID"
            className="input"
          />
        </div>

        <div className="query-section">
          <label>Course:</label>
          <select value={courseId} onChange={(e) => onCourseChange(e.target.value)} className="input">
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {studentId && courseId && (
        <TeacherConceptStatsView
          studentId={studentId}
          courseId={courseId}
          courseName={courseId.replace(/_/g, ' ')}
          topics={topics}
          apiKey={apiKey}
        />
      )}
    </div>
  );
}

/**
 * Per-User Analytics View - displays individual student performance
 */
interface PerUserAnalyticsViewProps {
  topics: TopicMetadata[];
  studentId: string;
  selectedTopicId: string | null;
  studentStats: { userId: string; topicId: string; stats: UserStatsResponse; recommendation?: DifficultyRecommendationResponse } | null;
  loading: boolean;
  onStudentIdChange: (id: string) => void;
  onTopicChange: (topicId: string | null) => void;
  onLoadStats: () => void;
}

function PerUserAnalyticsView({
  topics,
  studentId,
  selectedTopicId,
  studentStats,
  loading,
  onStudentIdChange,
  onTopicChange,
  onLoadStats,
}: PerUserAnalyticsViewProps) {
  return (
    <div className="analytics-view per-user-view">
      <div className="query-panel">
        <h2>Student Performance Analytics</h2>
        <p className="view-description">View individual student progress across topics</p>

        <div className="query-section">
          <label>Student ID:</label>
          <input
            type="text"
            value={studentId}
            onChange={(e) => onStudentIdChange(e.target.value)}
            placeholder="Enter student ID"
            className="input"
            onKeyPress={(e) => e.key === 'Enter' && onLoadStats()}
          />
        </div>

        <div className="query-section">
          <label>Topic:</label>
          <select
            value={selectedTopicId || ''}
            onChange={(e) => onTopicChange(e.target.value || null)}
            className="input"
          >
            <option value="">Select a topic</option>
            {topics.map((topic) => (
              <option key={topic.topic_id} value={topic.topic_id}>
                {topic.topic_name} ({topic.course_id})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onLoadStats}
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Load Stats'}
        </button>
      </div>

      {studentStats && (
        <div className="stats-display">
          <div className="stats-header">
            <h3>
              Stats for {studentStats.userId} - {studentStats.topicId}
            </h3>
          </div>

          <div className="stats-grid">
            <StatCard
              label="Total Attempts"
              value={studentStats.stats.total_attempts}
              color="blue"
            />
            <StatCard
              label="Correct Attempts"
              value={studentStats.stats.correct_attempts}
              color="green"
            />
            <StatCard
              label="Success Rate"
              value={`${(studentStats.stats.success_rate * 100).toFixed(1)}%`}
              color="purple"
            />
            <StatCard
              label="Average Difficulty"
              value={studentStats.stats.average_difficulty.toFixed(1)}
              color="orange"
            />
            <StatCard
              label="Avg Time (seconds)"
              value={studentStats.stats.average_time_seconds.toFixed(1)}
              color="teal"
            />
          </div>

          {studentStats.recommendation && (
            <div className="recommendation-box">
              <h3>Difficulty Recommendation</h3>
              <div className="recommendation-content">
                <div className="recommended-level">
                  <span className="label">Recommended Difficulty:</span>
                  <span className="value">{studentStats.recommendation.recommended_difficulty}</span>
                </div>
                <div className="reasoning">
                  <p>{studentStats.recommendation.reasoning}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Per-Topic Analytics View - displays aggregated class performance
 */
interface PerTopicAnalyticsViewProps {
  topics: TopicMetadata[];
  selectedTopicId: string | null;
  topicStats: { topicId: string; stats: TeacherTopicStatsResponse } | null;
  loading: boolean;
  onTopicChange: (topicId: string | null) => void;
  onLoadStats: () => void;
}

function PerTopicAnalyticsView({
  topics,
  selectedTopicId,
  topicStats,
  loading,
  onTopicChange,
  onLoadStats,
}: PerTopicAnalyticsViewProps) {
  return (
    <div className="analytics-view per-topic-view">
      <div className="query-panel">
        <h2>Class Performance Analytics</h2>
        <p className="view-description">View aggregated class performance for a topic</p>

        <div className="query-section">
          <label>Topic:</label>
          <select
            value={selectedTopicId || ''}
            onChange={(e) => onTopicChange(e.target.value || null)}
            className="input"
          >
            <option value="">Select a topic</option>
            {topics.map((topic) => (
              <option key={topic.topic_id} value={topic.topic_id}>
                {topic.topic_name} ({topic.course_id})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onLoadStats}
          className="btn btn-primary"
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Load Topic Stats'}
        </button>
      </div>

      {topicStats && (
        <div className="stats-display">
          <div className="stats-header">
            <h3>Class Performance - {topicStats.topicId}</h3>
          </div>

          <div className="stats-grid">
            <StatCard
              label="Total Attempts"
              value={topicStats.stats.total_attempts}
              color="blue"
            />
            <StatCard
              label="Correct Attempts"
              value={topicStats.stats.correct_attempts}
              color="green"
            />
            <StatCard
              label="Success Rate"
              value={`${(topicStats.stats.success_rate * 100).toFixed(1)}%`}
              color="purple"
            />
            {topicStats.stats.average_difficulty !== undefined && (
              <StatCard
                label="Average Difficulty"
                value={topicStats.stats.average_difficulty.toFixed(1)}
                color="orange"
              />
            )}
            {topicStats.stats.average_time_seconds !== undefined && (
              <StatCard
                label="Avg Time (seconds)"
                value={topicStats.stats.average_time_seconds.toFixed(1)}
                color="teal"
              />
            )}
            <StatCard
              label="Unique Students"
              value={topicStats.stats.num_unique_students}
              color="blue"
            />
          </div>
        </div>
      )}

      {!topicStats && !loading && selectedTopicId && (
        <div className="empty-state">
          <p>No attempts found yet for this topic.</p>
        </div>
      )}
    </div>
  );
}
}


interface StatCardProps {
  label: string;
  value: string | number;
  color: 'blue' | 'green' | 'purple' | 'orange' | 'teal';
}

function StatCard({ label, value, color }: StatCardProps) {
  const colorMap = {
    blue: '#667eea',
    green: '#22c55e',
    purple: '#a855f7',
    orange: '#f59e0b',
    teal: '#14b8a6',
  };

  return (
    <div className="stat-card" style={{ borderLeftColor: colorMap[color] }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: colorMap[color] }}>
        {value}
      </div>
    </div>
  );
}