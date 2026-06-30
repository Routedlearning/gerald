def evaluate_week(
    history: list[dict],
    current_weight: float,
    current_5k: str,
    missed_streak: int,
    feedback_log: list[dict] | None = None,
) -> dict:
    completed = [w for w in history if w.get("completed")]
    missed = [w for w in history if not w.get("completed")]

    for entry in feedback_log or []:
        data = entry.get("data") or {}
        status = data.get("status")
        if status == "completed":
            completed.append({"source": "feedback", "rpe": data.get("rpe"), "energy": data.get("energy")})
        elif status == "missed":
            missed.append({"source": "feedback"})

    total = max(len(completed) + len(missed), 1)

    suggestions = {
        "volume_multiplier": 1.0,
        "deload": False,
        "five_k_boost": False,
        "notes": [],
    }

    completion_pct = len(completed) / total
    if completion_pct < 0.5 or missed_streak >= 2:
        suggestions["volume_multiplier"] = 0.8
        suggestions["deload"] = True
        suggestions["notes"].append("Lowered volume due to low adherence")

    if completion_pct >= 0.85:
        suggestions["volume_multiplier"] = 1.15
        suggestions["notes"].append("Increased volume: strong adherence")

    rpe_candidates = []
    for w in completed:
        feedback = w.get("feedback")
        if feedback and feedback.get("rpe"):
            rpe_candidates.append(feedback["rpe"])
    for entry in (feedback_log or []):
        data = entry.get("data") or {}
        if data.get("rpe"):
            rpe_candidates.append(data["rpe"])

    if rpe_candidates:
        avg_rpe = sum(rpe_candidates) / len(rpe_candidates)
        if avg_rpe >= 8.5:
            suggestions["deload"] = True
            suggestions["notes"].append("Deload: high RPE trend detected")

    low_energy_count = 0
    for entry in (feedback_log or []):
        data = entry.get("data") or {}
        energy = data.get("energy")
        if energy and energy <= 2:
            low_energy_count += 1

    if low_energy_count >= 2:
        suggestions["volume_multiplier"] = min(suggestions["volume_multiplier"], 0.9)
        if "Low energy feedback trend" not in suggestions["notes"]:
            suggestions["notes"].append("Low energy feedback trend")

    if current_5k and current_5k.strip() and _time_to_seconds(current_5k) < _time_to_seconds("38:30"):
        suggestions["five_k_boost"] = True
        suggestions["notes"].append("5k improved: add interval volume next week")

    return suggestions


def _time_to_seconds(t: str) -> int:
    t = t.strip()
    m, s = t.split(":")
    return int(m) * 60 + int(s)
