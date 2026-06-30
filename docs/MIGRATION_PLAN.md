# Gerald — Fitness Module Migration Plan

Goal: Relocate the working Fitness Coach module from `/root/projects/fitness-coach/` into `/root/projects/gerald/modules/fitness/` without disrupting cron, Telegram delivery, or data integrity.

## Current Source State

- Code root: `/root/projects/fitness-coach/`
- Python files: `adaptation.py`, `cli.py`, `feedback_parser.py`, `nutrition.py`, `planner.py`, `simulate_day.py`, `storage.py`
- Data: `workout_history.json`, `backups/`, `logs/`
- Scripts: `scripts/backup_workout_history.sh`, `scripts/cron_dispatch.sh`, `scripts/restore_workout_history.sh`
- Integration: Hermes cron job `02c87d1e02bf` → wrapper → Telegram chat `7435551643`
- Hardcoded paths in: `storage.py` (`HISTORY_PATH`, `BACKUP_DIR`), `cron_dispatch.sh`

## Migration Phases

### Phase 1 — Preparation
1. Audit absolute paths in all Python files and shell scripts.
2. Make `HISTORY_PATH` and `BACKUP_DIR` configurable via environment variable with existing defaults preserved.
3. Verify all external references (cron prompt, wrapper, Hermes memory) point to the source path.

### Phase 2 — Staging
1. Copy Python source to `/root/projects/gerald/modules/fitness/`.
2. Copy `scripts/` into the new module directory; update wrapper internal paths.
3. Move `backups/` and `logs/` to `/root/projects/gerald/modules/fitness/`.
4. Do **not** delete the original `/root/projects/fitness-coach/` yet.

### Phase 3 — Path Updates
1. Update `storage.py` defaults to new paths or keep defaults if env vars handle them.
2. Update `cron_dispatch.sh` to `cd` into the new module directory and invoke `cli.py` from the new path.
3. Update the Hermes cron job prompt to reference the new wrapper path.
4. Run `python3 cli.py --week-start 2026-06-29` from the new location to verify imports and data loading.

### Phase 4 — Verification
1. CLI contract: `--today`, `--week-start`, `--feedback`, `--feedback-summary`
2. Cron wrapper: manual run returns exit code 0 and correct stdout
3. Feedback loop: `--feedback "Done. RPE 7. Energy 4."` persists and appears in summary
4. Backup/restore: `scripts/backup_workout_history.sh` and `scripts/restore_workout_history.sh --latest`
5. Telegram delivery: dry-run or low-risk test message confirms wrapper output path is correct
6. Adaptation: feed test feedback and confirm `evaluate_week()` reads it

### Phase 5 — Cutover
1. Freeze fitness cron for one cycle to prevent race conditions.
2. Rename `/root/projects/fitness-coach/` to `/root/projects/fitness-coach.bak/`.
3. Update cron job reference permanently.
4. Run one full scheduling cycle.
5. Update `PROJECT_STATUS.md` and launch-week references.
6. Retain `.bak` for 48 hours, then delete only after successful delivery.

## Constraints and Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Absolute path breakage in wrapper or cron prompt | High | Environment-variable override in `storage.py`; single source of truth for paths |
| Permission drift during filesystem move | Medium | Verify `0600` on JSON and backups after each copy |
| Telegram delivery gap | Medium | Freeze one cron cycle; validate wrapper manually before resuming |
| Backup rotation inherits stale paths | Medium | Validate `backups/` directory exists at new path before first save |
| Rollback confusion | Low | Keep `.bak` until two successful deliveries confirmed |

## Rollback Procedure

If any verification step fails:
1. Revert Hermes cron prompt to `/root/projects/fitness-coach/scripts/cron_dispatch.sh`
2. Move data and code back from `.bak` to original location
3. Restore original `storage.py` path constants if env-var override was introduced
4. Re-run `--week-start` sanity check

## Approval Gate

No code relocation, path changes, or cron updates will proceed until this plan is explicitly approved.
