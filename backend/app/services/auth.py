"""
Authentication and authorization service for the Market Sentiment Analyzer.

Handles password hashing, JWT token creation/verification, user CRUD,
and watchlist management using the Motor async MongoDB driver.
"""

import datetime
import logging
from typing import Any, Dict, Optional

from bson import ObjectId
from jose import JWTError, jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]

from backend.app.core.config import settings
from backend.app.core.database import users_collection
from backend.app.schemas.auth import UserCreate, UserPublic

logger = logging.getLogger("app")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ──────────────────────────────────────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Args:
        plain_password: The raw password string from user input.

    Returns:
        The bcrypt-hashed password string.
    """
    return str(_pwd_context.hash(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.

    Uses passlib's constant-time comparison internally.

    Args:
        plain_password: The raw password from login input.
        hashed_password: The stored bcrypt hash from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return bool(_pwd_context.verify(plain_password, hashed_password))


# ──────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────────────────────────────────────


def create_access_token(user_id: str) -> str:
    """
    Creates a signed JWT access token for the given user ID.

    Args:
        user_id: MongoDB ObjectId string of the authenticated user.

    Returns:
        Signed JWT string.
    """
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire}
    return str(
        jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    )


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodes a JWT access token and returns the subject (user ID).

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The user_id string if the token is valid and not expired, else None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return str(payload.get("sub"))
    except JWTError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# User CRUD
# ──────────────────────────────────────────────────────────────────────────────


def _doc_to_user_public(doc: Dict[str, Any]) -> UserPublic:
    """
    Converts a raw MongoDB user document to a UserPublic schema.

    Args:
        doc: Raw document from users_collection with _id as ObjectId.

    Returns:
        UserPublic schema with id as hex string.
    """
    return UserPublic(
        id=str(doc["_id"]),
        email=str(doc["email"]),
        display_name=str(doc["display_name"]),
        watchlist=list(doc.get("watchlist", [])),
    )


async def create_user(payload: UserCreate) -> UserPublic:
    """
    Creates a new user in the database after hashing their password.

    Args:
        payload: Validated UserCreate input from the registration endpoint.

    Returns:
        The created user as a UserPublic schema.

    Raises:
        ValueError: If a user with the given email already exists.
        Exception: Propagates unexpected MongoDB errors.
    """
    existing = await users_collection.find_one({"email": payload.email})
    if existing:
        raise ValueError(f"Email {payload.email!r} is already registered.")

    user_doc: Dict[str, Any] = {
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "display_name": payload.display_name,
        "watchlist": [],
        "portfolio": [],
        "alerts": [],
    }

    result = await users_collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    logger.info("user_created: email=%s", payload.email)
    return _doc_to_user_public(user_doc)


async def authenticate_user(email: str, password: str) -> Optional[UserPublic]:
    """
    Verifies login credentials and returns the public user profile on success.

    Args:
        email: User email from login request.
        password: Plain-text password from login request.

    Returns:
        UserPublic if credentials are valid, None otherwise.
    """
    doc = await users_collection.find_one({"email": email})
    if not doc:
        return None
    if not verify_password(password, str(doc["hashed_password"])):
        return None
    return _doc_to_user_public(doc)


async def get_user_by_id(user_id: str) -> Optional[UserPublic]:
    """
    Fetches a user's public profile by their MongoDB ObjectId string.

    Args:
        user_id: Hex string representation of the user's ObjectId.

    Returns:
        UserPublic if found, None otherwise.
    """
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None

    doc = await users_collection.find_one({"_id": oid})
    if not doc:
        return None
    return _doc_to_user_public(doc)


async def add_to_watchlist(user_id: str, asset_id: str) -> UserPublic:
    """
    Adds an asset to a user's watchlist if not already present.

    Args:
        user_id: Hex string of the user's ObjectId.
        asset_id: Ticker symbol to add.

    Returns:
        Updated UserPublic profile.

    Raises:
        ValueError: If the user is not found.
    """
    try:
        oid = ObjectId(user_id)
    except Exception as exc:
        raise ValueError(f"Invalid user_id: {user_id!r}") from exc

    result = await users_collection.find_one_and_update(
        {"_id": oid},
        {"$addToSet": {"watchlist": asset_id}},
        return_document=True,
    )
    if not result:
        raise ValueError(f"User {user_id!r} not found.")

    logger.info("watchlist_add: user_id=%s asset_id=%s", user_id, asset_id)
    return _doc_to_user_public(result)


async def remove_from_watchlist(user_id: str, asset_id: str) -> UserPublic:
    """
    Removes an asset from a user's watchlist.

    Args:
        user_id: Hex string of the user's ObjectId.
        asset_id: Ticker symbol to remove.

    Returns:
        Updated UserPublic profile.

    Raises:
        ValueError: If the user is not found.
    """
    try:
        oid = ObjectId(user_id)
    except Exception as exc:
        raise ValueError(f"Invalid user_id: {user_id!r}") from exc

    result = await users_collection.find_one_and_update(
        {"_id": oid},
        {"$pull": {"watchlist": asset_id}},
        return_document=True,
    )
    if not result:
        raise ValueError(f"User {user_id!r} not found.")

    logger.info("watchlist_remove: user_id=%s asset_id=%s", user_id, asset_id)
    return _doc_to_user_public(result)
