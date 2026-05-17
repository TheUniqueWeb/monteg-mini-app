"""
app/api/v1/endpoints/tasks.py
─────────────────────────────────────────────────────────────────────────────
User-facing task endpoints:
  GET  /tasks          – List all active tasks (with completion status)
  POST /tasks/submit   – Submit a task with proof
  GET  /tasks/my       – Get current user's submission history
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.models import Task, UserTaskStatus, SubmissionStatus
from app.schemas.schemas import TaskOut, SubmissionOut, SubmitTaskRequest
from config import settings

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskOut], summary="List all active tasks")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Return all active tasks. Frontend can cross-reference with /tasks/my."""
    result = await db.execute(
        select(Task).where(Task.is_active == True).order_by(Task.created_at.desc())
    )
    return result.scalars().all()


@router.post("/submit", response_model=SubmissionOut, summary="Submit proof for a task")
async def submit_task(
    body: SubmitTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Submit a task.

    Rules:
    - Task must exist and be active.
    - User cannot resubmit a task that is Pending/Approved.
    - At least one proof field (text OR photo URL) must be provided.
    """
    # Validate at least one proof
    if not body.proof_text and not body.proof_photo_url:
        raise HTTPException(
            status_code=422,
            detail="At least one proof field (proof_text or proof_photo_url) is required.",
        )

    # Check task exists and is active
    task_result = await db.execute(
        select(Task).where(and_(Task.id == body.task_id, Task.is_active == True))
    )
    task: Task | None = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or inactive")

    # Check for existing non-rejected submission
    existing = await db.execute(
        select(UserTaskStatus).where(
            and_(
                UserTaskStatus.user_id == current_user_id,
                UserTaskStatus.task_id == body.task_id,
                UserTaskStatus.status.in_([
                    SubmissionStatus.SUBMITTED,
                    SubmissionStatus.PENDING,
                    SubmissionStatus.APPROVED,
                ]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You have already submitted this task. Wait for review.",
        )

    # Create submission
    submission = UserTaskStatus(
        user_id=current_user_id,
        task_id=body.task_id,
        status=SubmissionStatus.SUBMITTED,
        proof_text=body.proof_text,
        proof_photo_url=body.proof_photo_url,
    )
    db.add(submission)
    await db.flush()
    await db.refresh(submission)
    return submission


@router.get("/my", response_model=list[SubmissionOut], summary="My submission history")
async def my_submissions(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Return all submissions for the authenticated user, newest first."""
    result = await db.execute(
        select(UserTaskStatus)
        .where(UserTaskStatus.user_id == current_user_id)
        .order_by(UserTaskStatus.submitted_at.desc())
    )
    return result.scalars().all()
