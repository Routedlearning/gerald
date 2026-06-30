import sys
import datetime
import os
from planner import build_week
from adaptation import evaluate_week
import json
from storage import HISTORY_PATH

def simulate(day_name, week_start):
    with open(HISTORY_PATH) as f:
        state = json.load(f)

    last_week = [w for w in state.get("workouts", []) if w.get("week") == week_start]
    adaptation = evaluate_week(
        history=last_week,
        current_weight=state.get("last_weight", 290),
        current_5k=state.get("last_5k_time", "40:00"),
        missed_streak=state.get("missed_streak", 0),
    )

    week = build_week(weight_lbs=state.get("last_weight", 290), adaptation=adaptation)
    plan = week.get(day_name)
    if not plan:
        print(f"Day '{day_name}' not found.")
        return

    today = datetime.date.today()
    date_str = today.strftime("%A, %B %d, %Y")
    print(f"🏋️ {date_str} — {day_name.upper()}")
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
    if adaptation.get("notes"):
        print("Notes:")
        for n in adaptation["notes"]:
            print(f"- {n}")

if __name__ == "__main__":
    day = sys.argv[1] if len(sys.argv) > 1 else "Monday"
    week_start = sys.argv[2] if len(sys.argv) > 2 else "2026-06-29"
    simulate(day, week_start)
