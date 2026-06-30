# Gerald Platform Constitution

Purpose: Define the platform-wide, non-negotiable principles that govern every Gerald module regardless of domain.

---

## 1. Platform Purpose

Gerald is a modular personal-automation platform. Each module delivers a discrete domain service (fitness, career, health, home, research) through a common contract while remaining independently deployable.

## 2. Immutable Constraints

- Single-tenant by design; no multi-user coordination.
- Every module must be runnable from its own directory without requiring another module to be present.
- No module may assume the existence of other modules at import time.
- Sensitive data must remain local to the module directory unless the module explicitly defines an outbound contract.

## 3. Module Contract

Each module must provide:
- `docs/` — module-specific architecture, status, changelog.
- `scripts/` — module-specific helpers, wrappers, and cron entry points.
- A CLI or API surface that accepts plain-text input and emits plain-text output.
- A persistence layer using local JSON files with atomic writes and backup semantics if the module stores state.

## 4. Data Principles

- Biometric, health, financial, and location-adjacent data is classified as sensitive.
- Sensitive data must not appear in stdout, logs, LLM prompts, or cross-module messages.
- Summaries and dashboards may reference data presence, not values, unless the user explicitly requests value display.

## 5. Security Rules

- All sensitive files must be `0600` owner-only.
- Cron prompts must not embed session history, user names, or raw health strings.
- Failure paths must emit generic messages; no stack traces or raw payloads in user-visible channels.

## 6. Delivery Rules

- External delivery (Telegram, email, etc.) is defined per module and must not be assumed by the platform.
- Any cron-driven delivery must include a wrapper that logs exit status and handles failures without leaking module internals to the scheduler.

## 7. Adaptation Rules

- Adaptive behavior must be deterministic and explainable.
- Feedback loops are module-specific but must follow the same contract: parse → validate → persist → evaluate → adapt.
- No module may silently ignore user feedback.

## 8. Change Protocol

- New modules require a constitution entry, architecture doc, and migration plan.
- Existing modules may only be relocated with an explicit approved migration plan.
- Documentation updates are always allowed; code moves require approval.
