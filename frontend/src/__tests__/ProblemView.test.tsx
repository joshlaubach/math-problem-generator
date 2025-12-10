import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ProblemView } from '../components/ProblemView';

describe('ProblemView Component', () => {
  const mockProblem = {
    id: 'prob-1',
    topic_id: 'alg1_linear',
    course_id: 'algebra1',
    difficulty: 2,
    prompt_latex: 'x + 2 = 5',
    answer_type: 'numeric',
    final_answer: '3',
    solution: { steps: ['Subtract 2 from both sides', 'x = 3'] },
    calculator_mode: 'none',
    word_problem_prompt: null,
  };

  it('renders problem prompt', () => {
    const { container } = render(
      <ProblemView
        problem={mockProblem}
        onSubmit={() => {}}
        onRequestHint={() => Promise.resolve({ problem_id: 'p1', hint: 'test', hint_type: 'educational' })}
        loading={false}
      />
    );
    
    expect(container).toBeTruthy();
  });

  it('renders answer input field', () => {
    const { container } = render(
      <ProblemView
        problem={mockProblem}
        onSubmit={() => {}}
        onRequestHint={() => Promise.resolve({ problem_id: 'p1', hint: 'test', hint_type: 'educational' })}
        loading={false}
      />
    );
    
    const input = container.querySelector('input[type="text"]');
    expect(input).toBeInTheDocument();
  });

  it('renders check answer button', () => {
    const { container } = render(
      <ProblemView
        problem={mockProblem}
        onSubmit={() => {}}
        onRequestHint={() => Promise.resolve({ problem_id: 'p1', hint: 'test', hint_type: 'educational' })}
        loading={false}
      />
    );
    
    const button = container.querySelector('button');
    expect(button).toHaveTextContent(/Check Answer/i);
  });

  it('renders difficulty badge', () => {
    const { container } = render(
      <ProblemView
        problem={mockProblem}
        onSubmit={() => {}}
        onRequestHint={() => Promise.resolve({ problem_id: 'p1', hint: 'test', hint_type: 'educational' })}
        loading={false}
      />
    );
    
    const badge = container.querySelector('.difficulty-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('2');
  });
});
