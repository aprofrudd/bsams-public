"""Tests for the combine schemas — the API boundary's unit conversion and vocabulary.

These are the two rules a station operator meets directly:

  - a dynamometer that reads kg/s must land in the database as N/s, because the
    metric registry, the engine, promotion and the norms all assume N/s and none
    of them carry a unit
  - a weight category typed as "57 kg" must become the same "57kg" string the
    board filters on, or the filter chip silently matches nobody
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.combine import (
    WEIGHT_CATEGORIES,
    AttemptSubmit,
    CombineEventCreate,
    CombineEventResponse,
    CombineEventUpdate,
    GripMeasures,
    LeaderboardResponse,
    ParticipantUpdate,
    PublicLeaderboardResponse,
    TrunkRotationMeasures,
    normalise_weight_category,
)


class TestRfdUnitConversion:
    """RFD is stored canonically in N/s; kg/s is converted at the boundary."""

    def test_kg_s_converts_and_keeps_what_was_typed(self):
        """450 kg/s is 4413.0 N/s, and the typed number survives for checking."""
        measures = GripMeasures(
            left_kg=45, right_kg=50, rfd_left_n_s=450, rfd_unit="kg_s"
        )
        assert measures.rfd_left_n_s == 4413.0
        assert measures.rfd_left_entered == 450
        assert measures.rfd_unit_entered == "kg_s"

    def test_both_sides_convert(self):
        measures = GripMeasures(
            left_kg=45,
            right_kg=50,
            rfd_left_n_s=450,
            rfd_right_n_s=100,
            rfd_unit="kg_s",
        )
        assert measures.rfd_left_n_s == 4413.0
        assert measures.rfd_right_n_s == 980.7
        assert measures.rfd_left_entered == 450
        assert measures.rfd_right_entered == 100

    def test_n_s_passes_through_unchanged(self):
        """The default unit is already canonical, so nothing is rewritten."""
        measures = GripMeasures(left_kg=45, rfd_left_n_s=1450, rfd_right_n_s=1500)
        assert measures.rfd_left_n_s == 1450
        assert measures.rfd_right_n_s == 1500
        assert measures.rfd_left_entered is None
        assert measures.rfd_right_entered is None
        assert measures.rfd_unit_entered is None

    def test_range_checked_after_conversion(self):
        """2100 kg/s is 20594 N/s — in range as typed, over the ceiling as stored."""
        with pytest.raises(ValidationError) as exc_info:
            GripMeasures(left_kg=45, rfd_left_n_s=2100, rfd_unit="kg_s")
        assert "20000" in str(exc_info.value)

    def test_in_range_after_conversion_is_accepted(self):
        measures = GripMeasures(left_kg=45, rfd_left_n_s=2000, rfd_unit="kg_s")
        assert measures.rfd_left_n_s == 19613.3

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            GripMeasures(left_kg=45, rfd_left_n_s=-1)

    def test_zero_allowed(self):
        """A dynamometer that reports no RFD is a reading, not a mistake."""
        measures = GripMeasures(left_kg=45, rfd_left_n_s=0)
        assert measures.rfd_left_n_s == 0

    def test_client_supplied_provenance_cannot_skip_the_conversion(self):
        """The "as entered" fields are server-owned.

        A correction naturally PATCHes back the measures it loaded, which already
        carry `rfd_unit_entered`; if that echoed value suppressed the conversion the
        typed kg/s numbers would be stored as N/s, an order of magnitude too low.
        """
        measures = GripMeasures(
            left_kg=50,
            rfd_left_n_s=160,
            rfd_unit="kg_s",
            rfd_unit_entered="kg_s",
            rfd_left_entered=150,
        )
        assert measures.rfd_left_n_s == 1569.1
        assert measures.rfd_left_entered == 160
        assert measures.rfd_unit_entered == "kg_s"

    def test_forged_provenance_is_discarded(self):
        """Otherwise a caller can claim the operator typed a number they never did."""
        measures = GripMeasures(
            left_kg=50, rfd_left_n_s=1200, rfd_unit_entered="kg_s", rfd_left_entered=9999
        )
        assert measures.rfd_left_n_s == 1200
        assert measures.rfd_left_entered is None
        assert measures.rfd_unit_entered is None

    def test_revalidating_a_stored_payload_does_not_convert_twice(self):
        stored = GripMeasures(left_kg=45, rfd_left_n_s=450, rfd_unit="kg_s").model_dump()
        assert GripMeasures(**stored).rfd_left_n_s == 4413.0

    def test_trunk_rotation_shares_the_conversion(self):
        measures = TrunkRotationMeasures(left_kg=120, rfd_left_n_s=450, rfd_unit="kg_s")
        assert measures.rfd_left_n_s == 4413.0

    def test_unknown_unit_rejected(self):
        with pytest.raises(ValidationError):
            GripMeasures(left_kg=45, rfd_left_n_s=450, rfd_unit="lbs_s")

    def test_stored_measures_carry_the_unit_only_when_it_changed_something(self):
        """`measures` holds measurements; the unit tag rides on the entered keys.

        The router persists `measures.model_dump()` minus its None values, so an
        N/s attempt stores exactly the keys it stored before this change.
        """
        canonical = GripMeasures(left_kg=45, rfd_left_n_s=1450).model_dump()
        assert "rfd_unit" not in canonical
        assert canonical["rfd_left_n_s"] == 1450

        converted = GripMeasures(
            left_kg=45, rfd_left_n_s=450, rfd_unit="kg_s"
        ).model_dump()
        assert "rfd_unit" not in converted
        assert converted["rfd_left_entered"] == 450
        assert converted["rfd_unit_entered"] == "kg_s"

    def test_attempt_submit_carries_the_conversion(self):
        """The discriminated union is what the station actually posts through."""
        body = AttemptSubmit(
            participant_id=uuid4(),
            measures={
                "station": "grip",
                "left_kg": 45,
                "rfd_left_n_s": 450,
                "rfd_unit": "kg_s",
            },
        )
        assert body.measures.rfd_left_n_s == 4413.0


class TestWeightCategoryVocabulary:
    """The 20 England Boxing categories, normalised on the way in."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("57", "57kg"),
            ("57 kg", "57kg"),
            ("57KG", "57kg"),
            ("57kg", "57kg"),
            (" 60 ", "60kg"),
            ("63.5", "63.5kg"),
            ("91+", "91+kg"),
            ("+91", "91+kg"),
            ("91kg+", "91+kg"),
            ("91+kg", "91+kg"),
            ("58kg", None),
            ("lightweight", None),
            ("", None),
            ("   ", None),
            (None, None),
        ],
    )
    def test_normaliser_table(self, raw, expected):
        assert normalise_weight_category(raw) == expected

    def test_twenty_categories_in_ascending_order(self):
        assert len(WEIGHT_CATEGORIES) == 20
        assert WEIGHT_CATEGORIES[0] == "46kg"
        assert WEIGHT_CATEGORIES[-1] == "91+kg"

    def test_canonical_values_survive_the_normaliser(self):
        """Re-importing a roster that BSAMS exported must not reject its own rows."""
        assert all(normalise_weight_category(c) == c for c in WEIGHT_CATEGORIES)


class TestParticipantUpdateWeightCategory:
    """Strict on the way in — an unknown category is a typo, not a new division."""

    def test_unknown_category_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ParticipantUpdate(weight_category="58kg")
        assert "Unknown weight category '58kg'" in str(exc_info.value)

    def test_typed_variant_normalised(self):
        assert ParticipantUpdate(weight_category="57 kg").weight_category == "57kg"

    def test_blank_clears_the_field(self):
        """A cleared input means "no category", which is a legitimate roster state."""
        update = ParticipantUpdate(weight_category="")
        assert update.weight_category is None
        assert update.model_dump(exclude_unset=True) == {"weight_category": None}

    def test_omitted_stays_unset(self):
        assert ParticipantUpdate(bib=7).model_dump(exclude_unset=True) == {"bib": 7}


class TestEventScoringSettings:
    def test_rfd_unit_defaults_to_n_s(self):
        event = CombineEventCreate(event_name="BS Combine", event_date="2026-09-19")
        assert event.rfd_unit == "n_s"

    def test_rfd_unit_kg_s_accepted(self):
        event = CombineEventCreate(
            event_name="BS Combine", event_date="2026-09-19", rfd_unit="kg_s"
        )
        assert event.rfd_unit == "kg_s"
        assert CombineEventUpdate(rfd_unit="kg_s").rfd_unit == "kg_s"

    def test_unknown_rfd_unit_rejected(self):
        with pytest.raises(ValidationError):
            CombineEventCreate(
                event_name="BS Combine", event_date="2026-09-19", rfd_unit="lbs_s"
            )

    def test_absolute_w_rejected(self):
        """Watts scored against a W/kg norm made every boxer read ELITE."""
        with pytest.raises(ValidationError):
            CombineEventCreate(
                event_name="BS Combine",
                event_date="2026-09-19",
                airbike_score_basis="absolute_w",
            )
        with pytest.raises(ValidationError):
            CombineEventUpdate(airbike_score_basis="absolute_w")

    def test_w_per_kg_still_accepted(self):
        event = CombineEventCreate(
            event_name="BS Combine",
            event_date="2026-09-19",
            airbike_score_basis="w_per_kg",
        )
        assert event.airbike_score_basis == "w_per_kg"


class TestEventDateWindow:
    """A combine is booked a season or so either side of today.

    The public link's expiry is recomputed from `event_date` on every PATCH and on
    every rotate, so a mistyped year issues a link that is already expired and the
    board 404s. The console guards its own date field, but it is not the only caller
    — the API takes this from any client.
    """

    def test_a_mistyped_year_is_refused(self):
        """"0002-09-19" is a real onChange from a keyboard edit of the year."""
        with pytest.raises(ValidationError):
            CombineEventCreate(event_name="BS Combine", event_date="0002-09-19")

    def test_a_far_future_date_is_refused(self):
        with pytest.raises(ValidationError):
            CombineEventCreate(event_name="BS Combine", event_date="2099-09-19")

    def test_a_patch_cannot_smuggle_one_past(self):
        with pytest.raises(ValidationError):
            CombineEventUpdate(event_date="0002-09-19")

    def test_this_season_is_accepted(self):
        today = date.today()
        assert CombineEventUpdate(event_date=today).event_date == today
        soon = today + timedelta(days=30)
        assert (
            CombineEventCreate(event_name="BS Combine", event_date=soon).event_date
            == soon
        )

    def test_an_omitted_date_is_still_a_valid_patch(self):
        """Most console PATCHes never touch the date."""
        assert CombineEventUpdate(venue="EIS").model_dump(exclude_unset=True) == {
            "venue": "EIS"
        }


class TestLandmineLadder:
    """The reference load has to sit on the ladder the stations offer.

    `score_attempt` drops every landmine throw outside the reference tolerance, so a
    reference load that no ladder load is near means the Punch panel stays empty all
    day while every throw still saves and still promotes a VBT profile.
    """

    def _create(self, **overrides) -> CombineEventCreate:
        payload = {"event_name": "BS Combine 2026", "event_date": "2026-09-19"}
        payload.update(overrides)
        return CombineEventCreate(**payload)

    def test_the_defaults_agree_with_each_other(self):
        event = self._create()
        assert event.landmine_reference_load_kg in event.landmine_loads_kg

    def test_a_ladder_that_orphans_the_reference_load_is_rejected(self):
        """The Friday-setup mistake: a real ladder typed over the default reference."""
        with pytest.raises(ValidationError) as exc:
            self._create(landmine_loads_kg=[12, 17, 22, 27])
        assert "22" in str(exc.value)  # names the nearest ladder load

    def test_moving_the_ladder_and_the_reference_together_is_accepted(self):
        event = self._create(
            landmine_loads_kg=[12, 17, 22, 27], landmine_reference_load_kg=22
        )
        assert event.landmine_loads_kg == [12, 17, 22, 27]

    def test_tolerance_is_what_decides_not_exact_membership(self):
        event = self._create(
            landmine_loads_kg=[12, 17, 22, 27],
            landmine_reference_load_kg=22.5,
            landmine_reference_tolerance_kg=1,
        )
        assert event.landmine_reference_load_kg == 22.5

    def test_a_zero_tolerance_demands_an_exact_ladder_load(self):
        with pytest.raises(ValidationError):
            self._create(
                landmine_loads_kg=[12, 17, 22, 27],
                landmine_reference_load_kg=22.5,
                landmine_reference_tolerance_kg=0,
            )

    def test_the_update_schema_rejects_an_empty_ladder(self):
        with pytest.raises(ValidationError):
            CombineEventUpdate(landmine_loads_kg=[])

    def test_the_update_schema_caps_the_ladder_at_twelve(self):
        with pytest.raises(ValidationError):
            CombineEventUpdate(landmine_loads_kg=[float(n) for n in range(1, 14)])

    @pytest.mark.parametrize("loads", [[0], [-5, 10], [10, 150]])
    def test_the_update_schema_range_checks_each_load(self, loads):
        with pytest.raises(ValidationError):
            CombineEventUpdate(landmine_loads_kg=loads)

    def test_the_update_schema_sorts_and_dedupes_like_create(self):
        assert CombineEventUpdate(landmine_loads_kg=[25, 10, 10, 15]).landmine_loads_kg == [
            10,
            15,
            25,
        ]

    def test_an_unrelated_patch_stays_partial(self):
        assert CombineEventUpdate(venue="EIS").landmine_loads_kg is None


class TestOverallScoreBasis:
    """Which composite the Combine Score shows — opt-in, per event.

    The z composite is what every existing event uses, so the default has to be 'z'
    everywhere: an event created today must behave exactly as it did yesterday.
    """

    def test_a_new_event_defaults_to_the_z_basis(self):
        event = CombineEventCreate(event_name="BS Combine", event_date="2026-09-19")
        assert event.overall_score_basis == "z"

    def test_percentile_can_be_chosen_on_create(self):
        event = CombineEventCreate(
            event_name="BS Combine",
            event_date="2026-09-19",
            overall_score_basis="percentile",
        )
        assert event.overall_score_basis == "percentile"

    def test_the_basis_can_be_switched_by_patch(self):
        assert (
            CombineEventUpdate(overall_score_basis="percentile").overall_score_basis
            == "percentile"
        )
        assert CombineEventUpdate(overall_score_basis="z").overall_score_basis == "z"

    def test_an_unknown_basis_is_refused(self):
        with pytest.raises(ValidationError):
            CombineEventCreate(
                event_name="BS Combine",
                event_date="2026-09-19",
                overall_score_basis="rank",
            )
        with pytest.raises(ValidationError):
            CombineEventUpdate(overall_score_basis="rank")

    def test_an_unrelated_patch_leaves_the_basis_alone(self):
        """Most console PATCHes never touch it, and an unset field is not a switch."""
        assert CombineEventUpdate(venue="EIS").model_dump(exclude_unset=True) == {
            "venue": "EIS"
        }
        assert CombineEventUpdate(venue="EIS").overall_score_basis is None

    def test_the_event_response_carries_it_and_defaults_to_z(self):
        """A row read back before the migration has run has no column to report."""
        field = CombineEventResponse.model_fields["overall_score_basis"]
        assert field.default == "z"


class TestLeaderboardScoreBasis:
    """The board has to label the number it is showing."""

    def _payload(self, **overrides):
        payload = {
            "event_name": "BS Combine 2026",
            "event_date": "2026-09-19",
            "results_updated_at": "2026-09-19T09:00:00Z",
            "participant_count": 0,
            "stations": [],
            "overall": [],
        }
        payload.update(overrides)
        return payload

    def test_both_payloads_default_to_z(self):
        assert PublicLeaderboardResponse(**self._payload()).score_basis == "z"
        assert LeaderboardResponse(**self._payload()).score_basis == "z"

    def test_both_payloads_carry_percentile(self):
        public = PublicLeaderboardResponse(**self._payload(score_basis="percentile"))
        authenticated = LeaderboardResponse(**self._payload(score_basis="percentile"))
        assert public.score_basis == "percentile"
        assert authenticated.score_basis == "percentile"

    def test_an_unknown_basis_is_refused(self):
        with pytest.raises(ValidationError):
            PublicLeaderboardResponse(**self._payload(score_basis="rank"))
