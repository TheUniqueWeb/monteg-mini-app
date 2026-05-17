"""
app/core/security.py
─────────────────────────────────────────────────────────────────────────────
JWT helpers + Telegram WebApp init-data verification (HMAC-SHA256).
All auth flows go through this module.
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import unquote, parse_qsl

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from config import settings

# ── Bearer scheme (reads Authorization: Bearer <token>) ──────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


# ── Telegram Init-Data Verification ──────────────────────────────────────────

def verify_telegram_init_data(init_data: str) -> dict:
    """
    Verify the Telegram WebApp initData string using HMAC-SHA256.

    Algorithm (per Telegram docs):
    1. Parse the query string.
    2. Remove 'hash' field and sort remaining key=value pairs.
    3. Compute HMAC-SHA256 over the joined string using a key derived from BOT_TOKEN.
    4. Compare against the provided hash.

    Returns parsed user dict on success, raises HTTPException on failure.
    """
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    # Build the data-check string
    data_check_arr = [f"{k}={v}" for k, v in sorted(parsed.items())]
    data_check_string = "\n".join(data_check_arr)

    # Derive secret key: HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()

    # Compute expected hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram init-data signature")

    # Optional: check freshness (auth_date within 24 h)
    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Init-data has expired")

    # Decode nested user JSON
    user_str = parsed.get("user", "{}")
    return json.loads(unquote(user_str))


# ── JWT Helpers ───────────────────────────────────────────────────────────────

def create_access_token(telegram_id: int, is_admin: bool = False) -> str:
    """Mint a signed JWT for the given Telegram user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(telegram_id),
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode & validate a JWT; raises HTTPException on any failure."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI Dependencies ──────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> int:
    """Dependency: extract and return the current user's telegram_id from JWT."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    return int(payload["sub"])


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> int:
    """
    Dependency: same as get_current_user_id but also verifies the user is an admin.
    Use on all admin-only endpoints.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    telegram_id = int(payload["sub"])

    # Double-check: must be in the hard-coded admin list AND token must carry the flag
    if telegram_id not in settings.ADMIN_IDS or not payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return telegram_id
