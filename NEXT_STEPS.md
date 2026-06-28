# NEXT_STEPS.md

Roadmap for Fitness Coach v2.x and beyond. No implementation has started on any of these items.

---

## Priority Order

### 1. Feed `feedback_log` into the adaptation engine
**Rationale:** Right now `adaptation.evaluate_week()` reads only from the `workouts` list (which is still empty). Every RPE, miss, energy, and weight entry sits in `feedback_log` but never influences volume, deload, or interval decisions. Until this is wired, the "plan → execute → log → adapt" loop is broken. This is the single highest-value item because it closes the loop that the entire feedback system was built to support.

### 2. Telegram message handler that routes natural messages to the parser
**Rationale:** `feedback_parser` is tested and works, but there is no Telegram inbound handler yet. Users cannot actually send feedback from their phones — they can only use the CLI. The next session should add a message-receive hook that calls `feedback_parser.parse()` and persists via `storage.save()`.

### 3. Handle the v2 -> v3 state migration (`workouts` backlog + feedback fusion)
**Rationale:** As `feedback_log` grows, merging it back into `workouts` (or exposing it to the planner without rewriting history) will need a clear migration contract. Defining v3 shape now prevents another backward-compat patch later.

### 4. Add a nightly integrity check (lightweight cron)
**Rationale:** A low-cost cron job that runs `storage.validate()` against the live file and alerts on failure gives early warning of disk corruption or permission issues without waiting for the 5 AM plan send to fail.

### 5. Harden `storage.py` against poisoned JSON (load-time validation)
**Rationale:** `load()` currently reads JSON and trusts the schema version. A malformed or truncated file would crash at runtime rather than triggering the quarantine path. Adding decode + key checks to `load()` would catch this at read time.

---

## Stopping / Starting Points

**Stopping point for this session:** Schema v2 migration, feedback parser, and CLI interface are written, tested, and documented. The system is at a clean checkpoint where the next operator can pick up with item #1 above without ambiguity.

**Starting point for next session:** Item #1 — wire `feedback_log` into `adaptation.evaluate_week()`. Begin by reading the current `feedback_log` alongside `workouts` in `evaluate_week()`, then extend the rule engine to consider average RPE and miss rate from the new array. That single change makes the feedback system functional rather than archival.
