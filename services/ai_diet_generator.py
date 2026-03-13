import os
import json
from config import Config

EATWELL_HARVARD_GUIDELINES = """
PLATE COMPOSITION RULES (Harvard Healthy Eating Plate + UK Eatwell Guide):

1. VEGETABLES (~37% plate, Eatwell ~1/3):
   - At least 5 portions of varied fruit & vegetables daily
   - Potatoes/French fries do NOT count as vegetables
   - Indian: spinach, broccoli, cauliflower, bhindi, baingan, lauki, carrot, tomato, peas

2. WHOLE GRAINS (~25% plate):
   - Choose wholegrain: whole wheat roti, brown rice, oats, daliya, whole wheat pasta
   - Limit refined grains (white rice, maida, white bread)

3. HEALTHY PROTEIN (~25% plate):
   - Prioritise: fish (2 portions/week, 1 oily), poultry, beans, pulses, eggs, plain nuts
   - Limit red meat; avoid processed/cured meats entirely
   - Indian: dal, rajma, chana, moong, tofu, paneer (moderate), eggs, chicken, fish

4. FRUITS (~12% plate):
   - Eat plenty of fruits of all colours daily
   - Limit fruit juice to 150ml/day (Eatwell); 1 small glass/day (Harvard)

5. HEALTHY OILS (small amount):
   - Use unsaturated oils: mustard, olive, rice bran (small amounts)
   - Limit butter and ghee; avoid trans fats (vanaspati)

6. DAIRY: Lower-fat options, 1-2 servings/day. Semi-skimmed milk, low-fat yoghurt.

7. HYDRATION: 6-8 glasses water/day (Eatwell). Avoid sugary drinks. Limit juice to 150ml.

8. EAT LESS OFTEN: crisps, biscuits, cakes, fried snacks, sweets, sauces high in salt/sugar.

9. DAILY REFERENCE: 2000 kcal women, 2500 kcal men (Eatwell traffic light labelling).
"""


def build_prompt(user_data, metrics):
    goal_map = {'weight_loss': 'Weight Loss', 'muscle_gain': 'Muscle Gain', 'maintain': 'Weight Maintenance'}
    diet_map = {'vegetarian': 'Vegetarian', 'non_vegetarian': 'Non-Vegetarian', 'vegan': 'Vegan'}

    return f"""You are a professional nutritionist trained in the Harvard Healthy Eating Plate and UK Eatwell Guide. Generate a personalized evidence-based 7-day diet plan.

NUTRITION GUIDELINES TO STRICTLY FOLLOW:
{EATWELL_HARVARD_GUIDELINES}

USER PROFILE:
- Age: {user_data.get('age')} | Gender: {user_data.get('gender','').title()} | Country: {user_data.get('country','India')}
- Height: {user_data.get('height')}cm | Weight: {user_data.get('weight')}kg
- BMI: {metrics['bmi']} ({metrics['bmi_category']}) | BMR: {metrics['bmr']} kcal
- Daily Calorie Target: {metrics['daily_calories']} kcal
- Protein: {metrics['protein']}g | Carbs: {metrics['carbs']}g | Fats: {metrics['fats']}g
- Goal: {goal_map.get(user_data.get('goal'), 'Maintain')}
- Diet Type: {diet_map.get(user_data.get('diet_type'), 'Non-Vegetarian')}
- Allergies: {user_data.get('food_allergies', 'None')}
- Activity: {metrics['activity_level'].replace('_',' ').title()}
- Sleep: {user_data.get('sleep_hours',7)}h ({user_data.get('sleep_quality','Average')})
- Stress: {user_data.get('stress_level','Moderate')}
- Water: {user_data.get('water_intake','1-2 liters')}/day
- Current breakfast: {user_data.get('breakfast_foods','Not specified')}
- Current lunch: {user_data.get('lunch_foods','Not specified')}
- Current dinner: {user_data.get('dinner_foods','Not specified')}
- Junk food/week: {user_data.get('junk_food_frequency','1-2')}

MEAL PLAN RULES:
1. Every meal: ~half vegetables+fruit, ~quarter whole grains, ~quarter protein (Harvard Plate)
2. Achieve 5-a-day fruit & veg (Eatwell)
3. Include 2 fish meals across the week (if non-vegetarian)
4. Whole grains only — whole wheat roti, brown rice, oats, daliya
5. Beans/pulses as primary protein where possible
6. Healthy oils in small amounts only
7. Include portion sizes; use Indian foods
8. Vary all 7 days

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "week_plan": {{
    "Monday": {{
      "breakfast": {{"meal": "name", "description": "desc with portions", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "eatwell_segments": ["vegetables","whole_grains","protein"]}},
      "lunch": {{"meal": "name", "description": "desc", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "eatwell_segments": []}},
      "dinner": {{"meal": "name", "description": "desc", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "eatwell_segments": []}},
      "snacks": {{"meal": "name", "description": "desc", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "eatwell_segments": []}}
    }},
    "Tuesday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Wednesday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Thursday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Friday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Saturday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Sunday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}}
  }},
  "eatwell_compliance": {{
    "fruit_veg_portions_per_day": 0,
    "whole_grain_meals": 0,
    "fish_meals_per_week": 0,
    "processed_food_meals": 0,
    "harvard_plate_score": 0
  }},
  "lifestyle_tips": ["tip1","tip2","tip3","tip4","tip5","tip6","tip7","tip8"],
  "grocery_list": ["item1","item2","item3","item4","item5","item6","item7","item8","item9","item10"],
  "foods_to_limit": ["food1","food2","food3"],
  "important_notes": "2-3 sentence personalized note referencing Harvard Plate and Eatwell"
}}"""


def generate_with_gemini(prompt):
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")


def generate_with_openai(prompt):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3500
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def parse_ai_response(raw_text):
    text = raw_text.strip()
    for prefix in ['```json', '```']:
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith('```'):
        text = text[:-3]
    return json.loads(text.strip())


def get_fallback_plan(user_data, metrics):
    is_veg = user_data.get('diet_type') in ['vegetarian', 'vegan']
    cal = int(metrics['daily_calories'])
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    templates = [
        {"breakfast": ("Oats Porridge + Mixed Fruits", "50g oats in 200ml semi-skimmed milk, banana + apple. Wholegrain, low sugar.", ["whole_grains","fruits","dairy"]),
         "lunch":     ("Whole Wheat Roti + Dal Tadka + Sabzi + Salad", "2 whole wheat rotis, 1 katori moong dal, 1 katori mixed veg, salad.", ["whole_grains","protein","vegetables"]),
         "dinner":    ("Brown Rice + Rajma + Stir-fried Spinach", "3/4 cup brown rice, 1 katori rajma, 1 katori stir-fried spinach.", ["whole_grains","protein","vegetables"]),
         "snacks":    ("Mixed Nuts + 1 Fruit + Water", "20g almonds/walnuts, 1 guava or apple. 6-8 glasses water target.", ["protein","fruits"])},
        {"breakfast": ("Vegetable Daliya Upma", "1 cup broken wheat with peas, carrot, onion. High fibre.", ["whole_grains","vegetables"]),
         "lunch":     ("Chana Masala + 2 Roti + Raita + Salad", "1 katori chana, 2 whole wheat rotis, low-fat raita, salad.", ["protein","whole_grains","vegetables","dairy"]),
         "dinner":    ("Grilled Fish/Tofu + Brown Rice + Stir-fried Veg" if not is_veg else "Tofu Bhurji + Brown Rice + Veg", "150g grilled fish/tofu, 1/2 cup brown rice, broccoli + capsicum.", ["protein","vegetables","whole_grains"]),
         "snacks":    ("Fruit Chaat + Buttermilk", "Seasonal fruit bowl + 1 glass low-fat buttermilk.", ["fruits","dairy"])},
        {"breakfast": ("Moong Dal Cheela + Mint Chutney", "3 cheelas (high protein, low fat), green chutney.", ["protein","vegetables"]),
         "lunch":     ("Palak Dal + 2 Roti + Baingan Bharta + Salad", "Spinach dal, 2 rotis, baingan bharta, green salad.", ["protein","whole_grains","vegetables"]),
         "dinner":    ("Chicken/Paneer Tikka + Quinoa + Salad", "150g lean protein, 1/2 cup quinoa, large mixed salad.", ["protein","whole_grains","vegetables"]),
         "snacks":    ("Roasted Chana + 1 Orange", "30g roasted chana + 1 orange. High fibre, no frying.", ["protein","fruits"])},
        {"breakfast": ("Idli (3) + Sambar + Coconut Chutney", "3 steamed idlis, vegetable sambar (protein + veg), small chutney.", ["whole_grains","protein","vegetables"]),
         "lunch":     ("Mixed Veg Brown Rice Pulao + Dal + Raita", "1 cup veg brown rice pulao, masoor dal, low-fat curd.", ["whole_grains","vegetables","protein","dairy"]),
         "dinner":    ("Egg/Chickpea Curry + 2 Roti + Stir-fried Methi", "2 eggs or chickpea curry, 2 rotis, stir-fried fenugreek.", ["protein","whole_grains","vegetables"]),
         "snacks":    ("Low-fat Yoghurt + Banana", "150g plain low-fat yoghurt + 1 banana. No added sugar.", ["dairy","fruits"])},
        {"breakfast": ("Whole Wheat Toast + Eggs/Paneer + Tomato", "2 slices WW toast, 2 scrambled eggs or paneer, 2 tomatoes.", ["whole_grains","protein","vegetables"]),
         "lunch":     ("Fish Curry/Rajma + Brown Rice + Salad", "150g fish (Eatwell 2x/week) or rajma, 3/4 cup brown rice, salad.", ["protein","whole_grains","vegetables"]),
         "dinner":    ("Vegetable Khichdi + Low-fat Curd", "1.5 cups moong dal + brown rice khichdi with carrots + peas, curd.", ["whole_grains","protein","vegetables","dairy"]),
         "snacks":    ("Apple + Almonds", "1 medium apple + 15g almonds. Healthy fats + fibre.", ["fruits","protein"])},
        {"breakfast": ("Poha + Sprouts + Lime", "1 cup poha with peas, onion, mustard seeds, topped with sprouts.", ["whole_grains","vegetables","protein"]),
         "lunch":     ("Lentil Soup + Whole Wheat Bread + Salad", "Large bowl masoor soup, 2 WW bread slices, green salad.", ["protein","whole_grains","vegetables"]),
         "dinner":    ("Grilled Paneer/Chicken + Roasted Veg + Chapati", "150g grilled protein, roasted cauliflower + pepper, 2 rotis.", ["protein","vegetables","whole_grains"]),
         "snacks":    ("Fruit Smoothie (no sugar)", "Banana + 150ml semi-skimmed milk + spinach. Max 150ml juice (Eatwell).", ["fruits","dairy"])},
        {"breakfast": ("Vegetable Omelette/Besan Cheela + WW Toast", "2-egg omelette with spinach + onion, 1 slice WW toast.", ["protein","vegetables","whole_grains"]),
         "lunch":     ("Full Eatwell Thali: Dal + Sabzi + Roti + Salad + Curd", "2 rotis, dal, seasonal sabzi, salad, 100g curd. Complete plate.", ["whole_grains","protein","vegetables","dairy"]),
         "dinner":    ("Oats Vegetable Soup + Sautéed Vegetables", "1 bowl oats veg soup, 1 cup sautéed mixed veg, minimal oil.", ["whole_grains","vegetables"]),
         "snacks":    ("Mixed Seeds + 1 Seasonal Fruit", "20g pumpkin + sunflower seeds, 1 seasonal fruit. Healthy fats.", ["protein","fruits"])}
    ]

    def make_meal(t, mtype):
        name, desc, segs = t
        pct = {'breakfast':0.25,'lunch':0.35,'dinner':0.30,'snacks':0.10}.get(mtype, 0.25)
        return {"meal": name, "description": desc,
                "calories": int(cal*pct), "protein": int(metrics['protein']*pct),
                "carbs": int(metrics['carbs']*pct), "fats": int(metrics['fats']*pct),
                "eatwell_segments": segs}

    week_plan = {}
    for i, day in enumerate(days):
        t = templates[i]
        week_plan[day] = {k: make_meal(t[k], k) for k in ["breakfast","lunch","dinner","snacks"]}

    return {
        "week_plan": week_plan,
        "eatwell_compliance": {
            "fruit_veg_portions_per_day": 6,
            "whole_grain_meals": 18,
            "fish_meals_per_week": 2,
            "processed_food_meals": 0,
            "harvard_plate_score": 85
        },
        "lifestyle_tips": [
            "🥗 Fill half your plate with vegetables and fruits at every meal (Harvard Healthy Eating Plate)",
            "🌾 Choose wholegrain roti, brown rice, and oats — limit white rice and maida (Eatwell Guide)",
            "💧 Drink 6–8 glasses of water daily; limit fruit juice to 150ml/day (Eatwell Guide)",
            "🐟 Eat 2 portions of fish per week, 1 oily (salmon/mackerel) — Eatwell recommendation",
            "🫘 Prioritise dal, rajma, chana, and moong for protein — high fibre, low fat",
            "🚫 Avoid processed meats, trans fats (vanaspati), and sugary drinks completely",
            "🏃 Stay physically active every day — combines with diet for best results (Harvard Plate)",
            "🛑 Eat fried snacks, sweets, and biscuits less often and in small amounts (Eatwell Guide)"
        ],
        "grocery_list": [
            "Oats / Daliya (wholegrain)", "Whole wheat atta", "Brown rice",
            "Moong + masoor + toor dal", "Rajma / chana / chickpeas",
            "Seasonal vegetables (spinach, cauliflower, peas, carrot, tomato)",
            "Seasonal fruits (banana, apple, guava, papaya, orange)",
            "Low-fat curd / semi-skimmed milk", "Eggs / tofu / low-fat paneer",
            "Mustard or olive oil (small)", "Mixed nuts (almonds, walnuts)", "Roasted chana"
        ],
        "foods_to_limit": [
            "White rice & maida (refined grains) — replace with whole grain versions",
            "Fried snacks: samosa, pakora, namkeen — Eatwell: eat less often",
            "Sugary drinks: cold drinks, packaged juice, excess sugar in chai"
        ],
        "important_notes": (
            f"Your plan follows the Harvard Healthy Eating Plate and UK Eatwell Guide: "
            f"half your plate is vegetables & fruits, quarter whole grains, quarter healthy protein. "
            f"Targeting {int(metrics['daily_calories'])} kcal/day for {user_data.get('goal','your goal').replace('_',' ')}."
        )
    }


def generate_diet_plan(user_data, metrics):
    prompt = build_prompt(user_data, metrics)
    try:
        if Config.AI_PROVIDER == 'openai' and Config.OPENAI_API_KEY:
            raw = generate_with_openai(prompt)
        elif Config.GEMINI_API_KEY:
            raw = generate_with_gemini(prompt)
        else:
            return get_fallback_plan(user_data, metrics)
        return parse_ai_response(raw)
    except Exception as e:
        print(f"AI generation failed: {e}. Using fallback plan.")
        return get_fallback_plan(user_data, metrics)
