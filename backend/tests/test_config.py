"""Tests for core configuration."""

import os
from unittest.mock import patch

import pytest

from app.core.config import Settings, get_settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self):
        """Settings should have sensible defaults.

        Isolated from both sources deliberately. The environment is genuinely cleared
        — the previous spelling copied `os.environ` and re-applied it with
        `clear=True`, which clears and then puts everything straight back — and
        `_env_file=None` keeps a developer's real `backend/.env` out of a test about
        what the defaults are. Without both, this passes only on a machine that has
        not been set up to run the app.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.supabase_url == ""
            assert settings.supabase_key == ""
            assert settings.api_v1_prefix == "/api/v1"

    def test_loads_from_environment(self):
        """Settings should load from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "test-key",
            },
        ):
            settings = Settings()
            assert settings.supabase_url == "https://test.supabase.co"
            assert settings.supabase_key == "test-key"

    def test_case_insensitive(self):
        """Settings should be case insensitive for env vars."""
        with patch.dict(os.environ, {"supabase_url": "https://lower.supabase.co"}):
            settings = Settings()
            assert settings.supabase_url == "https://lower.supabase.co"

    def test_an_unrelated_key_in_the_env_file_does_not_break_startup(self, tmp_path):
        """A key in `.env` that is not an app setting must not be fatal.

        Unknown *environment* variables are never collected, but every key in the
        dotenv file is, so one line meant for something else fails the whole model.
        `scripts/seed_combine.py` reads BSAMS_REHEARSAL_EMAIL straight from the
        environment and the documented place to keep it is `backend/.env` — the very
        file this loads. Rejecting it takes the app down at import, before `main`
        reaches a line of its own, which is a strange way to find out that a helper
        script has a variable.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SUPABASE_URL=https://test.supabase.co\n"
            "BSAMS_REHEARSAL_EMAIL=coach@example.com\n"
        )

        settings = Settings(_env_file=str(env_file))

        assert settings.supabase_url == "https://test.supabase.co"


class TestGetSettings:
    """Test get_settings function."""

    def test_returns_settings_instance(self):
        """get_settings should return a Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching(self):
        """get_settings should return cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
