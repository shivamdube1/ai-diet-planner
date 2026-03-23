"""
Meal swap service — generates an alternative meal with same nutritional profile.
Uses cache to avoid redundant API calls.
"""
import json, hashlib, time
from config import Config
from services.ai_diet_generator import EATWELL_HARVARD_GUIDELINES

_swap_cache: dict = {}
_TTL = 4 * 3600


def swap_meal(day: str, meal_type: str, current_meal: dict, user_data: dict, plan_targets: dict) -> dict:
    """Generate an alternative meal matching same calories/macros."""

    # Cache key
    cache_key = hashlib.md5(
        f"{meal_type}|{current_meal.get('meal','')}|{user_data.get('diet_type')}|{user_data.get('cuisine_preference','Indian')}|{int(current_meal.get('calories',0)//50)*50}".encode()
    ).hexdigest()

    cached = _swap_cache.get(cache_key)
    if cached and (time.time() - cached['ts']) < _TTL:
        print(f"Swap cache HIT {cache_key[:8]}")
        return cached['meal']

    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        diet_type = user_data.get('diet_type', 'non_vegetarian')
        is_veg = diet_type in ['vegetarian', 'vegan']
        cuisine = user_data.get('cuisine_preference', 'Indian')
        allergies = user_data.get('food_allergies', 'None')

        restriction = ""
        if diet_type == 'vegan':
            restriction = "⛔ VEGAN: Absolutely no meat, fish, dairy, or eggs. Plant-based only."
        elif diet_type == 'vegetarian':
            restriction = "⛔ VEGETARIAN: No meat or fish. Dairy and eggs allowed."

        target_cal = current_meal.get('calories', 400)
        target_p   = current_meal.get('protein', 20)
        target_c   = current_meal.get('carbs', 50)
        target_f   = current_meal.get('fats', 10)

        prompt = f"""Generate ONE alternative {meal_type} meal that is DIFFERENT from "{current_meal.get('meal', '')}".

{restriction}
Nutrition guidelines: {EATWELL_HARVARD_GUIDELINES[:500]}

Requirements:
- Cuisine: {cuisine}
- Meal type: {meal_type}
- Target calories: {target_cal} kcal (±50 kcal tolerance)
- Target protein: {target_p}g (±5g)
- Target carbs: {target_c}g (±10g)  
- Target fats: {target_f}g (±5g)
- Allergies to avoid: {allergies}
- Must be completely different from: {current_meal.get('meal', '')}
- Use practical, affordable {cuisine} ingredients

Respond ONLY with valid JSON:
{{
  "meal": "meal name",
  "description": "detailed description with exact portions",
  "calories": {target_cal},
  "protein": {target_p},
  "carbs": {target_c},
  "fats": {target_f},
  "fibre": 5,
  "prep_time": "20 min",
  "eatwell_segments": ["vegetables", "whole_grains", "protein"]
}}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0]

        new_meal = json.loads(raw.strip())

        # Safety check: veg/vegan enforcement
        if is_veg:
            banned = ['chicken','fish','tuna','salmon','mutton','beef','prawn']
            meal_text = json.dumps(new_meal).lower()
            if any(w in meal_text for w in banned):
                return _fallback_swap(meal_type, current_meal, diet_type, cuisine)

        # Cache it
        _swap_cache[cache_key] = {'meal': new_meal, 'ts': time.time()}
        return new_meal

    except Exception as e:
        print(f"Swap error: {e}")
        return _fallback_swap(meal_type, current_meal, user_data.get('diet_type','non_vegetarian'),
                              user_data.get('cuisine_preference','Indian'))


def _fallback_swap(meal_type: str, current: dict, diet_type: str, cuisine: str) -> dict:
    """Fallback when AI unavailable."""
    is_veg = diet_type in ['vegetarian', 'vegan']
    swaps = {
        'breakfast': [
            ("Moong Dal Cheela × 2 + Mint Chutney", "High-protein gram flour pancakes with herbs", ["protein","vegetables"]),
            ("Oats Upma + Mixed Vegetables", "Savoury oats cooked with seasonal veg", ["whole_grains","vegetables"]),
            ("Vegetable Poha + Sprouts", "Flattened rice with peas and moong sprouts", ["whole_grains","vegetables","protein"]),
        ],
        'lunch': [
            ("Dal Tadka + Brown Rice + Raita", "Tempered yellow dal with brown rice and curd", ["protein","whole_grains","dairy"]),
            ("Rajma + 2 Roti + Salad", "Kidney bean curry with whole wheat rotis", ["protein","whole_grains","vegetables"]),
            ("Chana Masala + Rice + Cucumber Salad", "Spiced chickpea curry bowl", ["protein","whole_grains","vegetables"]),
        ],
        'dinner': [
            ("Palak Dal + 2 Roti + Stir-fried Bhindi", "Spinach lentil soup with whole wheat rotis", ["protein","whole_grains","vegetables"]),
            ("Vegetable Khichdi + Low-fat Curd", "Comforting moong dal and rice one-pot", ["whole_grains","protein","dairy"]),
            ("Masoor Dal + Lauki Sabzi + Roti", "Red lentils with bottle gourd curry", ["protein","vegetables","whole_grains"]),
        ],
        'snacks': [
            ("Mixed Nuts + 1 Seasonal Fruit", "20g almonds/walnuts + apple or guava", ["protein","fruits"]),
            ("Roasted Chana + Buttermilk", "30g roasted chickpeas + spiced buttermilk", ["protein","dairy"]),
            ("Fruit Chaat + Lime", "Seasonal fruits with chaat masala", ["fruits"]),
        ],
    }
    options = swaps.get(meal_type, swaps['snacks'])
    import random
    name, desc, segs = random.choice(options)
    cal = current.get('calories', 350)
    p   = current.get('protein', 15)
    return {"meal": name, "description": desc, "calories": cal,
            "protein": p, "carbs": current.get('carbs',40), "fats": current.get('fats',10),
            "fibre": 5, "prep_time": "15 min", "eatwell_segments": segs}
