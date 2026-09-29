"""Security tests for the PUBLIC combine board.

This endpoint is unauthenticated and the URL lives on a gym wall, so the tests
here are mostly about what must NOT come back. The backend holds the Supabase
service_role key, which means row-level security protects nothing on this path —
every filter and every field projection is Python code, and this file is what
holds that code honest.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fake_supabase import FakeSupabase, FakeTable
from tests.test_combine_router import make_athlete, make_event, make_participant

client = TestClient(app)

UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

FORBIDDEN_SUBSTRINGS = [
    "gender",
    "athlete_id",
    "participant_id",
    "attempt_id",
    "combine_event_id",
    "coach_id",
    "user_id",
    "share_token",
    "date_of_birth",
    "body_mass",
    "email",
    "entered_by",
    "bs_norms",
    "z_bs",
    "mean_z",
]


def values_text(response) -> str:
    """The payload as text with the timestamps dropped.

    Scanning the whole document is the point of these tests, but `results_updated_at`
    carries microseconds, so roughly one poll in two hundred contains "855" by
    coincidence and fails a test about what the board publishes. A timestamp cannot
    carry a wattage, so dropping it costs the check nothing.
    """
    return json.dumps({k: v for k, v in response.json().items() if not k.endswith("_at")})


def _future(days: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def live_event(**overrides) -> dict:
    return make_event(
        status="live",
        public_display_consent_confirmed_at=datetime.now(timezone.utc).isoformat(),
        share_token_expires_at=_future(),
        **overrides,
    )


class LookupExplodes(FakeSupabase):
    """A store whose event lookup fails — a Supabase wobble, not a bad token."""

    def table(self, name: str):
        if name == "combine_events":
            raise RuntimeError("connection reset by peer")
        return super().table(name)


@pytest.fixture
def board():
    """A live event with two boxers and a CMJ result each."""
    event = live_event(
        # Bands are gender-matched with no pooled fallback, so the snapshot has to
        # carry the split the refresh endpoint writes.
        bs_norms_snapshot={
            "height_cm": {
                "mean": 38.0,
                "sd": 5.0,
                "n": 40,
                "by_gender": {"male": {"mean": 38.0, "sd": 5.0, "n": 40}},
            }
        }
    )
    a1, a2 = make_athlete("Jack Reid"), make_athlete("Sam Okoro")
    p1 = make_participant(event, a1, bib=1)
    p2 = make_participant(event, a2, bib=2, weight_category="60kg")

    store = FakeSupabase(
        combine_events=[event],
        athletes=[a1, a2],
        combine_participants=[p1, p2],
        combine_attempts=[
            {
                "id": str(uuid4()),
                "combine_event_id": event["id"],
                "participant_id": p1["id"],
                "station": "cmj",
                "attempt_number": 1,
                "measures": {"height_cm": 43.0},
                "voided_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid4()),
                "combine_event_id": event["id"],
                "participant_id": p2["id"],
                "station": "cmj",
                "attempt_number": 1,
                "measures": {"height_cm": 38.0},
                "voided_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ],
        performance_events=[],
        vbt_profiles=[],
        vbt_sets=[],
        air_bike_tests=[],
        air_bike_sprints=[],
        profiles=[],
    )
    with patch("app.core.supabase_client.get_supabase_client", return_value=store):
        yield store, event


class TestAccess:
    def test_no_authentication_required(self, board):
        _, event = board
        response = client.get(f"/api/v1/combine/public/{event['share_token']}")
        assert response.status_code == 200
        assert response.json()["event_name"] == "BS Combine 2026"

    def test_meta_endpoint_is_minimal(self, board):
        _, event = board
        response = client.get(f"/api/v1/combine/public/{event['share_token']}/meta")
        assert response.status_code == 200
        assert set(response.json()) == {
            "event_name",
            "event_date",
            "venue",
            "status",
            "results_updated_at",
            "participant_count",
        }


class TestFailuresAreIndistinguishable:
    """A caller must not be able to tell a revoked token from one that never existed."""

    def _expect_404(self, token):
        response = client.get(f"/api/v1/combine/public/{token}")
        assert response.status_code == 404
        return response

    def test_unknown_token(self, board):
        self._expect_404("tok_does_not_exist")

    def test_draft_event_is_not_public(self, board):
        store, event = board
        store.data["combine_events"][0]["status"] = "draft"
        self._expect_404(event["share_token"])

    def test_revoked_token(self, board):
        store, event = board
        store.data["combine_events"][0]["share_revoked_at"] = datetime.now(timezone.utc).isoformat()
        self._expect_404(event["share_token"])

    def test_expired_token(self, board):
        store, event = board
        store.data["combine_events"][0]["share_token_expires_at"] = _past()
        self._expect_404(event["share_token"])

    def test_consent_not_confirmed(self, board):
        """No confirmation that minors' names may be shown means no public board."""
        store, event = board
        store.data["combine_events"][0]["public_display_consent_confirmed_at"] = None
        self._expect_404(event["share_token"])

    def test_closed_events_stay_visible(self, board):
        store, event = board
        store.data["combine_events"][0]["status"] = "closed"
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200

    def test_unknown_and_expired_return_identical_responses(self, board):
        store, event = board
        unknown = client.get("/api/v1/combine/public/tok_does_not_exist")
        store.data["combine_events"][0]["share_token_expires_at"] = _past()
        expired = client.get(f"/api/v1/combine/public/{event['share_token']}")
        assert unknown.status_code == expired.status_code
        assert unknown.json() == expired.json()

    def test_over_length_token_is_rejected_before_touching_the_database(self):
        mock_client = MagicMock()
        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.get("/api/v1/combine/public/" + "x" * 200)
        assert response.status_code == 404
        mock_client.table.assert_not_called()


class TestTransientLookupFailures:
    """A database blip must not read as a revoked board.

    The kiosk clears the screen after three consecutive 404s, so answering a failed
    lookup with "not found" blanks a TV in a full hall over a network wobble. The
    identical-404 rule constrains what a *successful* lookup may reveal; a failure
    that happens for every token, valid or not, reveals nothing.
    """

    @pytest.fixture
    def broken(self):
        event = live_event()
        store = LookupExplodes(
            combine_events=[event],
            combine_participants=[],
            combine_attempts=[],
            athletes=[],
            profiles=[],
        )
        with patch("app.core.supabase_client.get_supabase_client", return_value=store):
            yield event

    def test_a_failed_lookup_is_not_a_404(self, broken):
        response = client.get(f"/api/v1/combine/public/{broken['share_token']}")
        assert response.status_code == 503

    def test_the_meta_endpoint_fails_the_same_way(self, broken):
        response = client.get(f"/api/v1/combine/public/{broken['share_token']}/meta")
        assert response.status_code == 503

    def test_the_failure_looks_the_same_for_any_token(self, broken):
        """Otherwise a 503 on a valid token and a 404 on an unknown one would tell a
        caller which tokens exist."""
        valid = client.get(f"/api/v1/combine/public/{broken['share_token']}")
        unknown = client.get("/api/v1/combine/public/tok_does_not_exist")
        assert (valid.status_code, valid.json()) == (unknown.status_code, unknown.json())
        assert broken["share_token"] not in valid.text


class TestPayloadLeakage:
    def test_no_identifiers_anywhere_in_the_payload(self, board):
        _, event = board
        body = client.get(f"/api/v1/combine/public/{event['share_token']}").text
        for needle in FORBIDDEN_SUBSTRINGS:
            assert needle not in body, f"public payload leaked '{needle}'"

    def test_no_uuid_shaped_value_anywhere_in_the_payload(self, board):
        """The strongest form of the check — nothing that could be a database id."""
        _, event = board
        body = client.get(f"/api/v1/combine/public/{event['share_token']}").text
        assert UUID_PATTERN.search(body) is None

    def test_never_calls_the_admin_benchmark_pool(self, board):
        """Norms come from the snapshot on the event row, never from a live admin query."""
        _, event = board
        with patch("app.services.admin_pool.get_admin_athletes") as pool_athletes, patch(
            "app.services.admin_pool.get_admin_athlete_ids"
        ) as pool_ids:
            client.get(f"/api/v1/combine/public/{event['share_token']}")
        pool_athletes.assert_not_called()
        pool_ids.assert_not_called()

    def test_benchmark_is_a_band_not_a_number(self, board):
        _, event = board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        leader = cmj["results"][0]
        assert leader["bs_band"] == "elite"  # 43.0 against mean 38.0, sd 5.0
        assert "z_bs" not in leader

    def test_benchmark_can_be_switched_off(self, board):
        store, event = board
        store.data["combine_events"][0]["show_bs_benchmark"] = False
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["bs_band"] is None

    def test_air_bike_is_published_per_kilogram_only(self, board):
        """Publishing absolute watts alongside W/kg would make body mass derivable."""
        store, event = board
        participant = store.data["combine_participants"][0]
        store.data["combine_attempts"].append(
            {
                "id": str(uuid4()),
                "combine_event_id": event["id"],
                "participant_id": participant["id"],
                "station": "air_bike",
                "attempt_number": 1,
                "measures": {
                    "sprint_number": 1,
                    "power_7s": 855.0,
                    "power_17s": 700.0,
                    "power_27s": 600.0,
                },
                "voided_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        bike = next(p for p in data["stations"] if p["station"] == "air_bike")
        assert bike["unit"] == "W/kg"
        assert bike["results"][0]["value"] == 15.0
        assert "855" not in values_text(
            client.get(f"/api/v1/combine/public/{event['share_token']}")
        )


class TestDisplayPolicy:
    def test_full_names_by_default(self, board):
        _, event = board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["display_name"] == "Jack Reid"

    def test_first_initial_style(self, board):
        store, event = board
        store.data["combine_events"][0]["public_name_style"] = "first_initial"
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["display_name"] == "Jack R."

    def test_bib_only_style(self, board):
        store, event = board
        store.data["combine_events"][0]["public_name_style"] = "bib"
        body = client.get(f"/api/v1/combine/public/{event['share_token']}").text
        assert "Jack" not in body
        assert "#1" in body

    def test_club_can_be_hidden(self, board):
        store, event = board
        store.data["combine_events"][0]["show_club"] = False
        body = client.get(f"/api/v1/combine/public/{event['share_token']}").text
        assert "Repton" not in body

    def test_filters_are_offered_from_the_roster(self, board):
        _, event = board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["filters"]["weight_category"] == ["57kg", "60kg"]

    def test_filtering_narrows_the_board(self, board):
        _, event = board
        data = client.get(
            f"/api/v1/combine/public/{event['share_token']}?weight_category=60kg"
        ).json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert [r["display_name"] for r in cmj["results"]] == ["Sam Okoro"]


class TestForgivingFilters:
    """These are typed onto a TV by hand, like the panel and rotate parameters.

    An exact, case-sensitive match turns `?wc=57KG` into an empty board in a full
    hall — the outcome the forgiving parsing elsewhere on this URL exists to avoid.
    """

    def _names(self, event, query=""):
        data = client.get(f"/api/v1/combine/public/{event['share_token']}{query}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        return [r["display_name"] for r in cmj["results"]]

    def test_a_shouted_weight_category_still_matches(self, board):
        _, event = board
        assert self._names(event, "?weight_category=60KG") == ["Sam Okoro"]

    def test_a_spaced_or_bare_weight_category_still_matches(self, board):
        _, event = board
        assert self._names(event, "?weight_category=60%20kg") == ["Sam Okoro"]
        assert self._names(event, "?weight_category=60") == ["Sam Okoro"]

    def test_a_lower_case_club_still_matches(self, board):
        store, event = board
        store.data["combine_participants"][1]["club"] = "Islington"
        assert self._names(event, "?club=islington") == ["Sam Okoro"]

    def test_a_padded_age_group_still_matches(self, board):
        store, event = board
        store.data["combine_participants"][1]["age_group"] = "senior"
        assert self._names(event, "?age_group=%20Junior%20") == ["Jack Reid"]

    def test_two_spellings_of_one_filter_share_a_cache_entry(self, board):
        """Otherwise the same board is computed and cached twice per poll."""
        _, event = board
        canonical = client.get(
            f"/api/v1/combine/public/{event['share_token']}?weight_category=60kg"
        )
        shouted = client.get(
            f"/api/v1/combine/public/{event['share_token']}?weight_category=60KG"
        )
        assert shouted.headers["etag"] == canonical.headers["etag"]
        assert shouted.json() == canonical.json()

    def test_a_filter_matching_nobody_shows_the_whole_board(self, board):
        """A typo falls back to no filter, the way an unknown panel falls back to
        rotating. A blank screen is the one answer the board must never give."""
        _, event = board
        assert len(self._names(event, "?weight_category=lightweight")) == 2
        assert len(self._names(event, "?club=not-a-club")) == 2


class TestCachingHeaders:
    def test_etag_is_returned(self, board):
        _, event = board
        response = client.get(f"/api/v1/combine/public/{event['share_token']}")
        assert response.headers["etag"].startswith('W/"')
        assert response.headers["cache-control"] == "no-cache"

    def test_matching_etag_returns_304(self, board):
        _, event = board
        first = client.get(f"/api/v1/combine/public/{event['share_token']}")
        second = client.get(
            f"/api/v1/combine/public/{event['share_token']}",
            headers={"If-None-Match": first.headers["etag"]},
        )
        assert second.status_code == 304
        # Without this a proxy may serve the 304 from its own cache and the board
        # stops noticing new results.
        assert second.headers["cache-control"] == "no-cache"
        assert second.headers["etag"] == first.headers["etag"]

    def test_etag_changes_when_results_change(self, board):
        store, event = board
        first = client.get(f"/api/v1/combine/public/{event['share_token']}")
        store.data["combine_events"][0]["results_updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        second = client.get(f"/api/v1/combine/public/{event['share_token']}")
        assert first.headers["etag"] != second.headers["etag"]

    def test_etag_differs_per_filter(self, board):
        _, event = board
        unfiltered = client.get(f"/api/v1/combine/public/{event['share_token']}")
        filtered = client.get(
            f"/api/v1/combine/public/{event['share_token']}?weight_category=57kg"
        )
        assert unfiltered.headers["etag"] != filtered.headers["etag"]


class TestRateLimitKey:
    def test_limiter_is_keyed_on_the_token_not_the_client_address(self):
        """Every screen and iPad in the gym shares one proxy address upstream,
        so an IP bucket would throttle the whole venue as a single client."""
        from app.routers.combine import _token_key

        request = MagicMock()
        request.path_params = {"token": "tok_abc"}
        assert _token_key(request) == "combine_public:tok_abc"

    def test_falls_back_to_the_address_when_there_is_no_token(self):
        from app.routers.combine import _token_key

        request = MagicMock()
        request.path_params = {}
        request.client.host = "203.0.113.7"
        assert _token_key(request) == "203.0.113.7"

    def test_repeated_polling_stays_inside_the_limit(self, board):
        """Two screens at 5s is 24 requests a minute; the limit must not bite."""
        _, event = board
        for _ in range(30):
            assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200


class TestPublicLimitFitsTheAudience:
    """One bucket per token is shared by every device showing the link.

    Twenty screens polling every 5 s is 240 requests a minute — the old ceiling
    exactly — and a 304 counts against it too, so the TV would throttle itself.
    """

    def test_the_board_survives_three_hundred_polls(self, board):
        _, event = board
        for _ in range(300):
            assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200

    def test_the_meta_endpoint_survives_three_hundred_polls(self, board):
        _, event = board
        for _ in range(300):
            response = client.get(f"/api/v1/combine/public/{event['share_token']}/meta")
            assert response.status_code == 200


class TestHiddenClubsCannotBeEnumerated:
    """`?club=` must do nothing at all when the board hides clubs.

    Otherwise the wall URL narrows to one club, and the hidden club membership of
    named minors can be read back off the board a filter at a time.
    """

    @staticmethod
    def _two_clubs(store):
        store.data["combine_participants"][0]["club"] = "Repton"
        store.data["combine_participants"][1]["club"] = "Islington"

    def test_the_club_filter_is_ignored(self, board):
        store, event = board
        self._two_clubs(store)
        store.data["combine_events"][0]["show_club"] = False

        data = client.get(
            f"/api/v1/combine/public/{event['share_token']}?club=Repton"
        ).json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert len(cmj["results"]) == 2
        assert data["participant_count"] == 2

    def test_the_club_filter_does_not_even_key_the_cache(self, board):
        store, event = board
        self._two_clubs(store)
        store.data["combine_events"][0]["show_club"] = False

        plain = client.get(f"/api/v1/combine/public/{event['share_token']}")
        filtered = client.get(f"/api/v1/combine/public/{event['share_token']}?club=Repton")
        assert filtered.headers["etag"] == plain.headers["etag"]

    def test_the_club_filter_still_narrows_a_board_that_shows_clubs(self, board):
        store, event = board
        self._two_clubs(store)
        data = client.get(
            f"/api/v1/combine/public/{event['share_token']}?club=Islington"
        ).json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert [r["display_name"] for r in cmj["results"]] == ["Sam Okoro"]


class TestBandsAreForLeadersOnly:
    def test_only_the_rank_one_row_carries_a_band(self, board):
        """A band beside every raw value brackets the Boxing Science mean and SD."""
        _, event = board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert [r["rank"] for r in cmj["results"]] == [1, 2]
        assert cmj["results"][0]["bs_band"] == "elite"
        assert cmj["results"][1]["bs_band"] is None


class TestTokenLifecycleWithAWarmCache:
    """The per-worker payload cache must never outlive the token it was built for."""

    def test_rotate_kills_the_warmed_link(self, board):
        _, event = board
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200
        assert client.post(
            f"/api/v1/combine/events/{event['id']}/rotate-token"
        ).status_code == 200
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 404

    def test_revoke_kills_the_warmed_link(self, board):
        _, event = board
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200
        assert client.post(
            f"/api/v1/combine/events/{event['id']}/revoke-token"
        ).status_code == 200
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 404

    def test_a_revoked_token_404s_even_with_a_matching_etag(self, board):
        """A 304 is still a disclosure: it says the board is there."""
        _, event = board
        warm = client.get(f"/api/v1/combine/public/{event['share_token']}")
        client.post(f"/api/v1/combine/events/{event['id']}/revoke-token")

        response = client.get(
            f"/api/v1/combine/public/{event['share_token']}",
            headers={"If-None-Match": warm.headers["etag"]},
        )
        assert response.status_code == 404


class TestEveryFailureLooksTheSame:
    def test_unknown_draft_revoked_expired_and_unconsented_are_identical(self, board):
        store, event = board
        row = store.data["combine_events"][0]
        pristine = dict(row)

        def failure(**changes):
            row.clear()
            row.update(pristine)
            row.update(changes)
            response = client.get(f"/api/v1/combine/public/{event['share_token']}")
            return response.status_code, response.text

        seen = {
            failure(status="draft"),
            failure(share_revoked_at=datetime.now(timezone.utc).isoformat()),
            failure(share_token_expires_at=_past()),
            failure(public_display_consent_confirmed_at=None),
        }
        unknown = client.get("/api/v1/combine/public/tok_does_not_exist")
        seen.add((unknown.status_code, unknown.text))

        assert seen == {(404, unknown.text)}


class TestScoreBasisOnThePublicBoard:
    """The board says which composite it is showing, and publishes nothing more.

    Each test issues one request after mutating the store: the payload cache is keyed
    on the event id, which is fresh per fixture, so a single request never reads a
    board built from the settings this test just changed.
    """

    def test_the_payload_declares_the_basis(self, board):
        _, event = board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["score_basis"] == "z"

    def test_a_row_written_before_the_migration_reads_as_z(self, board):
        store, event = board
        store.data["combine_events"][0].pop("overall_score_basis", None)
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["score_basis"] == "z"

    def test_a_percentile_event_is_labelled_and_scored_by_percentile(self, board):
        store, event = board
        store.data["combine_events"][0]["overall_score_basis"] = "percentile"
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["score_basis"] == "percentile"
        # Two boxers on one station: 43.0 cm beats 38.0 cm, so 100 and 0.
        assert [e["combine_score"] for e in data["overall"]] == [100.0, 0.0]

    def test_the_percentile_board_leaks_nothing_new(self, board):
        store, event = board
        store.data["combine_events"][0]["overall_score_basis"] = "percentile"
        response = client.get(f"/api/v1/combine/public/{event['share_token']}")
        for needle in FORBIDDEN_SUBSTRINGS:
            assert needle not in response.text, f"public payload leaked '{needle}'"
        assert UUID_PATTERN.search(response.text) is None

    def test_the_percentile_board_still_bands_only_the_leader(self, board):
        """The basis changes the composite, never what the benchmark publishes."""
        store, event = board
        store.data["combine_events"][0]["overall_score_basis"] = "percentile"
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        cmj = next(p for p in data["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["bs_band"] == "elite"
        assert cmj["results"][1]["bs_band"] is None


class _ProjectingTable(FakeTable):
    """A table that honours an explicit column list, the way PostgREST does."""

    def execute(self):
        result = super().execute()
        if self.op != "select" or "*" in self.select_cols:
            return result
        columns = {c.strip() for c in self.select_cols.split(",")}
        result.data = [{k: v for k, v in row.items() if k in columns} for row in result.data]
        return result


class ProjectingStore(FakeSupabase):
    """A store whose `combine_events` reads return only the columns asked for.

    The shared fake hands back whole rows whatever the select list says, so a column
    left out of an explicit projection still reaches the router in a test and goes
    missing only in production. The public event read is the one place in this router
    that names its columns (decision 113) — so it is the one place that needs a store
    which projects.
    """

    def table(self, name: str):
        return _ProjectingTable(self, name) if name == "combine_events" else super().table(name)


@pytest.fixture
def projecting_board(board):
    """The same event and results, read through a store that honours projections."""
    store, event = board
    projecting = ProjectingStore(**{k: list(v) for k, v in store.data.items()})
    with patch("app.core.supabase_client.get_supabase_client", return_value=projecting):
        yield projecting, event


class TestThePublicReadFetchesTheColumnsItScoresOn:
    """What the public event read does not select, the board cannot score on."""

    def test_the_score_basis_column_survives_the_projection(self, projecting_board):
        """Regression: `overall_score_basis` has to be named in the select list.

        A column missing from an explicit projection reads as absent however the row
        is written, and `overall_basis()` maps absent to 'z' — so the console would
        switch to percentile and the wall would quietly keep scoring on z.
        """
        store, event = projecting_board
        store.data["combine_events"][0]["overall_score_basis"] = "percentile"
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["score_basis"] == "percentile"
        assert [e["combine_score"] for e in data["overall"]] == [100.0, 0.0]

    def test_a_default_event_still_reads_as_z_through_the_projection(self, projecting_board):
        _, event = projecting_board
        data = client.get(f"/api/v1/combine/public/{event['share_token']}").json()
        assert data["score_basis"] == "z"


class TestAPayloadCachedBeforeTheDeploy:
    """The payload shape changed, so every board cached against the old one is stale."""

    def test_a_kiosk_holding_a_pre_deploy_etag_is_not_told_it_is_current(self, board):
        """`PAYLOAD_SCHEMA_VERSION` keys the ETag for exactly this reason.

        Without a bump the server answers a pre-deploy `If-None-Match` with 304 and the
        kiosk keeps a payload that has no `score_basis` in it — until the next result
        lands, which on a quiet station can be a long time.
        """
        store, event = board
        row = store.data["combine_events"][0]
        # Built exactly as `_etag_for` builds it, but pinned to the old schema version:
        # an unfiltered board's key is four empty filter values joined, not an empty
        # string, and an ETag that never matched would pass this test for no reason.
        filter_key = "|".join(["", "", "", ""])
        stale_raw = f"{row['id']}|{row.get('results_updated_at')}|{filter_key}|1"
        stale = 'W/"' + hashlib.sha256(stale_raw.encode()).hexdigest()[:32] + '"'

        response = client.get(
            f"/api/v1/combine/public/{event['share_token']}",
            headers={"If-None-Match": stale},
        )

        assert response.status_code == 200
        assert response.json()["score_basis"] == "z"
