import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ScrollableTabBar } from '@/components/ScrollableTabBar';

// Mock scrollIntoView since jsdom doesn't implement it
beforeAll(() => {
  Element.prototype.scrollIntoView = jest.fn();
});

const mockTabs = [
  { key: 'jump', label: 'Jump Assessments' },
  { key: 'vbt', label: 'VBT Assessments' },
  { key: 'mobility', label: 'Mobility' },
  { key: 'isometrics', label: 'Isometrics' },
];

describe('ScrollableTabBar', () => {
  it('renders all provided tab labels', () => {
    render(
      <ScrollableTabBar tabs={mockTabs} activeTab="jump" onTabChange={jest.fn()} />
    );

    expect(screen.getByText('Jump Assessments')).toBeInTheDocument();
    expect(screen.getByText('VBT Assessments')).toBeInTheDocument();
    expect(screen.getByText('Mobility')).toBeInTheDocument();
    expect(screen.getByText('Isometrics')).toBeInTheDocument();
  });

  it('active tab has accent background styling', () => {
    render(
      <ScrollableTabBar tabs={mockTabs} activeTab="vbt" onTabChange={jest.fn()} />
    );

    const activeButton = screen.getByText('VBT Assessments');
    expect(activeButton).toHaveClass('bg-accent');

    const inactiveButton = screen.getByText('Jump Assessments');
    expect(inactiveButton).not.toHaveClass('bg-accent');
  });

  it('calls onTabChange with correct key on tab click', () => {
    const onTabChange = jest.fn();
    render(
      <ScrollableTabBar tabs={mockTabs} activeTab="jump" onTabChange={onTabChange} />
    );

    fireEvent.click(screen.getByText('Mobility'));
    expect(onTabChange).toHaveBeenCalledWith('mobility');
  });

  it('container has horizontal scroll enabled', () => {
    const { container } = render(
      <ScrollableTabBar tabs={mockTabs} activeTab="jump" onTabChange={jest.fn()} />
    );

    const scrollContainer = container.querySelector('.scroll-container');
    expect(scrollContainer).toBeInTheDocument();
    expect(scrollContainer).toHaveClass('flex', 'flex-nowrap');
  });
});
