"""
Simple in-memory plan cache — reduces Gemini API calls for similar profiles.
Cache key = hash of key user parameters. TTL = 6 hours.
"""
import hashlib, json, time

_cache: dict = {}
_TTL = 6 * 3600  # 6 hours


def _make_key(user_data: dict, metrics: dict) -> str:
    key_fields = {
        'diet_type':    user_data.get('diet_type'),
        'goal':         user_data.get('goal'),
        'gender':       user_data.get('gender'),
        'age_band':     (user_data.get('age', 25) // 10) * 10,
        'bmi_cat':      metrics.get('bmi_category'),
        'cal_band':     (int(metrics.get('daily_calories', 2000)) // 100) * 100,
        'activity':     metrics.get('activity_level'),
        'medical':      user_data.get('medical_conditions', ''),
        'cuisine':      user_data.get('cuisine_preference', 'Indian'),
    }
    raw = json.dumps(key_fields, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(user_data: dict, metrics: dict):
    key = _make_key(user_data, metrics)
    entry = _cache.get(key)
    if entry and (time.time() - entry['ts']) < _TTL:
        print(f"Cache HIT for key {key[:8]}")
        return entry['plan']
    return None


def set_cached(user_data: dict, metrics: dict, plan: dict):
    key = _make_key(user_data, metrics)
    _cache[key] = {'plan': plan, 'ts': time.time()}
    # Prune old entries if cache grows large
    if len(_cache) > 200:
        oldest = sorted(_cache.items(), key=lambda x: x[1]['ts'])[:50]
        for k, _ in oldest:
            del _cache[k]


def cache_stats():
    now = time.time()
    valid = sum(1 for v in _cache.values() if (now - v['ts']) < _TTL)
    return {'total': len(_cache), 'valid': valid}
