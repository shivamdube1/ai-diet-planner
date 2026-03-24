import base64
import os
import re
import tempfile
from typing import Any, Dict, Optional, Tuple

from config import Config


def _strip_data_url_prefix(data: str) -> Tuple[str, Optional[str]]:
    """
    Accepts either:
      - raw base64 string
      - data URL: data:<mime>;base64,<payload>
    Returns (base64_payload, mime_type_from_data_url_or_none)
    """
    m = re.match(r"^\s*data:([^;]+);base64,(.*)\s*$", data, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return data.strip(), None
    return m.group(2).strip(), m.group(1).strip()


def _decode_base64(data: str) -> bytes:
    return base64.b64decode(data, validate=True)


def _gemini_text(prompt: str) -> str:
    import google.generativeai as genai

    if not Config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def _gemini_vision(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """
    Uses google-generativeai's upload_file() API by writing a temporary file.
    This keeps the service self-contained and avoids extra image dependencies.
    """
    import google.generativeai as genai

    if not Config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=Config.GEMINI_API_KEY)

    suffix = ".jpg"
    if mime_type.lower() in ("image/png", "png"):
        suffix = ".png"
    elif mime_type.lower() in ("image/webp", "webp"):
        suffix = ".webp"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        tmp_path = f.name
        f.write(image_bytes)

    try:
        uploaded = genai.upload_file(tmp_path)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content([prompt, uploaded])
        return (resp.text or "").strip()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def analyze_food_image(image_data: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Returns a JSON-serializable dict. Designed to be resilient:
    - Works even when no AI key is configured (returns a friendly error).
    - If Gemini is configured, attempts multimodal analysis.
    """
    b64, mime_from_data_url = _strip_data_url_prefix(image_data or "")
    mime = (mime_from_data_url or mime_type or "image/jpeg").strip()

    try:
        image_bytes = _decode_base64(b64)
    except Exception:
        return {"success": False, "error": "Invalid base64 image payload"}

    if not Config.GEMINI_API_KEY and not Config.OPENAI_API_KEY:
        return {
            "success": False,
            "error": "Food image analysis is not configured (set GEMINI_API_KEY or OPENAI_API_KEY).",
        }

    prompt = (
        "You are a nutrition assistant. Analyze the food in the photo and return JSON only with keys:\n"
        "foods (array of {name, portion_guess}), total_calories_kcal (number), "
        "macros_g ({protein, carbs, fats}), confidence (0-1), notes (string).\n"
        "If uncertain, keep confidence low and explain in notes."
    )

    # Prefer Gemini because this project already uses it elsewhere.
    if Config.GEMINI_API_KEY:
        try:
            text = _gemini_vision(prompt, image_bytes, mime)
            return {"success": True, "provider": "gemini", "raw": text}
        except Exception as e:
            return {"success": False, "provider": "gemini", "error": str(e)}

    # OpenAI vision can be added later; return a clear message for now.
    return {"success": False, "provider": "openai", "error": "OpenAI vision is not implemented in this build."}


def analyze_voice_text(transcript: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight transcript analysis used by /api/voice-log.
    If AI isn't configured, falls back to a basic heuristic extraction.
    """
    t = (transcript or "").strip()
    if not t:
        return {"success": False, "error": "Empty transcript"}

    if Config.GEMINI_API_KEY:
        prompt = (
            "You are a nutrition coach. Given the user's voice transcript describing meals, "
            "extract what they ate and summarize potential issues.\n\n"
            f"User context (may be empty): {user or {}}\n\n"
            f"Transcript:\n{t}\n\n"
            "Return JSON only with keys: items (array of strings), summary (string), "
            "warnings (array of strings), suggested_next_step (string)."
        )
        try:
            text = _gemini_text(prompt)
            return {"success": True, "provider": "gemini", "raw": text}
        except Exception as e:
            return {"success": False, "provider": "gemini", "error": str(e)}

    # Fallback: naive extraction of likely food tokens.
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\\-']{2,}", t.lower())
    stop = {
        "today",
        "yesterday",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
        "snacks",
        "ate",
        "had",
        "have",
        "with",
        "and",
        "then",
        "also",
        "some",
        "a",
        "an",
        "the",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "my",
        "i",
    }
    items = []
    for tok in tokens:
        if tok in stop:
            continue
        if tok not in items:
            items.append(tok)
        if len(items) >= 12:
            break

    return {
        "success": True,
        "provider": "heuristic",
        "items": items,
        "summary": "Transcript captured. Enable GEMINI_API_KEY for richer analysis.",
        "warnings": [],
        "suggested_next_step": "Log quantities/portions to estimate calories and macros.",
    }

