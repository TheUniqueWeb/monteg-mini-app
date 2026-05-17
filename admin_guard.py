"""
app/middleware/admin_guard.py
─────────────────────────────────────────────────────────────────────────────
Starlette middleware that short-circuits any request to /api/v1/admin/*
unless the caller presents a valid JWT with admin privileges.

This is a defence-in-depth layer on top of the per-endpoint `require_admin`
dependency — even if a developer forgets to add the dependency, the middleware
will block the request.
"""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import JWTError, jwt

from config import settings

logger = logging.getLogger("cybearn.admin_guard")


class AdminGuardMiddleware(BaseHTTPMiddleware):
    """
    Block /api/v1/admin/* requests that do not carry a valid admin JWT.

    Flow
    ────
    1. If the path doesn't start with ADMIN_PREFIX → pass through immediately.
    2. Extract the Bearer token from the Authorization header.
    3. Decode and validate the JWT.
    4. Confirm the telegram_id is in the ADMIN_IDS allow-list.
    5. Log every admin action with timestamp, user-id, and path.
    6. On any failure → return 403 JSON immediately, log the violation.
    """

    ADMIN_PREFIX = "/api/v1/admin"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # ── Skip non-admin routes ─────────────────────────────────────────────
        if not request.url.path.startswith(self.ADMIN_PREFIX):
            return await call_next(request)

        # ── Extract token ─────────────────────────────────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return self._deny(request, "Missing or malformed Authorization header")

        token = auth_header.split(" ", 1)[1]

        # ── Decode & validate ─────────────────────────────────────────────────
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            return self._deny(request, f"JWT error: {exc}")

        telegram_id = int(payload.get("sub", 0))
        is_admin_flag = payload.get("is_admin", False)

        # ── Admin allow-list check ────────────────────────────────────────────
        if telegram_id not in settings.ADMIN_IDS or not is_admin_flag:
            return self._deny(request, f"User {telegram_id} is not an admin", telegram_id)

        # ── Audit log ─────────────────────────────────────────────────────────
        start = time.perf_counter()
        logger.info(
            "ADMIN ACTION | user=%s | method=%s | path=%s",
            telegram_id,
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ADMIN RESPONSE | user=%s | status=%s | %.1fms",
            telegram_id,
            response.status_code,
            elapsed_ms,
        )
        return response

    @staticmethod
    def _deny(request: Request, reason: str, user_id: int = 0) -> JSONResponse:
        logger.warning(
            "ADMIN BLOCKED | user=%s | path=%s | reason=%s",
            user_id or "unknown",
            request.url.path,
            reason,
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Admin access denied", "reason": reason},
        )
