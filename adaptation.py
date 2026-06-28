def evaluate_week(
    history: list[dict],
    current_weight: float,
    current_5k: str,
    missed_streak: int,
) -> dict:
    completed = [w for w in history if w.get("completed")]
    missed = [w for w in history if not w.get("completed")]
    n = len(history) or 1

    suggestions = {
        "volume_multiplier": 1.0,
        "deload": False,
        "five_k_boost": False,
        "notes": [],
    }

    completion_pct = len(completed) / n
    if completion_pct < 0.5 or missed_streak >= 2:
        suggestions["volume_multiplier"] = 0.8
        suggestions["deload"] = True
        suggestions["notes"].append("Lowered volume due to low adherence")

    if completion_pct >= 0.85:
        suggestions["volume_multiplier"] = 1.15
        suggestions["notes"].append("Increased volume: strong adherence")

    rpe_values = [w["feedback"].get("rpe", 0) for w in completed if w.get("feedback")]
    if rpe_values and (sum(rpe_values) / len(rpe_values)) >= 8.5:
        suggestions["deload"] = True
        suggestions["notes"].append("Deload: high RPE trend detected")

    if current_5k and _time_to_seconds(current_5k) < _time_to_seconds("38:30"):
        suggestions["five_k_boost"] = True
        suggestions["notes"].append("5k improved: add interval volume next week")

    return suggestions


def _time_to_seconds(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)
