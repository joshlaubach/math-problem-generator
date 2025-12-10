import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MathText } from '../components/MathText';

// Mock KaTeX to avoid rendering errors in tests
vi.mock('react-katex', () => ({
  BlockMath: ({ math }: { math: string }) => <div data-testid="block-math">{math}</div>,
  InlineMath: ({ math }: { math: string }) => <span data-testid="inline-math">{math}</span>,
}));

describe('MathText Component', () => {
  it('renders block math by default', () => {
    render(<MathText latex="x^2 + y^2 = z^2" />);
    
    const blockMath = screen.getByTestId('block-math');
    expect(blockMath).toBeInTheDocument();
    expect(blockMath).toHaveTextContent('x^2 + y^2 = z^2');
  });

  it('renders inline math when inline prop is true', () => {
    render(<MathText latex="x^2" inline={true} />);
    
    const inlineMath = screen.getByTestId('inline-math');
    expect(inlineMath).toBeInTheDocument();
    expect(inlineMath).toHaveTextContent('x^2');
  });

  it('renders empty state when latex is empty', () => {
    render(<MathText latex="" />);
    
    const emptyState = screen.getByText('[No content]');
    expect(emptyState).toBeInTheDocument();
  });

  it('renders empty state when latex is whitespace only', () => {
    render(<MathText latex="   " />);
    
    const emptyState = screen.getByText('[No content]');
    expect(emptyState).toBeInTheDocument();
  });

  it('has correct CSS classes for block math', () => {
    const { container } = render(<MathText latex="x = 5" />);
    
    const mathDiv = container.querySelector('.math-text.block');
    expect(mathDiv).toBeInTheDocument();
  });

  it('has correct CSS classes for inline math', () => {
    const { container } = render(<MathText latex="x = 5" inline={true} />);
    
    const mathSpan = container.querySelector('.math-text.inline');
    expect(mathSpan).toBeInTheDocument();
  });
});
