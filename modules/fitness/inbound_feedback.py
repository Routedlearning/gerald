#!/usr/bin/env python3
"""Fast inbound Telegram feedback handler for Gerald Fitness module.

Local test server only:
  - binds 127.0.0.1:8080
  - accepts Telegram-style updates at /telegram/feedback
  - routes simple text logs through feedback_parser -> storage.save
  - no LLM, no Hermes agent loop
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn


# fitness module directory on sys.path so imports work when run from scripts/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feedback_parser import parse as parse_feedback  # noqa: E402
from storage import load, save  # noqa: E402


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip(), 10)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


ALLOWED_CHAT_ID = _env_int("GERALD_ALLOWED_CHAT_ID", 7435551643)
MAX_MESSAGE_LENGTH = _env_int("GERALD_MAX_MESSAGE_LENGTH", 2000)
DEBUG_TIMING = os.environ.get("GERALD_DEBUG_TIMING", "0") == "1"
PORT = _env_int("GERALD_PORT", 8080)
HOST = "127.0.0.1"

MODULE_DIR = Path(__file__).resolve().parent
HISTORY_PATH = MODULE_DIR / "workout_history.json"
_BACKUP_DIR = MODULE_DIR / "backups"
_LOCK_PATH = _BACKUP_DIR / ".inbound_feedback.lock"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class _FileLock:
    def __init__(self, path: Path):
        self._path = path
        self._fd = None

    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self._path), os.O_CREAT | os.O_RDWR)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._fd is not None:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
        finally:
            self._fd = None


class FeedbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/telegram/feedback":
            self._respond(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._respond(400, {"error": "bad request"})
            return

        message = body.get("message") or {}
        text = message.get("text")
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if not text or not isinstance(text, str):
            self._respond(400, {"error": "missing message text"})
            return

        if chat_id != ALLOWED_CHAT_ID:
            self._respond(401, {"error": "not allowed"})
            return

        if len(text) > MAX_MESSAGE_LENGTH:
            self._respond(413, {"error": "message too long"})
            return

        total_start = time.perf_counter()
        try:
            parse_start = time.perf_counter()
            entry = parse_feedback(text)
            parse_ms = (time.perf_counter() - parse_start) * 1000

            with _FileLock(_LOCK_PATH):
                write_start = time.perf_counter()
                state = load()
                fl = state.get("feedback_log", [])

                # dedup against last normalized entry only
                if fl and fl[-1].get("normalized") == entry.normalized:
                    response_payload = {
                        "ok": True,
                        "reply": "Duplicate entry skipped",
                    }
                    if DEBUG_TIMING:
                        total_ms = (time.perf_counter() - total_start) * 1000
                        response_payload.update({
                            "duplicate": True,
                            "parse_ms": f"{parse_ms:.1f}",
                            "total_ms": f"{total_ms:.1f}",
                        })
                    self._respond(200, response_payload)
                    return

                fl.append({
                    "entry_id": entry.entry_id,
                    "received_at": entry.received_at,
                    "type": entry.type,
                    "normalized": entry.normalized,
                    "data": entry.data,
                })
                state["feedback_log"] = fl
                save(state)
                write_ms = (time.perf_counter() - write_start) * 1000

            total_ms = (time.perf_counter() - total_start) * 1000

            response = {"ok": True}
            if DEBUG_TIMING:
                response.update({
                    "reply": (
                        f"Logged ({entry.type}, id={entry.entry_id})\n"
                        f"Parse: {parse_ms:.1f} ms\n"
                        f"Write: {write_ms:.1f} ms\n"
                        f"Total: {total_ms:.1f} ms"
                    ),
                    "parse_ms": f"{parse_ms:.1f}",
                    "write_ms": f"{write_ms:.1f}",
                    "total_ms": f"{total_ms:.1f}",
                })
            else:
                response["reply"] = f"Logged ({entry.type}, id={entry.entry_id})"

            self._respond(200, response)
        except Exception:
            total_ms = (time.perf_counter() - total_start) * 1000
            self._respond(500, {
                "ok": False,
                "error": "server error",
                "total_ms": f"{total_ms:.1f}" if DEBUG_TIMING else None,
            })

    def _respond(self, code, payload):
        payload_bytes = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload_bytes)))
        self.end_headers()
        self.wfile.write(payload_bytes)

    def log_message(self, format, *args):
        sys.stderr.write(
            "%s - - [%s] %s\n"
            % (self.client_address[0], self.log_date_time_string(), format % args)
        )


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    server = ThreadedHTTPServer((HOST, PORT), FeedbackHandler)
    sys.stderr.write(f"Listening on {HOST}:{PORT}/telegram/feedback\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("Shutting down.\n")
        server.server_close()


if __name__ == "__main__":
    main()
