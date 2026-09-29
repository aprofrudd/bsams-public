"""Authentication and security utilities."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase_client import get_supabase_client

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Authenticated user with role information."""

    id: UUID
    role: str  # "admin", "coach", or "athlete"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """
    Get the current authenticated user.

    Reads JWT from HttpOnly cookie first, then falls back to Authorization header.
    Validates the token via Supabase Auth and returns the authenticated user
    with role information from the profiles table.

    Returns:
        AuthenticatedUser: The current user's ID and role.

    Raises:
        HTTPException: 401 if token is missing or invalid.
    """
    # Try cookie first, then Authorization header
    token = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured",
        )

    try:
        user_response = client.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(user.id)

        # Look up role from profiles table
        try:
            profile_result = (
                client.table("profiles")
                .select("role")
                .eq("id", str(user_id))
                .execute()
            )
            if profile_result.data and profile_result.data[0].get("role"):
                role = profile_result.data[0]["role"]
            else:
                role = "coach"  # New user, profile exists but no role yet
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify user role",
            )

        return AuthenticatedUser(id=user_id, role=role)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
