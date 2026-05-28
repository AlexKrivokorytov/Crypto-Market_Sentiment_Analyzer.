"""
FastAPI dependency injection functions for authentication.

Provides `get_current_user` which extracts and validates the Bearer JWT
from the Authorization header, returning the decoded UserPublic or raising 401.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.schemas.auth import UserPublic
from backend.app.services.auth import decode_access_token, get_user_by_id

_bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UserPublic:
    """
    FastAPI dependency that extracts and validates the JWT Bearer token.

    Raises a 401 if the token is missing, expired, or the user no longer exists.

    Args:
        credentials: HTTPAuthorizationCredentials injected by FastAPI from the
                     Authorization: Bearer <token> header.

    Returns:
        The authenticated UserPublic profile.

    Raises:
        HTTPException: 401 UNAUTHORIZED if the token is invalid or user not found.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise unauthorized

    user = await get_user_by_id(user_id)
    if not user:
        raise unauthorized

    return user
