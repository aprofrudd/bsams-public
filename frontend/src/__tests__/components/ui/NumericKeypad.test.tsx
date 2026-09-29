import { render, screen, fireEvent } from '@testing-library/react';
import { NumericKeypad, appendKey } from '@/components/ui/NumericKeypad';

describe('appendKey', () => {
  it('builds a decimal value, which NumberStepper cannot do', () => {
    let value = '';
    for (const key of ['4', '1', '.', '2']) {
      value = appendKey(value, key);
    }
    expect(value).toBe('41.2');
  });

  it('allows only one decimal point', () => {
    expect(appendKey('41.2', '.')).toBe('41.2');
  });

  it('starts a bare decimal with a leading zero', () => {
    expect(appendKey('', '.')).toBe('0.');
  });

  it('replaces a lone leading zero rather than making "05"', () => {
    expect(appendKey('0', '5')).toBe('5');
  });

  it('caps the decimal places', () => {
    expect(appendKey('2.53', '1', { maxDecimals: 2 })).toBe('2.53');
    expect(appendKey('2.5', '3', { maxDecimals: 2 })).toBe('2.53');
  });

  it('caps the integer digits so a stuck key cannot produce nonsense', () => {
    expect(appendKey('8550', '1', { maxIntegerDigits: 4 })).toBe('8550');
  });

  it('backspaces', () => {
    expect(appendKey('41.2', 'back')).toBe('41.');
  });

  it('clears', () => {
    expect(appendKey('41.2', 'clear')).toBe('');
  });
});

describe('NumericKeypad', () => {
  it('emits the updated value on a key press', () => {
    const onChange = jest.fn();
    render(<NumericKeypad value="41" onChange={onChange} />);
    fireEvent.click(screen.getByLabelText('.'));
    expect(onChange).toHaveBeenCalledWith('41.');
  });

  it('clears on the Clear key', () => {
    const onChange = jest.fn();
    render(<NumericKeypad value="41.2" onChange={onChange} />);
    fireEvent.click(screen.getByText('Clear'));
    expect(onChange).toHaveBeenCalledWith('');
  });

  it('has touch-sized targets for a gym iPad', () => {
    render(<NumericKeypad value="" onChange={jest.fn()} />);
    expect(screen.getByLabelText('7').className).toContain('min-h-[64px]');
  });
});
