"""Tests for audit logging service."""

from unittest.mock import MagicMock, patch, call
from uuid import uuid4, UUID

import pytest

from app.services.audit import log_event, log_deletion


class TestLogEvent:
    """Test audit log_event function."""

    def test_log_event_no_db_returns_gracefully(self):
        """Should not crash when no database connection available."""
        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = None
            # Should not raise
            log_event(
                user_id=uuid4(),
                action="login",
            )

    def test_log_event_with_all_parameters(self):
        """Should insert audit record with all fields populated."""
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"

        user_id = uuid4()
        resource_id = uuid4()

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client

            log_event(
                user_id=user_id,
                action="data_export",
                resource_type="athlete",
                resource_id=resource_id,
                details={"format": "json"},
                request=mock_request,
            )

            mock_client.table.assert_called_once_with("audit_log")
            insert_call = mock_client.table.return_value.insert
            insert_call.assert_called_once()

            record = insert_call.call_args[0][0]
            assert record["action"] == "data_export"
            assert record["user_id"] == str(user_id)
            assert record["resource_type"] == "athlete"
            assert record["resource_id"] == str(resource_id)
            assert record["ip_address"] == "192.168.1.1"
            assert record["details"] == {"format": "json"}

    def test_log_event_minimal_parameters(self):
        """Should insert audit record with only required fields."""
        mock_client = MagicMock()

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client

            log_event(
                user_id=None,
                action="system_startup",
            )

            record = mock_client.table.return_value.insert.call_args[0][0]
            assert record["action"] == "system_startup"
            assert "user_id" not in record
            assert "resource_type" not in record
            assert "resource_id" not in record
            assert "ip_address" not in record
            assert "details" not in record

    def test_log_event_handles_db_exception(self):
        """Should catch and log exceptions without crashing."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "DB error"
        )

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client
            # Should not raise
            log_event(
                user_id=uuid4(),
                action="login",
            )


class TestLogDeletion:
    """Test audit log_deletion function."""

    def test_log_deletion_no_db_returns_gracefully(self):
        """Should not crash when no database connection available."""
        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = None
            # Should not raise
            log_deletion(
                deleted_by=uuid4(),
                entity_type="athlete",
                entity_id=uuid4(),
            )

    def test_log_deletion_with_summary(self):
        """Should insert deletion record with entity summary."""
        mock_client = MagicMock()
        deleted_by = uuid4()
        entity_id = uuid4()

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client

            log_deletion(
                deleted_by=deleted_by,
                entity_type="athlete",
                entity_id=entity_id,
                entity_summary={"name": "John Doe", "email": "john@example.com"},
            )

            mock_client.table.assert_called_once_with("deletion_log")
            insert_call = mock_client.table.return_value.insert
            insert_call.assert_called_once()

            record = insert_call.call_args[0][0]
            assert record["deleted_by"] == str(deleted_by)
            assert record["entity_type"] == "athlete"
            assert record["entity_id"] == str(entity_id)
            assert record["entity_summary"]["name"] == "John Doe"

    def test_log_deletion_without_summary(self):
        """Should insert deletion record without summary when not provided."""
        mock_client = MagicMock()
        deleted_by = uuid4()
        entity_id = uuid4()

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client

            log_deletion(
                deleted_by=deleted_by,
                entity_type="account",
                entity_id=entity_id,
            )

            record = mock_client.table.return_value.insert.call_args[0][0]
            assert record["deleted_by"] == str(deleted_by)
            assert record["entity_type"] == "account"
            assert record["entity_id"] == str(entity_id)
            assert "entity_summary" not in record

    def test_log_deletion_handles_db_exception(self):
        """Should catch and log exceptions without crashing."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "DB error"
        )

        with patch("app.services.audit.get_supabase_client") as mock:
            mock.return_value = mock_client
            # Should not raise
            log_deletion(
                deleted_by=uuid4(),
                entity_type="athlete",
                entity_id=uuid4(),
            )
