"""Tests for program marketplace router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROGRAMS_PATCH = "app.core.supabase_client.get_supabase_client"

SAMPLE_PROGRAM_ID = str(uuid4())
SAMPLE_TEMPLATE_ID = str(uuid4())
ADMIN_ID = "00000000-0000-0000-0000-000000000099"
COACH_ID = "00000000-0000-0000-0000-000000000001"


def _make_program(program_id=None, is_published=True, category="Strength"):
    """Create sample program data."""
    return {
        "id": program_id or str(uuid4()),
        "created_by": ADMIN_ID,
        "program_name": "Train Like a Champion",
        "description": "A complete training program",
        "category": category,
        "cover_image_url": None,
        "is_published": is_published,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _make_template(template_id=None, program_id=None):
    """Create sample program template data."""
    return {
        "id": template_id or str(uuid4()),
        "program_id": program_id or SAMPLE_PROGRAM_ID,
        "template_name": "Day 1 - Upper Body",
        "training_type": "Strength",
        "order_index": 1,
        "notes": "Focus on pressing",
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "exercise_category": "Strength",
                "order_index": 1,
                "sets": 3,
                "reps": 5,
                "weight_kg": 80.0,
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client for coach (default) endpoints."""
    with patch(PROGRAMS_PATCH) as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


class TestCreateProgram:
    """Test POST /api/v1/programs/ (admin only)."""

    def test_create_program_success(self, admin_client):
        """Admin should create a program."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_data = _make_program()
            mock_client.table.return_value.insert.return_value.execute.return_value.data = [program_data]

            response = admin_client.post(
                "/api/v1/programs/",
                json={
                    "program_name": "Train Like a Champion",
                    "description": "A complete training program",
                    "category": "Strength",
                    "is_published": True,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["program_name"] == "Train Like a Champion"
            assert data["template_count"] == 0

    def test_create_program_non_admin_403(self, mock_supabase):
        """Coach should get 403."""
        response = client.post(
            "/api/v1/programs/",
            json={
                "program_name": "My Program",
                "category": "Strength",
            },
        )
        assert response.status_code == 403

    def test_create_program_duplicate_409(self, admin_client):
        """Duplicate program name should return 409."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
                "duplicate key value violates unique constraint"
            )

            response = admin_client.post(
                "/api/v1/programs/",
                json={
                    "program_name": "Existing Program",
                    "category": "Strength",
                },
            )
            assert response.status_code == 409


class TestUpdateProgram:
    """Test PATCH /api/v1/programs/{id} (admin only)."""

    def test_update_program_success(self, admin_client):
        """Admin should update a program."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())
            program_data = _make_program(program_id=program_id)

            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if table_name == "program_packages":
                    if call_count[0] == 1:
                        # Verify exists
                        mock_table.select.return_value.eq.return_value.execute.return_value.data = [program_data]
                    elif call_count[0] == 2:
                        # Update
                        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
                            {**program_data, "description": "Updated desc"}
                        ]
                    else:
                        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                elif table_name == "program_templates":
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                    mock_table.select.return_value.eq.return_value.execute.return_value.count = 0
                elif table_name == "program_installations":
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.patch(
                f"/api/v1/programs/{program_id}",
                json={"description": "Updated desc"},
            )

            assert response.status_code == 200

    def test_update_program_not_found(self, admin_client):
        """Should return 404 for non-existent program."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

            response = admin_client.patch(
                f"/api/v1/programs/{uuid4()}",
                json={"description": "Updated"},
            )

            assert response.status_code == 404


class TestDeleteProgram:
    """Test DELETE /api/v1/programs/{id} (admin only)."""

    def test_delete_program_success(self, admin_client):
        """Admin should delete a program, 204."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())
            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    # Verify exists
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        _make_program(program_id=program_id)
                    ]
                else:
                    # Delete
                    mock_table.delete.return_value.eq.return_value.execute.return_value = None
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.delete(f"/api/v1/programs/{program_id}")
            assert response.status_code == 204

    def test_delete_program_not_found(self, admin_client):
        """Should return 404 for non-existent program."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

            response = admin_client.delete(f"/api/v1/programs/{uuid4()}")
            assert response.status_code == 404


class TestListPrograms:
    """Test GET /api/v1/programs/"""

    def test_list_programs_returns_published(self, mock_supabase):
        """Should return published programs."""
        program_data = _make_program()

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    program_data
                ]
            elif table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.select.return_value.eq.return_value.execute.return_value.count = 2
            elif table_name == "program_installations":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/programs/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["program_name"] == "Train Like a Champion"

    def test_list_programs_with_category_filter(self, mock_supabase):
        """Category filter should be applied."""
        program_data = _make_program(category="Conditioning")

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    program_data
                ]
            elif table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.select.return_value.eq.return_value.execute.return_value.count = 0
            elif table_name == "program_installations":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/programs/?category=Conditioning")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_programs_includes_install_status(self, mock_supabase):
        """is_installed flag should be set correctly."""
        program_data = _make_program(program_id=SAMPLE_PROGRAM_ID)

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    program_data
                ]
            elif table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.select.return_value.eq.return_value.execute.return_value.count = 0
            elif table_name == "program_installations":
                # User has it installed
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"program_id": SAMPLE_PROGRAM_ID}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/programs/")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["is_installed"] is True


class TestGetProgramDetail:
    """Test GET /api/v1/programs/{id}"""

    def test_get_program_detail(self, mock_supabase):
        """Should return program with templates."""
        program_id = str(uuid4())
        program_data = _make_program(program_id=program_id)
        template_data = _make_template(program_id=program_id)

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [program_data]
            elif table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    template_data
                ]
            elif table_name == "program_installations":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/programs/{program_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["program_name"] == "Train Like a Champion"
        assert len(data["templates"]) == 1
        assert data["templates"][0]["template_name"] == "Day 1 - Upper Body"


class TestInstallProgram:
    """Test POST /api/v1/programs/{id}/install"""

    def test_install_program_success(self, mock_supabase):
        """Should install a published program, 201."""
        program_id = str(uuid4())

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": program_id, "is_published": True}
                ]
            elif table_name == "program_installations":
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "user_id": COACH_ID, "program_id": program_id}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(f"/api/v1/programs/{program_id}/install")

        assert response.status_code == 201

    def test_install_program_already_installed_409(self, mock_supabase):
        """Should return 409 if already installed."""
        program_id = str(uuid4())

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_packages":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": program_id, "is_published": True}
                ]
            elif table_name == "program_installations":
                mock_table.insert.return_value.execute.side_effect = Exception(
                    "duplicate key value violates unique constraint"
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(f"/api/v1/programs/{program_id}/install")

        assert response.status_code == 409

    def test_install_program_not_published_404(self, mock_supabase):
        """Should return 404 for unpublished program."""
        program_id = str(uuid4())

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": program_id, "is_published": False}
        ]

        response = client.post(f"/api/v1/programs/{program_id}/install")

        assert response.status_code == 404


class TestUninstallProgram:
    """Test DELETE /api/v1/programs/{id}/install"""

    def test_uninstall_program_success(self, mock_supabase):
        """Should uninstall and return 204."""
        program_id = str(uuid4())

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # Check installation exists
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            else:
                # Delete
                mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/programs/{program_id}/install")

        assert response.status_code == 204

    def test_uninstall_program_not_installed_404(self, mock_supabase):
        """Should return 404 when not installed."""
        program_id = str(uuid4())

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/programs/{program_id}/install")

        assert response.status_code == 404


class TestProgramTemplates:
    """Test program template CRUD (admin only)."""

    def test_add_template_success(self, admin_client):
        """Admin should add a template to a program."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())
            template_data = _make_template(program_id=program_id)

            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if table_name == "program_packages":
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        _make_program(program_id=program_id)
                    ]
                elif table_name == "program_templates":
                    mock_table.insert.return_value.execute.return_value.data = [template_data]
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.post(
                f"/api/v1/programs/{program_id}/templates",
                json={
                    "template_name": "Day 1 - Upper Body",
                    "training_type": "Strength",
                    "order_index": 1,
                    "exercises": [
                        {
                            "exercise_name": "Bench Press",
                            "exercise_category": "Strength",
                            "sets": 3,
                            "reps": 5,
                            "weight_kg": 80.0,
                        }
                    ],
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["template_name"] == "Day 1 - Upper Body"

    def test_add_template_non_admin_403(self, mock_supabase):
        """Coach should get 403."""
        program_id = str(uuid4())

        response = client.post(
            f"/api/v1/programs/{program_id}/templates",
            json={
                "template_name": "Day 1",
                "training_type": "Strength",
            },
        )

        assert response.status_code == 403

    def test_add_template_duplicate_409(self, admin_client):
        """Duplicate template name should return 409."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())

            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if table_name == "program_packages":
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        _make_program(program_id=program_id)
                    ]
                elif table_name == "program_templates":
                    mock_table.insert.return_value.execute.side_effect = Exception(
                        "duplicate key value violates unique constraint"
                    )
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.post(
                f"/api/v1/programs/{program_id}/templates",
                json={
                    "template_name": "Day 1",
                    "training_type": "Strength",
                },
            )

            assert response.status_code == 409

    def test_update_template_success(self, admin_client):
        """Admin should update a program template."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())
            template_id = str(uuid4())
            template_data = _make_template(template_id=template_id, program_id=program_id)

            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    # Verify exists
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        template_data
                    ]
                else:
                    # Update
                    mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {**template_data, "notes": "Updated notes"}
                    ]
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.patch(
                f"/api/v1/programs/{program_id}/templates/{template_id}",
                json={"notes": "Updated notes"},
            )

            assert response.status_code == 200

    def test_delete_template_success(self, admin_client):
        """Admin should delete a program template, 204."""
        with patch(PROGRAMS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            program_id = str(uuid4())
            template_id = str(uuid4())
            template_data = _make_template(template_id=template_id, program_id=program_id)

            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    # Verify exists
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        template_data
                    ]
                else:
                    # Delete
                    mock_table.delete.return_value.eq.return_value.execute.return_value = None
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = admin_client.delete(
                f"/api/v1/programs/{program_id}/templates/{template_id}"
            )

            assert response.status_code == 204


class TestInstalledTemplates:
    """Test GET /api/v1/programs/installed-templates"""

    def test_installed_templates_returns_from_installed_programs(self, mock_supabase):
        """Should return templates from installed programs with program_name."""
        program_id = str(uuid4())
        template_data = _make_template(program_id=program_id)

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_installations":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"program_id": program_id}
                ]
            elif table_name == "program_packages":
                mock_table.select.return_value.in_.return_value.execute.return_value.data = [
                    {"id": program_id, "program_name": "Train Like a Champion"}
                ]
            elif table_name == "program_templates":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = [
                    template_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/programs/installed-templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["program_name"] == "Train Like a Champion"
        assert data[0]["template_name"] == "Day 1 - Upper Body"

    def test_installed_templates_empty_when_none_installed(self, mock_supabase):
        """Should return empty list when no programs installed."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/v1/programs/installed-templates")

        assert response.status_code == 200
        assert response.json() == []


class TestApplyProgramTemplate:
    """Test POST /api/v1/programs/templates/{id}/apply"""

    def test_apply_program_template_success(self, mock_supabase):
        """Should create exercise prescriptions with set expansion."""
        template_id = str(uuid4())
        program_id = str(uuid4())
        session_id = str(uuid4())
        athlete_id = str(uuid4())

        template_data = _make_template(template_id=template_id, program_id=program_id)

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [template_data]
            elif table_name == "program_installations":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": athlete_id, "status": None, "created_by": COACH_ID}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                # Return 3 prescriptions (one per set for 3-set exercise)
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "session_id": session_id, "exercise_name": "Bench Press", "set_number": i}
                    for i in range(1, 4)
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/programs/templates/{template_id}/apply?session_id={session_id}"
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3

    def test_apply_program_template_not_installed_403(self, mock_supabase):
        """Should return 403 when program not installed."""
        template_id = str(uuid4())
        program_id = str(uuid4())
        session_id = str(uuid4())

        template_data = _make_template(template_id=template_id, program_id=program_id)

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "program_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [template_data]
            elif table_name == "program_installations":
                # Not installed
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/programs/templates/{template_id}/apply?session_id={session_id}"
        )

        assert response.status_code == 403

    def test_apply_program_template_no_database_503(self):
        """Should return 503 when database not configured."""
        with patch(PROGRAMS_PATCH, return_value=None):
            response = client.post(
                f"/api/v1/programs/templates/{uuid4()}/apply?session_id={uuid4()}"
            )
        assert response.status_code == 503


class TestProgramSchemaValidation:
    """Test schema validation."""

    def test_program_name_stripped(self):
        """Program name should be stripped of whitespace."""
        from app.schemas.program import ProgramPackageCreate

        p = ProgramPackageCreate(program_name="  My Program  ", category="Strength")
        assert p.program_name == "My Program"

    def test_program_name_empty_rejected(self):
        """Empty program name should raise validation error."""
        from app.schemas.program import ProgramPackageCreate

        with pytest.raises(Exception):
            ProgramPackageCreate(program_name="   ", category="Strength")

    def test_template_name_stripped(self):
        """Template name should be stripped of whitespace."""
        from app.schemas.program import ProgramTemplateCreate

        t = ProgramTemplateCreate(
            template_name="  Day 1  ",
            training_type="Strength",
        )
        assert t.template_name == "Day 1"

    def test_exercise_name_stripped(self):
        """Exercise name should be stripped."""
        from app.schemas.program import ProgramExercise

        ex = ProgramExercise(exercise_name="  Bench Press  ")
        assert ex.exercise_name == "Bench Press"

    def test_exercise_sets_default_to_one(self):
        """Sets should default to 1."""
        from app.schemas.program import ProgramExercise

        ex = ProgramExercise(exercise_name="Squat")
        assert ex.sets == 1

    def test_invalid_intensity_type(self):
        """Invalid intensity_type should raise validation error."""
        from app.schemas.program import ProgramExercise

        with pytest.raises(Exception):
            ProgramExercise(exercise_name="Run", intensity_type="invalid")
