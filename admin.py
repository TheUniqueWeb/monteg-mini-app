"""
app/api/v1/endpoints/admin.py
─────────────────────────────────────────────────────────────────────────────
Admin-only endpoints – ALL protected by `require_admin` dependency AND the
AdminGuardMiddleware layer. Double-layered security by design.

Routes:
  Tasks:
    POST   /admin/tasks             – Create a task
    DELETE /admin/tasks/{id}        – Delete a task
    PATCH  /admin/tasks/{id}        – Toggle active status

  Submissions:
    GET    /admin/submissions        – List pending submissions
    POST   /admin/submissions/{id}/review – Approve / Reject

  Withdrawals:
    GET    /admin/withdrawals        – List pending withdrawals
    POST   /admin/withdrawals/{id}/review – Approve / Reject

  Users:
    GET    /admin/users              – List all users
    POST   /admin/users/{id}/ban    – Ban / unban a user

  Broadcast:
    POST   /admin/broadcast          – Send Telegram message
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import (
    Task, User, UserTaskStatus, WithdrawRequest,
    SubmissionStatus, WithdrawStatus
)
from app.schemas.schemas import (
    TaskCreate, TaskOut,
    SubmissionOut, ReviewSubmission,
    WithdrawOut, ReviewWithdraw,
    UserOut, BroadcastRequest, BroadcastResult,
    MessageResponse,
)
from app.services import telegram_service
from config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


# ══════════════════════════════════════════════════════════════════════════════
#  TASK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/tasks", response_model=TaskOut, summary="Create a new task")
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    task = Task(**body.model_dump())
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", response_model=MessageResponse, summary="Delete a task")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task: Task | None = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    return MessageResponse(message=f"Task '{task.title}' deleted successfully.")


@router.patch("/tasks/{task_id}/toggle", response_model=TaskOut, summary="Toggle task active status")
async def toggle_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task: Task | None = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_active = not task.is_active
    return task


# ══════════════════════════════════════════════════════════════════════════════
#  SUBMISSION REVIEW
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/submissions",
    response_model=list[SubmissionOut],
    summary="List pending submissions",
)
async def list_pending_submissions(
    status: Optional[SubmissionStatus] = SubmissionStatus.SUBMITTED,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    """Defaults to SUBMITTED status; pass ?status=Approved to see approved ones."""
    result = await db.execute(
        select(UserTaskStatus)
        .where(UserTaskStatus.status == status)
        .order_by(UserTaskStatus.submitted_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/submissions/{submission_id}/review",
    response_model=SubmissionOut,
    summary="Approve or reject a submission",
)
async def review_submission(
    submission_id: int,
    body: ReviewSubmission,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    """
    Approve or reject a task submission.
    On approval: credits the reward_amount to the user's balance automatically.
    On rejection: stores the reject_reason and notifies the user.
    """
    # Fetch submission
    result = await db.execute(
        select(UserTaskStatus).where(UserTaskStatus.id == submission_id)
    )
    sub: UserTaskStatus | None = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.status not in (SubmissionStatus.SUBMITTED, SubmissionStatus.PENDING):
        raise HTTPException(status_code=409, detail="Submission already reviewed")

    # Fetch task for reward amount and title
    task_result = await db.execute(select(Task).where(Task.id == sub.task_id))
    task: Task = task_result.scalar_one()

    # Fetch user for balance update
    user_result = await db.execute(select(User).where(User.telegram_id == sub.user_id))
    user: User = user_result.scalar_one()

    sub.reviewed_at = datetime.now(timezone.utc)

    if body.approve:
        sub.status = SubmissionStatus.APPROVED
        # ── Credit balance ────────────────────────────────────────────────────
        user.balance     += task.reward_amount
        user.total_earned += task.reward_amount

        # Multi-level referral commission on task completion
        if user.referred_by and settings.REFERRAL_COMMISSION_RATES:
            ref_result = await db.execute(
                select(User).where(User.telegram_id == user.referred_by)
            )
            referrer: User | None = ref_result.scalar_one_or_none()
            if referrer:
                l1_bonus = task.reward_amount * settings.REFERRAL_COMMISSION_RATES[0]
                referrer.balance     += l1_bonus
                referrer.total_earned += l1_bonus

        await telegram_service.notify_task_approved(user.telegram_id, task.title, task.reward_amount)
    else:
        sub.status = SubmissionStatus.REJECTED
        sub.reject_reason = body.reject_reason
        await telegram_service.notify_task_rejected(
            user.telegram_id, task.title, body.reject_reason
        )

    await db.flush()
    await db.refresh(sub)
    return sub


# ══════════════════════════════════════════════════════════════════════════════
#  WITHDRAWAL MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/withdrawals", response_model=list[WithdrawOut], summary="List withdrawals")
async def list_withdrawals(
    status: WithdrawStatus = WithdrawStatus.PENDING,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    result = await db.execute(
        select(WithdrawRequest)
        .where(WithdrawRequest.status == status)
        .order_by(WithdrawRequest.created_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/withdrawals/{withdraw_id}/review",
    response_model=WithdrawOut,
    summary="Process a withdrawal request",
)
async def review_withdrawal(
    withdraw_id: int,
    body: ReviewWithdraw,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    result = await db.execute(
        select(WithdrawRequest).where(WithdrawRequest.id == withdraw_id)
    )
    req: WithdrawRequest | None = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if req.status != WithdrawStatus.PENDING:
        raise HTTPException(status_code=409, detail="Already processed")

    req.processed_at = datetime.now(timezone.utc)

    if body.approve:
        req.status = WithdrawStatus.APPROVED
    else:
        req.status = WithdrawStatus.REJECTED
        req.reject_reason = body.reject_reason
        # Refund balance on rejection
        user_result = await db.execute(
            select(User).where(User.telegram_id == req.user_id)
        )
        user: User = user_result.scalar_one()
        user.balance += req.amount

    await telegram_service.notify_withdraw_processed(
        req.user_id, req.amount, body.approve, body.reject_reason
    )
    return req


# ══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/users", response_model=list[UserOut], summary="List all users")
async def list_users(
    banned_only: bool = False,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    q = select(User)
    if banned_only:
        q = q.where(User.is_banned == True)
    result = await db.execute(q.order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users/{telegram_id}/ban", response_model=MessageResponse, summary="Ban or unban a user")
async def toggle_ban(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = not user.is_banned
    action = "banned" if user.is_banned else "unbanned"
    return MessageResponse(message=f"User {telegram_id} has been {action}.")


# ══════════════════════════════════════════════════════════════════════════════
#  BROADCAST / NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/broadcast", response_model=BroadcastResult, summary="Send broadcast message")
async def broadcast_message(
    body: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    """
    Send a Telegram message to:
    - A specific user if `target_telegram_id` is provided.
    - ALL non-banned users if `target_telegram_id` is None.
    """
    if body.target_telegram_id:
        # Single user
        ok = await telegram_service.send_message(
            body.target_telegram_id, body.message, parse_mode=body.parse_mode
        )
        return BroadcastResult(total=1, success=int(ok), failed=int(not ok))

    # All users
    user_result = await db.execute(
        select(User.telegram_id).where(User.is_banned == False)
    )
    ids = [row[0] for row in user_result.all()]
    success, failed = await telegram_service.broadcast(
        ids, body.message, parse_mode=body.parse_mode
    )
    return BroadcastResult(total=len(ids), success=success, failed=failed)
