// Mock data and utilities for testing and development

export interface MockProblem {
  id: string;
  type: string;
  difficulty: string;
  title: string;
  description: string;
  expectedAnswer: number;
}

export interface MockStudent {
  id: string;
  name: string;
  email: string;
  grade: string;
  totalProblems: number;
  problemsSolved: number;
  averageScore: number;
}

export const mockProblems: MockProblem[] = [
  {
    id: "prob_001",
    type: "algebra",
    difficulty: "easy",
    title: "Simple Linear Equation",
    description: "Solve: 2x + 3 = 11",
    expectedAnswer: 4,
  },
  {
    id: "prob_002",
    type: "geometry",
    difficulty: "medium",
    title: "Circle Area",
    description: "Find the area of a circle with radius 5",
    expectedAnswer: 78.54,
  },
  {
    id: "prob_003",
    type: "calculus",
    difficulty: "hard",
    title: "Derivative",
    description: "Find the derivative of f(x) = 3x² + 2x at x = 2",
    expectedAnswer: 14,
  },
];

export const mockStudent: MockStudent = {
  id: "stud_001",
  name: "John Doe",
  email: "john@example.com",
  grade: "Grade 10",
  totalProblems: 150,
  problemsSolved: 89,
  averageScore: 85.5,
};

/**
 * Gets a mock problem by ID
 * @param id Problem ID
 * @returns The mock problem or undefined
 */
export function getMockProblem(id: string): MockProblem | undefined {
  return mockProblems.find((p) => p.id === id);
}

/**
 * Gets all mock problems of a specific type
 * @param type Problem type (algebra, geometry, calculus)
 * @returns Array of problems matching the type
 */
export function getMockProblemsByType(type: string): MockProblem[] {
  return mockProblems.filter((p) => p.type === type);
}

/**
 * Gets all mock problems of a specific difficulty
 * @param difficulty Problem difficulty (easy, medium, hard)
 * @returns Array of problems matching the difficulty
 */
export function getMockProblemsByDifficulty(difficulty: string): MockProblem[] {
  return mockProblems.filter((p) => p.difficulty === difficulty);
}

/**
 * Generates a random mock problem
 * @returns A random problem from the mock data
 */
export function getRandomMockProblem(): MockProblem {
  return mockProblems[Math.floor(Math.random() * mockProblems.length)];
}

/**
 * Updates mock student progress
 * @param problemsSolved New number of problems solved
 * @param averageScore New average score
 * @returns Updated student object
 */
export function updateMockStudentProgress(
  problemsSolved: number,
  averageScore: number
): MockStudent {
  return {
    ...mockStudent,
    problemsSolved,
    averageScore,
  };
}
