"""
app/models/models.py - All ORM models for CybEarn.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────────

class TaskType(str, enum.Enum):
    SOCIAL = "Social"      # Follow / Like / Share
    AD = "Ad"              # Watch a Montage ad
    CUSTOM = "Custom"      # Any other action


class SubmissionStatus(str, enum.Enum):
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class WithdrawStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    telegram_id   = Column(BigInteger, primary_key=True, index=True)
    username      = Column(String(64), nullable=True)
    first_name    = Column(String(128), nullable=False)
    photo_url     = Column(String(512), nullable=True)
    balance       = Column(Float, default=0.0, nullable=False)
    total_earned  = Column(Float, default=0.0, nullable=False)
    is_banned     = Column(Boolean, default=False, nullable=False)
    wallet_address = Column(String(256), nullable=True)

    # Referral
    referred_by   = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    referral_code = Column(String(32), unique=True, nullable=False)   # e.g. "uid_<telegram_id>"

    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    task_statuses    = relationship("UserTaskStatus", back_populates="user", lazy="selectin")
    withdraw_requests = relationship("WithdrawRequest", back_populates="user", lazy="selectin")
    referrals        = relationship(
        "User", foreign_keys=[referred_by],
        backref="referrer", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.telegram_id} name={self.first_name}>"


# ── Task ──────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    title         = Column(String(256), nullable=False)
    description   = Column(Text, nullable=True)
    reward_amount = Column(Float, nullable=False)
    task_url      = Column(String(512), nullable=True)
    task_type     = Column(SAEnum(TaskType), nullable=False, default=TaskType.CUSTOM)
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    submissions = relationship("UserTaskStatus", back_populates="task", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r}>"


# ── UserTaskStatus ────────────────────────────────────────────────────────────

class UserTaskStatus(Base):
    __tablename__ = "user_task_statuses"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    task_id         = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status          = Column(SAEnum(SubmissionStatus), default=SubmissionStatus.SUBMITTED)
    proof_text      = Column(Text, nullable=True)
    proof_photo_url = Column(String(512), nullable=True)
    reject_reason   = Column(Text, nullable=True)      # Admin fills on rejection
    submitted_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="task_statuses")
    task = relationship("Task", back_populates="submissions")

    def __repr__(self) -> str:
        return f"<UserTaskStatus user={self.user_id} task={self.task_id} status={self.status}>"


# ── WithdrawRequest ───────────────────────────────────────────────────────────

class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    amount         = Column(Float, nullable=False)
    status         = Column(SAEnum(WithdrawStatus), default=WithdrawStatus.PENDING)
    wallet_address = Column(String(256), nullable=False)
    reject_reason  = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at   = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="withdraw_requests")

    def __repr__(self) -> str:
        return f"<WithdrawRequest id={self.id} user={self.user_id} amount={self.amount}>"
