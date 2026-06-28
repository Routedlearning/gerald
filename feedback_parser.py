"""
feedback_parser.py — Platform-agnostic message parser for fitness/biometric feedback.

Pure functions only. No file I/O, no storage calls, no logging, no Telegram code,
no LLM calls.  Testable from CLI or any future interface.

Input  : message (str)
Output : FeedbackEntry dataclass

Rules
-----
- Missing fields  → null (no guessing).
- Conflicting values within one message → last-write-wins.
- `type` inferred from presence of workout vs biometric signals.
- `ENTRY_ID`  : UTC ISO timestamp + 6-char alphabet suffix (collision-safe within 10 s).
- `normalized`: lowercased, punctuation→spaces, whitespace-collapsed.  Used for dedup.
"""

from __future__ import annotations

import re
import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Data class returned to callers
# ---------------------------------------------------------------------------

@dataclass
class FeedbackEntry:
    entry_id:   str
    received_at: str      # ISO-8601 UTC, e.g. "2026-06-29T08:14:00Z"
    type:        str      # "workout" | "biometric" | "mixed"
    normalized:  str      # dedup key
    data:        dict


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FILLER_WORDS = frozenset({
    "the", "a", "an", "is", "it", "i", "me", "my", "today", "now",
    "here", "this", "that", "was", "were", "just", "ok", "okay",
    "yes", "no", "not", "but", "and", "so", "then", "very", "really",
})


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s/]", " ", text)   # keep / for "126/78" blood-pressure format
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _blank_data() -> dict:
    return {
        "status":       None,   # "completed" | "missed" | null
        "rpe":          None,   # int 1-10 or null
        "energy":       None,   # int 1-5  or null
        "notes":        None,   # str ≤ 300 chars or null
        "weight_lbs":   None,   # float / int > 0 or null
        "sleep_hours":  None,   # float 0.1-48 or null
        "bp_systolic":  None,   # int 40-300 or null
        "bp_diastolic": None,   # int 20-200 or null
        "raw":          "",
    }


def _make_id(ts: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{ts}-{suffix}"


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse(message: str) -> FeedbackEntry:
    if not message or not message.strip():
        raise ValueError("Empty message")

    now_ts   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry_id = _make_id(now_ts)
    norm     = _normalize(message)

    fields = _extract_fields(message, norm)
    fields["raw"] = message

    entry_type = _infer_type(fields)

    return FeedbackEntry(
        entry_id   = entry_id,
        received_at = now_ts,
        type       = entry_type,
        normalized = norm,
        data       = fields,
    )


def _infer_type(data: dict) -> str:
    workout    = any(data.get(k) is not None for k in ("status", "rpe", "energy"))
    biometric = any(data.get(k) is not None for k in (
        "weight_lbs", "sleep_hours", "bp_systolic", "bp_diastolic",
    ))
    if workout and biometric:
        return "mixed"
    if workout:
        return "workout"
    if biometric:
        return "biometric"
    return "workout"   # bare "Done." is workout feedback


# ---------------------------------------------------------------------------
# Signal extraction — ordered by precedence; later signals overwrite earlier.
# Returns position-set of consumed characters so leftovers become notes.
# ---------------------------------------------------------------------------

def _extract_fields(raw: str, norm: str) -> dict:
    fields = _blank_data()
    consumed: set[int] = set()

    def _consume(m: Optional[re.Match]) -> None:
        if m is not None:
            for i in range(m.start(), m.end()):
                consumed.add(i)

    # --- status ----------------------------------------------------------
    if re.search(r"\b(miss(?:ed|ing)?|skipped|rest day|didn't|did not|no (?:workout|session|training))\b", norm):
        fields["status"] = "missed"
        _consume(re.search(r"\b(miss(?:ed|ing)?|skipped|rest day|didn't|did not|no (?:workout|session|training))\b", norm))
    m = re.search(r"\b(done|completed|finished|did it|knocked out|crushed|smashed)\b", norm)
    _consume(m)
    if m and fields.get("status") is None:
        fields["status"] = "completed"

    # --- RPE -------------------------------------------------------------
    m = re.search(r"\brpe[\s:]*([1-9]|10)\b", norm)
    _consume(m)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 10:
            fields["rpe"] = val

    # --- energy ----------------------------------------------------------
    m = re.search(r"\benergy[\s:/]*([1-5])\b", norm)
    _consume(m)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 5:
            fields["energy"] = val

    # --- weight ----------------------------------------------------------
    m = re.search(r"\b(?:weight|wt)[\s:]*(\d+\.?\d*)\b", norm)
    _consume(m)
    if m:
        try:
            v = float(m.group(1))
            if v > 0:
                fields["weight_lbs"] = v
        except ValueError:
            pass

    # --- sleep -----------------------------------------------------------
    m = re.search(
        r"\b(?:slept|sleep)[\s:]*(\d+(?:\.\d+)?)\s*h(?:\s*(\d{1,2})\s*m)?\b",
        norm,
    )
    _consume(m)
    if m:
        try:
            hrs  = float(m.group(1))
            mins = float(m.group(2)) if m.group(2) else 0.0
            total = hrs + mins / 60.0
            if 0.1 <= total <= 48:
                fields["sleep_hours"] = round(total, 2)
        except ValueError:
            pass

    # --- blood pressure --------------------------------------------------
    m = re.search(r"\bbp[\s:]*(\d{1,3})\s*/\s*(\d{1,3})\b", norm)
    _consume(m)
    if m:
        try:
            sys_v = int(m.group(1))
            dia_v = int(m.group(2))
            if 40 <= sys_v <= 300 and 20 <= dia_v <= 200:
                fields["bp_systolic"]  = sys_v
                fields["bp_diastolic"] = dia_v
        except ValueError:
            pass

    # --- leftover → notes ------------------------------------------------
    remaining = "".join(
        c for idx, c in enumerate(norm) if idx not in consumed
    ).strip()
    remaining = re.sub(r"\s+", " ", remaining).strip(".,;: ")

    if not remaining:
        return fields

    words = remaining.split()
    meaningful = [w for w in words if w.lower() not in _FILLER_WORDS]
    if not meaningful:
        return fields

    note_text = " ".join(meaningful)
    if len(note_text) > 300:
        note_text = note_text[:297].rsplit(" ", 1)[0] + "..."
    fields["notes"] = note_text

    return fields
