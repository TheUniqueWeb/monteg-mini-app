"""
app/api/v1/endpoints/auth.py
─────────────────────────────────────────────────────────────────────────────
POST /auth/login  – Verify Telegram WebApp initData and issue a JWT.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_telegram_init_data, create_access_token
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import TelegramInitData, TokenResponse, UserOut
from config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate via Telegram WebApp")
async def login(
    body: TelegramInitData,
    ref: str | None = Query(None, description="Referral code from URL"),
    db: AsyncSession = Depends(get_db),
):
    """
    1. Verify the Telegram initData HMAC signature.
    2. Upsert the user in the database (create if first time).
    3. Handle referral attribution (only once, on first login).
    4. Return a signed JWT.
    """
    # ── Step 1: Verify signature ──────────────────────────────────────────────
    tg_user = verify_telegram_init_data(body.init_data)

    telegram_id: int = tg_user["id"]
    first_name: str  = tg_user.get("first_name", "User")
    username: str | None = tg_user.get("username")
    photo_url: str | None = tg_user.get("photo_url")

    # ── Step 2: Upsert user ───────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user: User | None = result.scalar_one_or_none()

    is_new_user = user is None

    if is_new_user:
        # Generate a stable referral code
        referral_code = f"uid_{telegram_id}"
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            photo_url=photo_url,
            referral_code=referral_code,
        )
        db.add(user)

        # ── Step 3: Referral attribution ──────────────────────────────────────
        if ref:
            ref_result = await db.execute(
                select(User).where(User.referral_code == ref)
            )
            referrer: User | None = ref_result.scalar_one_or_none()

            if referrer and referrer.telegram_id != telegram_id:
                user.referred_by = referrer.telegram_id
                user.balance     += settings.REFERRAL_BONUS_REFEREE
                user.total_earned += settings.REFERRAL_BONUS_REFEREE

                # Level-1 commission for direct referrer
                referrer.balance     += settings.REFERRAL_BONUS_REFERRER
                referrer.total_earned += settings.REFERRAL_BONUS_REFERRER
                db.add(referrer)

                # Level-2 commission for referrer's referrer
                if referrer.referred_by:
                    l2_result = await db.execute(
                        select(User).where(User.telegram_id == referrer.referred_by)
                    )
                    l2: User | None = l2_result.scalar_one_or_none()
                    if l2:
                        l2_bonus = settings.REFERRAL_BONUS_REFERRER * settings.REFERRAL_COMMISSION_RATES[1]
                        l2.balance     += l2_bonus
                        l2.total_earned += l2_bonus
                        db.add(l2)
    else:
        # Update mutable profile fields on each login
        user.first_name = first_name
        if username:
            user.username = username
        if photo_url:
            user.photo_url = photo_url

    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account is banned")

    await db.flush()   # Assign IDs before creating token

    # ── Step 4: Issue JWT ─────────────────────────────────────────────────────
    is_admin = telegram_id in settings.ADMIN_IDS
    token = create_access_token(telegram_id, is_admin=is_admin)

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )
