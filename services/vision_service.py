"""
Food image recognition using Google Gemini Vision API.
Accepts base64-encoded image, returns estimated nutrition data.
"""
import json, base64
from config import Config


VISION_PROMPT = """You are a professional nutritionist and food recognition expert.
Analyze this food image and provide a detailed nutritional estimate.

Identify ALL food items visible. For each item, estimate portion size based on visual cues 
(plate size, utensils, hands for scale).

Respond ONLY with valid JSON, no markdown:
{
  "identified_foods": [
    {"name": "food name", "portion": "estimated portion (e.g. 1 cup, 2 pieces, 150g)", 
     "calories": 0, "protein": 0, "carbs": 0, "fats": 0}
  ],
  "total": {"calories": 0, "protein": 0, "carbs": 0, "fats": 0},
  "meal_type_guess": "breakfast/lunch/dinner/snack",
  "health_rating": "excellent/good/moderate/poor",
  "health_notes": "brief note about nutritional quality",
  "confidence": "high/medium/low"
}
If image is not food, return: {"error": "No food detected in image"}"""


def analyze_food_image(image_data: str, mime_type: str = "image/jpeg") -> dict:
    """
    Analyze a food image using Gemini Vision.
    image_data: base64-encoded image string
    Returns dict with nutrition data or error
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Decode base64 to bytes
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

        import google.generativeai as genai
        image_part = {
            "mime_type": mime_type,
            "data": image_bytes
        }

        response = model.generate_content([VISION_PROMPT, image_part])
        raw = response.text.strip()

        # Clean markdown if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0]

        result = json.loads(raw.strip())
        return result

    except json.JSONDecodeError:
        return {"error": "Could not parse AI response", "raw": raw[:200] if 'raw' in dir() else ""}
    except Exception as e:
        return {"error": str(e)}


def analyze_voice_text(transcript: str, user_context: dict = None) -> dict:
    """
    Parse a voice/text description of a meal into nutrition data.
    e.g. "I had two boiled eggs and a slice of whole wheat toast"
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        cuisine = user_context.get('cuisine_preference', 'Indian') if user_context else 'Indian'

        prompt = f"""You are a nutritionist. Parse this meal description and estimate nutrition.
Meal description: "{transcript}"
User cuisine preference: {cuisine}

Respond ONLY with valid JSON:
{{
  "identified_foods": [
    {{"name": "food name", "portion": "quantity", "calories": 0, "protein": 0, "carbs": 0, "fats": 0}}
  ],
  "total": {{"calories": 0, "protein": 0, "carbs": 0, "fats": 0}},
  "meal_type_guess": "breakfast/lunch/dinner/snack",
  "cleaned_description": "standardized description for diary entry"
}}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0]
        return json.loads(raw.strip())

    except Exception as e:
        return {"error": str(e)}
