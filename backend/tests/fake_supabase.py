"""A small in-memory stand-in for the Supabase client.

The combine router touches six tables across a single request, so chained MagicMock
returns become unreadable fast. This fake stores rows in dicts and supports the
query shapes the router actually uses, which lets the tests assert on behaviour
(what ended up in the database) rather than on mock call plumbing.

Not a general Supabase implementation — only what these tests exercise.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


class _Result:
    def __init__(self, data: List[dict]):
        self.data = data


class FakeApiError(Exception):
    """Stands in for postgrest's APIError, which carries the Postgres SQLSTATE.

    Promotion tells a conflict it must respect (`23505` — the athlete already has a
    row of their own) from a real failure by reading `.code`, so the fake has to
    carry one too.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeTable:
    def __init__(self, store: "FakeSupabase", name: str):
        self.store = store
        self.name = name
        self.op: Optional[str] = None
        self.payload: Any = None
        self.select_cols: str = "*"
        self.filters: List[tuple] = []
        self._limit: Optional[int] = None
        self._order: Optional[tuple] = None
        self._range: Optional[tuple] = None

    # -- builders ---------------------------------------------------------
    def select(self, cols: str = "*", **_kwargs) -> "FakeTable":
        self.op = "select"
        self.select_cols = cols
        return self

    def insert(self, payload) -> "FakeTable":
        self.op = "insert"
        self.payload = payload
        return self

    def update(self, payload) -> "FakeTable":
        self.op = "update"
        self.payload = payload
        return self

    def delete(self) -> "FakeTable":
        self.op = "delete"
        return self

    def eq(self, col: str, value) -> "FakeTable":
        self.filters.append(("eq", col, value))
        return self

    def in_(self, col: str, values) -> "FakeTable":
        self.filters.append(("in", col, list(values)))
        return self

    def is_(self, col: str, value) -> "FakeTable":
        self.filters.append(("is", col, value))
        return self

    def ilike(self, col: str, pattern: str) -> "FakeTable":
        self.filters.append(("ilike", col, pattern))
        return self

    def limit(self, n: int) -> "FakeTable":
        self._limit = n
        return self

    def order(self, col: str, desc: bool = False) -> "FakeTable":
        self._order = (col, desc)
        return self

    def range(self, start: int, end: int) -> "FakeTable":
        self._range = (start, end)
        return self

    # -- execution --------------------------------------------------------
    def _matches(self, row: dict) -> bool:
        for kind, col, value in self.filters:
            actual = row.get(col)
            if kind == "eq":
                if str(actual) != str(value):
                    return False
            elif kind == "in":
                if str(actual) not in {str(v) for v in value}:
                    return False
            elif kind == "is":
                if str(value).lower() == "null" and actual is not None:
                    return False
            elif kind == "ilike":
                needle = str(value).replace("%", "").lower()
                if needle not in str(actual or "").lower():
                    return False
        return True

    def _rows(self) -> List[dict]:
        return self.store.data.setdefault(self.name, [])

    def _join_athletes(self, rows: List[dict]) -> List[dict]:
        """Emulate `select("*, athletes!inner(...)")`."""
        athletes = {str(a["id"]): a for a in self.store.data.get("athletes", [])}
        joined = []
        for row in rows:
            athlete = athletes.get(str(row.get("athlete_id")))
            if athlete is None:
                continue  # !inner
            joined.append(
                {
                    **row,
                    "athletes": {
                        "first_name": athlete.get("first_name"),
                        "surname": athlete.get("surname"),
                        "name": athlete.get("name"),
                        "gender": athlete.get("gender"),
                        "date_of_birth": athlete.get("date_of_birth"),
                    },
                }
            )
        return joined

    def execute(self) -> _Result:
        rows = self._rows()

        if self.op == "insert":
            payload = self.payload if isinstance(self.payload, list) else [self.payload]
            created = []
            for item in payload:
                row = dict(item)
                row.setdefault("id", str(uuid4()))
                row.setdefault("created_at", _now())
                row.setdefault("updated_at", _now())
                self.store._apply_defaults(self.name, row)
                self.store._check_unique(self.name, row)
                rows.append(row)
                created.append(dict(row))
            return _Result(created)

        matched = [r for r in rows if self._matches(r)]

        if self.op == "update":
            # Postgres checks the whole statement before it commits, so nothing is
            # mutated until every updated row still satisfies its unique constraints.
            candidates = [{**row, **self.payload} for row in matched]
            for row, candidate in zip(matched, candidates):
                self.store._check_unique(self.name, candidate, ignore=row)
            for row in matched:
                row.update(self.payload)
                row["updated_at"] = _now()
            return _Result([dict(r) for r in matched])

        if self.op == "delete":
            ids = {id(r) for r in matched}
            self.store.data[self.name] = [r for r in rows if id(r) not in ids]
            self.store._cascade_delete(self.name, matched)
            return _Result([dict(r) for r in matched])

        # select
        if self._order:
            col, desc = self._order
            matched = sorted(matched, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._range:
            start, end = self._range
            matched = matched[start : end + 1]
        if self._limit is not None:
            matched = matched[: self._limit]
        # PostgREST truncates every response at db-max-rows, silently.
        if self.store.max_rows is not None:
            matched = matched[: self.store.max_rows]
        if "athletes!inner" in self.select_cols:
            return _Result(self._join_athletes(matched))
        return _Result([dict(r) for r in matched])


class FakeSupabase:
    """Holds the tables and emulates the one RPC the promotion path uses."""

    # A key with a None column is skipped, which is exactly how the partial indexes
    # behave: `performance_events` is unique only for combine-tagged rows, and
    # `combine_attempts.client_attempt_id` only when the client sent one.
    UNIQUE_KEYS = {
        "combine_participants": [("combine_event_id", "athlete_id"), ("combine_event_id", "bib")],
        "combine_attempts": [
            ("participant_id", "station", "attempt_number"),
            ("combine_event_id", "client_attempt_id"),
        ],
        "combine_events": [("share_token",)],
        # The tables promotion writes into. Each is unique per athlete per day, which
        # is why a combine save must never touch a row it did not create.
        "performance_events": [("athlete_id", "event_date", "combine_event_id")],
        "vbt_profiles": [("athlete_id", "exercise_name", "profile_date")],
        "air_bike_tests": [("athlete_id", "test_date")],
        "air_bike_sprints": [("test_id", "sprint_number")],
    }

    # FK ON DELETE CASCADE: {parent: [(child table, FK column), ...]}
    CASCADE_DELETES = {
        "combine_events": [
            ("combine_participants", "combine_event_id"),
            ("combine_attempts", "combine_event_id"),
        ],
        "combine_participants": [("combine_attempts", "participant_id")],
        "vbt_profiles": [("vbt_sets", "profile_id")],
        "air_bike_tests": [("air_bike_sprints", "test_id")],
    }

    # FK ON DELETE SET NULL (migration 033): deleting a combine event must not take
    # the athletes' results with it — the rows survive, untagged.
    SET_NULL_ON_DELETE = {
        "combine_events": [
            ("performance_events", "combine_event_id"),
            ("vbt_profiles", "combine_event_id"),
            ("air_bike_tests", "combine_event_id"),
        ],
    }

    def __init__(self, *, max_rows: Optional[int] = None, **tables: List[dict]):
        """`max_rows` mirrors PostgREST's db-max-rows cap on unpaginated selects."""
        self.data: Dict[str, List[dict]] = {k: list(v) for k, v in tables.items()}
        self.rpc_calls: List[tuple] = []
        self._bib_counter = itertools.count(1)
        self.max_rows = max_rows

    def table(self, name: str) -> FakeTable:
        return FakeTable(self, name)

    def _apply_defaults(self, name: str, row: dict) -> None:
        if name == "combine_events":
            row.setdefault("status", "draft")
            row.setdefault("results_updated_at", _now())
            row.setdefault("bs_norms_snapshot", {})
            row.setdefault("share_revoked_at", None)
            row.setdefault("public_display_consent_confirmed_at", None)
        if name == "combine_attempts":
            row.setdefault("voided_at", None)

    def _check_unique(self, name: str, row: dict, *, ignore: Optional[dict] = None) -> None:
        """Raise a 23505 if `row` collides. `ignore` is the row being updated."""
        for key in self.UNIQUE_KEYS.get(name, []):
            if any(row.get(col) is None for col in key):
                continue
            for existing in self.data.get(name, []):
                if existing is row or existing is ignore:
                    continue
                if all(str(existing.get(col)) == str(row.get(col)) for col in key):
                    raise FakeApiError(
                        "23505",
                        f"duplicate key value violates unique constraint on {key}",
                    )

    def _cascade_delete(self, name: str, deleted: List[dict]) -> None:
        ids = {str(r["id"]) for r in deleted if r.get("id") is not None}
        if not ids:
            return
        for child, column in self.CASCADE_DELETES.get(name, []):
            self.data[child] = [
                r for r in self.data.get(child, []) if str(r.get(column)) not in ids
            ]
        for child, column in self.SET_NULL_ON_DELETE.get(name, []):
            for row in self.data.get(child, []):
                if str(row.get(column)) in ids:
                    row[column] = None

    def rpc(self, name: str, params: dict):
        self.rpc_calls.append((name, params))

        class _Rpc:
            def __init__(self, outer, params):
                self.outer = outer
                self.params = params

            def execute(self):
                if name != "combine_upsert_event_metrics":
                    return _Result([])
                rows = self.outer.data.setdefault("performance_events", [])
                athlete_id = str(self.params["p_athlete_id"])
                event_id = str(self.params["p_combine_event_id"])
                event_date = str(self.params["p_event_date"])
                for row in rows:
                    # The real ON CONFLICT target is the full index, event_date included:
                    # a moved event date inserts a second row instead of updating.
                    if (
                        str(row.get("athlete_id")) == athlete_id
                        and str(row.get("event_date")) == event_date
                        and str(row.get("combine_event_id")) == event_id
                    ):
                        # ON CONFLICT ... DO UPDATE SET metrics = metrics || EXCLUDED.metrics
                        row["metrics"] = {**row.get("metrics", {}), **self.params["p_metrics"]}
                        return _Result([{"id": row["id"]}])
                new_row = {
                    "id": str(uuid4()),
                    "athlete_id": athlete_id,
                    "event_date": self.params["p_event_date"],
                    "metrics": dict(self.params["p_metrics"]),
                    "combine_event_id": event_id,
                    # Postgres fills these from column defaults; the fake must too,
                    # or response models that require them reject the row.
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                rows.append(new_row)
                return _Result([{"id": new_row["id"]}])

        return _Rpc(self, params)
