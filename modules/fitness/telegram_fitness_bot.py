#!/usr/bin/env python3
"""Separate Telegram bot for fast fitness logging.

This bot never touches the existing Hermes Telegram gateway or cron.
It should only be deployed alongside modules/fitness/inbound_feedback.py.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder, MessageHandler, filters

ALLOWED_CHAT_ID_ENV = "GERALD_ALLOWED_CHAT_ID"
INBOUND_URL_ENV = "GERALD_INBOUND_URL"
TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
DEBUG_TIMING_ENV = "GERALD_DEBUG_TIMING"
DRY_RUN_ENV = "GERALD_DRY_RUN"

DEFAULT_INBOUND_URL = "http://127.0.0.1:8080/telegram/feedback"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value, 10)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    token: str
    allowed_chat_id: int
    inbound_url: str
    debug_timing: bool
    dry_run: bool


def load_settings() -> Settings:
    token = _env(TOKEN_ENV)
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    allowed_chat_id = _env_int(ALLOWED_CHAT_ID_ENV, 0)
    if not allowed_chat_id:
        raise RuntimeError("Missing GERALD_ALLOWED_CHAT_ID")

    return Settings(
        token=token,
        allowed_chat_id=allowed_chat_id,
        inbound_url=_env(INBOUND_URL_ENV, DEFAULT_INBOUND_URL) or DEFAULT_INBOUND_URL,
        debug_timing=_env(DEBUG_TIMING_ENV, "0") == "1",
        dry_run=_env(DRY_RUN_ENV, "0") == "1",
    )


def _safe_update_payload(update: Update) -> dict:
    try:
        return json.loads(update.to_json())
    except Exception:
        return {"message": {"text": "", "chat": {}}}


def forward_to_local_handler(update: Update, settings: Settings) -> str:
    """Return the exact reply text for the user."""
    payload = _safe_update_payload(update)

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            settings.inbound_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        with urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8")
            code = resp.code
        elapsed = (time.perf_counter() - t0) * 1000

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {}

        if code != 200:
            resp_text = "Server error"
        elif parsed.get("ok"):
            resp_text = parsed.get("reply") or "Logged"
            if settings.debug_timing:
                extra = []
                for key in ("parse_ms", "write_ms", "total_ms"):
                    value = parsed.get(key)
                    if value is not None:
                        extra.append(f"{key}={value} ms")
                if extra:
                    resp_text += "\n" + ", ".join(extra)
        else:
            resp_text = "Not logged"

        if settings.debug_timing:
            logging.info("inbound duration=%sms elapsed=%sms", code, round(elapsed, 1))
        return resp_text
    except HTTPError as exc:
        logging.warning("inbound_http_error status=%s", exc.code)
        return "Server error"
    except URLError as exc:
        logging.warning("inbound_url_error reason=%s", exc.reason)
        return "Network error"
    except Exception as exc:
        logging.warning("inbound_unexpected_error type=%s", type(exc).__name__)
        return "Server error"


async def handle_text(update: Update, settings: Settings) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    chat = update.effective_chat
    if chat is None or chat.id != settings.allowed_chat_id:
        logging.info(
            "ignored_chat chat_id=%s type=%s",
            chat.id if chat else None,
            getattr(chat, "type", None),
        )
        return

    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.PRIVATE}:
        return

    reply = forward_to_local_handler(update, settings)
    try:
        await message.reply_text(reply)
    except Exception:
        logging.debug("reply_send_failed")


def preflight_dry_run(settings: Settings) -> int:
    logging.info("offline dry_run enabled; skipping telegram bootstrap")
    masked = settings.token[:4] if len(settings.token) >= 4 else "****"
    logging.info(
        "settings token_prefix=%s... allowed_chat_id=%s inbound_url=%s debug_timing=%s",
        masked,
        settings.allowed_chat_id,
        settings.inbound_url,
        settings.debug_timing,
    )
    return 0


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    settings = load_settings()
    if settings.dry_run:
        return preflight_dry_run(settings)

    application = (
        ApplicationBuilder().token(settings.token).concurrent_updates(True).build()
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u: handle_text(u, settings))
    )
    application.run_polling()
    return 0


if __name__ == "__main__":
    sys.exit(main())
