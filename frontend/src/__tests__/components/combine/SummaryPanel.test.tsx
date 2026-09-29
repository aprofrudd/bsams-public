import { render, screen, within } from '@testing-library/react';
import { SummaryPanel } from '@/components/combine/SummaryPanel';
import type {
  CombineLeaderboard,
  CombineOverallScoreBasis,
  CombineStationPanel,
  CombineResultRow,
} from '@/lib/types';

function row(name: string, value: number, rank: number): CombineResultRow {
  return {
    bib: rank,
    display_name: name,
    club: 'Repton',
    weight_category: '57kg',
    age_group: 'Junior',
    value,
    display_value: `${value}`,
    rank,
    attempts: 1,
    z_cohort: 0,
    bs_band: rank === 1 ? 'elite' : null,
    asymmetry_pct: null,
    dominant_side: null,
  };
}

function panel(overrides: Partial<CombineStationPanel> = {}): CombineStationPanel {
  return {
    station: 'cmj',
    label: 'Countermovement Jump',
    short_label: 'CMJ',
    unit: 'cm',
    decimals: 1,
    higher_is_better: true,
    cohort_basis: 'event',
    completed: 4,
    stats: { n: 4, mean: 42.6, median: 42.8, sd: 3.1, min: 38, max: 50.7 },
    results: [row('Reece Whitfield', 50.7, 1), row('Callum Byrne', 49.5, 2), row('Grace Rowley', 48.9, 3), row('Sam Kaur', 40.1, 4)],
    ...overrides,
  };
}

function board(
  stations: CombineStationPanel[],
  scoreBasis: CombineOverallScoreBasis = 'z'
): CombineLeaderboard {
  return {
    event_name: 'Combine',
    event_date: '2026-09-14',
    venue: null,
    results_updated_at: '2026-09-14T09:00:00Z',
    participant_count: 38,
    filters: {},
    stations,
    score_basis: scoreBasis,
    overall: [
      {
        bib: 1,
        display_name: 'Sam Kaur',
        club: 'GB Boxing',
        weight_category: '54kg',
        combine_score: 59,
        stations_completed: 6,
        eligible: true,
        rank: 1,
      },
    ],
  };
}

describe('SummaryPanel', () => {
  it('shows a card for every station', () => {
    const stations = [
      panel(),
      panel({ station: 'pogo', short_label: 'Pogo' }),
      panel({ station: 'grip', short_label: 'Grip' }),
    ];
    render(<SummaryPanel board={board(stations)} />);
    expect(screen.getByText('CMJ')).toBeInTheDocument();
    expect(screen.getByText('Pogo')).toBeInTheDocument();
    expect(screen.getByText('Grip')).toBeInTheDocument();
  });

  it('shows only the top three, not the whole field', () => {
    render(<SummaryPanel board={board([panel()])} />);
    expect(screen.getByText('Reece Whitfield')).toBeInTheDocument();
    expect(screen.getByText('Grace Rowley')).toBeInTheDocument();
    // 4th place is in the data but must not appear on an overview card
    expect(screen.queryByText('Sam Kaur', { selector: 'span.min-w-0' })).not.toBeInTheDocument();
  });

  it('shows the group average with its unit', () => {
    render(<SummaryPanel board={board([panel()])} />);
    expect(screen.getByText('Group average')).toBeInTheDocument();
    expect(screen.getByText(/42\.6/)).toBeInTheDocument();
  });

  it('shows how many boxers have been through each station', () => {
    render(<SummaryPanel board={board([panel({ completed: 28 })])} />);
    expect(screen.getByText('28/38')).toBeInTheDocument();
  });

  it('says a station has not started rather than rendering an empty card', () => {
    const empty = panel({
      completed: 0,
      results: [],
      stats: { n: 0, mean: null, median: null, sd: null, min: null, max: null },
    });
    render(<SummaryPanel board={board([empty])} />);
    expect(screen.getByText('Not started')).toBeInTheDocument();
    expect(screen.getByText('0/38')).toBeInTheDocument();
  });

  it('shows a dash for the average before anyone has been through', () => {
    const empty = panel({
      completed: 0,
      results: [],
      stats: { n: 0, mean: null, median: null, sd: null, min: null, max: null },
    });
    const { container } = render(<SummaryPanel board={board([empty])} />);
    expect(within(container).getByText('—')).toBeInTheDocument();
  });

  it('calls out who is leading overall', () => {
    render(<SummaryPanel board={board([panel()])} />);
    expect(screen.getByText('Leading overall')).toBeInTheDocument();
    expect(screen.getByText('Sam Kaur')).toBeInTheDocument();
    expect(screen.getByText(/6\/6 stations/)).toBeInTheDocument();
  });

  it('renders the rank the engine gave, not the row order', () => {
    // Two boxers on 50.7 cm are both first; numbering the card 1, 2, 3 would put a
    // silver medal on a drawn result.
    const tied = panel({
      results: [row('Reece Whitfield', 50.7, 1), row('Callum Byrne', 50.7, 1), row('Grace Rowley', 48.9, 3)],
    });
    render(<SummaryPanel board={board([tied])} />);

    expect(screen.getAllByText('=1')).toHaveLength(2);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('tells you who the leader beat rather than their score', () => {
    const field = {
      ...board([panel()]),
      overall: [
        { ...board([panel()]).overall[0] },
        { ...board([panel()]).overall[0], bib: 2, display_name: 'Ali Byrne', combine_score: 54, rank: 2 },
        { ...board([panel()]).overall[0], bib: 3, display_name: 'Leo Pryce', combine_score: 51, rank: 3 },
      ],
    };
    render(<SummaryPanel board={field} />);

    // The composite is a coach's number; the wall says who you beat.
    expect(screen.queryByText(/59\.0/)).not.toBeInTheDocument();
    expect(screen.getByText(/beat 2 of 3 · 6\/6 stations/)).toBeInTheDocument();
  });

  it('marks which side a landmine best came from', () => {
    const landmine = panel({
      station: 'landmine',
      short_label: 'Landmine',
      unit: 'm/s',
      decimals: 2,
      results: [{ ...row('Reece Whitfield', 3.45, 1), side: 'right' }],
    });
    render(<SummaryPanel board={board([landmine])} />);
    expect(screen.getByText('R')).toBeInTheDocument();
  });

  it('omits the overall callout until someone is eligible', () => {
    const b = board([panel()]);
    b.overall = [{ ...b.overall[0], eligible: false, rank: null }];
    render(<SummaryPanel board={b} />);
    expect(screen.queryByText('Leading overall')).not.toBeInTheDocument();
  });

  it('says the same thing on either basis, since the count comes from the ranking', () => {
    const base = board([panel()], 'percentile');
    const field = {
      ...base,
      overall: [
        { ...base.overall[0] },
        { ...base.overall[0], bib: 2, display_name: 'Ali Byrne', combine_score: 54, rank: 2 },
        { ...base.overall[0], bib: 3, display_name: 'Leo Pryce', combine_score: 51, rank: 3 },
      ],
    };
    render(<SummaryPanel board={field} />);

    expect(screen.getByText(/beat 2 of 3 · 6\/6 stations/)).toBeInTheDocument();
  });

  it('omits the count when one boxer is ranked, having beaten nobody', () => {
    render(<SummaryPanel board={board([panel()])} />);

    expect(screen.queryByText(/beat /)).not.toBeInTheDocument();
    expect(screen.getByText(/6\/6 stations/)).toBeInTheDocument();
  });

  it('makes no claim about the scale in the overall callout', () => {
    // Deliberate: the callout prints the score and the stations behind it, so it reads
    // correctly on either basis. The scale is explained once, on the Combine Score
    // panel, rather than repeated in six-card type where it would be a second thing
    // to keep in step.
    render(<SummaryPanel board={board([panel()], 'percentile')} />);
    expect(screen.queryByText(/room average/)).not.toBeInTheDocument();
    expect(screen.queryByText(/beats the whole room/)).not.toBeInTheDocument();
  });
});
