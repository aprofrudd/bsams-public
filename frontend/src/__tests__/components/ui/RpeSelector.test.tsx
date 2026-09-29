import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { RpeSelector } from '@/components/ui/RpeSelector';

describe('RpeSelector', () => {
  it('renders 10 numbered segments (1-10)', () => {
    render(<RpeSelector value={0} onChange={jest.fn()} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(10);

    for (let i = 1; i <= 10; i++) {
      expect(screen.getByText(String(i))).toBeInTheDocument();
    }
  });

  it('clicking segment calls onChange with the value', () => {
    const onChange = jest.fn();
    render(<RpeSelector value={0} onChange={onChange} />);

    fireEvent.click(screen.getByText('7'));
    expect(onChange).toHaveBeenCalledWith(7);

    fireEvent.click(screen.getByText('3'));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it('color zones: 1-3 green, 4-6 yellow, 7-8 orange, 9-10 red', () => {
    // Render without a selected value so all buttons show their zone colors
    render(<RpeSelector value={0} onChange={jest.fn()} />);

    // Green zone: 1, 2, 3
    [1, 2, 3].forEach((n) => {
      const button = screen.getByText(String(n));
      expect(button.className).toContain('green');
    });

    // Yellow zone: 4, 5, 6
    [4, 5, 6].forEach((n) => {
      const button = screen.getByText(String(n));
      expect(button.className).toContain('yellow');
    });

    // Orange zone: 7, 8
    [7, 8].forEach((n) => {
      const button = screen.getByText(String(n));
      expect(button.className).toContain('orange');
    });

    // Red zone: 9, 10
    [9, 10].forEach((n) => {
      const button = screen.getByText(String(n));
      expect(button.className).toContain('red');
    });
  });

  it('selected segment uses active styling', () => {
    render(<RpeSelector value={5} onChange={jest.fn()} />);

    const selectedButton = screen.getByText('5');
    // Active yellow uses bg-yellow-500 (solid)
    expect(selectedButton.className).toContain('bg-yellow-500');
    expect(selectedButton.className).toContain('text-white');
  });
});
