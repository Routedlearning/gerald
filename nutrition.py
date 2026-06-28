def compute_macros(weight_lbs: float, goal: str = "cut", activity: str = "high") -> dict:
    if goal != "cut":
        raise ValueError("MVP only supports goal='cut'")

    protein_per_lb = 1.0
    fat_per_lb = 0.35

    if activity == "high":
        calories = weight_lbs * 8.5
    else:
        calories = weight_lbs * 7.5

    protein_g = min(weight_lbs * protein_per_lb, 220.0)
    fat_g = weight_lbs * fat_per_lb
    protein_cal = protein_g * 4
    fat_cal = fat_g * 9
    carb_cal = calories - protein_cal - fat_cal
    carb_g = max(carb_cal / 4, 0)

    return {
        "calories": int(calories),
        "protein_g": int(protein_g),
        "fat_g": int(fat_g),
        "carb_g": int(carb_g),
    }
