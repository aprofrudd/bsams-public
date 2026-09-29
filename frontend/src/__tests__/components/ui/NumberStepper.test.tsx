import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { NumberStepper } from '@/components/ui/NumberStepper';

describe('NumberStepper - segments variant', () => {
  it('renders correct number of segments', () => {
    render(
      <NumberStepper value={3} onChange={jest.fn()} min={1} max={5} variant="segments" />
    );

    // Should render buttons for 1, 2, 3, 4, 5
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(5);
    expect(buttons[0]).toHaveTextContent('1');
    expect(buttons[4]).toHaveTextContent('5');
  });

  it('clicking a segment calls onChange with the correct value', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={1} onChange={onChange} min={1} max={5} variant="segments" />
    );

    fireEvent.click(screen.getByText('4'));
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it('active segment has accent styling', () => {
    render(
      <NumberStepper value={3} onChange={jest.fn()} min={1} max={5} variant="segments" />
    );

    const activeButton = screen.getByText('3');
    expect(activeButton).toHaveClass('bg-accent');

    const inactiveButton = screen.getByText('1');
    expect(inactiveButton).not.toHaveClass('bg-accent');
  });
});

describe('NumberStepper - plusminus variant', () => {
  it('renders text input with numeric inputMode', () => {
    render(
      <NumberStepper value={5} onChange={jest.fn()} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('inputMode', 'numeric');
    expect(input).toHaveAttribute('pattern', '[0-9]*');
  });

  it('displays value in input', () => {
    render(
      <NumberStepper value={5} onChange={jest.fn()} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.value).toBe('5');
  });

  it('renders empty when value is 0', () => {
    render(
      <NumberStepper value={0} onChange={jest.fn()} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.value).toBe('');
  });

  it('calls onChange with typed number', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={0} onChange={onChange} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '45' } });
    expect(onChange).toHaveBeenCalledWith(45);
  });

  it('strips non-numeric characters', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={0} onChange={onChange} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'abc' } });
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('allows clearing the input', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={45} onChange={onChange} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(0);
    expect((input as HTMLInputElement).value).toBe('');
  });

  it('clamps to max when exceeded', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={0} onChange={onChange} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '700' } });
    expect(onChange).toHaveBeenCalledWith(600);
  });

  it('clamps to min on blur', () => {
    const onChange = jest.fn();
    render(
      <NumberStepper value={0} onChange={onChange} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '0' } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenLastCalledWith(1);
  });

  it('shows placeholder with range', () => {
    render(
      <NumberStepper value={0} onChange={jest.fn()} min={1} max={600} variant="plusminus" />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('placeholder', '1-600');
  });
});
