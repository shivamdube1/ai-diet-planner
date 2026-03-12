def analyze_health(user_data, metrics):
    """Generate health analysis and insights from user data."""
    insights = []
    warnings = []
    score = 100  # Start with perfect health score

    # BMI Analysis
    bmi = metrics['bmi']
    if bmi < 18.5:
        warnings.append("Your BMI indicates you are underweight. Consider increasing caloric intake with nutrient-dense foods.")
        score -= 15
    elif 18.5 <= bmi < 25:
        insights.append("Your BMI is in the healthy range. Keep up the great work!")
    elif 25 <= bmi < 30:
        warnings.append("Your BMI indicates you are overweight. A moderate calorie deficit and regular exercise can help.")
        score -= 10
    else:
        warnings.append("Your BMI indicates obesity. Consult a healthcare provider and follow the personalized plan carefully.")
        score -= 20

    # Sleep Analysis
    sleep_hours = float(user_data.get('sleep_hours', 7))
    sleep_quality = user_data.get('sleep_quality', 'average')
    if sleep_hours < 6:
        warnings.append("You're getting less than 6 hours of sleep. Poor sleep disrupts hormones that control hunger and metabolism.")
        score -= 15
    elif sleep_hours >= 7:
        insights.append("Good sleep duration! Quality sleep supports weight management and muscle recovery.")

    if sleep_quality in ['poor']:
        warnings.append("Poor sleep quality affects cortisol levels and can increase cravings for unhealthy foods.")
        score -= 10

    # Stress Analysis
    stress = user_data.get('stress_level', 'moderate')
    if stress == 'high':
        warnings.append("High stress levels increase cortisol, promoting fat storage especially around the abdomen.")
        score -= 10
    elif stress == 'low':
        insights.append("Low stress levels support healthy metabolism and better food choices.")

    # Water Intake
    water = user_data.get('water_intake', '1-2 liters')
    if water == '<1 liter':
        warnings.append("Your water intake is very low. Dehydration slows metabolism and is often confused with hunger.")
        score -= 10
    elif water in ['2-3 liters', '>3 liters']:
        insights.append("Great hydration! Adequate water intake supports digestion and metabolism.")

    # Activity Level
    activity = metrics.get('activity_level', 'sedentary')
    if activity == 'sedentary':
        warnings.append("Sedentary lifestyle increases risk of metabolic disorders. Try to incorporate at least 30 minutes of movement daily.")
        score -= 10
    elif activity in ['active', 'very_active']:
        insights.append("Your active lifestyle significantly boosts your metabolism and overall health.")

    # Junk food frequency
    junk = user_data.get('junk_food_frequency', '1-2')
    if junk in ['5+', 'daily']:
        warnings.append("Frequent junk food consumption provides empty calories and micronutrient deficiencies.")
        score -= 10
    elif junk in ['0', 'rarely']:
        insights.append("Excellent! Minimal junk food consumption supports your health goals.")

    # Outside food
    outside = user_data.get('outside_food_frequency', 'occasionally')
    if outside in ['daily', 'most days']:
        warnings.append("Frequent restaurant/takeout meals often contain hidden calories, sodium, and unhealthy fats.")
        score -= 5

    score = max(0, min(100, score))

    return {
        'health_score': score,
        'score_label': get_score_label(score),
        'insights': insights,
        'warnings': warnings,
        'total_issues': len(warnings)
    }


def get_score_label(score):
    if score >= 85:
        return ('Excellent', 'success')
    elif score >= 70:
        return ('Good', 'info')
    elif score >= 50:
        return ('Fair', 'warning')
    else:
        return ('Needs Improvement', 'danger')
