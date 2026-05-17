"""
app/api/v1/endpoints/users.py
─────────────────────────────────────────────────────────────────────────────
User-facing profile, referral, and withdrawal endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import User, WithdrawRequest, WithdrawStatus
from app.schemas.schemas import (
    UserOut, UserUpdate,
    WithdrawCreate, WithdrawOut,
    ReferralStats, LeaderboardEntry,
    MessageResponse,
)
from config import settings

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut, summary="Get my profile")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(select(User).where(User.telegram_id == current_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserOut, summary="Update profile (wallet address)")
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(select(User).where(User.telegram_id == current_user_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.wallet_address is not None:
        user.wallet_address = body.wallet_address
    return user


@router.get("/me/referrals", response_model=ReferralStats, summary="My referral stats")
async def get_referrals(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Return referral link, total direct referrals, and commission earned."""
    result = await db.execute(select(User).where(User.telegram_id == current_user_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # All direct referrals
    ref_result = await db.execute(
        select(User).where(User.referred_by == current_user_id)
    )
    referred_users = ref_result.scalars().all()

    # Commission = sum of each referral's total_earned × level-1 rate
    rate = settings.REFERRAL_COMMISSION_RATES[0] if settings.REFERRAL_COMMISSION_RATES else 0
    total_commission = sum(u.total_earned * rate for u in referred_users)

    referral_link = f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}"

    return ReferralStats(
        referral_link=referral_link,
        total_referrals=len(referred_users),
        total_commission=total_commission,
        referrals=[UserOut.model_validate(u) for u in referred_users],
    )


@router.post("/me/withdraw", response_model=WithdrawOut, summary="Request a withdrawal")
async def request_withdrawal(
    body: WithdrawCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Submit a withdrawal request.
    - Amount must meet the minimum threshold.
    - Balance is deducted immediately (refunded if admin rejects).
    """
    result = await db.execute(select(User).where(User.telegram_id == current_user_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.amount < settings.MIN_WITHDRAW_AMOUNT:
        raise HTTPException(
            status_code=422,
            detail=f"Minimum withdrawal is {settings.MIN_WITHDRAW_AMOUNT} {settings.COIN_SYMBOL}",
        )

    if user.balance < body.amount:
        raise HTTPException(status_code=422, detail="Insufficient balance")

    # Deduct immediately; refund on rejection via admin
    user.balance -= body.amount

    req = WithdrawRequest(
        user_id=current_user_id,
        amount=body.amount,
        wallet_address=body.wallet_address or user.wallet_address,
        status=WithdrawStatus.PENDING,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


@router.get("/me/withdrawals", response_model=list[WithdrawOut], summary="My withdrawal history")
async def my_withdrawals(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WithdrawRequest)
        .where(WithdrawRequest.user_id == current_user_id)
        .order_by(WithdrawRequest.created_at.desc())
    )
    return result.scalars().all()


@router.get("/leaderboard", response_model=list[LeaderboardEntry], summary="Top earners")
async def leaderboard(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),   # Requires login
):
    result = await db.execute(
        select(User)
        .where(User.is_banned == False)
        .order_by(desc(User.total_earned))
        .limit(limit)
    )
    users = result.scalars().all()
    return [
        LeaderboardEntry(
            rank=i + 1,
            telegram_id=u.telegram_id,
            first_name=u.first_name,
            username=u.username,
            total_earned=u.total_earned,
        )
        for i, u in enumerate(users)
    ]
