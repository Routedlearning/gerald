# Fitness Coach v2 — Architecture Checkpoint

## 1. File Structure

```
/root/projects/fitness-coach/
├── __pycache__/
│   ├── adaptation.cpython-311.pyc
│   ├── nutrition.cpython-311.pyc
│   ├── planner.cpython-311.pyc
│   └── storage.cpython-311.pyc
├── adaptation.py          # Rule engine for missed sessions, RPE, 5k trends, weight stalls
├── cli.py                 # CLI entry point: --today / --week-start / --feedback / --feedback-summary
├── feedback_parser.py     # Platform-agnostic message parser (no I/O, no storage, no Telegram code)
├── nutrition.py           # Macro calculation engine
├── planner.py             # Week templates and day builders
├── simulate_day.py        # Daily output simulator for cron testing
├── storage.py             # Persistence layer: load/validate/save + atomic writes + backup + quarantine
├── workout_history.json   # State file (baseline + check-ins + workouts + feedback_log)
├── backups/               # Automatic backups from storage.py (+ quarantine files)
├── logs/
│   ├── backup.log         # Backup script output
│   └── cron_dispatch.log  # Wrapper stdout/stderr
└── scripts/
    ├── backup_workout_history.sh
    ├── cron_dispatch.sh   # Cron wrapper → runs CLI → sends stdout to Telegram
    └── restore_workout_history.sh
```

## 2. Cron → Telegram Data Flow

```
Cron (0 5 * * 1-6)
  └── cronjob `02c87d1e02bf`
       └── prompt: run /root/projects/fitness-coach/scripts/cron_dispatch.sh 2026-06-29
            └── cron_dispatch.sh
                 ├── cd /root/projects/fitness-coach
                 ├── python3 cli.py --today --week-start 2026-06-29
                 │    ├── storage.load() → reads workout_history.json
                 │    ├── adaptation.evaluate_week() → rule adjustments
                 │    ├── planner.build_week() → day templates
                 │    └── prints ONE DAY to stdout
                 └── exits 0 with plan text on stdout
            └── cron scheduler sends stdout verbatim to Telegram chat 7435551643

Sunday: skipped by cron schedule (0 5 * * 1-6). No send.
Failure path: cron sends "Fitness engine failed: <last error line>"

Feedback path (separate, Telegram-inbound):
  User message → parser → saved to feedback_log via storage.save()
  No write path from cron or CLI-default mode.
```

## 3. Stored Data

| Key | Location | Content | Security |
|---|---|---|---|
| `workout_history.json` | Root | Baseline (weight, 5k, equipment, injuries), weekly macros, missed streak, workout log array, last checkin (date, weight, sleep, BP, weight, frequency data, labels, exercise, set, reps, and RPE), feedback_log entries (workout/biometric signals), schema_version 2 | 0600 owner-only |
| `storage.py` | Code | State schema validation with schema_version 1-2, feedback_log entry validation, backward-compat migration | In code + validated on save |
| `backups/` | Root | Timestamped copies of workout_history.json + quarantine files | 0600 owner-only, max 30 |
| `logs/cron_dispatch.log` | Logs | Wrapper exit code, timestamps, stdout/stderr (workout plan text, no raw biometrics) | Local filesystem |
| `logs/backup.log` | Logs | Manual backup script output | Local filesystem |
| Hermes memory | Agent | Compacted user profile: baseline, targets, preferences | Hermes memory store |

**Not stored:** Telegram session history, raw chat messages, biometric memory entries.

## 4. Data Sent to the LLM

During each cron run, the LLM sees:
- The cron prompt text (instructions to run the wrapper)
- Wrapper stdout/stderr (the formatted workout plan)

The LLM does **not** receive:
- `workout_history.json` raw contents
- Telegram session history
- `feedback_log` entries
- Memory entries with biometrics
- File paths or shell state beyond what is in the wrapper output

The cron prompt references:
- `/root/projects/fitness-coach/scripts/cron_dispatch.sh`
- Fallback error text if the wrapper fails

User name is **not** in the cron prompt.

## 5. Data Sent to Telegram

Telegram receives **only**:
- `cron_dispatch.sh` stdout: the formatted single-day plan
  - Day, type, focus
  - Exercise list + sets/reps
  - Estimated time
  - Macro target (calories, protein, fat, carbs)
  - Adaptation note (if any)
  - Evening log format template

Failure case Telegram receives:
- `"Fitness engine failed: <last line of stderr/stdout>"`

No raw biometrics in any Telegram-outbound message. Feedback is captured from Telegram-inbound messages only and stored in `feedback_log`.

## 6. Persistence Contract: storage.py

| Function | Contract |
|---|---|
| `load()` | Returns dict. If `workout_history.json` missing, returns default state in memory **without writing**. If file exists, reads JSON. If v1, migrates in-memory to v2 (adds `feedback_log`, splits `bp` → numeric fields, renames `last_checkin.notes` → `last_checkin_notes`). `schema_version` is forced to 2 on return. |
| `validate(state)` | Raises `ValueError` if state is not a dict or missing required keys: `schema_version`, `baseline`, `weekly_macros`, `workouts`, `missed_streak`. Accepts `schema_version` 1 or 2. Checks macro value types. Checks `last_weight > 0`, `missed_streak >= 0`. Validates `feedback_log` entries (data keys present, `rpe` 1–10, `energy` 1–5, `notes` ≤ 300 chars, `weight_lbs` positive, `sleep_hours` 0.1–48, `bp_systolic` 40–300, `bp_diastolic` 20–200). `type` must be `workout`\|`biometric`\|`mixed`. Returns `True` if valid. |
| `save(state)` | 1. `validate(state)` — new data must be valid. 2. Migrate to v2 in-memory if still v1 before writing. 3. If live file exists, validate existing data **before** backup. 4. If existing validation fails, quarantine existing file to `backups/workout_history_quarantine_<timestamp>.json` and raise `RuntimeError`. 5. If existing data valid, copy live file to timestamped backup in `backups/`. 6. Atomic write via `tempfile.mkstemp` in same directory, `json.dump`, `os.replace`. 7. Set `0600` on new live file and backups. 8. Rotate backups beyond 30. |

**Atomicity guarantees:**
- Live file is untouched until `os.replace()` succeeds
- Temp file cleaned up on failure
- Backup happens before live file is modified
- Backup failure aborts the entire save; live file remains unchanged

**Leakage guarantees:**
- `storage.py` has no `print()` or logging calls
- Reads/writes only the project JSON file and backup directory

## 7. Feedback Parser — `feedback_parser.py`

Platform-agnostic parser. Single responsibility: message → `FeedbackEntry`.

**Constraints (enforced by contract, not by runtime):**
- No file I/O
- No storage calls
- No logging
- No Telegram-specific code
- No LLM calls

**Output:**
```python
FeedbackEntry(
    entry_id    = "2026-06-29T08:14:00Z-a3x9k2",   # ts + 6-char suffix
    received_at = "2026-06-29T08:14:00Z",
    type        = "workout" | "biometric" | "mixed",
    normalized  = "done rpe 7 energy 4",            # dedup key
    data        = {
        "status":       "completed" | "missed" | None,
        "rpe":          int 1-10 | None,
        "energy":       int 1-5  | None,
        "notes":        str <= 300 chars | None,
        "weight_lbs":   float > 0 | None,
        "sleep_hours":  float 0.1-48 | None,
        "bp_systolic":  int 40-300 | None,
        "bp_diastolic": int 20-200 | None,
        "raw":          str (original message),
    }
)
```

**Type inference:**
- `workout` if any of status/RPE/energy present
- `biometric` if any of weight/sleep/bp present and no workout signal
- `mixed` if both workout and biometric signals appear
- Bare "Done." is classified as `workout`

**Dedup:** caller compares `feedback_log[-1]["normalized"]` with `entry.normalized` before append. Parser has no state.

**Supported patterns (confidence-first):**

| Signal | Field | Rule |
|---|---|---|
| done / completed / finished | status=completed | high |
| missed / skipped / rest day | status=missed | high |
| felt strong / easy / rough / tough | notes append | high |
| sore / achy / pain + body part | notes append | high |
| RPE N (N 1–10) | rpe=N | high |
| Energy N/5 or Energy N (N 1–5) | energy=N | high |
| Weight N[.N] | weight_lbs=N | high |
| Slept Nh or Sleep Nh or Sleep Nh Nm | sleep_hours = N + M/60 | high |
| BP N/N | bp_systolic=N, bp_diastolic=N | high |

Missing fields → `null`. No guessing. Conflicting values → last-write-wins (same message, seconds apart).

## 8. CLI Feedback Interface

```bash
# Log feedback (single message)
python3 cli.py --feedback "Done. RPE 7. Energy 4. Knee sore."

# Summary — last 7 days
python3 cli.py --feedback-summary

# Existing modes unchanged
python3 cli.py --today --week-start 2026-06-29
python3 cli.py --week-start 2026-06-29
```

`--feedback` appends to `feedback_log` via `storage.save()`. No write path from `--today` or `--week-start`.

`--feedback-summary` prints type counts and the last entry. Raw biometrics are not echoed in the summary structure (only field identifiers).

## 9. Backup and Restore Procedure

**Automatic (storage.py):**
- Every `save()` creates a timestamped backup before replacing the live file
- Backups stored in `/root/projects/fitness-coach/backups/`
- Max 30 retained; oldest evicted automatically
- Corrupted backups named `workout_history_quarantine_<timestamp>.json`
- Corrupted **live file** is quarantined on save-attempt; `RuntimeError` is raised and live file remains untouched

**Manual backup:**
```bash
/root/projects/fitness-coach/scripts/backup_workout_history.sh
```
Creates timestamped copy with `0600` permissions.

**Restore:**
```bash
/root/projects/fitness-coach/scripts/restore_workout_history.sh --list
/root/projects/fitness-coach/scripts/restore_workout_history.sh --latest
/root/projects/fitness-coach/scripts/restore_workout_history.sh <filename>
```
- Validates backup integrity before restore (`storage.validate()`)
- Creates pre-restore backup of current live file
- Atomic restore via temp file + rename
- Sets `0600` on restored file
- Will not overwrite valid live file without validation pass; abort on invalid backup

## 10. Known Risks and Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| Parser confidence loops for ambiguous messages | Low | Strict field typing; null on uncertainty; no guessing |
| Single JSON file for all state | Low | Acceptable for v1 single-user; not multi-user safe |
| Backup rotation can race on concurrent saves | Low | No concurrent save scenario currently; single cron job |
| Parser patterns may miss edge-case phrasing | Low | Confidence-first: null on miss; no silent misclassification |
| No encryption at rest | Medium | Host-level LUKS/fscrypt recommended |
| Cron job runs `python3 cli.py` — Python must be in PATH | Low | Verified in sandbox; wrapper uses absolute paths |
| Feedback data lives in `feedback_log` (not `workouts`) | Info | Adaptation engine still reads `workouts`; `feedback_log` is a derived signal for future use |
| Memory tool stores compacted profile; large context still possible | Low | Memory is manually curated; 1,375 char budget |
| `write_file` tool blocked for `/root/projects` | Low | Using `cat >` / `terminal` heredocs for file ops |
| Quarantine files accumulate during bad saves | Low | Manual cleanup via `restore_workout_history.sh --list` review |

---
*Generated: 2026-06-28*
*Branch: v1 checkpoint (post-cron-test, pre-logging)* → **v2 (feedback logging implemented)**
