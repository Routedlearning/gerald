import json
import os
import tempfile
from datetime import datetime

HISTORY_PATH = "/root/projects/fitness-coach/workout_history.json"
BACKUP_DIR   = "/root/projects/fitness-coach/backups"
MAX_BACKUPS  = 30


def _ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)


def _default_state():
    return {
        "schema_version": 2,
        "baseline": {
            "weight_lbs": 290,
            "five_k_time": "40:00",
            "max_session_minutes": 60,
            "equipment": ["full gym", "pull-up bar", "treadmill"],
            "injuries": [],
            "goal_murph_prescribed_date": "2027-05-31",
        },
        "weekly_macros": {
            "calories": 2465,
            "protein_g": 220,
            "fat_g": 101,
            "carb_g": 167,
        },
        "week_start": None,
        "workouts": [],
        "missed_streak": 0,
        "last_5k_time": "40:00",
        "last_weight": 290,
        "last_checkin": None,
        "feedback_log": [],
    }


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def _migrate_v1_to_v2(state: dict) -> None:
    """Mutate a v1 state object in-place so it passes validate() for v2.

    - Bump schema_version.
    - Add feedback_log if missing.
    - Split legacy string `bp` in last_checkin → bp_systolic/bp_diastolic.
    - Rename legacy `notes` in last_checkin → last_checkin_notes.
    """
    if state.get("schema_version") == 2:
        return

    state["schema_version"] = 2

    state.setdefault("feedback_log", [])

    lc = state.get("last_checkin")
    if isinstance(lc, dict):
        # Legacy string-format bp → separate fields
        bp_str = lc.pop("bp", None)
        if isinstance(bp_str, str) and "/" in bp_str:
            parts = bp_str.split("/", 1)
            try:
                state["last_checkin"]["bp_systolic"]  = int(parts[0])
                state["last_checkin"]["bp_diastolic"] = int(parts[1])
            except (ValueError, IndexError):
                state["last_checkin"]["bp_systolic"]  = None
                state["last_checkin"]["bp_diastolic"] = None
        elif bp_str is not None:
            # Already split somehow — leave as-is
            state["last_checkin"]["bp"] = bp_str

        # Rename legacy notes key
        if "notes" in lc and "last_checkin_notes" not in lc:
            state["last_checkin"]["last_checkin_notes"] = lc.pop("notes")

    return


# ---------------------------------------------------------------------------
# Backup rotation
# ---------------------------------------------------------------------------

def _rotate_backups():
    if not os.path.isdir(BACKUP_DIR):
        return
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if (
            f.startswith("workout_history_") and f.endswith(".json")
        )],
        reverse=True,
    )
    for old in backups[MAX_BACKUPS:]:
        os.remove(os.path.join(BACKUP_DIR, old))


# ---------------------------------------------------------------------------
# Validation — accepts v1 (via migration) and clean v2 states
# ---------------------------------------------------------------------------

def validate(state):
    if not isinstance(state, dict):
        raise ValueError("State must be a JSON object")

    required = [
        "schema_version", "baseline", "weekly_macros", "workouts",
        "missed_streak",
    ]
    for key in required:
        if key not in state:
            raise ValueError(f"Missing required key: {key}")

    if not isinstance(state["workouts"], list):
        raise ValueError("workouts must be a list")

    sv = state.get("schema_version")
    if sv not in (1, 2):
        raise ValueError(f"schema_version must be 1 or 2, got {sv!r}")

    macros = state["weekly_macros"]
    for k in ("calories", "protein_g", "fat_g", "carb_g"):
        if k not in macros or not isinstance(macros[k], (int, float)):
            raise ValueError(f"Invalid macro value: {k}")

    # Semantic checks
    if "last_weight" in state and state["last_weight"] is not None:
        if not isinstance(state["last_weight"], (int, float)) or state["last_weight"] <= 0:
            raise ValueError("last_weight must be a positive number")

    if "missed_streak" in state:
        if not isinstance(state["missed_streak"], int) or state["missed_streak"] < 0:
            raise ValueError("missed_streak must be a nonnegative integer")

    if "last_5k_time" in state and state["last_5k_time"] is not None:
        if not isinstance(state["last_5k_time"], str):
            raise ValueError("last_5k_time must be a string")

    # --- feedback_log validation (v2) --------------------------------
    fl = state.get("feedback_log")
    if fl is not None:
        if not isinstance(fl, list):
            raise ValueError("feedback_log must be a a list or absent")
        for i, entry in enumerate(fl):
            _validate_feedback_entry(entry, index=i)

    # --- last_checkin validation -------------------------------------
    lc = state.get("last_checkin")
    if isinstance(lc, dict):
        _validate_last_checkin(lc)

    return True


def _validate_feedback_entry(entry: dict, index: int) -> None:
    prefix = f"feedback_log[{index}]"

    if not isinstance(entry, dict):
        raise ValueError(f"{prefix}: entry must be a dict")

    for key in ("entry_id", "received_at", "type", "normalized", "data"):
        if key not in entry:
            raise ValueError(f"{prefix}: missing key {key}")

    if entry["type"] not in ("workout", "biometric", "mixed"):
        raise ValueError(f"{prefix}: type must be workout|biometric|mixed")

    d = entry.get("data")
    if not isinstance(d, dict):
        raise ValueError(f"{prefix}: data must be a dict")

    if d.get("status") not in (None, "completed", "missed"):
        raise ValueError(f"{prefix}: status must be completed|missed|null")

    if d.get("rpe") is not None:
        if not isinstance(d["rpe"], int) or not (1 <= d["rpe"] <= 10):
            raise ValueError(f"{prefix}: rpe must be int 1-10")

    if d.get("energy") is not None:
        if not isinstance(d["energy"], int) or not (1 <= d["energy"] <= 5):
            raise ValueError(f"{prefix}: energy must be int 1-5")

    if d.get("notes") is not None:
        if not isinstance(d["notes"], str) or len(d["notes"]) > 300:
            raise ValueError(f"{prefix}: notes must be str ≤300 chars")

    if d.get("weight_lbs") is not None:
        if not isinstance(d["weight_lbs"], (int, float)) or d["weight_lbs"] <= 0:
            raise ValueError(f"{prefix}: weight_lbs must be positive number")

    if d.get("sleep_hours") is not None:
        if not isinstance(d["sleep_hours"], (int, float)) or not (0.1 <= d["sleep_hours"] <= 48):
            raise ValueError(f"{prefix}: sleep_hours must float 0.1-48")

    if d.get("bp_systolic") is not None:
        if not isinstance(d["bp_systolic"], int) or not (40 <= d["bp_systolic"] <= 300):
            raise ValueError(f"{prefix}: bp_systolic must be int 40-300")

    if d.get("bp_diastolic") is not None:
        if not isinstance(d["bp_diastolic"], int) or not (20 <= d["bp_diastolic"] <= 200):
            raise ValueError(f"{prefix}: bp_diastolic must be int 20-200")


def _validate_last_checkin(lc: dict) -> None:
    if lc is None:
        return

    # Old (v1) string bp still acceptable; v2 writes use numeric fields.
    if "bp" in lc:
        val = lc["bp"]
        if not isinstance(val, str):
            raise ValueError("last_checkin.bp must be string (legacy) or absent")

    if "bp_systolic" in lc and lc["bp_systolic"] is not None:
        if not isinstance(lc["bp_systolic"], int) or not (40 <= lc["bp_systolic"] <= 300):
            raise ValueError("last_checkin.bp_systolic must be int 40-300")

    if "bp_diastolic" in lc and lc["bp_diastolic"] is not None:
        if not isinstance(lc["bp_diastolic"], int) or not (20 <= lc["bp_diastolic"] <= 200):
            raise ValueError("last_checkin.bp_diastolic must be int 20-200")

    if "weight_lbs" in lc and lc["weight_lbs"] is not None:
        if not isinstance(lc["weight_lbs"], (int, float)) or lc["weight_lbs"] <= 0:
            raise ValueError("last_checkin.weight_lbs must be positive number")

    if "sleep_hours" in lc and lc["sleep_hours"] is not None:
        if not isinstance(lc["sleep_hours"], (int, float)) or not (0.1 <= lc["sleep_hours"] <= 48):
            raise ValueError("last_checkin.sleep_hours must float 0.1-48")


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load():
    if not os.path.exists(HISTORY_PATH):
        return _default_state()

    with open(HISTORY_PATH, "r") as f:
        state = json.load(f)

    sv = state.get("schema_version", 1)
    if sv == 1:
        _migrate_v1_to_v2(state)

    return state


def save(state):
    _ensure_dirs()
    validate(state)

    # --- migrate pre-save so the file on disk is always v2 ------------
    sv = state.get("schema_version", 1)
    if sv == 1:
        _migrate_v1_to_v2(state)
    # If schema_version was absent entirely after migration, force 2
    state.setdefault("schema_version", 2)

    # Validate existing file BEFORE backup
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r") as f:
                existing = json.load(f)
            _migrate_v1_to_v2(existing)
            validate(existing)
        except Exception as exc:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            quarantine_path = os.path.join(
                BACKUP_DIR, f"workout_history_quarantine_{ts}.json"
            )
            os.makedirs(BACKUP_DIR, exist_ok=True)
            with open(HISTORY_PATH, "rb") as src, open(quarantine_path, "wb") as dst:
                dst.write(src.read())
            os.chmod(quarantine_path, 0o600)
            raise RuntimeError(
                f"Existing data is invalid — quarantined to {quarantine_path}. "
                f"Original error: {exc}"
            )

    # Backup existing live file
    if os.path.exists(HISTORY_PATH):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"workout_history_{ts}.json")
            with open(HISTORY_PATH, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())
            os.chmod(backup_path, 0o600)
            _rotate_backups()
        except Exception as exc:
            raise RuntimeError(
                f"Backup failed — live file untouched. Error: {exc}"
            )

    # Atomic write via temp file in same directory
    dir_name = os.path.dirname(HISTORY_PATH)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, HISTORY_PATH)
        os.chmod(HISTORY_PATH, 0o600)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
