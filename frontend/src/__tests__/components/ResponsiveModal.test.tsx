import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResponsiveModal } from '@/components/ResponsiveModal';

// Mock useMediaQuery hooks to return desktop mode (not mobile) by default
jest.mock('@/lib/hooks/useMediaQuery', () => ({
  useIsMobileModal: jest.fn(() => false),
}));

// Mock useFocusTrap to return a simple ref
jest.mock('@/lib/hooks/useFocusTrap', () => ({
  useFocusTrap: () => ({ current: null }),
}));

describe('ResponsiveModal', () => {
  it('renders children inside modal when isOpen=true', () => {
    render(
      <ResponsiveModal isOpen={true} onClose={jest.fn()}>
        <p>Modal content here</p>
      </ResponsiveModal>
    );

    expect(screen.getByText('Modal content here')).toBeInTheDocument();
  });

  it('does not render when isOpen=false', () => {
    render(
      <ResponsiveModal isOpen={false} onClose={jest.fn()}>
        <p>Hidden content</p>
      </ResponsiveModal>
    );

    expect(screen.queryByText('Hidden content')).not.toBeInTheDocument();
  });

  it('calls onClose on Escape key press', () => {
    const onClose = jest.fn();
    render(
      <ResponsiveModal isOpen={true} onClose={onClose}>
        <p>Content</p>
      </ResponsiveModal>
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('displays title in header', () => {
    render(
      <ResponsiveModal isOpen={true} onClose={jest.fn()} title="Test Title">
        <p>Content</p>
      </ResponsiveModal>
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Title').tagName).toBe('H2');
  });

  it('applies correct maxWidth class', () => {
    const { container } = render(
      <ResponsiveModal isOpen={true} onClose={jest.fn()} maxWidth="lg">
        <p>Content</p>
      </ResponsiveModal>
    );

    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toHaveClass('max-w-lg');
  });

  it('applies default maxWidth md when not specified', () => {
    const { container } = render(
      <ResponsiveModal isOpen={true} onClose={jest.fn()}>
        <p>Content</p>
      </ResponsiveModal>
    );

    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toHaveClass('max-w-md');
  });
});
