"""Shared test configuration."""

from uuid import UUID

import pytest

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_ADMIN_ID = UUID("00000000-0000-0000-0000-000000000099")
TEST_ATHLETE_ID = UUID("00000000-0000-0000-0000-000000000002")


async def override_get_current_user() -> AuthenticatedUser:
    """Test override that returns a fixed user with coach role."""
    return AuthenticatedUser(id=TEST_USER_ID, role="coach")


async def override_get_current_admin() -> AuthenticatedUser:
    """Test override that returns a fixed user with admin role."""
    return AuthenticatedUser(id=TEST_ADMIN_ID, role="admin")


async def override_get_current_athlete() -> AuthenticatedUser:
    """Test override that returns a fixed user with athlete role."""
    return AuthenticatedUser(id=TEST_ATHLETE_ID, role="athlete")


# Apply dependency override for all tests
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def test_user_id() -> UUID:
    """Return the test user UUID for assertions."""
    return TEST_USER_ID


@pytest.fixture
def test_admin_id() -> UUID:
    """Return the test admin UUID for assertions."""
    return TEST_ADMIN_ID


@pytest.fixture
def test_athlete_id() -> UUID:
    """Return the test athlete UUID for assertions."""
    return TEST_ATHLETE_ID


@pytest.fixture
def admin_client():
    """Provide a test client authenticated as admin."""
    from fastapi.testclient import TestClient

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_get_current_admin
    client = TestClient(app)
    yield client
    if original:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def athlete_client():
    """Provide a test client authenticated as athlete."""
    from fastapi.testclient import TestClient

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_get_current_athlete
    client = TestClient(app)
    yield client
    if original:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset rate limiter storage between tests."""
    yield
    from app.routers.uploads import limiter as uploads_limiter
    from app.routers.auth import limiter as auth_limiter
    from app.routers.admin import limiter as admin_limiter
    from app.routers.invitations import limiter as invitations_limiter
    from app.routers.events import limiter as events_limiter
    from app.routers.analysis import limiter as analysis_limiter
    from app.routers.athletes import limiter as athletes_limiter
    from app.routers.data_export import limiter as export_limiter
    from app.routers.database_analysis import limiter as db_analysis_limiter
    from app.routers.combine import limiter as combine_limiter
    from app.routers.combine import public_limiter as combine_public_limiter

    uploads_limiter.reset()
    auth_limiter.reset()
    admin_limiter.reset()
    invitations_limiter.reset()
    events_limiter.reset()
    analysis_limiter.reset()
    athletes_limiter.reset()
    export_limiter.reset()
    db_analysis_limiter.reset()
    combine_limiter.reset()
    combine_public_limiter.reset()
