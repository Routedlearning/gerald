# Fitness Coach Project Constitution

Purpose: Define the immutable scope, constraints, and behavioral rules for the fitness-coach project. This document takes precedence over ad-hoc requests.

---

## 1. Purpose

- Deliver a daily, automated fitness and nutrition plan via Telegram.
- Adapt the plan based on actual execution feedback (RPE, energy, missed sessions).
- Maintain privacy and data hygiene as first-class requirements.

## 2. Boundaries

- Scope: single user, single device, weekly cron-driven plan delivery.
- Not in scope: multi-user support, real-time coaching, commercial distribution, medical advice.
- Storage scope: project-local JSON files only; no external databases or cloud sync.

## 3. Data Principles

- Health data (workouts, biometrics, feedback) remains local to `/root/projects/gerald/modules/fitness`.
- Raw biometrics must not appear in outbound messages, LLM prompts, or summary views.
- Backup and restore commands must preserve permissions and atomicity.

## 4. Delivery Rules

- Cron delivers at `0 5 * * 1-6` only; Sunday is silent.
- Wrapper stdout is the canonical outbound artifact; failure path emits a generic "engine failed" notice.
- Cron must not rely on interactive input or ambient state beyond the project directory.

## 5. Adaptation Rules

- Adaptation is deterministic and explainable; outputs must show rule-derived notes.
- Feedback loop is mandatory: logged RPE, energy, and miss data must be consumed by the adaptation engine.
- Planner must respect hard time caps (e.g., ≤60 minutes per session).

## 6. Nutrition Rules

- Baseline macros: 2465 kcal, 220 g protein, 101 g fat, 167 g carbs.
- Adjustments are driven by weight trend and feedback, not by random variation.

## 7. Security Rules

- No raw biometric echo in `--feedback-summary`.
- No Telegram session history leakage into cron runs.
- File permissions must be enforced (`0600` for sensitive data).

## 8. Change Protocol

- Requires an explicit user go-ahead before build tasks resume.
- Documentation updates are allowed at any time.
- Architecture changes require matching updates to `ARCHITECTURE.md`, `PROJECT_STATUS.md`, and this file.
