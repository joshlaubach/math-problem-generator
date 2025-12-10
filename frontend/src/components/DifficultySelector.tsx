/**
 * Difficulty selector component
 */

interface DifficultySelectorProps {
  selectedDifficulty: number | null;
  minDifficulty?: number;
  maxDifficulty?: number;
  recommendedDifficulty?: number;
  onSelectDifficulty: (difficulty: number) => void;
}

export function DifficultySelector({
  selectedDifficulty,
  minDifficulty = 1,
  maxDifficulty = 4,
  recommendedDifficulty,
  onSelectDifficulty,
}: DifficultySelectorProps) {
  const difficulties = Array.from({ length: maxDifficulty - minDifficulty + 1 }, (_, i) =>
    minDifficulty + i
  );

  return (
    <div className="difficulty-selector">
      <h3>Select Difficulty</h3>
      <div className="difficulty-buttons">
        {difficulties.map((difficulty) => (
          <button
            key={difficulty}
            className={`difficulty-btn ${selectedDifficulty === difficulty ? 'selected' : ''} ${
              recommendedDifficulty === difficulty ? 'recommended' : ''
            }`}
            onClick={() => onSelectDifficulty(difficulty)}
          >
            {difficulty}
            {recommendedDifficulty === difficulty && <span className="badge">Recommended</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
