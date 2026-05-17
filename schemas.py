"""
app/schemas/schemas.py - Pydantic v2 request & response schemas.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.models.models import TaskType, SubmissionStatus, WithdrawStatus


# ══════════════════════════════════════════════════════════════════════════════
#  Auth
# ══════════════════════════════════════════════════════════════════════════════

class TelegramInitData(BaseModel):
    """Raw init-data string sent by the Telegram WebApp."""
    init_data: str = Field(..., description="Raw Telegram WebApp initData string")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ══════════════════════════════════════════════════════════════════════════════
#  User
# ══════════════════════════════════════════════════════════════════════════════

class UserOut(BaseModel):
    telegram_id:    int
    username:       Optional[str]
    first_name:     str
    photo_url:      Optional[str]
    balance:        float
    total_earned:   float
    is_banned:      bool
    wallet_address: Optional[str]
    referral_code:  str
    created_at:     datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    wallet_address: Optional[str] = Field(None, max_length=256)


class LeaderboardEntry(BaseModel):
    rank:        int
    telegram_id: int
    first_name:  str
    username:    Optional[str]
    total_earned: float

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  Task
# ══════════════════════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    title:         str = Field(..., max_length=256)
    description:   Optional[str] = None
    reward_amount: float = Field(..., gt=0)
    task_url:      Optional[str] = Field(None, max_length=512)
    task_type:     TaskType = TaskType.CUSTOM


class TaskOut(BaseModel):
    id:            int
    title:         str
    description:   Optional[str]
    reward_amount: float
    task_url:      Optional[str]
    task_type:     TaskType
    is_active:     bool
    created_at:    datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
#  Task Submission
# ══════════════════════════════════════════════════════════════════════════════

class SubmitTaskRequest(BaseModel):
    task_id:        int
    proof_text:     Optional[str] = Field(None, max_length=2000)
    proof_photo_url: Optional[str] = Field(None, max_length=512)

    @field_validator("proof_text", "proof_photo_url", mode="before")
    @classmethod
    def at_least_one_proof(cls, v, info):
        return v   # Cross-field validation done in the endpoint


class SubmissionOut(BaseModel):
    id:              int
    user_id:         int
    task_id:         int
    status:          SubmissionStatus
    proof_text:      Optional[str]
    proof_photo_url: Optional[str]
    reject_reason:   Optional[str]
    submitted_at:    datetime
    reviewed_at:     Optional[datetime]
    task:            Optional[TaskOut] = None

    model_config = {"from_attributes": True}


class ReviewSubmission(BaseModel):
    """Admin: approve or reject a submission."""
    approve:       bool
    reject_reason: Optional[str] = Field(None, max_length=500)


# ══════════════════════════════════════════════════════════════════════════════
#  Withdraw
# ══════════════════════════════════════════════════════════════════════════════

class WithdrawCreate(BaseModel):
    amount:         float = Field(..., gt=0)
    wallet_address: str   = Field(..., max_length=256)


class WithdrawOut(BaseModel):
    id:             int
    user_id:        int
    amount:         float
    status:         WithdrawStatus
    wallet_address: str
    reject_reason:  Optional[str]
    created_at:     datetime
    processed_at:   Optional[datetime]

    model_config = {"from_attributes": True}


class ReviewWithdraw(BaseModel):
    """Admin: approve or reject a withdrawal."""
    approve:       bool
    reject_reason: Optional[str] = Field(None, max_length=500)


# ══════════════════════════════════════════════════════════════════════════════
#  Notifications / Broadcast
# ══════════════════════════════════════════════════════════════════════════════

class BroadcastRequest(BaseModel):
    """Admin: send a message to one user or all users."""
    message:          str = Field(..., max_length=4096)
    target_telegram_id: Optional[int] = Field(
        None, description="If None, broadcasts to ALL users."
    )
    parse_mode: str = Field("HTML", pattern="^(HTML|Markdown|MarkdownV2)$")


class BroadcastResult(BaseModel):
    total:   int
    success: int
    failed:  int


# ══════════════════════════════════════════════════════════════════════════════
#  Referral
# ══════════════════════════════════════════════════════════════════════════════

class ReferralStats(BaseModel):
    referral_link:   str
    total_referrals: int
    total_commission: float
    referrals:       List[UserOut]


# ══════════════════════════════════════════════════════════════════════════════
#  Generic
# ══════════════════════════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str
    success: bool = True
