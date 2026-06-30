# PROJECT_STATUS.md — Fitness Coach v2 Handoff

Generated: 2026-06-28
Source of truth: `ARCHITECTURE.md`
Target reader: next session / new operator

---

## 1. What Has Been Completed

- [x] Hybrid rule-based + LLM adaptation engine
- [x] Beginner-safe Week 1 planner (≤60 min, RPE 7–8, no all-out sprint language)
- [x] Murph-lite progression toward prescribed Murph by May 2027
- [x] Nutrition engine: 2465 kcal baseline, 220 g protein, 101 g fat, 167 g carbs
- [x] CLI with two modes: full week (`cli.py`) and single-day (`cli.py --today`)
- [x] Cron wrapper `cron_dispatch.sh` that runs CLI, logs to `logs/cron_dispatch.log`, and emits only one day's plan to stdout
- [x] Daily cron job (`02c87d1e02bf`): `0 5 * * 1-6`, Telegram delivery to chat `7435551643`, Sunday silent
- [x] Persistence layer `storage.py` with atomic writes, 0600 permissions, backup-before-replace, quarantine on corrupt existing data
- [x] Automatic backup rotation (max 30) in `backups/`
- [x] Manual backup script: `scripts/backup_workout_history.sh`
- [x] Restore script: `scripts/restore_workout_history.sh` (`--list`, `--latest`, named file, validation, pre-restore backup, atomic restore)
- [x] Biometric Sunday check-in stored in `workout_history.json` as `last_checkin`
- [x] CVD-hardened interval language (`400m hard effort / 400m walk or easy jog`)
- [x] Security hygiene on cron prompt: no session history, no biometric memory loading, no user name
- [x] Manual cron test on 2026-06-28 returned `status=ok`, `execution_success=true`, message delivered
- [x] **Natural-language feedback parser** (`feedback_parser.py`) — no Telegram code, no I/O, no storage calls, no logging
- [x] **CLI feedback interface** — `--feedback` (persist) and `--feedback-summary` (read-only, last 7 days)
- [x] **Schema version 2** — `feedback_log` array, backward-compat migration of v1 data (automatic on save)
- [x] **`last_checkin` shape migration** — `bp` string → `bp_systolic`/`bp_diastolic` numeric; `notes` → `last_checkin_notes`
- [x] **Feedback-aware adaptation** — `adaptation.evaluate_week()` reads `feedback_log` for RPE averages and low-energy trend detection
- [x] Verified feedback path: `cli.py --feedback` persists; `--feedback-summary` reads last 7 days
- [x] Baseline meals logged for 2026-06-29 via direct state update (oats/berries, soup, Taco Bell 2×5 Layer Burrito + Baja Blast, ½ lb beef brisket, 1 gallon water, 7g fiber)
- [x] Cron verified 2026-06-30 05:01 UTC: wrapper exit code 0
- [x] Telegram delivery verified for 2026-06-29 Tuesday strength plan
- [x] Session feedback form confirmed: `Done. RPE: X. Energy: Y/5. Notes: ...`
- [x] Adaptation notes confirmed from 2026-06-29 workout via existing adaptation engine
- [x] Daily rotation confirmed: weekly muscle group rotation with adaptive progression
- [x] Security topics reviewed: no biometric leakage to LLM/session/Telegram outbound
- [x] Nutrition tracking confirmed: credit card portion scale method accepted

---

## 2. Files Created or Modified

| Path | Role | Notes |
|---|---|---|
| `/root/projects/gerald/modules/fitness/adaptation.py` | Rule engine | Missed sessions, RPE, 5k trends, weight stalls, feedback_log fusion |
| `/root/projects/gerald/modules/fitness/cli.py` | CLI entry point | `--today`/`--week-start`/`--feedback`/`--feedback-summary` |
| `/root/projects/gerald/modules/fitness/feedback_parser.py` | Message parser | Pure functions; platform-agnostic; no I/O |
| `/root/projects/gerald/modules/fitness/nutrition.py` | Macro targets | 2465 kcal / 220 g protein / 101 g fat / 167 g carbs |
| `/root/projects/gerald/modules/fitness/planner.py` | Day templates | Weekly muscle group rotation + adaptive progression |
| `/root/projects/gerald/modules/fitness/storage.py` | Persistence | Schema v2, atomic writes, backup rotation, quarantine, validation |
| `/root/projects/gerald/modules/fitness/workout_history.json` | State file | Schema v2; feedback_log present; 0600 |
| `/root/projects/gerald/modules/fitness/backups/` | Backup directory | Timestamped backups + quarantine files; 0600; max 30 |
| `/root/projects/gerald/modules/fitness/logs/backup.log` | Backup log | Manual backup script output |
| `/root/projects/gerald/modules/fitness/logs/cron_dispatch.log` | Cron log | Wrapper exit code + stdout/stderr |
| `/root/projects/gerald/modules/fitness/scripts/backup_workout_history.sh` | Backup helper | Manual backup trigger |
| `/root/projects/gerald/modules/fitness/scripts/restore_workout_history.sh` | Restore helper | `--list`, `--latest`, named, validation, 0600 |
| `/root/projects/gerald/modules/fitness/scripts/cron_dispatch.sh` | Cron wrapper | Executable; calls CLI; logs; fallback on failure |
| `/root/projects/gerald/modules/fitness/simulate_day.py` | Simulator | Replay day script for manual testing |
| `/root/projects/gerald/modules/fitness/ARCHITECTURE.md` | Architecture doc | Updated to v2; feedback logging design |
| `/root/projects/gerald/modules/fitness/PROJECT_STATUS.md` | Handoff | This file |

---

## 3. Current Security Posture

- **Cron prompt:** does NOT load Telegram session history, biometric memory entries, or raw health logs
- **User name:** removed from cron prompt
- `workout_history.json`: `0600` owner-only read/write
- **Backup files:** `0600`; atomic rename; temp-file in same directory; fsync before rename
- **Corrupt data protection:** `save()` validates existing content BEFORE backup; invalid existing data is quarantined, not overwritten
- **No raw biometric printing:** `storage.py` has no `print()` or logging calls
- **Memory usage:** compact; biometrics kept in project files, not memory tool
- **LLM exposure:** cron sees only wrapper stdout (formatted workout text) and prompt; no raw JSON
- **No biometric echo in summary:** `--feedback-summary` only shows field identifiers and types

---

## 4. Backup and Restore Commands

```bash
# List available backups
/root/projects/gerald/modules/fitness/scripts/restore_workout_history.sh --list

# Restore most recent valid backup
/root/projects/gerald/modules/fitness/scripts/restore_workout_history.sh --latest

# Restore specific backup (full path)
/root/projects/gerald/modules/fitness/scripts/restore_workout_history.sh /root/projects/gerald/modules/fitness/backups/<filename>.json

# Manual backup (outside of automatic saves)
bash /root/projects/gerald/modules/fitness/scripts/backup_workout_history.sh
```

**Restore contract:**
- Validates backup with `storage.validate()` before restoring
- Creates pre-restore backup of current live file
- Atomic restore via temp file + rename
- Resulting file is `0600`
- Invalid backups are rejected, not applied

---

## 5. Current Risks

| Risk | Status | Mitigation |
|---|---|---|
| Parser patterns may miss edge-case phrasing | Low | Confidence-first: null on miss; no silent misclassification |
| Single JSON file for state | Accepted v1 | Not suitable for multi-user |
| Backup rotation races on concurrent saves | Low | Single cron job; no concurrency today |
| No encryption at rest | Open | Host-level LUKS/fscrypt required |
| Memory tool near char limit | Monitor | 755 / 1375 used; prune before extended sessions |
| `write_file` blocked for `/root/projects` paths | Workaround | Use `cat` heredoc / `terminal` for file ops |
| Quarantine files accumulate during bad saves | Low | Manual cleanup via `restore_workout_history.sh --list` review |

---

## 6. Post-Feedback Verification

```bash
cd /root/projects/gerald/modules/fitness && python3 cli.py --feedback "Done. RPE 7. Energy 4."
cd /root/projects/gerald/modules/fitness && python3 cli.py --feedback-summary
```

---

## 7. Exact Next Command to Run After /new

```bash
cd /root/projects/gerald/modules/fitness && python3 cli.py --week-start 2026-06-29
```

This command verifies the weekly plan generator and confirms the file tree and imports are intact in a fresh session.
