def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI."""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 1)


def get_bmi_category(bmi):
    """Return BMI classification."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"


def calculate_bmr(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor BMR formula."""
    if gender.lower() == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr, 1)


def get_activity_multiplier(activity_level):
    """Map activity level to TDEE multiplier."""
    multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    return multipliers.get(activity_level.lower(), 1.55)


def map_exercise_to_activity(exercise_frequency, work_type, daily_steps):
    """Determine activity level from questionnaire answers."""
    score = 0

    freq_scores = {'0': 0, '1-2': 1, '3-5': 2, '6-7': 3}
    score += freq_scores.get(exercise_frequency, 1)

    work_scores = {'sedentary': 0, 'mixed': 1, 'physical': 2}
    score += work_scores.get(work_type, 0)

    step_scores = {'<3000': 0, '3000-6000': 1, '6000-10000': 2, '>10000': 3}
    score += step_scores.get(daily_steps, 1)

    if score <= 1:
        return 'sedentary'
    elif score <= 3:
        return 'light'
    elif score <= 5:
        return 'moderate'
    elif score <= 7:
        return 'active'
    else:
        return 'very_active'


def calculate_tdee(bmr, activity_level):
    """Calculate Total Daily Energy Expenditure."""
    multiplier = get_activity_multiplier(activity_level)
    return round(bmr * multiplier, 1)


def calculate_goal_calories(tdee, goal):
    """Adjust calories based on goal."""
    adjustments = {
        'weight_loss': -500,
        'muscle_gain': 300,
        'maintain': 0
    }
    adjustment = adjustments.get(goal, 0)
    return round(tdee + adjustment, 1)


def calculate_macros(daily_calories, goal):
    """Calculate macronutrient targets in grams."""
    if goal == 'weight_loss':
        protein_pct, carb_pct, fat_pct = 0.35, 0.40, 0.25
    elif goal == 'muscle_gain':
        protein_pct, carb_pct, fat_pct = 0.30, 0.45, 0.25
    else:
        protein_pct, carb_pct, fat_pct = 0.25, 0.50, 0.25

    protein_g = round((daily_calories * protein_pct) / 4, 1)
    carbs_g = round((daily_calories * carb_pct) / 4, 1)
    fats_g = round((daily_calories * fat_pct) / 9, 1)

    return protein_g, carbs_g, fats_g


def run_all_calculations(user_data):
    """Run all health metric calculations for a user."""
    bmi = calculate_bmi(user_data['weight'], user_data['height'])
    bmi_category = get_bmi_category(bmi)
    bmr = calculate_bmr(
        user_data['weight'], user_data['height'],
        user_data['age'], user_data['gender']
    )

    activity_level = map_exercise_to_activity(
        user_data.get('activity_level', '1-2'),
        user_data.get('work_type', 'sedentary'),
        user_data.get('daily_steps', '3000-6000')
    )

    tdee = calculate_tdee(bmr, activity_level)
    daily_calories = calculate_goal_calories(tdee, user_data.get('goal', 'maintain'))
    protein, carbs, fats = calculate_macros(daily_calories, user_data.get('goal', 'maintain'))

    return {
        'bmi': bmi,
        'bmi_category': bmi_category,
        'bmr': bmr,
        'tdee': tdee,
        'activity_level': activity_level,
        'daily_calories': daily_calories,
        'protein': protein,
        'carbs': carbs,
        'fats': fats
    }
