# NEXT_STEPS.md

Roadmap for Fitness Coach v2.x and beyond.

---

## Completed in this checkpoint

- Feedback-aware adaptation: `adaptation.evaluate_week()` now reads `feedback_log`
- Low-energy trend detection added alongside existing RPE deload rule

---

## Priority Order

### 1. Harden `load()` against malformed JSON
**Rationale:** `load()` currently reads JSON and trusts the schema version. A malformed or truncated file would crash at runtime rather than triggering the quarantine path. Adding decode + key checks to `load()` would catch this at read time.

### 2. Add a nightly integrity check (lightweight cron)
**Rationale:** A low-cost cron job that runs `storage.validate()` against the live file and alerts on failure gives early warning of disk corruption or permission issues without waiting for the 5 AM plan send to fail.

### 3. Handle v2 -> v3 state migration (`workouts` backlog + feedback fusion)
**Rationale:** As `feedback_log` grows, merging it back into `workouts` (or exposing it to the planner without rewriting history) will need a clear migration contract. Defining v3 shape now prevents another backward-compat patch later.

### 4. Telegram message handler that routes natural messages to the parser
**Rationale:** `feedback_parser` is tested and works, but there is no Telegram inbound handler yet. Users cannot actually send feedback from their phones — they can only use the CLI. The next session should add a message-receive hook that calls `feedback_parser.parse()` and persists via `storage.save()`.

---

## Starting point after this checkpoint

1. Harden `storage.load()` malformed-JSON handling
2. Nightly validation cron job
3. v2 -> v3 state migration contract
