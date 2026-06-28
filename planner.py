from nutrition import compute_macros

DAY_TEMPLATES = {
    "Monday": {
        "type": "strength",
        "focus": "Lower body + posterior chain",
        "exercises": [
            "Back Squat 3x10 (moderate weight, focus on depth)",
            "Romanian Deadlift 3x10 (light/moderate)",
            "Leg Press 3x12",
            "Walking Lunges 3x12 each leg",
            "Glute Bridges 3x15 (add weight when easy)",
            "Optional: Calf Raises 3x15",
        ],
    },
    "Tuesday": {
        "type": "strength",
        "focus": "Upper body push + pull",
        "exercises": [
            "Bench Press 3x10 (moderate weight)",
            "Overhead Press (dumbbell or barbell) 3x10",
            "Bent-over Row 3x10 (light/moderate)",
            "Lat Pulldown or Assisted Pull-ups 3x10",
            "Dumbbell Curl 3x12",
            "Tricep Pushdown 3x12",
        ],
    },
    "Wednesday": {
        "type": "cardio",
        "focus": "Treadmill intervals or 5k",
        "exercises": [
            "Option A: Treadmill intervals — 400m hard effort / 400m walk or easy jog × 6",
            "Option B: Steady 5k run at conversational pace",
        ],
    },
    "Thursday": {
        "type": "strength",
        "focus": "Full body",
        "exercises": [
            "Deadlift 3x8 (light/moderate, form first)",
            "Incline Bench Press 3x10",
            "Pull-ups or Assisted Pull-ups 3x8",
            "Goblet Squat 3x12",
            "Shoulder Press 3x10",
            "Optional: Farmer's Walk 3x30 sec",
        ],
    },
    "Friday": {
        "type": "cardio",
        "focus": "Murph-style conditioning",
        "exercises": [
            "Bodyweight circuit: 10 pull-ups (assisted if needed), 20 push-ups, 30 air squats — repeat 3x",
            "Finish with 1 mile walk/jog",
        ],
    },
    "Saturday": {
        "type": "murph",
        "focus": "Murph-lite progression",
        "exercises": [
            "20–30 pull-ups (use band or assisted machine if needed)",
            "40–60 push-ups (knees allowed)",
            "80–100 air squats",
            "Cardio finisher: 4x 400m hard effort / walk or easy jog with 1 min rest between",
        ],
    },
    "Sunday": {
        "type": "recovery",
        "focus": "Mobility, walking, stretching",
        "exercises": [
            "10–15 min brisk walk",
            "10 min stretching (legs, shoulders, chest, hips)",
            "Optional: 5 min foam rolling",
        ],
    },
}

MURPH_PRESCRIBED = {
    "pull_ups": 100,
    "push_ups": 200,
    "air_squats": 300,
    "run_miles": [1.0, 1.0],
}


def build_week(
    weight_lbs: float,
    adaptation: dict | None = None,
) -> dict:
    adaptation = adaptation or {}
    volume_mult = adaptation.get("volume_multiplier", 1.0)
    deload = adaptation.get("deload", False)
    if deload:
        volume_mult *= 0.8
    volume_mult = max(volume_mult, 0.5)

    macros = compute_macros(weight_lbs, goal="cut", activity="high")
    week = {}
    for day, template in DAY_TEMPLATES.items():
        week[day] = _build_day(template, volume_mult, macros, deload)
    return week


def _build_day(template: dict, volume_mult: float, macros: dict, deload: bool) -> dict:
    if template["type"] == "recovery":
        est = 20
    elif template["type"] == "murph":
        est = 45
    else:
        est = 50 if not deload else 40
    est = min(est, 55)

    day = {
        "type": template["type"],
        "focus": template["focus"],
        "estimated_minutes": est,
        "macro_note": f"Macros: {macros['calories']} kcal · {macros['protein_g']}g protein · {macros['fat_g']}g fat · {macros['carb_g']}g carbs",
    }
    day["workout"] = "\n".join(template["exercises"])
    return day
