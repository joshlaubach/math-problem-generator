/**
 * Topic selector component
 */

import { TopicMetadata } from '../api/types';
import './TopicSelector.css';

interface TopicSelectorProps {
  topics: TopicMetadata[];
  selectedTopicId: string | null;
  onSelectTopic: (topicId: string) => void;
  loading?: boolean;
}

export function TopicSelector({
  topics,
  selectedTopicId,
  onSelectTopic,
  loading = false,
}: TopicSelectorProps) {
  if (loading) {
    return <div className="topic-selector loading">Loading topics...</div>;
  }

  return (
    <div className="topic-selector">
      <h3>Select Topic</h3>
      <div className="topic-list">
        {topics.map((topic) => (
          <button
            key={topic.topic_id}
            className={`topic-card ${selectedTopicId === topic.topic_id ? 'selected' : ''}`}
            onClick={() => onSelectTopic(topic.topic_id)}
          >
            <div className="topic-name">{topic.topic_name}</div>
            <div className="topic-course">{topic.course_id}</div>
            <div className="topic-difficulty">
              Difficulty: {topic.difficulty_range.min}-{topic.difficulty_range.max}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
