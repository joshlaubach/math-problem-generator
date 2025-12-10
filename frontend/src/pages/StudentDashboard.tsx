/**
 * Student dashboard - main student interface
 * 
 * Features:
 * - Select topics and difficulty levels
 * - Generate and solve problems with real-time hints
 * - localStorage persistence for last selected topic and difficulty
 * - Next Problem button for seamless problem generation
 * - Skills tab with concept-level performance heatmap
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { useAuthUser } from '../hooks/useAuthUser';
import { TopicMetadata, ProblemResponse, HintResponse } from '../api/types';
import { TopicSelector } from '../components/TopicSelector';
import { DifficultySelector } from '../components/DifficultySelector';
import { ProblemView } from '../components/ProblemView';
import { SkillsView } from '../components/SkillsView';
import './StudentDashboard.css';

interface StudentDashboardProps {
  userId: string;
}

/**
 * LocalStorage keys for persisting user preferences
 */
const STORAGE_KEYS = {
  LAST_TOPIC_ID: 'mpg_last_topic_id',
  LAST_DIFFICULTY: 'mpg_last_difficulty',
  ACTIVE_TAB: 'mpg_active_tab',
};

type TabType = 'practice' | 'skills_sat' | 'skills_ap';

export function StudentDashboard({ userId }: StudentDashboardProps) {
  const { backendUserId, legacyUserId } = useAuthUser();
  // Use backendUserId if authenticated, otherwise use legacyUserId or passed userId
  const effectiveUserId = backendUserId || legacyUserId || userId;

  const [topics, setTopics] = useState<TopicMetadata[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<number | null>(null);
  const [recommendedDifficulty, setRecommendedDifficulty] = useState<number | null>(null);
  const [problem, setProblem] = useState<ProblemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [problemLoading, setProblemLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastCorrect, setLastCorrect] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('practice');

  // Fetch topics on mount
  useEffect(() => {
    const fetchTopics = async () => {
      try {
        const data = await apiClient.getTopics();
        setTopics(data);
        setError(null);

        // After topics are loaded, restore last selection from localStorage
        const savedTopicId = localStorage.getItem(STORAGE_KEYS.LAST_TOPIC_ID);
        const savedDifficultyStr = localStorage.getItem(STORAGE_KEYS.LAST_DIFFICULTY);
        const savedTab = localStorage.getItem(STORAGE_KEYS.ACTIVE_TAB) as TabType | null;

        // Only restore topic if it exists in current topics list
        if (savedTopicId && data.find(t => t.topic_id === savedTopicId)) {
          setSelectedTopicId(savedTopicId);
        }

        // Only restore difficulty if valid
        if (savedDifficultyStr) {
          const savedDifficulty = parseInt(savedDifficultyStr, 10);
          if (!isNaN(savedDifficulty)) {
            setSelectedDifficulty(savedDifficulty);
          }
        }

        // Restore last active tab
        if (savedTab && ['practice', 'skills_sat', 'skills_ap'].includes(savedTab)) {
          setActiveTab(savedTab);
        }
      } catch (err) {
        setError('Failed to load topics');
      } finally {
        setLoading(false);
      }
    };

    fetchTopics();
  }, []);

  // Fetch recommendation when topic changes
  useEffect(() => {
    if (!selectedTopicId) {
      setRecommendedDifficulty(null);
      return;
    }

    // Persist selected topic to localStorage
    localStorage.setItem(STORAGE_KEYS.LAST_TOPIC_ID, selectedTopicId);

    const fetchRecommendation = async () => {
      try {
        const rec = await apiClient.getDifficultyRecommendation(effectiveUserId, selectedTopicId);
        setRecommendedDifficulty(rec.recommended_difficulty);
      } catch (err) {
        // Recommendation is optional
        setRecommendedDifficulty(null);
      }
    };

    fetchRecommendation();
  }, [selectedTopicId, effectiveUserId]);

  // Persist difficulty selection to localStorage
  useEffect(() => {
    if (selectedDifficulty !== null) {
      localStorage.setItem(STORAGE_KEYS.LAST_DIFFICULTY, String(selectedDifficulty));
    }
  }, [selectedDifficulty]);

  // Persist active tab to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_TAB, activeTab);
  }, [activeTab]);

  const handleGenerateProblem = async () => {
    if (!selectedTopicId || selectedDifficulty === null) {
      setError('Please select topic and difficulty');
      return;
    }

    setProblemLoading(true);
    try {
      const problemData = await apiClient.generateProblem({
        topicId: selectedTopicId,
        difficulty: selectedDifficulty,
        calculatorMode: 'none',
      });
      setProblem(problemData);
      setLastCorrect(null); // Reset correct state for new problem
      setError(null);
    } catch (err) {
      setError('Failed to generate problem');
    } finally {
      setProblemLoading(false);
    }
  };

  const handleSubmitAttempt = async (isCorrect: boolean, timeTaken: number) => {
    if (!problem || !selectedTopicId) return;

    // Update lastCorrect state (used to show/hide Next Problem button)
    setLastCorrect(isCorrect);

    try {
      const selectedTopic = topics.find(t => t.topic_id === selectedTopicId);
      if (!selectedTopic) return;

      await apiClient.submitAttempt({
        userId: effectiveUserId,
        problemId: problem.id,
        topicId: selectedTopicId,
        courseId: selectedTopic.course_id,
        difficulty: problem.difficulty,
        isCorrect,
        timeTakenSeconds: timeTaken,
      });
    } catch (err) {
      console.error('Failed to submit attempt:', err);
    }
  };

  const handleRequestHint = async (): Promise<HintResponse> => {
    if (!problem) throw new Error('No problem selected');

    return await apiClient.requestHint({
      problem_id: problem.id,
      problem_latex: problem.prompt_latex,
    });
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
  };

  const selectedTopic = selectedTopicId ? topics.find(t => t.topic_id === selectedTopicId) : null;

  return (
    <div className="student-dashboard">
      {error && <div className="error-banner">{error}</div>}

      {/* Tab Navigation */}
      <div className="dashboard-tabs">
        <button
          className={`tab-button ${activeTab === 'practice' ? 'active' : ''}`}
          onClick={() => handleTabChange('practice')}
        >
          Practice
        </button>
        <button
          className={`tab-button ${activeTab === 'skills_sat' ? 'active' : ''}`}
          onClick={() => handleTabChange('skills_sat')}
        >
          SAT Math Skills
        </button>
        <button
          className={`tab-button ${activeTab === 'skills_ap' ? 'active' : ''}`}
          onClick={() => handleTabChange('skills_ap')}
        >
          AP Calculus Skills
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'practice' && (
        <div className="dashboard-grid">
          <div className="sidebar">
            <TopicSelector
              topics={topics}
              selectedTopicId={selectedTopicId}
              onSelectTopic={setSelectedTopicId}
              loading={loading}
            />

            {selectedTopicId && (
              <DifficultySelector
                selectedDifficulty={selectedDifficulty}
                minDifficulty={selectedTopic?.difficulty_range.min || 1}
                maxDifficulty={selectedTopic?.difficulty_range.max || 4}
                recommendedDifficulty={recommendedDifficulty}
                onSelectDifficulty={setSelectedDifficulty}
              />
            )}

            {selectedTopicId && selectedDifficulty !== null && (
              <button
                onClick={handleGenerateProblem}
                className="btn btn-primary btn-large"
                disabled={problemLoading}
              >
                {problemLoading ? 'Generating...' : 'Generate Problem'}
              </button>
            )}
          </div>

          <div className="main-content">
            {problem ? (
              <div>
                <div className="problem-header-info">
                  <span>Topic: <strong>{selectedTopicId}</strong></span>
                  <span>Difficulty: <strong>{problem.difficulty}</strong></span>
                  {problem.calculator_mode && (
                    <span>Calculator: <strong>{problem.calculator_mode}</strong></span>
                  )}
                </div>
                <ProblemView
                  problem={problem}
                  onSubmit={handleSubmitAttempt}
                  onRequestHint={handleRequestHint}
                />
                {/* Next Problem button - only show if last attempt was correct */}
                {lastCorrect === true && (
                  <div className="next-problem-section">
                    <button
                      onClick={handleGenerateProblem}
                      className="btn btn-success btn-large"
                      disabled={problemLoading}
                    >
                      {problemLoading ? 'Generating...' : '→ Next Problem'}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <h2>Welcome to the Math Problem Generator</h2>
                <p>Select a topic and difficulty level to get started!</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'skills_sat' && (
        <SkillsView courseId="sat_math" courseName="SAT Math" />
      )}

      {activeTab === 'skills_ap' && (
        <SkillsView courseId="ap_calculus" courseName="AP Calculus" />
      )}
    </div>
  );
}
