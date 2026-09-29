import { render, screen } from '@testing-library/react';
import { OverallPanel } from '@/components/combine/OverallPanel';
import type {
  CombineLeaderboard,
  CombineOverallEntry,
  CombineOverallScoreBasis,
} from '@/lib/types';

function entry(
  name: string,
  score: number,
  rank: number,
  overrides: Partial<CombineOverallEntry> = {}
): CombineOverallEntry {
  return {
    bib: rank,
    display_name: name,
    club: 'Repton',
    weight_category: '57kg',
    combine_score: score,
    stations_completed: 6,
    eligible: true,
    rank,
    ...overrides,
  };
}

function board(
  scoreBasis: CombineOverallScoreBasis,
  overall: CombineOverallEntry[] = [
    entry('Reece Whitfield', 62.4, 1),
    entry('Callum Byrne', 57.1, 2),
  ]
): CombineLeaderboard {
  return {
    event_name: 'Rehearsal Combine',
    event_date: '2026-09-19',
    venue: 'Performance Centre',
    results_updated_at: '2026-09-19T09:00:00Z',
    participant_count: 12,
    filters: {},
    stations: [],
    overall,
    score_basis: scoreBasis,
  };
}

describe('OverallPanel', () => {
  it('makes no claim about a scale, because the score is not on the wall', () => {
    render(<OverallPanel board={board('z')} />);

    // The old caption explained a T-score. Nothing on this panel needs explaining now.
    expect(screen.queryByText('50 is the room average')).not.toBeInTheDocument();
    expect(
      screen.getByText('position across the stations each boxer has completed')
    ).toBeInTheDocument();
  });

  it('reads the same on either basis, having nothing to relabel', () => {
    render(<OverallPanel board={board('percentile')} />);

    expect(screen.queryByText('100 beats the whole room')).not.toBeInTheDocument();
    expect(screen.queryByText('50 is the room average')).not.toBeInTheDocument();
    expect(
      screen.getByText('position across the stations each boxer has completed')
    ).toBeInTheDocument();
  });

  it('prints the same score to one decimal place on either basis', () => {
    // The basis changes the caption, never the number the engine sent.
    const { unmount } = render(<OverallPanel board={board('z')} />);
    // The composite is a coach's number and is deliberately absent from the wall.
    expect(screen.queryByText('62.4')).not.toBeInTheDocument();
    expect(screen.queryByText('57.1')).not.toBeInTheDocument();
    expect(screen.getByText('1st')).toBeInTheDocument();
    unmount();

    render(<OverallPanel board={board('percentile')} />);
    // The composite is a coach's number and is deliberately absent from the wall.
    expect(screen.queryByText('62.4')).not.toBeInTheDocument();
    expect(screen.queryByText('57.1')).not.toBeInTheDocument();
    expect(screen.getByText('1st')).toBeInTheDocument();
  });

  it('keeps the composite off the wall even when it is a tidy whole number', () => {
    render(<OverallPanel board={board('percentile', [entry('Sam Kaur', 59, 1)])} />);

    expect(screen.queryByText('59.0')).not.toBeInTheDocument();
    expect(screen.queryByText('59')).not.toBeInTheDocument();
    expect(screen.getByText('Sam Kaur')).toBeInTheDocument();
  });

  it('ranks and names the boxers on the board', () => {
    render(<OverallPanel board={board('z')} />);
    expect(screen.getByText('1st')).toBeInTheDocument();
    expect(screen.getByText('Reece Whitfield')).toBeInTheDocument();
    expect(screen.getByText('2nd')).toBeInTheDocument();
  });

  it('counts the boxers still short of the completion threshold', () => {
    const b = board('z', [
      entry('Reece Whitfield', 62.4, 1),
      entry('Grace Rowley', 0, 0, { eligible: false, rank: null, stations_completed: 2 }),
    ]);
    render(<OverallPanel board={b} />);
    expect(screen.getByText(/1 still in progress/)).toBeInTheDocument();
  });

  it('says scores are pending rather than showing an empty board', () => {
    render(<OverallPanel board={board('percentile', [])} />);
    expect(
      screen.getByText('Scores appear once boxers have completed enough stations')
    ).toBeInTheDocument();
  });
});

describe('OverallPanel, the plain-English line', () => {
  it('says how many boxers each one beat, on either basis', () => {
    const entries = [entry('Reece Whitfield', 62.4, 1), entry('Callum Byrne', 57.1, 2)];
    const { unmount } = render(<OverallPanel board={board('z', entries)} />);
    expect(screen.getByText('beat 1 of 2')).toBeInTheDocument();
    expect(screen.getByText('beat 0 of 2')).toBeInTheDocument();
    unmount();

    // The count comes from the ranking, not the scale, so percentile reads the same.
    render(<OverallPanel board={board('percentile', entries)} />);
    expect(screen.getByText('beat 1 of 2')).toBeInTheDocument();
  });

  it('gives boxers who tie the same count, because they beat the same people', () => {
    const entries = [
      entry('Reece Whitfield', 62.4, 1),
      entry('Callum Byrne', 57.1, 2),
      // A real roster never repeats a bib, and the row key is the bib.
      entry('Grace Rowley', 57.1, 2, { bib: 3 }),
    ];
    render(<OverallPanel board={board('z', entries)} />);

    expect(screen.getByText('beat 2 of 3')).toBeInTheDocument();
    expect(screen.getAllByText('beat 0 of 3')).toHaveLength(2);
  });

  it('says nothing when one boxer is ranked, having beaten nobody', () => {
    render(<OverallPanel board={board('z', [entry('Reece Whitfield', 62.4, 1)])} />);
    expect(screen.queryByText(/^beat /)).not.toBeInTheDocument();
  });

  it('counts only ranked boxers, not those still short of the threshold', () => {
    const entries = [
      entry('Reece Whitfield', 62.4, 1),
      entry('Callum Byrne', 57.1, 2),
      entry('Sam Kaur', 70.0, null as unknown as number, { eligible: false, stations_completed: 2 }),
    ];
    render(<OverallPanel board={board('z', entries)} />);

    expect(screen.getByText('beat 1 of 2')).toBeInTheDocument();
    expect(screen.queryByText('beat 0 of 3')).not.toBeInTheDocument();
  });
});
