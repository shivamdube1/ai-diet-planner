import os
import json
from config import Config


def build_prompt(user_data, metrics):
    """Build the AI prompt from user data and calculated metrics."""
    goal_map = {
        'weight_loss': 'Weight Loss',
        'muscle_gain': 'Muscle Gain',
        'maintain': 'Weight Maintenance'
    }
    diet_map = {
        'vegetarian': 'Vegetarian',
        'non_vegetarian': 'Non-Vegetarian',
        'vegan': 'Vegan'
    }

    prompt = f"""You are a professional nutritionist and dietitian. Generate a detailed, personalized 7-day diet plan for the following person.

USER PROFILE:
- Name: {user_data.get('name', 'User')}
- Age: {user_data.get('age')} years
- Gender: {user_data.get('gender').title()}
- Height: {user_data.get('height')} cm
- Weight: {user_data.get('weight')} kg
- Country: {user_data.get('country', 'India')}

HEALTH METRICS:
- BMI: {metrics['bmi']} ({metrics['bmi_category']})
- BMR: {metrics['bmr']} kcal/day
- TDEE: {metrics['tdee']} kcal/day
- Daily Calorie Target: {metrics['daily_calories']} kcal
- Protein Target: {metrics['protein']}g/day
- Carbohydrates Target: {metrics['carbs']}g/day
- Fats Target: {metrics['fats']}g/day

GOALS & PREFERENCES:
- Primary Goal: {goal_map.get(user_data.get('goal'), 'Maintain Weight')}
- Target Weight: {user_data.get('target_weight', 'Not specified')} kg
- Diet Type: {diet_map.get(user_data.get('diet_type'), 'Non-Vegetarian')}
- Food Allergies/Restrictions: {user_data.get('food_allergies', 'None')}
- Budget: {user_data.get('budget_preference', 'Moderate')}

LIFESTYLE:
- Activity Level: {metrics['activity_level'].replace('_', ' ').title()}
- Exercise: {user_data.get('exercise_type', 'Walking')} — {user_data.get('activity_level', '3-5')} days/week
- Daily Steps: {user_data.get('daily_steps', '3000-6000')}
- Sleep: {user_data.get('sleep_hours', 7)} hours, quality: {user_data.get('sleep_quality', 'Average')}
- Stress Level: {user_data.get('stress_level', 'Moderate')}
- Work Type: {user_data.get('work_type', 'Sedentary desk job')}
- Water Intake: {user_data.get('water_intake', '1-2 liters')}/day

CURRENT EATING HABITS:
- Breakfast: {user_data.get('breakfast_foods', 'Not specified')}
- Lunch: {user_data.get('lunch_foods', 'Not specified')}
- Dinner: {user_data.get('dinner_foods', 'Not specified')}
- Snacks: {user_data.get('snacks', 'Not specified')}
- Beverages: {user_data.get('beverages', 'Not specified')}
- Meals per day: {user_data.get('meals_per_day', 3)}
- Outside food frequency: {user_data.get('outside_food_frequency', 'Occasionally')}
- Junk food per week: {user_data.get('junk_food_frequency', '1-2 times')}

MEAL TIMING:
- Breakfast: {user_data.get('breakfast_time', '8:00 AM')}
- Lunch: {user_data.get('lunch_time', '1:00 PM')}
- Dinner: {user_data.get('dinner_time', '8:00 PM')}
- Late night eating: {user_data.get('late_night_eating', 'Rarely')}

INSTRUCTIONS:
1. Use primarily Indian food options with local ingredients
2. Keep it practical, affordable, and easy to prepare
3. Include exact portion sizes
4. Account for the meal timing preferences

Respond ONLY with a valid JSON object in exactly this format (no markdown, no extra text):
{{
  "week_plan": {{
    "Monday": {{
      "breakfast": {{"meal": "meal name", "description": "brief description", "calories": 000, "protein": 00, "carbs": 00, "fats": 00}},
      "lunch": {{"meal": "meal name", "description": "brief description", "calories": 000, "protein": 00, "carbs": 00, "fats": 00}},
      "dinner": {{"meal": "meal name", "description": "brief description", "calories": 000, "protein": 00, "carbs": 00, "fats": 00}},
      "snacks": {{"meal": "snack name", "description": "brief description", "calories": 000, "protein": 00, "carbs": 00, "fats": 00}}
    }},
    "Tuesday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Wednesday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Thursday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Friday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Saturday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}},
    "Sunday": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": {{}}}}
  }},
  "lifestyle_tips": [
    "tip 1",
    "tip 2",
    "tip 3",
    "tip 4",
    "tip 5",
    "tip 6"
  ],
  "grocery_list": ["item1", "item2", "item3", "item4", "item5", "item6", "item7", "item8"],
  "important_notes": "A 2-3 sentence personalized note about their plan"
}}"""
    return prompt


def generate_with_gemini(prompt):
    """Generate diet plan using Google Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")


def generate_with_openai(prompt):
    """Generate diet plan using OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def parse_ai_response(raw_text):
    """Parse and clean the AI JSON response."""
    text = raw_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return json.loads(text.strip())


def get_fallback_plan(user_data, metrics):
    """Return a static fallback plan when AI is unavailable."""
    is_veg = user_data.get('diet_type') in ['vegetarian', 'vegan']
    cal = int(metrics['daily_calories'])
    
    protein_food = "Paneer 100g + Dal" if is_veg else "Chicken breast 150g"
    lunch_main = "Rajma chawal + raita" if is_veg else "Chicken curry + 2 roti"
    dinner_main = "Mixed veg sabzi + 2 roti + dal" if is_veg else "Fish curry + rice + salad"

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_plan = {}
    for day in days:
        week_plan[day] = {
            "breakfast": {
                "meal": "Oats Upma + Boiled Eggs" if not is_veg else "Oats Upma + Fruit",
                "description": "Nutritious morning meal with complex carbs and protein",
                "calories": int(cal * 0.25), "protein": int(metrics['protein'] * 0.25),
                "carbs": int(metrics['carbs'] * 0.25), "fats": int(metrics['fats'] * 0.25)
            },
            "lunch": {
                "meal": lunch_main,
                "description": "Balanced midday meal with protein and carbohydrates",
                "calories": int(cal * 0.35), "protein": int(metrics['protein'] * 0.35),
                "carbs": int(metrics['carbs'] * 0.35), "fats": int(metrics['fats'] * 0.35)
            },
            "dinner": {
                "meal": dinner_main,
                "description": "Light, nutritious dinner to support recovery",
                "calories": int(cal * 0.30), "protein": int(metrics['protein'] * 0.30),
                "carbs": int(metrics['carbs'] * 0.30), "fats": int(metrics['fats'] * 0.30)
            },
            "snacks": {
                "meal": "Mixed nuts + fruits" if is_veg else "Boiled eggs + fruits",
                "description": "Healthy mid-meal snack",
                "calories": int(cal * 0.10), "protein": int(metrics['protein'] * 0.10),
                "carbs": int(metrics['carbs'] * 0.10), "fats": int(metrics['fats'] * 0.10)
            }
        }

    return {
        "week_plan": week_plan,
        "lifestyle_tips": [
            "Drink at least 8 glasses of water daily",
            "Avoid processed and packaged foods",
            "Eat slowly and mindfully — chew each bite well",
            "Don't skip breakfast — it sets your metabolism for the day",
            "Include a 20–30 minute walk after dinner",
            "Sleep 7–8 hours per night for optimal recovery"
        ],
        "grocery_list": [
            "Oats", "Brown rice", "Lentils (dal)", "Vegetables (seasonal)",
            "Fruits (banana, apple, papaya)", "Curd/yogurt", "Nuts and seeds",
            "Whole wheat roti flour"
        ],
        "important_notes": f"This plan is designed to help you reach your {user_data.get('goal', 'health')} goal with {int(metrics['daily_calories'])} calories/day. Adjust portions based on hunger and energy levels."
    }


def generate_diet_plan(user_data, metrics):
    """Main function to generate AI diet plan."""
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
