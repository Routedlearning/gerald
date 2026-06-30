# CHANGELOG

## [0.2.0] — 2026-06-28

### Added
- Natural-language feedback parser (`feedback_parser.py`) — platform-agnostic, no I/O, no storage calls, no Telegram code
- CLI feedback interface: `--feedback` and `--feedback-summary`
- Schema v2: new `feedback_log` array in `workout_history.json`
- Automated SSL certificate monitoring for daily Telegram delivery via `ssl_checker.py`

### Changed
- Parser handles Done, Missed, Completed, RPE, Energy, Weight, BP, Sleep, Knee felt sore
- Missing fields stored as null; no guessing
- Mixed workout/biometric messages auto-classified as "mixed" type
- Updated ARCHITECTURE.md and PROJECT_STATUS.md through v2

### Fixed
- BP normalization: preserves `/` separator for `126/78` format
- Quarantine path: corrupt live file safely isolated before replacement
- v1 migration: automatic on save without data loss
- Dedup guard: skips repeated normalized entries

---

## [0.1.0] — 2026-06-28

### Added
- Cron job `02c87d1e02bf` — `0 5 * * 1-6`, Telegram chat 7435551643
- `cli.py` with `--today` and full-week modes
- Rule-based adaptation engine (`adaptation.py`) — missed sessions, RPE, 5k trends, weight stalls
- Macro engine (`nutrition.py`) — 2465 kcal, 220g protein capped, dynamic by weight
