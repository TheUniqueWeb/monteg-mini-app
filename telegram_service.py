"""
app/services/telegram_service.py
─────────────────────────────────────────────────────────────────────────────
All Telegram Bot API interactions: sending messages, broadcasts, etc.
Uses httpx for async HTTP calls (no blocking).
"""
import asyncio
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("cybearn.telegram")

# Base URL for Bot API calls
_API_BASE = f"{settings.TELEGRAM_API_URL}/bot{settings.BOT_TOKEN}"


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[dict] = None,
) -> bool:
    """
    Send a single message to a Telegram user.
    Returns True on success, False on any error.
    """
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(f"{_API_BASE}/sendMessage", json=payload)
            data = resp.json()
            if not data.get("ok"):
                logger.warning("Telegram sendMessage failed for %s: %s", chat_id, data)
                return False
            return True
        except Exception as exc:
            logger.error("Telegram sendMessage error for %s: %s", chat_id, exc)
            return False


async def broadcast(
    chat_ids: list[int],
    text: str,
    parse_mode: str = "HTML",
    delay_between: float = 0.05,   # Respect Telegram rate limits (30 msg/s)
) -> tuple[int, int]:
    """
    Send a message to multiple users.

    Args:
        chat_ids: List of Telegram user IDs.
        text: Message text.
        parse_mode: HTML, Markdown, or MarkdownV2.
        delay_between: Seconds to wait between each send.

    Returns:
        (success_count, failed_count)
    """
    success = 0
    failed = 0

    for chat_id in chat_ids:
        ok = await send_message(chat_id, text, parse_mode=parse_mode)
        if ok:
            success += 1
        else:
            failed += 1
        await asyncio.sleep(delay_between)

    logger.info(
        "Broadcast complete: %d success / %d failed out of %d total",
        success, failed, len(chat_ids)
    )
    return success, failed


async def notify_task_approved(user_id: int, task_title: str, reward: float) -> None:
    """DM the user when their task submission is approved."""
    text = (
        f"✅ <b>Task Approved!</b>\n\n"
        f"Your submission for <b>{task_title}</b> has been approved.\n"
        f"<b>{reward:,.1f} {settings.COIN_SYMBOL}</b> added to your balance!"
    )
    await send_message(user_id, text)


async def notify_task_rejected(
    user_id: int,
    task_title: str,
    reason: Optional[str],
) -> None:
    """DM the user when their task submission is rejected."""
    reason_text = f"\n\n<b>Reason:</b> {reason}" if reason else ""
    text = (
        f"❌ <b>Task Rejected</b>\n\n"
        f"Your submission for <b>{task_title}</b> was not approved.{reason_text}\n\n"
        f"You can resubmit with better proof."
    )
    await send_message(user_id, text)


async def notify_withdraw_processed(
    user_id: int,
    amount: float,
    approved: bool,
    reason: Optional[str] = None,
) -> None:
    """DM the user about their withdrawal status."""
    if approved:
        text = (
            f"💸 <b>Withdrawal Approved!</b>\n\n"
            f"Your withdrawal of <b>{amount:,.1f} {settings.COIN_SYMBOL}</b> "
            f"has been processed. Check your wallet!"
        )
    else:
        reason_text = f"\n\n<b>Reason:</b> {reason}" if reason else ""
        text = (
            f"🚫 <b>Withdrawal Rejected</b>\n\n"
            f"Your withdrawal of <b>{amount:,.1f} {settings.COIN_SYMBOL}</b> "
            f"was rejected.{reason_text}"
        )
    await send_message(user_id, text)
