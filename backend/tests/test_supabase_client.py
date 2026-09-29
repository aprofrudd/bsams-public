"""Tests for Supabase client."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client


class TestGetSupabaseClient:
    """Test get_supabase_client function."""

    def test_returns_none_when_not_configured(self):
        """Should return None when Supabase URL/key are not set."""
        get_settings.cache_clear()
        get_supabase_client.cache_clear()

        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
            get_settings.cache_clear()
            get_supabase_client.cache_clear()
            client = get_supabase_client()
            assert client is None

    def test_returns_none_when_url_missing(self):
        """Should return None when only URL is missing."""
        get_settings.cache_clear()
        get_supabase_client.cache_clear()

        with patch.dict(
            os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": "some-key"}, clear=False
        ):
            get_settings.cache_clear()
            get_supabase_client.cache_clear()
            client = get_supabase_client()
            assert client is None

    def test_returns_none_when_key_missing(self):
        """Should return None when only key is missing."""
        get_settings.cache_clear()
        get_supabase_client.cache_clear()

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": ""},
            clear=False,
        ):
            get_settings.cache_clear()
            get_supabase_client.cache_clear()
            client = get_supabase_client()
            assert client is None

    @patch("app.core.supabase_client.create_client")
    def test_creates_client_when_configured(self, mock_create_client):
        """Should create client when URL and key are configured."""
        get_settings.cache_clear()
        get_supabase_client.cache_clear()

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-anon-key",
            },
        ):
            get_settings.cache_clear()
            get_supabase_client.cache_clear()
            client = get_supabase_client()

            mock_create_client.assert_called_once_with(
                "https://test.supabase.co", "test-anon-key"
            )
            assert client is mock_client

    @patch("app.core.supabase_client.create_client")
    def test_caching(self, mock_create_client):
        """Should return cached client on subsequent calls."""
        get_settings.cache_clear()
        get_supabase_client.cache_clear()

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-anon-key",
            },
        ):
            get_settings.cache_clear()
            get_supabase_client.cache_clear()
            client1 = get_supabase_client()
            client2 = get_supabase_client()

            # create_client should only be called once
            assert mock_create_client.call_count == 1
            assert client1 is client2
