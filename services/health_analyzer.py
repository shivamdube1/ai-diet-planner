def analyze_health(user_data, metrics):
    """
    Health analysis incorporating Harvard Healthy Eating Plate
    and UK Eatwell Guide compliance checks.
    """
    insights = []
    warnings = []
    score = 100

    # ── BMI (Harvard + Eatwell both reference healthy weight) ──
    bmi = metrics['bmi'] if isinstance(metrics, dict) else user_data.get('bmi', 22)
    bmi_category = metrics.get('bmi_category', user_data.get('bmi_category', 'Normal')) if isinstance(metrics, dict) else user_data.get('bmi_category', 'Normal')

    if bmi < 18.5:
        warnings.append("Your BMI indicates underweight. Increase intake with nutrient-dense whole grains, healthy proteins, and dairy (Eatwell Guide).")
        score -= 15
    elif 18.5 <= bmi < 25:
        insights.append("Your BMI is in the healthy range — maintain it with the Harvard Plate balance of veg, whole grains, and protein.")
    elif 25 <= bmi < 30:
        warnings.append("BMI indicates overweight. The Eatwell Guide recommends reducing refined grains, fried foods, and sugary drinks.")
        score -= 10
    else:
        warnings.append("BMI indicates obesity. Follow the Harvard Plate: half vegetables, quarter whole grains, quarter lean protein. Consult a doctor.")
        score -= 20

    # ── Fruit & Vegetable Intake (Eatwell: 5-a-day) ──
    junk = user_data.get('junk_food_frequency', '1-2')
    outside = user_data.get('outside_food_frequency', 'occasionally')
    meals_day = int(user_data.get('meals_per_day', 3))

    if junk in ['5+', 'daily']:
        warnings.append("High junk food frequency limits your 5-a-day target. Eatwell Guide: eat crisps, sweets, and fried foods less often and in small amounts.")
        score -= 12
    elif junk in ['0', 'rarely', '1-2']:
        insights.append("Good — minimal junk food helps you meet the Eatwell Guide's 5-a-day fruit & vegetable target.")

    if outside in ['daily', 'most days']:
        warnings.append("Frequent restaurant meals often contain hidden salt, fat, and refined grains. Eatwell: choose foods lower in fat, salt, and sugar.")
        score -= 8

    # ── Whole Grains (Harvard Plate: quarter of plate) ──
    breakfast = (user_data.get('breakfast_foods') or '').lower()
    refined_triggers = ['white rice', 'maida', 'white bread', 'naan', 'paratha']
    wholegrain_triggers = ['oats', 'daliya', 'brown rice', 'whole wheat', 'roti', 'porridge']

    has_refined = any(r in breakfast for r in refined_triggers)
    has_wholegrain = any(w in breakfast for w in wholegrain_triggers)

    if has_refined:
        warnings.append("Refined grains detected in your diet. Harvard Plate recommends whole grains (brown rice, whole wheat roti, oats) over refined versions.")
        score -= 8
    if has_wholegrain:
        insights.append("Wholegrain foods detected — great alignment with the Harvard Healthy Eating Plate and Eatwell Guide.")

    # ── Hydration (Eatwell: 6-8 glasses/day) ──
    water = user_data.get('water_intake', '1-2 liters')
    if water == '<1 liter':
        warnings.append("Critical: under 1L of water/day. Eatwell recommends 6–8 glasses/day. Dehydration slows metabolism and is often mistaken for hunger.")
        score -= 12
    elif water == '1-2 liters':
        warnings.append("Water intake is below the Eatwell Guide target of 6–8 glasses (1.5–2L minimum). Aim for 2–3L especially on active days.")
        score -= 5
    elif water in ['2-3 liters', '>3 liters']:
        insights.append("Excellent hydration — meets or exceeds the Eatwell Guide recommendation of 6–8 glasses per day.")

    # ── Protein Quality (Harvard Plate: healthy protein sources) ──
    diet_type = user_data.get('diet_type', 'non_vegetarian')
    if diet_type == 'vegan':
        insights.append("Vegan diet aligns well with Harvard Plate's emphasis on beans, pulses, and plant protein. Ensure B12 supplementation.")
    elif diet_type == 'vegetarian':
        insights.append("Vegetarian diet supports Harvard Plate goals. Include dal, rajma, paneer, and eggs for complete protein coverage.")

    lunch_foods = (user_data.get('lunch_foods') or '').lower()
    dinner_foods = (user_data.get('dinner_foods') or '').lower()
    pulse_triggers = ['dal', 'rajma', 'chana', 'moong', 'lentil', 'beans']
    if any(p in lunch_foods + dinner_foods for p in pulse_triggers):
        insights.append("Beans and pulses detected — excellent! Eatwell Guide: eat more beans and pulses as a primary protein source.")

    # ── Sleep (affects appetite hormones — Eatwell indirectly supports sleep hygiene) ──
    sleep_hours = float(user_data.get('sleep_hours', 7))
    sleep_quality = user_data.get('sleep_quality', 'average')

    if sleep_hours < 6:
        warnings.append("Under 6 hours sleep disrupts ghrelin and leptin — the hormones controlling hunger. Poor sleep increases cravings for high-sugar, high-fat foods.")
        score -= 15
    elif sleep_hours >= 7:
        insights.append("Good sleep duration supports healthy appetite regulation and metabolism.")

    if sleep_quality == 'poor':
        warnings.append("Poor sleep quality increases cortisol, promoting fat storage. Reducing caffeine and screen time before bed can help.")
        score -= 8

    # ── Stress (cortisol links to overeating and fat storage) ──
    stress = user_data.get('stress_level', 'moderate')
    if stress == 'high':
        warnings.append("High stress raises cortisol, increasing cravings for sugary and fatty foods (the exact foods the Eatwell Guide says to eat less often).")
        score -= 10
    elif stress == 'low':
        insights.append("Low stress levels support better food choices and healthy metabolism.")

    # ── Physical Activity (Harvard Plate: Stay Active reminder) ──
    activity = metrics.get('activity_level', 'sedentary') if isinstance(metrics, dict) else 'sedentary'
    if activity == 'sedentary':
        warnings.append("Sedentary lifestyle. Harvard Healthy Eating Plate emphasises: Stay Active! Even a 30-min daily walk significantly improves health outcomes.")
        score -= 10
    elif activity in ['active', 'very_active']:
        insights.append("Active lifestyle — combined with the Harvard Plate approach, this significantly reduces chronic disease risk.")

    # ── Oils & Fats (Harvard: use healthy oils; Eatwell: choose unsaturated) ──
    beverages = (user_data.get('beverages') or '').lower()
    snacks = (user_data.get('snacks') or '').lower()
    if any(s in snacks for s in ['biscuit', 'chips', 'namkeen', 'pakora', 'samosa', 'fried']):
        warnings.append("Fried/processed snacks detected. Eatwell Guide: choose lower-fat snacks — opt for fruits, nuts, or roasted chana instead.")
        score -= 8

    if any(b in beverages for b in ['cold drink', 'soda', 'juice', 'pepsi', 'cola', 'energy']):
        warnings.append("Sugary beverages detected. Harvard Plate: avoid sugary drinks. Eatwell: limit juice to 150ml/day. Switch to water or unsweetened tea.")
        score -= 8
    elif any(b in beverages for b in ['water', 'green tea', 'black tea', 'buttermilk']):
        insights.append("Healthy beverage choices detected — aligned with both Harvard Plate and Eatwell Guide recommendations.")

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
