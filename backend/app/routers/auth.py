"""Authentication API router."""

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from uuid import UUID

from supabase import ClientOptions, create_client
from app.core.config import get_settings
from app.core.supabase_client import get_client_or_503, get_supabase_client
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.auth import (
    AthleteSignupRequest, AuthRequest, AuthResponse, SignupRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, ChangeEmailRequest,
)
from app.services.audit import log_event

logger = logging.getLogger(__name__)

# Account lockout constants
LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 minutes


def _check_lockout(email: str, request: Request | None = None) -> None:
    """Check if an email is locked out due to too many failed attempts (DB-backed)."""
    client = get_supabase_client()
    if not client:
        return  # Can't check lockout without DB — fail open for availability

    try:
        # Cleanup: delete attempts older than 1 hour
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        client.table("login_attempts").delete().lt(
            "attempted_at", one_hour_ago
        ).execute()
    except Exception:
        pass  # Best-effort cleanup

    try:
        # Count recent attempts within the lockout window
        window_start = (datetime.now(timezone.utc) - timedelta(seconds=LOCKOUT_WINDOW_SECONDS)).isoformat()
        result = (
            client.table("login_attempts")
            .select("id", count="exact")
            .eq("email", email)
            .gte("attempted_at", window_start)
            .execute()
        )
        count = result.count if result.count is not None else len(result.data or [])
        if count >= LOCKOUT_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Please try again in 15 minutes.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Fail open — don't block login if lockout check fails


def _record_failed_attempt(email: str, request: Request | None = None) -> None:
    """Record a failed login attempt in the database."""
    client = get_supabase_client()
    if not client:
        return

    ip_address = None
    if request and request.client:
        ip_address = request.client.host

    try:
        record: dict = {"email": email}
        if ip_address:
            record["ip_address"] = ip_address
        client.table("login_attempts").insert(record).execute()
    except Exception:
        pass  # Best-effort


def _clear_failed_attempts(email: str) -> None:
    """Clear failed attempts on successful login or password reset."""
    client = get_supabase_client()
    if not client:
        return

    try:
        client.table("login_attempts").delete().eq("email", email).execute()
    except Exception:
        pass  # Best-effort

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# Cookie settings
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = "lax"


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set HttpOnly auth cookie on response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clear auth cookie from response."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def _ensure_profile_exists(client, user_id: str, email: str) -> None:
    """Create a profiles row if one doesn't already exist."""
    existing = (
        client.table("profiles")
        .select("id")
        .eq("id", user_id)
        .execute()
    )
    if not existing.data:
        client.table("profiles").insert(
            {"id": user_id, "email": email, "role": "coach"}
        ).execute()


def _auth_client():
    """Build a throwaway client to sign one user in.

    supabase 2.27.3 swaps a client's Authorization header to the signed-in user on
    SIGNED_IN (library client.py:334-346), so signing in on the cached service-role
    singleton would leave every later query on that worker running as the last person
    to log in, under their row-level security. This client lives for a single request,
    so it needs neither a refresh loop nor a persisted session.
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


@router.post("/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup(request: Request, body: SignupRequest, response: Response):
    """Sign up a new user with email and password."""
    client = get_client_or_503()  # service-role singleton: DB work only

    try:
        result = _auth_client().auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        logger.exception("Signup failed for %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed",
        )

    if not result.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Check if email confirmation is required.",
        )

    # Ensure profile row exists (fallback if DB trigger didn't fire)
    _ensure_profile_exists(client, str(result.user.id), result.user.email)

    _set_auth_cookie(response, result.session.access_token)

    return AuthResponse(
        user_id=result.user.id,
        email=result.user.email,
    )


@router.post("/login", response_model=AuthResponse)
# Flood guard, not the brute-force guard: every BSAMS user reaches the API through the
# same proxy address, so a room of iPads signing in shares one bucket. Per-account
# guessing is caught by the email-keyed _check_lockout below.
@limiter.limit("30/minute")
async def login(request: Request, body: AuthRequest, response: Response):
    """Log in with email and password."""
    # Check for account lockout before attempting login
    _check_lockout(body.email, request)

    client = get_client_or_503()  # service-role singleton: DB work only

    try:
        result = _auth_client().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        _record_failed_attempt(body.email, request)
        logger.warning("Failed login attempt for %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Clear failed attempts on successful login
    _clear_failed_attempts(body.email)

    # Ensure profile row exists (fallback for users created before trigger)
    _ensure_profile_exists(client, str(result.user.id), result.user.email)

    _set_auth_cookie(response, result.session.access_token)

    return AuthResponse(
        user_id=result.user.id,
        email=result.user.email,
    )


@router.post("/signup/athlete", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup_athlete(request: Request, response: Response, body: AthleteSignupRequest):
    """Sign up a new athlete user with an invitation code."""
    client = get_client_or_503()

    # 1. Validate invite code (must exist and be unused)
    invite = (
        client.table("athlete_invitations")
        .select("*")
        .eq("invite_code", body.invite_code)
        .is_("used_at", "null")
        .execute()
    )
    if not invite.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation code",
        )

    invite_data = invite.data[0]

    # Check expiry
    expires_at = datetime.fromisoformat(invite_data["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation code has expired",
        )

    # 2. Create auth user on a throwaway client, so `client` stays service-role
    try:
        auth_response = _auth_client().auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        logger.exception("Athlete signup failed for %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed",
        )

    user = auth_response.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed",
        )

    if not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Check if email confirmation is required.",
        )

    # 3. Create profile with role='athlete'
    try:
        client.table("profiles").insert({
            "id": str(user.id),
            "email": body.email,
            "role": "athlete",
        }).execute()
    except Exception:
        pass  # Profile might already exist

    # 4. Link athlete record
    client.table("athletes").update(
        {"user_id": str(user.id)}
    ).eq("id", invite_data["athlete_id"]).execute()

    # 5. Consume invitation
    client.table("athlete_invitations").update({
        "used_at": datetime.now(timezone.utc).isoformat(),
        "used_by": str(user.id),
    }).eq("invite_code", body.invite_code).is_("used_at", "null").execute()

    # 6. Set cookie and return
    _set_auth_cookie(response, auth_response.session.access_token)

    return AuthResponse(
        user_id=str(user.id),
        email=body.email,
    )


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """Send a password reset email. Always returns 200 to prevent email enumeration."""
    try:
        settings = get_settings()
        client = get_supabase_client()
        if client:
            redirect_url = f"{settings.frontend_url}/reset-password" if settings.frontend_url else None
            options = {"redirect_to": redirect_url} if redirect_url else {}
            client.auth.reset_password_email(body.email, options=options)
    except Exception:
        logger.info("Forgot-password request for %s (may or may not exist)", body.email)
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    """Reset password using recovery token from email link."""
    client = get_client_or_503()

    # Resolve user from access_token (implicit flow) or code (PKCE flow)
    access_token = body.access_token
    if body.code:
        # PKCE flow: exchange code for session first
        try:
            settings = get_settings()
            pkce_client = create_client(settings.supabase_url, settings.supabase_key)
            session_response = pkce_client.auth.exchange_code_for_session(
                {"auth_code": body.code}
            )
            if session_response.session:
                access_token = session_response.session.access_token
            else:
                raise ValueError("No session returned")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reset link",
            )

    # Validate token and get user
    try:
        user_response = client.auth.get_user(access_token)
        user = user_response.user
        if not user:
            raise ValueError("No user")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset link",
        )

    # Update password via admin API
    try:
        settings = get_settings()
        admin_client = create_client(settings.supabase_url, settings.supabase_key)
        admin_client.auth.admin.update_user_by_id(
            str(user.id), {"password": body.new_password}
        )
    except Exception:
        logger.exception("Failed to reset password for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )

    # Invalidate all sessions (refresh tokens) globally
    try:
        admin_client.auth.admin.sign_out(str(user.id))
    except Exception:
        pass  # Best-effort

    # Clear lockout so user can login immediately
    if user.email:
        _clear_failed_attempts(user.email)

    # Audit log
    try:
        log_event(user.id, "password_reset_completed")
    except Exception:
        pass

    return {"message": "Password has been reset successfully. Please log in with your new password."}


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    response: Response,
    body: ChangePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Change password for authenticated user. Requires current password verification."""
    client = get_client_or_503()

    # Look up email from profiles table
    profile = (
        client.table("profiles")
        .select("email")
        .eq("id", str(current_user.id))
        .execute()
    )
    if not profile.data or not profile.data[0].get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find user profile",
        )
    email = profile.data[0]["email"]

    # Verify current password
    try:
        settings = get_settings()
        verify_client = create_client(settings.supabase_url, settings.supabase_key)
        verify_client.auth.sign_in_with_password(
            {"email": email, "password": body.current_password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password via admin API (fresh client to avoid singleton mutation)
    try:
        admin_client = create_client(settings.supabase_url, settings.supabase_key)
        admin_client.auth.admin.update_user_by_id(
            str(current_user.id), {"password": body.new_password}
        )
    except Exception:
        logger.exception("Failed to change password for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )

    # Invalidate all sessions (refresh tokens) globally
    try:
        admin_client.auth.admin.sign_out(str(current_user.id))
    except Exception:
        pass  # Best-effort

    # Clear current session cookie
    _clear_auth_cookie(response)

    # Audit log
    try:
        log_event(current_user.id, "password_changed", request=request)
    except Exception:
        pass

    return {"message": "Password changed successfully. Please log in again."}


@router.post("/change-email")
@limiter.limit("3/minute")
async def change_email(
    request: Request,
    response: Response,
    body: ChangeEmailRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Change email for authenticated user. Requires current password verification."""
    client = get_client_or_503()

    # Look up current email from profiles table
    profile = (
        client.table("profiles")
        .select("email")
        .eq("id", str(current_user.id))
        .execute()
    )
    if not profile.data or not profile.data[0].get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find user profile",
        )
    current_email = profile.data[0]["email"]

    # Verify current password
    try:
        settings = get_settings()
        verify_client = create_client(settings.supabase_url, settings.supabase_key)
        verify_client.auth.sign_in_with_password(
            {"email": current_email, "password": body.current_password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update auth email via admin API
    try:
        admin_client = create_client(settings.supabase_url, settings.supabase_key)
        admin_client.auth.admin.update_user_by_id(
            str(current_user.id), {"email": body.new_email}
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "already" in error_msg or "duplicate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use",
            )
        logger.exception("Failed to change email for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email change failed",
        )

    # Update profiles table to stay in sync
    try:
        client.table("profiles").update(
            {"email": body.new_email}
        ).eq("id", str(current_user.id)).execute()
    except Exception:
        logger.exception("Failed to sync email in profiles for user %s", current_user.id)

    # Invalidate all sessions (refresh tokens) globally
    try:
        admin_client.auth.admin.sign_out(str(current_user.id))
    except Exception:
        pass  # Best-effort

    # Clear current session cookie
    _clear_auth_cookie(response)

    # Audit log
    try:
        log_event(current_user.id, "email_changed", request=request)
    except Exception:
        pass

    return {"message": "Email changed successfully. Please log in again."}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Log out the current user (invalidate session server-side)."""
    try:
        settings = get_settings()
        admin_client = create_client(settings.supabase_url, settings.supabase_key)
        admin_client.auth.admin.sign_out(str(current_user.id))
    except Exception:
        pass  # Best-effort server-side invalidation

    _clear_auth_cookie(response)
    return None


@router.get("/me")
async def get_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Return current authenticated user info. Includes athlete_id for athlete users."""
    result = {"user_id": str(current_user.id), "role": current_user.role, "email": ""}

    client = get_supabase_client()
    if client:
        # Fetch email from profiles
        profile = (
            client.table("profiles")
            .select("email")
            .eq("id", str(current_user.id))
            .execute()
        )
        if profile.data and profile.data[0].get("email"):
            result["email"] = profile.data[0]["email"]

        if current_user.role == "athlete":
            athlete = (
                client.table("athletes")
                .select("id")
                .eq("user_id", str(current_user.id))
                .execute()
            )
            if athlete.data:
                result["athlete_id"] = athlete.data[0]["id"]

    return result
