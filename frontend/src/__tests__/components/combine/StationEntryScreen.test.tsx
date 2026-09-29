import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StationEntryScreen } from '@/components/combine/stations/StationEntryScreen';
import { ApiError, combineApi } from '@/lib/api';
import type {
  CombineAttempt,
  CombineEvent,
  CombineStation,
  CombineStationRoster,
  CombineStationRosterEntry,
} from '@/lib/types';

/**
 * The station screen is the only part of the combine an operator touches on the
 * day, with a boxer waiting. These cover the ways it used to lose or invent data:
 * a retry double-logging an attempt, one stray tap voiding a result, a false
 * "that looks high" on every boxer, and a landmine throw saved with no side.
 */

jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api');
  return {
    ...actual,
    combineApi: {
      stationRoster: jest.fn(),
      listAttempts: jest.fn(),
      submitAttempt: jest.fn(),
      deleteAttempt: jest.fn(),
    },
  };
});

const api = combineApi as jest.Mocked<typeof combineApi>;

function makeEvent(overrides: Partial<CombineEvent> = {}): CombineEvent {
  return {
    id: 'event-1',
    coach_id: 'coach-1',
    event_name: 'Boxing Science Combine',
    event_date: '2026-09-19',
    venue: 'Sheffield',
    status: 'live',
    share_token: 'tok',
    share_url_path: '/combine/live/tok',
    share_token_expires_at: '2026-09-21T00:00:00Z',
    share_revoked_at: null,
    public_display_consent_confirmed_at: '2026-09-18T09:00:00Z',
    public_name_style: 'full',
    show_bs_benchmark: true,
    show_club: true,
    landmine_exercise_name: 'Landmine Punch Throw',
    landmine_loads_kg: [10, 15, 20, 25],
    landmine_reference_load_kg: 20,
    landmine_reference_tolerance_kg: 1,
    landmine_velocity_metric: 'peak',
    airbike_score_basis: 'w_per_kg',
    rfd_unit: 'n_s',
    min_stations_for_overall: 3,
    overall_score_basis: 'z',
    bs_norms_updated_at: null,
    bs_norms_coverage: {},
    results_updated_at: '2026-09-19T09:00:00Z',
    participant_count: 2,
    notes: null,
    created_at: '2026-09-18T09:00:00Z',
    updated_at: '2026-09-18T09:00:00Z',
    ...overrides,
  };
}

function makeEntry(
  overrides: Partial<CombineStationRosterEntry> = {}
): CombineStationRosterEntry {
  return {
    participant_id: 'p1',
    bib: 1,
    name: 'Reece Whitfield',
    club: 'Repton',
    weight_category: '57kg',
    body_mass_kg: 57,
    squad: null,
    attempt_count: 0,
    best_value: null,
    best_display: null,
    last_attempt_at: null,
    status: 'todo',
    ...overrides,
  };
}

function makeRoster(
  station: CombineStation,
  entries: CombineStationRosterEntry[]
): CombineStationRoster {
  return {
    station,
    label: 'Station',
    unit: 'cm',
    total: entries.length,
    done: entries.filter((e) => e.status === 'done').length,
    entries,
  };
}

function makeAttempt(overrides: Partial<CombineAttempt> = {}): CombineAttempt {
  return {
    id: 'a1',
    combine_event_id: 'event-1',
    participant_id: 'p1',
    station: 'cmj',
    attempt_number: 1,
    measures: { height_cm: 41.2 },
    value: 41.2,
    display_value: '41.2 cm',
    voided_at: null,
    notes: null,
    created_at: '2026-09-19T09:05:00Z',
    ...overrides,
  };
}

/** Taps the keypad, which is the only way a number reaches a station field. */
function typeDigits(text: string) {
  for (const character of text) {
    fireEvent.click(screen.getByRole('button', { name: character }));
  }
}

function pickField(label: RegExp) {
  fireEvent.click(screen.getByRole('button', { name: label }));
}

async function pickBoxer(name: RegExp) {
  fireEvent.click(await screen.findByRole('button', { name }));
}

function saveButton(): HTMLButtonElement {
  return screen.getByRole('button', {
    name: /save attempt|looks high/i,
  }) as HTMLButtonElement;
}

beforeEach(() => {
  jest.clearAllMocks();
  api.stationRoster.mockResolvedValue(makeRoster('cmj', [makeEntry()]));
  api.listAttempts.mockResolvedValue([]);
  api.submitAttempt.mockResolvedValue(makeAttempt());
  api.deleteAttempt.mockResolvedValue(undefined);
});

describe('client_attempt_id', () => {
  it('reuses the id on a retry and mints a new one after an edit', async () => {
    const timeout = new ApiError(408, 'Timed out — check the connection and tap SAVE again');
    api.submitAttempt
      .mockRejectedValueOnce(timeout)
      .mockRejectedValueOnce(timeout)
      .mockResolvedValue(makeAttempt());

    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('41.2');

    fireEvent.click(saveButton());
    await screen.findByText(/Timed out/);

    // The response was lost, not the attempt: the same payload must carry the
    // same id or the retry logs a second jump.
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalledTimes(2));

    const [first, second] = api.submitAttempt.mock.calls.map((call) => call[1].client_attempt_id);
    expect(first).toBeTruthy();
    expect(second).toBe(first);

    // A corrected number is a different attempt, so it needs its own id.
    fireEvent.click(screen.getByRole('button', { name: 'Backspace' }));
    typeDigits('3');
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalledTimes(3));

    expect(api.submitAttempt.mock.calls[2][1].client_attempt_id).not.toBe(first);
  });

  it('clears the save error once a save succeeds', async () => {
    api.submitAttempt
      .mockRejectedValueOnce(new ApiError(500, 'Could not save that attempt'))
      .mockResolvedValue(makeAttempt());

    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('41.2');

    fireEvent.click(saveButton());
    await screen.findByText('Could not save that attempt');

    fireEvent.click(saveButton());
    await waitFor(() => expect(screen.queryByText('Could not save that attempt')).toBeNull());
  });
});

describe('voiding an attempt', () => {
  // The disarm test switches to fake timers part-way through; hand them back so the
  // rest of the suite keeps its real ones.
  afterEach(() => jest.useRealTimers());

  it('takes two taps, so one stray touch cannot delete a result', async () => {
    api.listAttempts.mockResolvedValue([makeAttempt()]);
    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);

    fireEvent.click(await screen.findByRole('button', { name: /41\.2 cm/ }));
    expect(api.deleteAttempt).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: /tap again to remove/i }));
    await waitFor(() => expect(api.deleteAttempt).toHaveBeenCalledWith('a1'));
  });

  it('disarms after a few seconds, so an armed chip cannot be voided an hour later', async () => {
    // The other half of the guard: without the disarm, a chip armed by a stray
    // touch at 10:05 is still armed when the operator taps it to read it at 10:40,
    // and that tap deletes the result with no undo.
    api.listAttempts.mockResolvedValue([makeAttempt()]);
    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    const chip = await screen.findByRole('button', { name: /41\.2 cm/ });

    // Faked only now: the roster and attempts above resolve as microtasks, and the
    // arm's timeout is registered by the tap below, after the switch.
    jest.useFakeTimers();
    fireEvent.click(chip);
    expect(screen.getByRole('button', { name: /tap again to remove/i })).toBeInTheDocument();

    act(() => jest.advanceTimersByTime(5000));
    expect(screen.getByRole('button', { name: /41\.2 cm/ })).toBeInTheDocument();

    // So the next tap arms again rather than deleting.
    fireEvent.click(screen.getByRole('button', { name: /41\.2 cm/ }));
    expect(api.deleteAttempt).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /tap again to remove/i })).toBeInTheDocument();
  });

  it('arms one chip at a time, so tapping another leaves the first alone', async () => {
    api.listAttempts.mockResolvedValue([
      makeAttempt(),
      makeAttempt({
        id: 'a2',
        attempt_number: 2,
        measures: { height_cm: 43.5 },
        value: 43.5,
        display_value: '43.5 cm',
      }),
    ]);
    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);

    fireEvent.click(await screen.findByRole('button', { name: /41\.2 cm/ }));
    fireEvent.click(screen.getByRole('button', { name: /43\.5 cm/ }));

    expect(screen.getByRole('button', { name: /41\.2 cm/ })).toBeInTheDocument();
    expect(api.deleteAttempt).not.toHaveBeenCalled();
  });
});

describe('the outlier guard', () => {
  it('compares a pogo attempt with the cohort best on the same scale', async () => {
    // Cohort bests are RSI; comparing 480 ms of flight with 2.5 turned SAVE amber
    // for every boxer after the first.
    api.stationRoster.mockResolvedValue(
      makeRoster('pogo', [makeEntry({ best_value: 2.5, best_display: '2.50' })])
    );

    render(<StationEntryScreen event={makeEvent()} station="pogo" />);
    await pickBoxer(/Reece Whitfield/);

    pickField(/Flight Time/);
    typeDigits('480');
    pickField(/Contact Time/);
    typeDigits('192');

    expect(screen.queryByText(/looks high/i)).toBeNull();
    expect(saveButton()).toBeEnabled();
  });

  it('still catches a missed decimal point', async () => {
    api.stationRoster.mockResolvedValue(
      makeRoster('cmj', [makeEntry({ best_value: 45, best_display: '45.0' })])
    );

    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('89');

    expect(screen.getByText(/looks high/i)).toBeInTheDocument();
  });
});

describe('out-of-range values', () => {
  it('keeps SAVE disabled with a hint when a gt=0 field holds zero', async () => {
    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('0');

    expect(saveButton()).toBeDisabled();
    expect(screen.getByText(/Jump Height must be over 0/)).toBeInTheDocument();
  });
});

describe('the air bike station', () => {
  it('warns when the boxer has no body mass, but still allows the save', async () => {
    api.stationRoster.mockResolvedValue(
      makeRoster('air_bike', [makeEntry({ body_mass_kg: null })])
    );

    render(<StationEntryScreen event={makeEvent()} station="air_bike" />);
    await pickBoxer(/Reece Whitfield/);

    expect(screen.getByText(/no body mass/i)).toBeInTheDocument();

    pickField(/^7s Power/);
    typeDigits('855');
    pickField(/17s Power/);
    typeDigits('700');
    pickField(/27s Power/);
    typeDigits('600');
    expect(saveButton()).toBeEnabled();
  });

  it('says nothing when the boxer has been weighed in', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('air_bike', [makeEntry()]));

    render(<StationEntryScreen event={makeEvent()} station="air_bike" />);
    await pickBoxer(/Reece Whitfield/);

    expect(screen.queryByText(/no body mass/i)).toBeNull();
  });

  it('defaults to the sprint the boxer has not done yet', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('air_bike', [makeEntry({ attempt_count: 1 })]));
    api.listAttempts.mockResolvedValue([
      makeAttempt({
        station: 'air_bike',
        measures: { sprint_number: 1, power_7s: 855 },
        display_value: '15.02 W/kg · S1',
      }),
    ]);

    render(<StationEntryScreen event={makeEvent()} station="air_bike" />);
    await pickBoxer(/Reece Whitfield/);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Sprint 2' })).toHaveClass('bg-accent')
    );
  });
});

describe('the landmine station', () => {
  it('will not save a throw without a side', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('landmine', [makeEntry()]));

    render(<StationEntryScreen event={makeEvent()} station="landmine" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('4.2');

    expect(saveButton()).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Right' }));
    expect(saveButton()).toBeEnabled();

    fireEvent.click(saveButton());
    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalled());
    expect(api.submitAttempt.mock.calls[0][1].measures).toMatchObject({
      station: 'landmine',
      load_kg: 20,
      peak_velocity_ms: 4.2,
      side: 'right',
    });
  });

  it('asks for the velocity the event actually ranks on', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('landmine', [makeEntry()]));

    render(
      <StationEntryScreen
        event={makeEvent({ landmine_velocity_metric: 'mean' })}
        station="landmine"
      />
    );
    await pickBoxer(/Reece Whitfield/);
    typeDigits('2.1');
    fireEvent.click(screen.getByRole('button', { name: 'Left' }));
    fireEvent.click(saveButton());

    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalled());
    expect(api.submitAttempt.mock.calls[0][1].measures).toMatchObject({
      mean_velocity_ms: 2.1,
      side: 'left',
    });
  });

  it('forgets the side when the next boxer steps up', async () => {
    api.stationRoster.mockResolvedValue(
      makeRoster('landmine', [makeEntry(), makeEntry({ participant_id: 'p2', bib: 2, name: 'Callum Byrne' })])
    );

    render(<StationEntryScreen event={makeEvent()} station="landmine" />);
    await pickBoxer(/Reece Whitfield/);
    fireEvent.click(screen.getByRole('button', { name: 'Right' }));

    await pickBoxer(/Callum Byrne/);
    typeDigits('4.2');
    expect(saveButton()).toBeDisabled();
  });
});

describe('the dynamometer stations', () => {
  it('labels RFD in the unit the event dynamometer reads, and says so in the payload', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('grip', [makeEntry()]));

    render(<StationEntryScreen event={makeEvent({ rfd_unit: 'kg_s' })} station="grip" />);
    await pickBoxer(/Reece Whitfield/);

    fireEvent.click(screen.getByRole('button', { name: /optional fields/i }));
    expect(screen.getAllByText('(kg/s)')).toHaveLength(2);

    pickField(/^Left/);
    typeDigits('45');
    fireEvent.click(saveButton());

    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalled());
    expect(api.submitAttempt.mock.calls[0][1].measures).toMatchObject({
      station: 'grip',
      left_kg: 45,
      rfd_unit: 'kg_s',
    });
  });
});

describe('who is on screen after a save', () => {
  it('stays on the boxer, and moves on only when asked', async () => {
    const entries = [
      makeEntry(),
      makeEntry({ participant_id: 'p2', bib: 2, name: 'Callum Byrne' }),
    ];
    api.stationRoster.mockImplementation(async () => makeRoster('cmj', entries));

    render(<StationEntryScreen event={makeEvent()} station="cmj" />);
    await pickBoxer(/Reece Whitfield/);
    typeDigits('41.2');
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.submitAttempt).toHaveBeenCalled());

    // One jump logged does not mean the boxer is finished — they have two more.
    entries[0] = makeEntry({ status: 'done', attempt_count: 1, best_value: 41.2, best_display: '41.2' });
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Reece Whitfield' })).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole('button', { name: /next boxer/i }));
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Callum Byrne' })).toBeInTheDocument()
    );
  });
});

describe('the landmine Ref badge', () => {
  it('marks every load the board would actually rank, not just an exact match', async () => {
    api.stationRoster.mockResolvedValue(makeRoster('landmine', [makeEntry()]));

    // A reference load between two ladder loads is a legitimate configuration: the
    // engine scores any throw within tolerance of it.
    render(
      <StationEntryScreen
        event={makeEvent({
          landmine_loads_kg: [12, 17, 22, 27],
          landmine_reference_load_kg: 22.5,
          landmine_reference_tolerance_kg: 1,
        })}
        station="landmine"
      />
    );
    await pickBoxer(/Reece Whitfield/);

    // 22 kg is 0.5 kg off the reference, so a throw at it counts — with no badge the
    // operator has no way to tell, and the badge's absence means nothing at all.
    expect(screen.getByRole('button', { name: '22 kg Ref' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '17 kg' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '27 kg' })).toBeInTheDocument();
  });
});
