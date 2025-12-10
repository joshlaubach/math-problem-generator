/**
 * Problem view component - displays a problem and handles submission
 */

import { useState } from 'react';
import { ProblemResponse, HintResponse } from '../api/types';
import { MathText } from './MathText';
import './ProblemView.css';

interface ProblemViewProps {
  problem: ProblemResponse;
  onSubmit: (isCorrect: boolean, timeTaken: number) => void;
  onRequestHint: () => Promise<HintResponse>;
  loading?: boolean;
}

export function ProblemView({
  problem,
  onSubmit,
  onRequestHint,
  loading = false,
}: ProblemViewProps) {
  const [answer, setAnswer] = useState('');
  const [hint, setHint] = useState<HintResponse | null>(null);
  const [showSolution, setShowSolution] = useState(false);
  const [hintLoading, setHintLoading] = useState(false);
  const [startTime] = useState(Date.now());
  const [submitted, setSubmitted] = useState(false);
  const [lastResult, setLastResult] = useState<boolean | null>(null);

  const handleCheckAnswer = () => {
    // Simple client-side answer comparison
    const normalizeAnswer = (ans: string) => ans.trim().toLowerCase();
    const userAnswer = normalizeAnswer(answer);
    const correctAnswer = normalizeAnswer(String(problem.final_answer));

    const isCorrect = userAnswer === correctAnswer;
    const timeTaken = Math.round((Date.now() - startTime) / 1000);

    setLastResult(isCorrect);
    setSubmitted(true);
    onSubmit(isCorrect, timeTaken);
  };

  const handleRequestHint = async () => {
    setHintLoading(true);
    try {
      const hintData = await onRequestHint();
      setHint(hintData);
    } finally {
      setHintLoading(false);
    }
  };

  if (loading) {
    return <div className="problem-view loading">Loading problem...</div>;
  }

  return (
    <div className="problem-view">
      <div className="problem-container">
        <div className="problem-header">
          <h2>Problem</h2>
          <div className="problem-info">
            <span className="difficulty">Difficulty: {problem.difficulty}</span>
            <span className="calculator-mode">{problem.calculator_mode}</span>
          </div>
        </div>

        <div className="problem-statement">
          <MathText latex={problem.prompt_latex} />
        </div>

        {!submitted ? (
          <div className="answer-section">
            <label htmlFor="answer-input">Your Answer:</label>
            <input
              id="answer-input"
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Enter your answer"
              className="input answer-input"
              onKeyPress={(e) => e.key === 'Enter' && handleCheckAnswer()}
            />
            <button onClick={handleCheckAnswer} className="btn btn-primary">
              Check Answer
            </button>
          </div>
        ) : (
          <div className={`result ${lastResult ? 'correct' : 'incorrect'}`}>
            {lastResult ? (
              <div className="result-message">✓ Correct!</div>
            ) : (
              <div className="result-message">✗ Incorrect</div>
            )}
            <div className="correct-answer">
              Correct Answer: <MathText latex={String(problem.final_answer)} inline />
            </div>
          </div>
        )}

        <div className="actions">
          <button
            onClick={handleRequestHint}
            className="btn btn-secondary"
            disabled={hintLoading}
          >
            {hintLoading ? 'Getting hint...' : 'Get Hint'}
          </button>
          <button onClick={() => setShowSolution(!showSolution)} className="btn btn-secondary">
            {showSolution ? 'Hide Solution' : 'Show Solution'}
          </button>
        </div>

        {hint && (
          <div className="hint-box">
            <h3>Hint</h3>
            <p>{hint.hint}</p>
          </div>
        )}

        {showSolution && (
          <div className="solution-box">
            <h3>Solution</h3>
            <p>Solution details would be displayed here</p>
          </div>
        )}
      </div>
    </div>
  );
}
