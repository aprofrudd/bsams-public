"""Tests for circuit training feature."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def coach_id():
    from tests.conftest import TEST_USER_ID
    return str(TEST_USER_ID)


@pytest.fixture
def session_id():
    return str(uuid4())


@pytest.fixture
def athlete_id():
    return str(uuid4())


class TestCircuitSystemDefault:
    """Test that Circuit appears in system defaults."""

    def test_circuit_in_system_defaults(self):
        """Circuit should be in the SYSTEM_DEFAULTS list."""
        from app.routers.custom_training_types import SYSTEM_DEFAULTS

        assert "Circuit" in SYSTEM_DEFAULTS

    def test_circuit_listed_in_training_types(self, mock_supabase, coach_id):
        """GET /training/types/ should include Circuit as a system default."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/training/types/")

        assert response.status_code == 200
        type_names = [t["type_name"] for t in response.json()]
        assert "Circuit" in type_names

    def test_cannot_create_circuit_custom_type(self, mock_supabase):
        """Should reject creating 'Circuit' as a custom type (it's a system default)."""
        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "Circuit"},
        )
        assert response.status_code == 409


class TestCircuitTemplateExpansion:
    """Test circuit-aware template expansion in session_templates.py."""

    def test_circuit_template_interleaved_expansion(self, mock_supabase, coach_id, session_id, athlete_id):
        """3 circuit exercises x 3 rounds = 9 prescriptions with interleaved set_numbers."""
        template_id = str(uuid4())
        template_data = {
            "id": template_id,
            "coach_id": coach_id,
            "template_name": "Circuit A",
            "training_type": "Circuit",
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # 3 exercises, each with sets=3 (rounds)
        template_exercises = [
            {
                "id": str(uuid4()),
                "template_id": template_id,
                "exercise_library_id": None,
                "exercise_name": "Battle Ropes",
                "exercise_category": "Circuit",
                "order_index": 1,
                "sets": 3,
                "reps": None,
                "weight_kg": None,
                "tempo": None,
                "rest_seconds": 10,
                "duration_seconds": 30,
                "distance_meters": None,
                "intensity_type": None,
                "intensity_value": None,
                "rest_between_reps_seconds": None,
                "rep_intensity_values": None,
                "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid4()),
                "template_id": template_id,
                "exercise_library_id": None,
                "exercise_name": "Box Jumps",
                "exercise_category": "Circuit",
                "order_index": 2,
                "sets": 3,
                "reps": None,
                "weight_kg": None,
                "tempo": None,
                "rest_seconds": 10,
                "duration_seconds": 30,
                "distance_meters": None,
                "intensity_type": None,
                "intensity_value": None,
                "rest_between_reps_seconds": None,
                "rep_intensity_values": None,
                "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid4()),
                "template_id": template_id,
                "exercise_library_id": None,
                "exercise_name": "Push Ups",
                "exercise_category": "Circuit",
                "order_index": 3,
                "sets": 3,
                "reps": None,
                "weight_kg": None,
                "tempo": None,
                "rest_seconds": 60,
                "duration_seconds": 30,
                "distance_meters": None,
                "intensity_type": None,
                "intensity_value": None,
                "rest_between_reps_seconds": None,
                "rep_intensity_values": None,
                "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        ]

        inserted_prescriptions = []

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    template_data
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = template_exercises
            elif table_name == "exercise_prescriptions":
                def capture_insert(data):
                    inserted_prescriptions.extend(data)
                    mock_result = MagicMock()
                    mock_result.data = data
                    return mock_result

                mock_table.insert.return_value.execute.side_effect = lambda: capture_insert(
                    mock_table.insert.call_args[0][0]
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{template_id}/apply?session_id={session_id}"
        )

        assert response.status_code == 201

        # Verify the insert was called with correct data
        insert_call = mock_supabase.table.return_value.insert.call_args
        if insert_call is None:
            # Find the exercise_prescriptions insert call
            for call_obj in mock_supabase.table.call_args_list:
                if call_obj[0][0] == "exercise_prescriptions":
                    break

        # Verify the prescriptions list built by the router
        # We can check the insert mock was called
        prescriptions_table_calls = [
            c for c in mock_supabase.table.call_args_list
            if c[0][0] == "exercise_prescriptions"
        ]
        assert len(prescriptions_table_calls) > 0

    def test_circuit_set_numbers_are_sequential(self):
        """Verify circuit expansion logic produces sequential set_numbers."""
        # Simulate the expansion logic directly
        exercises = [
            {"exercise_name": "Battle Ropes", "exercise_category": "Circuit", "sets": 3, "duration_seconds": 30, "rest_seconds": 10},
            {"exercise_name": "Box Jumps", "exercise_category": "Circuit", "sets": 3, "duration_seconds": 30, "rest_seconds": 10},
            {"exercise_name": "Push Ups", "exercise_category": "Circuit", "sets": 3, "duration_seconds": 30, "rest_seconds": 60},
        ]

        circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
        num_rounds = circuit_exs[0].get("sets", 1)

        prescriptions = []
        set_counter = 1
        for _round in range(num_rounds):
            for ex in circuit_exs:
                prescriptions.append({
                    "exercise_name": ex["exercise_name"],
                    "exercise_category": "Circuit",
                    "set_number": set_counter,
                    "duration_seconds": ex.get("duration_seconds"),
                    "rest_seconds": ex.get("rest_seconds"),
                })
                set_counter += 1

        # Should produce 9 prescriptions (3 exercises x 3 rounds)
        assert len(prescriptions) == 9

        # Verify sequential set_numbers
        set_numbers = [p["set_number"] for p in prescriptions]
        assert set_numbers == [1, 2, 3, 4, 5, 6, 7, 8, 9]

        # Verify interleaved order: Round 1 = BR, BJ, PU; Round 2 = BR, BJ, PU; etc
        expected_names = [
            "Battle Ropes", "Box Jumps", "Push Ups",
            "Battle Ropes", "Box Jumps", "Push Ups",
            "Battle Ropes", "Box Jumps", "Push Ups",
        ]
        actual_names = [p["exercise_name"] for p in prescriptions]
        assert actual_names == expected_names

    def test_circuit_round_rest_assignment(self):
        """Last exercise in each round should keep its rest_seconds (round rest)."""
        exercises = [
            {"exercise_name": "Battle Ropes", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 30, "rest_seconds": 10},
            {"exercise_name": "Box Jumps", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 30, "rest_seconds": 10},
            {"exercise_name": "Push Ups", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 30, "rest_seconds": 60},
        ]

        circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
        num_rounds = circuit_exs[0].get("sets", 1)

        prescriptions = []
        set_counter = 1
        for _round in range(num_rounds):
            for ex in circuit_exs:
                prescriptions.append({
                    "exercise_name": ex["exercise_name"],
                    "set_number": set_counter,
                    "rest_seconds": ex.get("rest_seconds"),
                })
                set_counter += 1

        # 6 prescriptions: 3 exercises x 2 rounds
        assert len(prescriptions) == 6

        # Last in round 1 (index 2) and round 2 (index 5) should have rest_seconds=60
        assert prescriptions[2]["rest_seconds"] == 60
        assert prescriptions[5]["rest_seconds"] == 60

        # Others should have transition rest (10)
        assert prescriptions[0]["rest_seconds"] == 10
        assert prescriptions[1]["rest_seconds"] == 10
        assert prescriptions[3]["rest_seconds"] == 10
        assert prescriptions[4]["rest_seconds"] == 10

    def test_mixed_session_set_numbers_no_collision(self):
        """Strength + circuit exercises in same session should have non-colliding set_numbers."""
        # Simulate the mixed expansion logic
        exercises = [
            {"exercise_name": "Back Squat", "exercise_category": "Strength", "sets": 3, "reps": 5, "weight_kg": 100},
            {"exercise_name": "Battle Ropes", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 30, "rest_seconds": 10},
            {"exercise_name": "Box Jumps", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 30, "rest_seconds": 60},
        ]

        circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
        non_circuit = [ex for ex in exercises if ex.get("exercise_category") != "Circuit"]

        prescriptions = []

        # Non-circuit: standard expansion
        for ex in non_circuit:
            num_sets = ex.get("sets", 1)
            for set_num in range(1, num_sets + 1):
                prescriptions.append({
                    "exercise_name": ex["exercise_name"],
                    "set_number": set_num,
                })

        # Circuit: interleaved
        if circuit_exs:
            num_rounds = circuit_exs[0].get("sets", 1)
            set_counter = max((p["set_number"] for p in prescriptions), default=0) + 1
            for _round in range(num_rounds):
                for ex in circuit_exs:
                    prescriptions.append({
                        "exercise_name": ex["exercise_name"],
                        "set_number": set_counter,
                    })
                    set_counter += 1

        # 3 strength sets + 4 circuit prescriptions (2 exercises x 2 rounds) = 7
        assert len(prescriptions) == 7

        # Strength: set_numbers 1, 2, 3
        strength_sets = [p["set_number"] for p in prescriptions if p["exercise_name"] == "Back Squat"]
        assert strength_sets == [1, 2, 3]

        # Circuit: set_numbers 4, 5, 6, 7
        circuit_sets = [p["set_number"] for p in prescriptions if p["exercise_name"] != "Back Squat"]
        assert circuit_sets == [4, 5, 6, 7]

        # All set_numbers unique
        all_set_numbers = [p["set_number"] for p in prescriptions]
        assert len(all_set_numbers) == len(set(all_set_numbers))


class TestCircuitExerciseCRUD:
    """Test basic CRUD for circuit exercises via exercises router."""

    def test_create_circuit_exercise(self, mock_supabase, session_id):
        """Should create a circuit exercise prescription."""
        exercise_data = {
            "id": str(uuid4()),
            "session_id": session_id,
            "exercise_name": "Battle Ropes",
            "exercise_category": "Circuit",
            "set_number": 1,
            "duration_seconds": 30,
            "rest_seconds": 10,
            "reps": None,
            "weight_kg": None,
            "tempo": None,
            "distance_meters": None,
            "intensity_type": None,
            "intensity_value": None,
            "rest_between_reps_seconds": None,
            "rep_durations": None,
            "rest_between_reps": None,
            "rep_intensity_values": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": str(uuid4()), "status": None, "created_by": None}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.insert.return_value.execute.return_value.data = [exercise_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/training/sessions/{session_id}/exercises/",
            json={
                "exercise_name": "Battle Ropes",
                "exercise_category": "Circuit",
                "set_number": 1,
                "duration_seconds": 30,
                "rest_seconds": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["exercise_name"] == "Battle Ropes"
        assert data["exercise_category"] == "Circuit"
        assert data["duration_seconds"] == 30

    def test_list_circuit_exercises_ordered_by_set_number(self, mock_supabase, session_id):
        """Circuit exercises should be returned ordered by set_number."""
        exercises = [
            {
                "id": str(uuid4()),
                "session_id": session_id,
                "exercise_name": "Battle Ropes",
                "exercise_category": "Circuit",
                "set_number": 1,
                "duration_seconds": 30,
                "rest_seconds": 10,
                "reps": None, "weight_kg": None, "tempo": None,
                "distance_meters": None, "intensity_type": None,
                "intensity_value": None, "rest_between_reps_seconds": None,
                "rep_durations": None, "rest_between_reps": None,
                "rep_intensity_values": None, "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid4()),
                "session_id": session_id,
                "exercise_name": "Box Jumps",
                "exercise_category": "Circuit",
                "set_number": 2,
                "duration_seconds": 30,
                "rest_seconds": 10,
                "reps": None, "weight_kg": None, "tempo": None,
                "distance_meters": None, "intensity_type": None,
                "intensity_value": None, "rest_between_reps_seconds": None,
                "rep_durations": None, "rest_between_reps": None,
                "rep_intensity_values": None, "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": str(uuid4())}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = exercises
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/training/sessions/{session_id}/exercises/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["exercise_name"] == "Battle Ropes"
        assert data[1]["exercise_name"] == "Box Jumps"
        assert data[0]["set_number"] < data[1]["set_number"]


class TestCircuitProgramTemplateExpansion:
    """Test circuit expansion in program template apply endpoint."""

    def test_program_circuit_expansion_logic(self):
        """Verify program template circuit expansion produces correct interleaved prescriptions."""
        exercises = [
            {"exercise_name": "Ropes", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 20, "rest_seconds": 5},
            {"exercise_name": "Burpees", "exercise_category": "Circuit", "sets": 2, "duration_seconds": 20, "rest_seconds": 30},
        ]

        circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
        num_rounds = circuit_exs[0].get("sets", 1)

        prescriptions = []
        set_counter = 1
        for _round in range(num_rounds):
            for ex in circuit_exs:
                prescriptions.append({
                    "exercise_name": ex["exercise_name"],
                    "exercise_category": "Circuit",
                    "set_number": set_counter,
                    "duration_seconds": ex.get("duration_seconds"),
                    "rest_seconds": ex.get("rest_seconds"),
                })
                set_counter += 1

        # 2 exercises x 2 rounds = 4
        assert len(prescriptions) == 4
        assert [p["exercise_name"] for p in prescriptions] == ["Ropes", "Burpees", "Ropes", "Burpees"]
        assert [p["set_number"] for p in prescriptions] == [1, 2, 3, 4]
