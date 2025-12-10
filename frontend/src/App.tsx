/**
 * Main app component
 */

import { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import { useUserIdentity } from './hooks/useUserIdentity';
import { Header } from './components/Header';
import { StudentDashboard } from './pages/StudentDashboard';
import { TeacherDashboard } from './pages/TeacherDashboard';
import { TopicMetadata } from './api/types';
import './App.css';

export function App() {
  const { userId, role, isTeacher, switchToTeacher, switchToStudent } = useUserIdentity();
  const [topics, setTopics] = useState<TopicMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadTopics = async () => {
      try {
        const data = await apiClient.getTopics();
        setTopics(data);
      } catch (error) {
        console.error('Failed to load topics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadTopics();
  }, []);

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="app">
      <Header
        role={role}
        isTeacher={isTeacher}
        userId={userId}
        onSwitchToTeacher={switchToTeacher}
        onSwitchToStudent={switchToStudent}
      />

      <main>
        {isTeacher ? (
          <TeacherDashboard topics={topics} />
        ) : (
          <StudentDashboard userId={userId} />
        )}
      </main>
    </div>
  );
}
