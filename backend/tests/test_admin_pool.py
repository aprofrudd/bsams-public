"""Tests for admin pool service."""

from unittest.mock import MagicMock

from app.services.admin_pool import get_admin_athlete_ids, get_admin_athletes, get_opted_in_athletes


class TestGetAdminAthleteIds:
    """Test get_admin_athlete_ids function."""

    def test_returns_empty_when_no_admins(self):
        """Should return empty list when no admin profiles exist."""
        mock_client = MagicMock()
        mock_profiles_result = MagicMock()
        mock_profiles_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_profiles_result

        result = get_admin_athlete_ids(mock_client)
        assert result == []

    def test_returns_athlete_ids_for_admin_users(self):
        """Should return athlete IDs belonging to admin users."""
        mock_client = MagicMock()

        # Mock profiles query
        mock_profiles_result = MagicMock()
        mock_profiles_result.data = [{"id": "admin-1"}, {"id": "admin-2"}]

        # Mock athletes queries
        mock_athletes_result_1 = MagicMock()
        mock_athletes_result_1.data = [{"id": "athlete-1"}, {"id": "athlete-2"}]
        mock_athletes_result_2 = MagicMock()
        mock_athletes_result_2.data = [{"id": "athlete-3"}]

        # Chain mocks
        table_mock = MagicMock()
        select_mock_profiles = MagicMock()
        eq_role_mock = MagicMock()
        eq_role_mock.execute.return_value = mock_profiles_result
        select_mock_profiles.eq.return_value = eq_role_mock

        select_mock_athletes = MagicMock()
        eq_coach_mock_1 = MagicMock()
        eq_coach_mock_1.execute.return_value = mock_athletes_result_1
        eq_coach_mock_2 = MagicMock()
        eq_coach_mock_2.execute.return_value = mock_athletes_result_2
        select_mock_athletes.eq.side_effect = [eq_coach_mock_1, eq_coach_mock_2]

        def table_dispatch(name):
            if name == "profiles":
                m = MagicMock()
                m.select.return_value = select_mock_profiles
                return m
            else:
                m = MagicMock()
                m.select.return_value = select_mock_athletes
                return m

        mock_client.table.side_effect = table_dispatch

        result = get_admin_athlete_ids(mock_client)
        assert set(result) == {"athlete-1", "athlete-2", "athlete-3"}


class TestGetAdminAthletes:
    """Test get_admin_athletes function."""

    def test_returns_empty_when_no_admins(self):
        """Should return empty list when no admin profiles exist."""
        mock_client = MagicMock()
        mock_profiles_result = MagicMock()
        mock_profiles_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_profiles_result

        result = get_admin_athletes(mock_client)
        assert result == []

    def test_returns_athletes_with_gender(self):
        """Should return athletes with id and gender for admin users."""
        mock_client = MagicMock()

        mock_profiles_result = MagicMock()
        mock_profiles_result.data = [{"id": "admin-1"}]

        mock_athletes_result = MagicMock()
        mock_athletes_result.data = [
            {"id": "athlete-1", "gender": "male"},
            {"id": "athlete-2", "gender": "female"},
        ]

        def table_dispatch(name):
            if name == "profiles":
                m = MagicMock()
                m.select.return_value.eq.return_value.execute.return_value = mock_profiles_result
                return m
            else:
                m = MagicMock()
                m.select.return_value.eq.return_value.execute.return_value = mock_athletes_result
                return m

        mock_client.table.side_effect = table_dispatch

        result = get_admin_athletes(mock_client)
        assert len(result) == 2
        assert result[0]["gender"] == "male"
        assert result[1]["gender"] == "female"


class TestGetOptedInAthletes:
    """Test get_opted_in_athletes function."""

    def test_returns_empty_when_no_consents(self):
        """Should return empty list when no consents exist."""
        mock_client = MagicMock()
        mock_consents = MagicMock()
        mock_consents.data = []
        mock_client.table.return_value.select.return_value.execute.return_value = mock_consents

        result = get_opted_in_athletes(mock_client)
        assert result == []

    def test_returns_empty_when_all_consents_false(self):
        """Should return empty list when all consents are False."""
        mock_client = MagicMock()

        mock_consents = MagicMock()
        mock_consents.data = [
            {"coach_id": "coach-1", "data_sharing_enabled": False},
            {"coach_id": "coach-2", "data_sharing_enabled": False},
        ]

        def table_dispatch(name):
            m = MagicMock()
            if name == "coach_consents":
                m.select.return_value.execute.return_value = mock_consents
            return m

        mock_client.table.side_effect = table_dispatch

        result = get_opted_in_athletes(mock_client)
        assert result == []

    def test_excludes_admin_coaches(self):
        """Should exclude admin accounts from opted-in coaches."""
        mock_client = MagicMock()

        mock_consents = MagicMock()
        mock_consents.data = [
            {"coach_id": "admin-1", "data_sharing_enabled": True},
        ]

        mock_admin_profiles = MagicMock()
        mock_admin_profiles.data = [{"id": "admin-1"}]

        def table_dispatch(name):
            m = MagicMock()
            if name == "coach_consents":
                m.select.return_value.execute.return_value = mock_consents
            elif name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value = mock_admin_profiles
            return m

        mock_client.table.side_effect = table_dispatch

        result = get_opted_in_athletes(mock_client)
        assert result == []

    def test_returns_opted_in_athletes(self):
        """Should return athletes from opted-in non-admin coaches."""
        mock_client = MagicMock()

        mock_consents = MagicMock()
        mock_consents.data = [
            {"coach_id": "coach-1", "data_sharing_enabled": True},
            {"coach_id": "coach-2", "data_sharing_enabled": False},
        ]

        mock_admin_profiles = MagicMock()
        mock_admin_profiles.data = [{"id": "admin-1"}]

        mock_athletes = MagicMock()
        mock_athletes.data = [
            {"id": "athlete-1", "gender": "male"},
            {"id": "athlete-2", "gender": "female"},
        ]

        def table_dispatch(name):
            m = MagicMock()
            if name == "coach_consents":
                m.select.return_value.execute.return_value = mock_consents
            elif name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value = mock_admin_profiles
            elif name == "athletes":
                m.select.return_value.in_.return_value.execute.return_value = mock_athletes
            return m

        mock_client.table.side_effect = table_dispatch

        result = get_opted_in_athletes(mock_client)
        assert len(result) == 2
        assert result[0]["id"] == "athlete-1"
        assert result[1]["gender"] == "female"
