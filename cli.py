import argparse
import datetime
import sys
from storage import load, save
from adaptation import evaluate_week
from planner import build_week
from feedback_parser import parse as parse_feedback

WEEK_START_OVERRIDE = "2026-06-29"


def build_week_for_display(weight_lbs, week_start_date, history_week_key):
    state = load()

    last_week = [w for w in state.get("workouts", []) if w.get("week") == history_week_key]
    adaptation = evaluate_week(
        history=last_week,
        current_weight=state.get("last_weight", weight_lbs),
        current_5k=state.get("last_5k_time", "40:00"),
        missed_streak=state.get("missed_streak", 0),
    )

    return build_week(weight_lbs=weight_lbs, adaptation=adaptation), adaptation


def cmd_today(week_start):
    state = load()
    weight_lbs = state.get("last_weight", 290)
    week = build_week_for_display(weight_lbs, week_start, week_start)[0]

    today_name = datetime.date.today().strftime("%A")
    plan = week.get(today_name)
    if not plan:
        print(f"No plan found for {today_name}.")
        return
    print(f"🏋️ {today_name.upper()} — Week of {week_start}")
    print(f"Type: {plan['type'].upper()}")
    print(f"Focus: {plan['focus']}")
    print(f"Estimated time: {plan['estimated_minutes']} min")
    print()
    print("Workout:")
    for line in plan["workout"].split("\n"):
        print(f"  {line}")
    print()
    print(plan["macro_note"])
    print()


def cmd_week(week_start):
    state = load()
    weight_lbs = state.get("last_weight", 290)
    week = build_week_for_display(weight_lbs, week_start, week_start)[0]

    print(f"Week starting {week_start}\n")
    for day, plan in week.items():
        print(f"{day}: {plan['type'].upper()} — {plan['focus']}")
        print(f"  {plan['workout']}")
        print(f"  Estimated time: {plan['estimated_minutes']} min")
        print(f"  {plan['macro_note']}")
        print()


def cmd_feedback(message: str):
    state = load()
    entry = parse_feedback(message)

    # Dedup guard: only check last entry's normalized text
    fl = state.get("feedback_log", [])
    if fl and fl[-1]["normalized"] == entry.normalized:
        print(f"Duplicate entry (id={entry.entry_id}). Skipped.")
        return

    fl.append({
        "entry_id":    entry.entry_id,
        "received_at": entry.received_at,
        "type":        entry.type,
        "normalized":  entry.normalized,
        "data":        entry.data,
    })
    state["feedback_log"] = fl

    save(state)
    print(f"Logged (id={entry.entry_id}, type={entry.type})")


def cmd_feedback_summary(days: int = 7):
    state = load()
    fl = state.get("feedback_log", [])

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    recent: list = []
    for e in fl:
        try:
            ts = datetime.datetime.fromisoformat(
                e["received_at"].replace("Z", "+00:00")
            )
            if ts >= cutoff:
                recent.append(e)
        except Exception:
            recent.append(e)

    if not recent:
        print(f"No feedback in the last {days} days.")
        return

    type_counts: dict = {}
    for e in recent:
        t = e["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    summary_parts = ", ".join(
        f"{t}:{type_counts[t]}" for t in sorted(type_counts)
    )

    last = recent[-1]
    print(f"Last {days} days: {len(recent)} entries ({summary_parts})")
    print(f"Latest ({last['received_at']}, type={last['type']}):")

    d = last["data"]
    parts: list = []
    if d.get("status"):
        parts.append(f"status={d['status']}")
    if d.get("rpe"):
        parts.append(f"rpe={d['rpe']}")
    if d.get("energy"):
        parts.append(f"energy={d['energy']}")
    if d.get("notes"):
        parts.append(f"notes={d['notes']}")
    if d.get("weight_lbs"):
        parts.append(f"weight={d['weight_lbs']}lbs")
    if d.get("sleep_hours"):
        parts.append(f"sleep={d['sleep_hours']}h")
    if d.get("bp_systolic") and d.get("bp_diastolic"):
        parts.append(f"bp={d['bp_systolic']}/{d['bp_diastolic']}")
    if parts:
        print("  " + ", ".join(parts))
    else:
        print("  (no structured data)")


def main():
    parser = argparse.ArgumentParser(description="Fitness Coach CLI")
    parser.add_argument("--week-start", default=WEEK_START_OVERRIDE,
                        help="ISO week-start date (default 2026-06-29)")
    parser.add_argument("--today", action="store_true",
                        help="Print only today's workout")
    parser.add_argument("--feedback", metavar="MSG",
                        help="Log workout/biometric feedback message")
    parser.add_argument("--feedback-summary",
                        action="store_true",
                        help="Show last 7 days of feedback")
    args = parser.parse_args()

    if args.feedback:
        cmd_feedback(args.feedback)
    elif args.feedback_summary:
        cmd_feedback_summary()
    elif args.today:
        cmd_today(args.week_start)
    else:
        cmd_week(args.week_start)


if __name__ == "__main__":
    main()
