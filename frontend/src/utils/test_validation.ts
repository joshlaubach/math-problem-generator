// Validation test utilities for answer checking

interface AnswerComparison {
  correct: boolean;
  expected: number;
  received: number;
  tolerance: number;
  difference: number;
}

/**
 * Compares two numbers with tolerance for floating point errors
 * @param expected The expected answer value
 * @param received The student's answer value
 * @param tolerance The acceptable difference (default 0.01)
 * @returns Comparison result object
 */
export function compareAnswers(
  expected: number,
  received: number,
  tolerance: number = 0.01
): AnswerComparison {
  const difference = Math.abs(expected - received);
  
  return {
    correct: difference <= tolerance,
    expected,
    received,
    tolerance,
    difference,
  };
}

/**
 * Checks if an answer matches within tolerance
 * @param expected The expected answer value
 * @param received The student's answer value
 * @param tolerance The acceptable difference (default 0.01)
 * @returns Boolean indicating if answer is correct
 */
export function isAnswerCorrect(
  expected: number,
  received: number,
  tolerance: number = 0.01
): boolean {
  return compareAnswers(expected, received, tolerance).correct;
}

/**
 * Parses a string input as a number for answer submission
 * @param input The user's input string
 * @returns The parsed number or null if invalid
 */
export function parseAnswerInput(input: string): number | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  const parsed = parseFloat(trimmed);
  if (isNaN(parsed)) return null;

  return parsed;
}

/**
 * Formats a number for display
 * @param value The number to format
 * @param decimalPlaces Number of decimal places (default 2)
 * @returns Formatted string
 */
export function formatNumber(value: number, decimalPlaces: number = 2): string {
  return parseFloat(value.toFixed(decimalPlaces)).toString();
}

/**
 * Validates if input is a valid number format
 * @param input The input string to validate
 * @returns Boolean indicating if input is valid
 */
export function isValidNumberInput(input: string): boolean {
  return parseAnswerInput(input) !== null;
}
