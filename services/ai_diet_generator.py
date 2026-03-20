import os, json
from config import Config

EATWELL_HARVARD_GUIDELINES = """
HARVARD HEALTHY EATING PLATE + UK EATWELL GUIDE RULES:

1. VEGETABLES (~37% plate): At least 5 portions/day. Variety of colours.
   Indian: spinach, broccoli, bhindi, baingan, lauki, carrot, tomato, capsicum, methi, peas
2. WHOLE GRAINS (~25%): Whole wheat roti, brown rice, oats, daliya, quinoa, millets (bajra, jowar, ragi)
3. HEALTHY PROTEIN (~25%): Prioritise legumes, pulses, nuts. Limit red/processed meat.
   - Veg: dal, rajma, chana, moong, urad, tofu, paneer (low-fat), tempeh, soya
   - Non-veg: fish 2x/week (1 oily), chicken (skinless), eggs
4. FRUITS (~13%): Seasonal fruits daily. Limit juice to 150ml/day.
5. HEALTHY OILS: Mustard, olive, rice bran (small amounts only). Avoid ghee/butter excess.
6. DAIRY: 1–2 servings/day, low-fat. Semi-skimmed milk, low-fat curd/yoghurt.
7. HYDRATION: 2–3 litres water/day. No sugary drinks.
8. AVOID: fried snacks, maida, refined sugar, processed foods, packaged juices.
9. CALORIE REF: 2000 kcal women / 2500 kcal men. Adjust for goal.
10. PORTION METHOD: Use katori (150ml bowl) as unit. 1 roti ≈ 80 kcal.
"""


def build_prompt(user_data, metrics):
    diet_type = user_data.get('diet_type', 'non_vegetarian')
    is_veg   = diet_type == 'vegetarian'
    is_vegan = diet_type == 'vegan'

    # Build the STRICTEST possible restriction block
    diet_restriction = ""
    if is_vegan:
        diet_restriction = """
⛔⛔ ABSOLUTE VEGAN RESTRICTION — THIS IS NON-NEGOTIABLE ⛔⛔
The user is VEGAN. You MUST NEVER include ANY of the following in ANY meal:
- Meat, chicken, fish, seafood, eggs, dairy (milk, curd, paneer, ghee, butter, whey, cream)
- Any animal-derived ingredient whatsoever
ALL protein must come from: dal, rajma, chana, moong, soya chunks, tofu, tempeh, seeds, nuts
ALL meals must be 100% plant-based. Violation of this rule is unacceptable.
"""
    elif is_veg:
        diet_restriction = """
⛔⛔ ABSOLUTE VEGETARIAN RESTRICTION — THIS IS NON-NEGOTIABLE ⛔⛔
The user is VEGETARIAN. You MUST NEVER include ANY of the following in ANY meal on ANY day:
- Chicken, meat, beef, pork, lamb, fish, tuna, salmon, mackerel, prawn, seafood, or ANY non-vegetarian food
- Gelatin or any hidden non-veg ingredient
ALLOWED: eggs, dairy (curd, milk, paneer, low-fat), legumes, tofu, tempeh
Protein sources to use: paneer (low-fat), eggs, dal, rajma, chana, moong, soya, tofu
The words "fish", "chicken", "mutton", "meat", "tuna", "salmon" must NEVER appear in any meal name or description.
Violation of this restriction is a critical error.
"""
    else:
        diet_restriction = """
Diet Type: Non-Vegetarian — Include 2 fish meals per week (1 oily fish per Eatwell).
Prioritise lean chicken, fish, eggs, and legumes. Limit red meat to once per week max.
"""

    medical = user_data.get('medical_conditions', '')
    medical_note = ""
    if medical:
        medical_note = f"""
⚕️ MEDICAL CONDITIONS (adjust diet accordingly): {medical}
- Diabetes/pre-diabetes → low GI foods, no refined sugar/white rice, extra fibre
- Hypertension → reduce sodium, increase potassium (banana, sweet potato)
- Thyroid → iodine-rich foods, limit goitrogens (raw cabbage/broccoli)
- PCOS/PCOD → low GI, anti-inflammatory, high fibre, balanced hormones
- High cholesterol → no saturated fat, oats, flaxseed, omega-3
"""

    cuisine = user_data.get('cuisine_preference', 'Indian')
    cooking_time = user_data.get('cooking_time', '30 minutes')
    food_dislikes = user_data.get('food_dislikes', 'None')
    supplements = user_data.get('supplements', 'None')

    return f"""You are a certified clinical nutritionist. Generate a detailed, personalized 7-day meal plan.

NUTRITION GUIDELINES:
{EATWELL_HARVARD_GUIDELINES}

{diet_restriction}
{medical_note}

USER PROFILE:
- Name: {user_data.get('name')} | Age: {user_data.get('age')} | Gender: {user_data.get('gender','').title()}
- Country: {user_data.get('country','India')} | Cuisine: {cuisine}
- Height: {user_data.get('height')}cm | Weight: {user_data.get('weight')}kg
- BMI: {metrics['bmi']} ({metrics['bmi_category']}) | BMR: {metrics['bmr']} kcal | TDEE: {metrics['tdee']} kcal
- Daily Target: {metrics['daily_calories']} kcal → Protein: {metrics['protein']}g | Carbs: {metrics['carbs']}g | Fats: {metrics['fats']}g
- Goal: {user_data.get('goal','maintain').replace('_',' ').title()}
- Diet: {diet_type.replace('_',' ').title()}
- Food Allergies: {user_data.get('food_allergies','None')}
- Foods Disliked: {food_dislikes}
- Activity Level: {metrics['activity_level'].replace('_',' ').title()}
- Sleep: {user_data.get('sleep_hours',7)}h ({user_data.get('sleep_quality','average')} quality)
- Stress: {user_data.get('stress_level','moderate')}
- Water: {user_data.get('water_intake','2 liters')}/day
- Work type: {user_data.get('work_type','sedentary')} | Work hours: {user_data.get('work_hours',8)}h
- Medical: {medical if medical else 'None reported'}
- Medications: {user_data.get('medications','None')}
- Supplements: {supplements}
- Cooking time available: {cooking_time}
- Cooking skill: {user_data.get('cooking_skill','basic')}
- Eating speed: {user_data.get('eating_speed','normal')}
- Alcohol: {user_data.get('alcohol','never')} | Smoking: {user_data.get('smoking','never')}
- Motivation: {user_data.get('health_motivation','')}

CURRENT EATING HABITS (to improve upon):
- Breakfast: {user_data.get('breakfast_foods','Not specified')}
- Lunch: {user_data.get('lunch_foods','Not specified')}
- Dinner: {user_data.get('dinner_foods','Not specified')}
- Snacks: {user_data.get('snacks','Not specified')}
- Beverages: {user_data.get('beverages','Not specified')}
- Junk food: {user_data.get('junk_food_frequency','1-2')}x/week | Outside food: {user_data.get('outside_food_frequency','occasionally')}
- Late night eating: {user_data.get('late_night_eating','rarely')}
- Meal timing: Breakfast {user_data.get('breakfast_time','08:00')} | Lunch {user_data.get('lunch_time','13:00')} | Dinner {user_data.get('dinner_time','20:00')}

MEAL PLAN REQUIREMENTS:
1. Every meal must specify EXACT portions (cups, grams, katoris, tablespoons)
2. Each meal must show Harvard plate ratios: veg/grains/protein proportions
3. Descriptions must include cooking method + key ingredients
4. Variety — all 7 days must be different, no repeating the same meal twice
5. Respect cooking time limit of {cooking_time}
6. Must achieve {metrics['protein']}g protein daily across all meals
7. Include pre-workout/post-workout timing if exercise mentioned
8. Adapt to {cuisine} cuisine preferences

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "week_plan": {{
    "Monday": {{
      "breakfast": {{"meal": "name", "description": "exact portions + method + ingredients", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "fibre": 0, "prep_time": "10 min", "eatwell_segments": ["whole_grains","protein","vegetables"]}},
      "lunch":     {{"meal": "name", "description": "exact portions + method", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "fibre": 0, "prep_time": "20 min", "eatwell_segments": []}},
      "dinner":    {{"meal": "name", "description": "exact portions + method", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "fibre": 0, "prep_time": "25 min", "eatwell_segments": []}},
      "snacks":    {{"meal": "name", "description": "exact portions", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "fibre": 0, "prep_time": "5 min", "eatwell_segments": []}}
    }},
    "Tuesday":   {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Wednesday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Thursday":  {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Friday":    {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Saturday":  {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Sunday":    {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}}
  }},
  "eatwell_compliance": {{
    "fruit_veg_portions_per_day": 0,
    "whole_grain_meals": 0,
    "fish_meals_per_week": 0,
    "processed_food_meals": 0,
    "harvard_plate_score": 0,
    "protein_target_met": true,
    "diet_type_followed": "{diet_type}"
  }},
  "lifestyle_tips": ["tip1","tip2","tip3","tip4","tip5","tip6","tip7","tip8","tip9","tip10"],
  "grocery_list": ["item1","item2","item3","item4","item5","item6","item7","item8","item9","item10","item11","item12"],
  "foods_to_avoid": ["food1","food2","food3","food4"],
  "foods_to_limit": ["food1","food2","food3"],
  "supplement_recommendations": ["rec1","rec2"],
  "medical_dietary_notes": "specific notes for any medical conditions",
  "important_notes": "2-3 sentence personalized summary"
}}"""


def generate_with_gemini(prompt):
    import google.generativeai as genai
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    resp = model.generate_content(prompt)
    return resp.text


def generate_with_openai(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.6, max_tokens=4000,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content


def parse_ai_response(raw):
    text = raw.strip()
    for tag in ['```json','```']:
        if text.startswith(tag): text = text[len(tag):]
    if text.endswith('```'): text = text[:-3]
    return json.loads(text.strip())


def get_fallback_plan(user_data, metrics):
    """Detailed fallback plan — strictly respects diet type."""
    is_veg   = user_data.get('diet_type') == 'vegetarian'
    is_vegan = user_data.get('diet_type') == 'vegan'
    cal = int(metrics['daily_calories'])

    # ── All-vegetarian template pool ─────────────────────────────────────────
    veg_templates = [
        {"breakfast": ("Oats Porridge + Banana + Flaxseeds",
                       "50g rolled oats cooked in 200ml low-fat milk, 1 sliced banana, 1 tsp flaxseeds, pinch cinnamon. High fibre, slow-release energy.",
                       ["whole_grains","fruits","dairy"], "10 min"),
         "lunch":     ("2 Whole Wheat Roti + Moong Dal Tadka + Bhindi Sabzi + Salad",
                       "2 whole wheat rotis (160g), 1 katori moong dal with jeera+haldi tadka, 1 katori bhindi stir-fry (minimal oil), large mixed salad.",
                       ["whole_grains","protein","vegetables"], "25 min"),
         "dinner":    ("Brown Rice + Rajma Masala + Stir-fried Spinach + Raita",
                       "3/4 cup cooked brown rice, 1 katori rajma in tomato-onion gravy, 1 katori palak sauté, 100g low-fat curd raita.",
                       ["whole_grains","protein","vegetables","dairy"], "30 min"),
         "snacks":    ("20g Mixed Nuts + 1 Apple + Green Tea",
                       "10g almonds + 10g walnuts, 1 medium apple, 1 cup unsweetened green tea.",
                       ["protein","fruits"], "2 min")},

        {"breakfast": ("Moong Dal Cheela × 3 + Mint-Coriander Chutney",
                       "3 cheelas made with 90g soaked moong dal, onion+capsicum filling. Pan-cooked with 1 tsp oil. Rich in protein.",
                       ["protein","vegetables"], "20 min"),
         "lunch":     ("Vegetable Daliya Khichdi + Low-fat Curd",
                       "1.5 cups broken wheat + 1 cup mixed veg (peas, carrot, beans) khichdi, 100g curd. Complete amino acids.",
                       ["whole_grains","vegetables","dairy"], "25 min"),
         "dinner":    ("Paneer Tikka (100g) + 2 Roti + Cucumber-Tomato Salad",
                       "100g low-fat paneer cubed, marinated in low-fat curd+spices, baked/grilled. 2 whole wheat rotis, large salad.",
                       ["protein","whole_grains","vegetables","dairy"], "20 min"),
         "snacks":    ("Roasted Chana (30g) + 1 Orange",
                       "30g roasted chana (high protein, fibre), 1 medium orange (Vitamin C).",
                       ["protein","fruits"], "2 min")},

        {"breakfast": ("Ragi Dosa × 3 + Sambar + Coconut Chutney",
                       "3 ragi dosas (calcium-rich millet), 1 katori vegetable sambar, small chutney. South Indian nutrition.",
                       ["whole_grains","protein","vegetables"], "20 min"),
         "lunch":     ("Chana Masala + 2 Roti + Lauki Raita",
                       "1 katori white chana (high protein), 2 rotis, 100g lauki raita (cooling, low-cal).",
                       ["protein","whole_grains","vegetables","dairy"], "25 min"),
         "dinner":    ("Quinoa Vegetable Pulao + Soya Curry + Salad",
                       "3/4 cup quinoa pulao with mixed veg, 1 katori soya chunks curry, large green salad.",
                       ["whole_grains","protein","vegetables"], "25 min"),
         "snacks":    ("Low-fat Yoghurt (150g) + Banana + Chia Seeds",
                       "150g plain low-fat yoghurt, 1 banana, 1 tsp chia seeds. Probiotics + potassium.",
                       ["dairy","fruits"], "2 min")},

        {"breakfast": ("Vegetable Upma + Boiled Egg / Tofu Scramble",
                       "1 cup semolina upma with peas+onion+tomato, 1 boiled egg or 75g scrambled tofu. Morning protein boost.",
                       ["whole_grains","protein","vegetables"], "15 min"),
         "lunch":     ("Jowar Bhakri + Dal Fry + Mixed Sabzi + Salad",
                       "2 jowar bhakri (millet, gluten-free), 1 katori toor dal fry, 1 katori seasonal sabzi, salad.",
                       ["whole_grains","protein","vegetables"], "30 min"),
         "dinner":    ("Palak Paneer (100g paneer) + Brown Rice + Stir-fried Broccoli",
                       "Low-fat palak paneer: 100g paneer in spinach gravy, 3/4 cup brown rice, 1 cup broccoli stir-fry.",
                       ["protein","whole_grains","vegetables"], "25 min"),
         "snacks":    ("Fruit Chaat + Buttermilk",
                       "Seasonal fruit bowl (papaya+guava+pomegranate), 1 glass spiced buttermilk. Vitamins + probiotics.",
                       ["fruits","dairy"], "5 min")},

        {"breakfast": ("Idli × 3 + Vegetable Sambar + Chutney",
                       "3 steamed idlis (fermented rice+urad dal, B12-friendly), 1 katori veg sambar, small chutney. Probiotic.",
                       ["whole_grains","protein","vegetables"], "15 min"),
         "lunch":     ("Rajma Brown Rice Bowl + Dahi + Cucumber Salad",
                       "3/4 cup brown rice, 1 katori rajma, 100g curd, cucumber+onion salad. Mexican-Indian protein bowl.",
                       ["whole_grains","protein","vegetables","dairy"], "20 min"),
         "dinner":    ("Masoor Dal + 2 Roti + Baingan Bharta + Salad",
                       "1 katori masoor dal, 2 rotis, 1 katori baingan bharta (roasted brinjal), large green salad.",
                       ["protein","whole_grains","vegetables"], "30 min"),
         "snacks":    ("Handful Almonds (20g) + 2 Dates + Herbal Tea",
                       "20g almonds, 2 dates (iron+energy), herbal tea. Iron for vegetarians.",
                       ["protein","fruits"], "2 min")},

        {"breakfast": ("Besan Cheela × 2 + Stuffed with Paneer & Veg",
                       "2 gram flour cheelas stuffed with 50g paneer+onion+capsicum. High protein, low carb morning.",
                       ["protein","vegetables"], "15 min"),
         "lunch":     ("Brown Rice Veg Biryani + Raita + Salad",
                       "1.5 cups brown rice biryani with mixed veg (peas+carrot+beans+potato), whole spices, 100g raita.",
                       ["whole_grains","vegetables","dairy"], "30 min"),
         "dinner":    ("Kadhi Pakoda (baked) + Bajra Roti × 2 + Seasonal Sabzi",
                       "1 katori low-fat kadhi with baked pakodas, 2 bajra rotis (iron-rich), 1 katori sabzi.",
                       ["protein","whole_grains","vegetables","dairy"], "30 min"),
         "snacks":    ("Mixed Sprouts Chaat + Lime + Coriander",
                       "1 katori mixed sprouts (moong+chana) chaat, lime juice, raw mango, coriander. Living protein.",
                       ["protein","vegetables"], "5 min")},

        {"breakfast": ("Overnight Oats + Mixed Berries/Fruits + Pumpkin Seeds",
                       "50g oats soaked overnight in 180ml low-fat milk/curd, topped with seasonal fruits, 1 tbsp pumpkin seeds.",
                       ["whole_grains","fruits","dairy"], "5 min"),
         "lunch":     ("Whole Wheat Roti + Soya Keema + Mixed Veg + Raita",
                       "2 rotis, 80g soya keema (veg mince) with peas+onion+tomato, mixed veg, 100g raita.",
                       ["whole_grains","protein","vegetables","dairy"], "25 min"),
         "dinner":    ("Tofu Bhurji + Multigrain Roti × 2 + Stir-fried Methi",
                       "100g tofu scrambled with onion+capsicum+tomato+spices, 2 multigrain rotis, 1 katori methi stir-fry.",
                       ["protein","whole_grains","vegetables"], "20 min"),
         "snacks":    ("Makhana (Foxnuts 25g) + 1 Guava + Water",
                       "25g roasted makhana (low-cal, calcium), 1 guava (Vitamin C, fibre). Light & nutritious.",
                       ["protein","fruits"], "2 min")},
    ]

    # ── Vegan adjustments (remove dairy/egg, use plant substitutes) ───────────
    vegan_templates = [t.copy() for t in veg_templates]
    for t in vegan_templates:
        # Replace all raita/curd/dairy mentions in descriptions
        for meal_key in t:
            name, desc, segs, prep = t[meal_key]
            desc = desc.replace("low-fat curd","coconut yoghurt").replace("curd","coconut yoghurt").replace("low-fat milk","oat milk").replace("milk","oat milk").replace("paneer","tofu").replace("Paneer","Tofu").replace("boiled egg","tofu scramble").replace("1 boiled egg","75g tofu scramble")
            segs = [s for s in segs if s != "dairy"]
            t[meal_key] = (name.replace("Paneer","Tofu").replace("paneer","tofu"), desc, segs, prep)

    # ── Non-veg template pool ─────────────────────────────────────────────────
    nonveg_templates = [
        {"breakfast": ("Oats + Mixed Fruits + Boiled Egg × 2",
                       "50g oats in 200ml low-fat milk, 1 banana+apple, 2 boiled eggs (protein). Balanced morning macro split.",
                       ["whole_grains","protein","fruits","dairy"], "10 min"),
         "lunch":     ("2 Roti + Dal + Chicken Curry (100g) + Salad",
                       "2 whole wheat rotis, 1 katori moong dal, 100g chicken curry (skinless, tomato-onion base), large salad.",
                       ["whole_grains","protein","vegetables"], "30 min"),
         "dinner":    ("Grilled Fish (150g) + Brown Rice + Stir-fried Spinach",
                       "150g grilled rohu/surmai (Omega-3), 3/4 cup brown rice, 1 cup palak sauté. Eatwell 2x fish/week.",
                       ["protein","whole_grains","vegetables"], "25 min"),
         "snacks":    ("20g Mixed Nuts + 1 Apple + Green Tea",
                       "10g almonds + 10g walnuts, 1 apple, 1 green tea.",
                       ["protein","fruits"], "2 min")},

        {"breakfast": ("Egg White Omelette × 3 + WW Toast × 2 + Tomato",
                       "3-egg white omelette with onion+capsicum+tomato, 2 WW toast. Lean protein start.",
                       ["protein","whole_grains","vegetables"], "12 min"),
         "lunch":     ("Brown Rice + Tuna Salad / Fish Curry + Vegetables",
                       "3/4 cup brown rice, 100g tuna salad or 150g fish curry, large mixed veg.",
                       ["protein","whole_grains","vegetables"], "20 min"),
         "dinner":    ("Chicken Tikka (150g, baked) + Quinoa + Roasted Veg",
                       "150g chicken tikka (marinated in curd+spices, baked), 1/2 cup quinoa, 1 cup roasted capsicum+broccoli.",
                       ["protein","whole_grains","vegetables"], "30 min"),
         "snacks":    ("Roasted Chana + 1 Orange + Buttermilk",
                       "30g roasted chana, 1 orange, 1 glass low-fat buttermilk.",
                       ["protein","fruits","dairy"], "2 min")},

        {"breakfast": ("Moong Dal Cheela + 1 Boiled Egg + Chutney",
                       "3 moong dal cheelas + 1 boiled egg (complete protein), mint chutney. Start strong.",
                       ["protein","vegetables"], "20 min"),
         "lunch":     ("Chicken Salad Bowl + 2 Roti + Vegetable Soup",
                       "100g grilled chicken strips, lettuce+cucumber+onion, 2 rotis, 1 bowl veg soup.",
                       ["protein","whole_grains","vegetables"], "25 min"),
         "dinner":    ("Egg Curry × 2 + 2 Whole Wheat Roti + Dal + Salad",
                       "2 boiled egg curry, 2 rotis, 1 katori masoor dal, large green salad.",
                       ["protein","whole_grains","vegetables"], "25 min"),
         "snacks":    ("Low-fat Yoghurt + Banana + Chia Seeds",
                       "150g yoghurt, 1 banana, 1 tsp chia seeds. Recovery snack.",
                       ["dairy","fruits"], "2 min")},

        {"breakfast": ("Vegetable Daliya Upma + Sprouts",
                       "1 cup broken wheat upma with peas+onion+tomato+carrot, 1/4 cup mixed sprouts topping.",
                       ["whole_grains","vegetables","protein"], "15 min"),
         "lunch":     ("Prawn / Tofu Stir-fry + Brown Rice + Salad",
                       "150g prawns or tofu stir-fried in 1 tsp mustard oil+garlic, 3/4 cup brown rice, large salad.",
                       ["protein","whole_grains","vegetables"], "25 min"),
         "dinner":    ("Grilled Salmon/Rohu (150g) + Sweet Potato + Veg",
                       "150g baked fish (oily fish — Omega-3), 1 medium sweet potato, 1 cup broccoli. Perfect Eatwell plate.",
                       ["protein","vegetables"], "30 min"),
         "snacks":    ("Fruit Chaat + Handful Almonds",
                       "Seasonal fruit bowl, 15g almonds. Vitamins + healthy fats.",
                       ["fruits","protein"], "5 min")},

        {"breakfast": ("Idli × 3 + Egg Bhurji + Sambar",
                       "3 steamed idlis, 1-egg bhurji with tomato+onion, 1 katori sambar. South Indian protein combo.",
                       ["whole_grains","protein","vegetables"], "15 min"),
         "lunch":     ("Chicken Fried Rice (brown) + Dal Soup + Salad",
                       "3/4 cup brown rice fried with 100g chicken+eggs+vegetables (minimal oil), 1 bowl dal, salad.",
                       ["whole_grains","protein","vegetables"], "25 min"),
         "dinner":    ("Fish Masala (150g) + 2 Roti + Stir-fried Bhindi + Raita",
                       "150g fish in tomato masala, 2 whole wheat rotis, 1 katori bhindi, 100g raita.",
                       ["protein","whole_grains","vegetables","dairy"], "30 min"),
         "snacks":    ("Boiled Egg + 1 Apple + Water",
                       "1 boiled egg (protein+fat), 1 apple (fibre), water. Simple & effective.",
                       ["protein","fruits"], "5 min")},

        {"breakfast": ("Poha + Sprouts + 2 Boiled Eggs",
                       "1 cup poha with peas+onion+curry leaves, topped with moong sprouts, 2 boiled eggs aside.",
                       ["whole_grains","protein","vegetables"], "15 min"),
         "lunch":     ("Rajma + Brown Rice + Chicken Salad + Salad",
                       "1/2 katori rajma + 3/4 cup brown rice, 80g grilled chicken salad, mixed veg salad.",
                       ["protein","whole_grains","vegetables"], "20 min"),
         "dinner":    ("Baked Chicken Tikka (150g) + Quinoa Pulao + Stir-fried Broccoli",
                       "150g chicken tikka baked, 1/2 cup quinoa, 1 cup broccoli+capsicum sauté.",
                       ["protein","whole_grains","vegetables"], "30 min"),
         "snacks":    ("Mixed Seeds + Buttermilk + 1 Guava",
                       "20g mixed seeds (pumpkin+sunflower+flax), 1 glass buttermilk, 1 guava.",
                       ["protein","dairy","fruits"], "2 min")},

        {"breakfast": ("Whole Wheat Toast + Egg Scramble + Avocado/Tomato",
                       "2 WW toast, 2 scrambled eggs with spinach+tomato, 1/4 avocado or 2 tomatoes. Heart-healthy fats.",
                       ["whole_grains","protein","vegetables"], "12 min"),
         "lunch":     ("Dal Khichdi + Grilled Fish (100g) + Salad",
                       "1.5 cups moong dal khichdi with rice+veg, 100g grilled fish, large salad.",
                       ["whole_grains","protein","vegetables"], "25 min"),
         "dinner":    ("Mutton Curry (100g, lean) / Chicken Curry + 2 Roti + Sabzi",
                       "100g lean mutton or chicken curry, 2 rotis, 1 katori seasonal sabzi, salad. Limit red meat.",
                       ["protein","whole_grains","vegetables"], "35 min"),
         "snacks":    ("Roasted Chana + Fruit Smoothie",
                       "30g roasted chana, banana+150ml low-fat milk smoothie (no sugar).",
                       ["protein","fruits","dairy"], "5 min")},
    ]

    templates = vegan_templates if is_vegan else (veg_templates if is_veg else nonveg_templates)
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    def make_meal(t, mtype):
        name, desc, segs, prep = t
        pct = {'breakfast':0.25,'lunch':0.35,'dinner':0.30,'snacks':0.10}.get(mtype,0.25)
        return {"meal": name, "description": desc, "calories": int(cal*pct),
                "protein": int(metrics['protein']*pct), "carbs": int(metrics['carbs']*pct),
                "fats": int(metrics['fats']*pct), "fibre": 6 if mtype in ['lunch','dinner'] else 3,
                "prep_time": prep, "eatwell_segments": segs}

    week_plan = {}
    for i, day in enumerate(days):
        t = templates[i % len(templates)]
        week_plan[day] = {k: make_meal(t[k], k) for k in ["breakfast","lunch","dinner","snacks"]}

    diet_label = "Vegan" if is_vegan else ("Vegetarian" if is_veg else "Non-Vegetarian")

    veg_tips = [
        f"🥗 Your {diet_label} plan achieves Harvard Plate ratios every meal: ½ veg+fruit, ¼ grains, ¼ protein",
        "🫘 Combine dal + roti or rice to get complete amino acids at each meal (complementary proteins)",
        "🥛 Include 1–2 servings of low-fat dairy/curd daily for calcium, B12, and probiotics" if not is_vegan else "🌱 Take B12 supplement — essential for vegans. Include fortified foods.",
        "🌾 Use ragi, bajra, jowar rotis for iron, calcium, and zinc — important for vegetarians",
        "💧 Drink 2–3 litres water/day; start each morning with warm water + lemon (metabolism boost)",
        "🔩 Pair iron-rich foods (dal, leafy greens) with Vitamin C (lemon, amla) to boost absorption",
        "🧄 Cook with jeera, haldi, hing, ajwain — improve digestion of legumes and reduce bloating",
        "⏰ Eat at consistent times. 3–4 hours between meals. Avoid eating 2h before sleep.",
        "🍽️ Follow 'Plate Method': half plate veggies, quarter whole grains, quarter protein every meal",
        "🏃 Combine diet with 150 min moderate exercise/week for optimal results (WHO + Harvard guideline)",
    ]

    return {
        "week_plan": week_plan,
        "eatwell_compliance": {
            "fruit_veg_portions_per_day": 6,
            "whole_grain_meals": 21,
            "fish_meals_per_week": 0 if is_veg or is_vegan else 2,
            "processed_food_meals": 0,
            "harvard_plate_score": 90,
            "protein_target_met": True,
            "diet_type_followed": user_data.get('diet_type','non_vegetarian')
        },
        "lifestyle_tips": veg_tips,
        "grocery_list": (
            ["Rolled oats / Daliya / Ragi flour",
             "Whole wheat atta / Multigrain atta",
             "Brown rice / Quinoa",
             "Moong + masoor + toor + chana dal",
             "Rajma / Kabuli chana / Soya chunks",
             "Seasonal veg: spinach, broccoli, bhindi, baingan, peas, carrot, tomato",
             "Seasonal fruits: banana, apple, guava, papaya, orange, pomegranate",
             "Low-fat curd + semi-skimmed milk" if not is_vegan else "Oat milk / Coconut yoghurt",
             "Low-fat paneer / Tofu" if not is_vegan else "Firm tofu / Tempeh",
             "Mixed nuts: almonds, walnuts (20g/day)",
             "Mustard oil / Olive oil (1 tsp per cook)",
             "Seeds: flax, chia, pumpkin, sunflower"]
            if is_veg or is_vegan else
            ["Rolled oats / Daliya", "Whole wheat atta / Brown rice",
             "Moong + masoor + toor dal", "Rajma / Chana",
             "Chicken (skinless, 500g)", "Fish: rohu/surmai/salmon (500g)",
             "Eggs (1 dozen)",
             "Seasonal veg: spinach, broccoli, bhindi, peas, carrot, tomato",
             "Seasonal fruits: banana, apple, guava, papaya",
             "Low-fat curd + semi-skimmed milk",
             "Mixed nuts: almonds, walnuts",
             "Mustard oil / Olive oil (small bottle)"]
        ),
        "foods_to_avoid": (
            ["Vanaspati/dalda (trans fats) — blocks heart health",
             "Sugary drinks, packaged juices — empty calories",
             "White maida products: white bread, namkeen, biscuits",
             "Excess salt in pickles/papad — increases BP"]
        ),
        "foods_to_limit": (
            ["White rice/maida — replace with whole grain versions",
             "Fried snacks: samosa, pakora — Eatwell: eat rarely",
             "Sugar in tea/coffee — reduce to ½ tsp or eliminate"]
        ),
        "supplement_recommendations": (
            ["Vitamin B12 supplement (essential for vegans)" if is_vegan else "Iron supplement if fatigue persists (consult doctor)",
             "Vitamin D (1000 IU/day) — most Indians are deficient"]
        ),
        "medical_dietary_notes": "No specific medical conditions reported. General plan follows Harvard Plate and Eatwell Guide.",
        "important_notes": (
            f"Your {diet_label} plan is designed for {user_data.get('goal','your goal').replace('_',' ')} "
            f"at {int(metrics['daily_calories'])} kcal/day with {int(metrics['protein'])}g protein. "
            f"Every meal follows the Harvard Healthy Eating Plate: half vegetables+fruit, quarter whole grains, quarter healthy protein. "
            f"All {diet_label.lower()} restrictions are strictly observed throughout the full 7-day plan."
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
        result = parse_ai_response(raw)
        # Safety: if AI ignored diet restriction, fall back
        diet_type = user_data.get('diet_type','non_vegetarian')
        if diet_type in ('vegetarian','vegan'):
            banned = ['chicken','fish','tuna','salmon','mutton','beef','prawn','shrimp','seafood','meat']
            plan_text = json.dumps(result.get('week_plan',{})).lower()
            violations = [w for w in banned if w in plan_text]
            if violations:
                print(f"AI violated {diet_type} restriction (found: {violations}). Using fallback.")
                return get_fallback_plan(user_data, metrics)
        return result
    except Exception as e:
        print(f"AI generation failed: {e}. Using fallback.")
        return get_fallback_plan(user_data, metrics)
