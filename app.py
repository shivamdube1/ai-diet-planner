

import os, uuid, json, secrets, logging, time
from functools import wraps
from datetime import date, datetime, timezone
from urllib.parse import urlparse
from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, flash, Response, make_response, abort)
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models.user_model   import create_tables, save_user, get_user_by_id, add_extended_columns
from models.diet_plan_model import save_diet_plan, get_diet_plan_by_user
from models.progress_model  import add_progress_entry, get_progress_by_user, get_latest_weight
from models.admin_model  import (get_all_users_with_plans, get_admin_stats,
                                  get_user_full_detail, delete_user_cascade,
                                  get_signups_last_30_days)
from models.auth_model   import (create_accounts_table, register_account, login_account,
                                  get_account_by_id, update_account, change_password,
                                  get_profiles_for_account, link_user_to_account,
                                  get_account_by_email, get_account_by_google_id,
                                  register_google_account)
from models.diary_model  import (add_diary_entry, get_diary_by_user_date,
                                  delete_diary_entry, get_diary_summary)
from models.reset_model  import (create_reset_token_table, create_reset_token,
                                  validate_reset_token, mark_token_used)
from services.diet_calculator  import run_all_calculations
from services.ai_diet_generator import generate_diet_plan
from services.health_analyzer  import analyze_health
from services.rate_limiter import is_allowed, get_ip
from services.plan_cache import get_cached, set_cached, cache_stats
from services.vision_service import analyze_food_image, analyze_voice_text
from services.meal_swap import swap_meal
from services.password_validator import validate_password

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ── CSRF Protection ──────────────────────────────────────────────────────────
csrf = CSRFProtect(app)

# Hash the admin password at startup for secure comparison
_ADMIN_PW_HASH = generate_password_hash(Config.ADMIN_PASSWORD)

os.makedirs('database', exist_ok=True)
try:
    create_tables()
    add_extended_columns()
    create_accounts_table()
    create_reset_token_table()
except Exception as e:
    app.logger.warning(f"⚠️  Database initialization failed (will retry on first request): {e}")


@app.context_processor
def inject_now():
    return {'now': lambda: datetime.now(timezone.utc)}


# ── Helpers ───────────────────────────────────────────────────────────────────

# Structured Security Event Logging
sec_logger = logging.getLogger('nutriai.security')
sec_logger.setLevel(logging.WARNING)

def sec_log(event: str, ip: str, extra: dict = None):
    """Emit a structured security event to stdout (captured by Render logs)."""
    payload = {
        'ts':    datetime.now(timezone.utc).isoformat(),
        'event': event,
        'ip':    ip,
        **(extra or {})
    }
    sec_logger.warning(json.dumps(payload))


# Brute force login tracking & lockout (in-memory)
_failed_logins = {}  # {email: [timestamp, ...]}

def record_failed_login(email: str) -> bool:
    """Record a failed login attempt. Returns True if account is now locked."""
    email_clean = (email or '').strip().lower()
    if not email_clean:
        return False
    now = time.time()
    window = 900  # 15 minutes
    attempts = [t for t in _failed_logins.get(email_clean, []) if now - t < window]
    attempts.append(now)
    _failed_logins[email_clean] = attempts
    return len(attempts) >= 10

def is_account_locked(email: str) -> bool:
    """Check if the account is locked."""
    email_clean = (email or '').strip().lower()
    if not email_clean:
        return False
    now = time.time()
    attempts = [t for t in _failed_logins.get(email_clean, []) if now - t < 900]
    return len(attempts) >= 10


# Request Anomaly Scanner
def detect_anomalies(req):
    """Scan request metadata and payload for anomalies."""
    ip = get_ip(req)
    ua = req.headers.get('User-Agent', '')
    size = req.content_length or 0
    anomalies = []

    # 1. Suspicious User-Agents
    suspicious_ua = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zgrab',
                     'python-requests', 'wget/', 'scrapy']
    if any(s in ua.lower() for s in suspicious_ua):
        anomalies.append(f'suspicious_ua:{ua[:50]}')

    # 2. Large request payload (>1MB)
    if size > 1024 * 1024:
        anomalies.append(f'large_request:{size}')

    # 3. Missing User-Agent (often bots)
    if not ua:
        anomalies.append('missing_ua')

    # 4. Long voice log transcript (>500 chars)
    if req.path == '/api/voice-log' and req.method == 'POST':
        try:
            data = req.get_json(silent=True) or {}
            transcript = data.get('transcript', '')
            if len(transcript) > 500:
                anomalies.append('long_transcript')
        except Exception:
            pass

    if anomalies:
        sec_log('ANOMALY', ip, {'path': req.path, 'flags': anomalies})

    return anomalies


@app.before_request
def scan_request():
    """Scan every incoming request for anomalies."""
    detect_anomalies(request)

def _clean(val, max_len=500):
    """Sanitize string input: strip whitespace and enforce max length."""
    return (val or '').strip()[:max_len]


def _safe_redirect_url(next_url):
    """Validate redirect URL is local (no scheme, no external host)."""
    if not next_url:
        return None
    parsed = urlparse(next_url)
    # Reject anything with a scheme (http://) or network location (//evil.com)
    if parsed.scheme or parsed.netloc:
        return None
    if not next_url.startswith('/'):
        return None
    return next_url


def _owns_user(user_id):
    """Check if current session is authorized to access this user_id."""
    if session.get('admin_logged_in'):
        return True
    if session.get('user_id') == user_id:
        return True
    acct = session.get('account_id')
    if acct:
        user = get_user_by_id(user_id)
        return user and user.get('account_id') == acct
    return False


# ── Decorators ────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get('account_id'):
            flash('Please log in to access that page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*a, **k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*a, **k)
    return d


# ── Security Headers ─────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    """Inject security headers on every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net translate.google.com translate.googleapis.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com translate.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
            "img-src 'self' data: blob: translate.google.com translate.googleapis.com; "
            "connect-src 'self' translate.googleapis.com; "
            "frame-src translate.google.com;"
        )
    # Cache static files in production for 1 year (performance optimization)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    # Service Worker header
    if '/sw.js' in request.path:
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


# ── Serve sw.js from root (avoids scope restriction) ─────────────────────────
@app.route('/sw.js')
def service_worker():
    """Serve the service worker from root so it can control all pages."""
    from flask import send_from_directory
    resp = send_from_directory('static', 'sw.js')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp


# ══════════════════════════════════════════════════════════════════════════════
#  SEO / UTILITY
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/robots.txt')
def robots():
    txt = f"User-agent: *\nDisallow: /admin/\nDisallow: /api/\nSitemap: {Config.SITE_URL}/sitemap.xml\n"
    return Response(txt, mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    base = Config.SITE_URL
    pages = ['/', '/questionnaire', '/login', '/register']
    urls = ''.join(f"""
  <url><loc>{base}{p}</loc><changefreq>weekly</changefreq>
  <priority>{'1.0' if p=='/' else '0.8'}</priority></url>""" for p in pages)
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>'
           f'<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    return Response(xml, mimetype='application/xml')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'date': str(date.today())})

@app.route('/health')
def health():
    checks = {'status': 'ok', 'db': False, 'cache': False}
    try:
        from db import fetchone, get_db
        conn = get_db()
        row = fetchone(conn, 'SELECT 1')
        conn.close()
        if row:
            checks['db'] = True
    except Exception as e:
        checks['db_error'] = str(e)
        checks['status'] = 'degraded'
    try:
        checks['cache'] = cache_stats()
    except Exception:
        pass
    checks['rate_limits'] = 'active'
    code = 200 if checks['status'] == 'ok' else 503
    return jsonify(checks), code

@app.route('/manifest.json')
def manifest():
    data = {
        "name": "NutriAI — AI Diet Planner",
        "short_name": "NutriAI",
        "description": "AI-powered personalised diet plans based on Harvard Healthy Eating Plate. Get your free 7-day meal plan in 60 seconds.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#0f172a",
        "theme_color": "#16a34a",
        "lang": "en-IN",
        "categories": ["health", "food", "lifestyle"],
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        "shortcuts": [
            {
                "name": "Get My Diet Plan",
                "short_name": "Diet Plan",
                "description": "Start your health analysis now",
                "url": "/questionnaire",
                "icons": [{"src": "/static/icon-192.png", "sizes": "192x192"}]
            },
            {
                "name": "My Dashboard",
                "short_name": "Dashboard",
                "description": "View your saved plans",
                "url": "/my-dashboard",
                "icons": [{"src": "/static/icon-192.png", "sizes": "192x192"}]
            }
        ],
        "screenshots": [
            {"src": "/static/og-image.png", "sizes": "1200x630", "type": "image/png", "form_factor": "wide", "label": "NutriAI Dashboard"}
        ]
    }
    resp = make_response(jsonify(data))
    resp.headers['Content-Type'] = 'application/manifest+json'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@app.route('/offline')
def offline_page():
    """Offline fallback page served by the service worker."""
    return render_template('offline.html')


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    stats = get_admin_stats()
    return render_template('index.html', stats=stats)

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/quick')
def quick_questionnaire():
    return render_template('quick_questionnaire.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # ── Rate limit: 5 plans per IP per 10 minutes ──
    ip = get_ip(request)
    if not is_allowed(f'analyze:{ip}', max_calls=5, window_seconds=600):
        flash('Too many requests. Please wait a few minutes before generating another plan.', 'warning')
        sec_log('RATE_LIMIT', ip, {'endpoint': '/analyze', 'limit': '5/10min'})
        return render_template('questionnaire.html',
                               error='Rate limit reached. Please try again in a few minutes.'), 429
    try:
        form = request.form
        try:
            age_val = int(form.get('age', 25))
        except ValueError:
            age_val = 25
        if age_val < 18:
            template = 'quick_questionnaire.html' if (request.referrer and '/quick' in request.referrer) else 'questionnaire.html'
            return render_template(template, error="You must be 18 years of age or older to use NutriAI (under DPDP children's-data rules)."), 400

        user_data = {
            'session_id': str(uuid.uuid4()),
            'name':     _clean(form.get('name',''), 200) or session.get('account_name','User'),
            'email':    _clean(form.get('email',''), 200) or session.get('account_email',''),
            'age':      min(max(age_val, 10), 100),
            'gender':   form.get('gender','male'),
            'height':   float(form.get('height',170)),
            'weight':   float(form.get('weight',70)),
            'country':  _clean(form.get('country','India'), 100),
            'goal':     form.get('goal','maintain'),
            'target_weight': float(form.get('target_weight')) if form.get('target_weight') else None,
            'diet_type':    form.get('diet_type','non_vegetarian'),
            'food_allergies':   _clean(form.get('food_allergies',''), 500),
            'budget_preference':form.get('budget_preference','moderate'),
            'activity_level':   form.get('exercise_frequency','1-2'),
            'exercise_type':    _clean(', '.join(form.getlist('exercise_type')) or 'Walking', 500),
            'daily_steps':      form.get('daily_steps','3000-6000'),
            'sleep_hours':      float(form.get('sleep_hours',7)),
            'sleep_quality':    form.get('sleep_quality','average'),
            'night_wakeups':    int(form.get('night_wakeups',0)),
            'daytime_fatigue':  form.get('daytime_fatigue','sometimes'),
            'stress_level':     form.get('stress_level','moderate'),
            'stress_sources':   _clean(', '.join(form.getlist('stress_sources')), 500),
            'work_hours':       int(form.get('work_hours',8)),
            'work_type':        form.get('work_type','sedentary'),
            'breakfast_time':   form.get('breakfast_time','08:00'),
            'lunch_time':       form.get('lunch_time','13:00'),
            'dinner_time':      form.get('dinner_time','20:00'),
            'late_night_eating':form.get('late_night_eating','rarely'),
            'water_intake':     form.get('water_intake','1-2 liters'),
            'breakfast_foods':  _clean(form.get('breakfast_foods',''), 500),
            'lunch_foods':      _clean(form.get('lunch_foods',''), 500),
            'dinner_foods':     _clean(form.get('dinner_foods',''), 500),
            'snacks':           _clean(form.get('snacks',''), 500),
            'beverages':        _clean(form.get('beverages',''), 500),
            'meals_per_day':    int(form.get('meals_per_day',3)),
            'outside_food_frequency': form.get('outside_food_frequency','occasionally'),
            'junk_food_frequency':    form.get('junk_food_frequency','1-2'),
            'medical_conditions': _clean(', '.join(form.getlist('medical_conditions')), 500),
            'medications':        _clean(form.get('medications',''), 500),
            'health_issues':      _clean(form.get('health_issues',''), 500),
            'menstrual_issues':   form.get('menstrual_issues','not_applicable'),
            'body_fat_pct':       float(form.get('body_fat_pct')) if form.get('body_fat_pct') else None,
            'cuisine_preference': form.get('cuisine_preference','Indian'),
            'food_dislikes':      _clean(form.get('food_dislikes',''), 500),
            'cooking_time':       form.get('cooking_time','30 minutes'),
            'cooking_skill':      form.get('cooking_skill','basic'),
            'eating_speed':       form.get('eating_speed','normal'),
            'meal_prep':          form.get('meal_prep','fresh_daily'),
            'alcohol':            form.get('alcohol','never'),
            'smoking':            form.get('smoking','never'),
            'supplements':        _clean(form.get('supplements',''), 500),
            'health_motivation':  _clean(form.get('health_motivation',''), 500),
            'exercise_intensity': form.get('exercise_intensity','moderate'),
            'sleep_issues':       _clean(', '.join(form.getlist('sleep_issues')), 500),
            'digestive_issues':   _clean(', '.join(form.getlist('digestive_issues')), 500),
            'bowel_frequency':    form.get('bowel_frequency','once_daily'),
            'probiotic_intake':   form.get('probiotic_intake','often'),
            'regular_drinks':     _clean(', '.join(form.getlist('regular_drinks')), 500),
            'sitting_hours':      int(form.get('sitting_hours',6)),
            'screen_time':        int(form.get('screen_time',8)),
            'work_shift':         form.get('work_shift','day'),
            'meal_skip':          form.get('meal_skip','never'),
            'stress_eating':      form.get('stress_eating','no_change'),
            'bedtime':            form.get('bedtime','23:00'),
        }
        metrics = run_all_calculations(user_data)
        user_data['activity_level'] = metrics['activity_level']
        user_id = save_user(user_data)
        if session.get('account_id'):
            link_user_to_account(user_id, session['account_id'])
        # Try cache first (saves Gemini API calls for similar profiles)
        diet_plan_data = get_cached(user_data, metrics)
        if not diet_plan_data:
            diet_plan_data = generate_diet_plan(user_data, metrics)
            set_cached(user_data, metrics, diet_plan_data)
        plan_record = {
            'user_id': user_id, 'bmi': metrics['bmi'], 'bmi_category': metrics['bmi_category'],
            'bmr': metrics['bmr'], 'tdee': metrics['tdee'], 'daily_calories': metrics['daily_calories'],
            'protein': metrics['protein'], 'carbs': metrics['carbs'], 'fats': metrics['fats'],
            'meal_plan':      json.dumps(diet_plan_data.get('week_plan',{})),
            'lifestyle_tips': json.dumps(diet_plan_data.get('lifestyle_tips',[])),
            'duration_weeks': 4
        }
        plan_id = save_diet_plan(plan_record)
        add_progress_entry(user_id, user_data['weight'], 'Starting weight')
        session['user_id']   = user_id
        session['user_name'] = user_data['name']
        return redirect(url_for('results', user_id=user_id, plan_id=plan_id))
    except ValueError as e:
        return render_template('questionnaire.html', error=f"Invalid input: {str(e)}"), 400
    except Exception as e:
        app.logger.error(f"Error in /analyze: {e}")
        return render_template('questionnaire.html', error="An error occurred. Please try again."), 500


@app.route('/results/<int:user_id>/<int:plan_id>')
def results(user_id, plan_id):
    # ── IDOR check: verify ownership ──
    if not _owns_user(user_id):
        flash('You do not have permission to view this plan.', 'danger')
        return redirect(url_for('index'))
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)
    if not user or not plan:
        return redirect(url_for('questionnaire'))
    week_plan      = json.loads(plan.get('meal_plan','{}'))
    lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]'))
    health_analysis = analyze_health(user, plan)
    has_medical = bool(user.get('medical_conditions','').strip())
    # Build plan_data from stored plan if available, else generate fallback
    plan_data = {}
    if week_plan:
        plan_data = {
            'week_plan': week_plan,
            'lifestyle_tips': lifestyle_tips,
        }
    if not plan_data.get('week_plan'):
        from services.ai_diet_generator import get_fallback_plan
        from services.diet_calculator import run_all_calculations
        try:
            metrics_for_plan = run_all_calculations(user)
            plan_data = get_fallback_plan(user, metrics_for_plan)
            if lifestyle_tips:
                plan_data['lifestyle_tips'] = lifestyle_tips
        except Exception:
            plan_data = {}
    return render_template('results.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, health_analysis=health_analysis,
        days=list(week_plan.keys()), has_medical=has_medical,
        plan_data=plan_data)


@app.route('/results/<int:user_id>/<int:plan_id>/print')
def results_print(user_id, plan_id):
    """Printable / shareable version of the plan."""
    # ── IDOR check ──
    if not _owns_user(user_id):
        flash('You do not have permission to view this plan.', 'danger')
        return redirect(url_for('index'))
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)
    if not user or not plan:
        return redirect(url_for('questionnaire'))
    week_plan      = json.loads(plan.get('meal_plan','{}'))
    lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]'))
    return render_template('print_plan.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, days=list(week_plan.keys()))


@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    # ── IDOR check ──
    if not _owns_user(user_id):
        flash('You do not have permission to view this dashboard.', 'danger')
        return redirect(url_for('index'))
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)
    progress_data  = get_progress_by_user(user_id)
    if not user:
        return redirect(url_for('index'))
    chart_labels  = [p['date']   for p in progress_data]
    chart_weights = [p['weight'] for p in progress_data]
    current_weight = get_latest_weight(user_id) or user['weight']
    week_plan, lifestyle_tips = {}, []
    if plan:
        week_plan      = json.loads(plan.get('meal_plan','{}'))
        lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]'))
    diary_today   = get_diary_by_user_date(user_id)
    diary_summary = get_diary_summary(user_id)
    return render_template('dashboard.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, progress_data=progress_data,
        chart_labels=json.dumps(chart_labels), chart_weights=json.dumps(chart_weights),
        current_weight=current_weight, days=list(week_plan.keys())[:3] if week_plan else [],
        diary_today=diary_today, diary_summary=diary_summary)


# ══════════════════════════════════════════════════════════════════════════════
#  API ENDPOINTS (CSRF-exempt for JSON, but require session auth)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/diary/add', methods=['POST'])
@csrf.exempt
def api_diary_add():
    ip = get_ip(request)
    if not is_allowed(f'diary:{ip}', max_calls=30, window_seconds=60):
        sec_log('RATE_LIMIT', ip, {'endpoint': '/api/diary/add'})
        return jsonify({'error': 'Too many requests'}), 429
    try:
        d = request.get_json()
        user_id = d.get('user_id')
        # ── Auth check ──
        if not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        entry_id = add_diary_entry(
            user_id, session.get('account_id'), d.get('meal_type','snack'),
            _clean(d.get('food_name',''), 200), d.get('calories',0),
            d.get('protein',0), d.get('carbs',0), d.get('fats',0),
            _clean(d.get('notes',''), 500), d.get('date')
        )
        diary   = get_diary_by_user_date(user_id, d.get('date'))
        summary = get_diary_summary(user_id, d.get('date'))
        return jsonify({'success': True, 'id': entry_id, 'diary': diary, 'summary': summary})
    except Exception as e:
        app.logger.error(f"Error in api_diary_add: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500

@app.route('/api/diary/delete', methods=['POST'])
@csrf.exempt
def api_diary_delete():
    try:
        d = request.get_json()
        user_id = d.get('user_id')
        # ── Auth check ──
        if not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        delete_diary_entry(d.get('id'), user_id)
        summary = get_diary_summary(user_id)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        app.logger.error(f"Error in api_diary_delete: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500

@app.route('/api/progress/add', methods=['POST'])
@csrf.exempt
def add_progress():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        weight  = float(data.get('weight'))
        if not user_id or not weight: return jsonify({'error':'Missing fields'}),400
        if weight < 20 or weight > 500: return jsonify({'error':'Invalid weight'}),400
        # ── Auth check ──
        if not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        add_progress_entry(user_id, weight, _clean(data.get('notes',''), 500))
        progress = get_progress_by_user(user_id)
        return jsonify({'success':True,
                        'labels': [p['date']   for p in progress],
                        'weights':[p['weight'] for p in progress]})
    except Exception as e:
        app.logger.error(f"Error in add_progress: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500

@app.route('/api/bmi-check', methods=['POST'])
@csrf.exempt
def bmi_check():
    try:
        data   = request.get_json()
        weight = float(data.get('weight',0))
        height = float(data.get('height',0))
        if weight<=0 or height<=0: return jsonify({'error':'Invalid values'}),400
        from services.diet_calculator import calculate_bmi, get_bmi_category
        bmi = calculate_bmi(weight, height)
        return jsonify({'bmi':bmi,'category':get_bmi_category(bmi)})
    except Exception as e:
        app.logger.error(f"Error in bmi_check: {e}", exc_info=True)
        return jsonify({'error': 'Invalid inputs. Please check your weight and height values.'}), 400


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/register', methods=['GET','POST'])
def register():
    if session.get('account_id'): return redirect(url_for('my_dashboard'))
    error = None
    if request.method == 'POST':
        ip = get_ip(request)
        if not is_allowed(f'register:{ip}', max_calls=5, window_seconds=3600):
            error = 'Too many registration attempts. Please try again later.'
            sec_log('RATE_LIMIT', ip, {'endpoint': '/register', 'limit': '5/1hr'})
        else:
            name     = _clean(request.form.get('name',''), 200)
            email    = _clean(request.form.get('email',''), 200)
            password = request.form.get('password','')
            confirm  = request.form.get('confirm_password','')
            if not name or not email or not password:
                error = 'All fields are required.'
            else:
                pw_valid, pw_err = validate_password(password)
                if not pw_valid:
                    error = pw_err
                elif password != confirm:
                    error = 'Passwords do not match.'
                else:
                    account_id, err = register_account(name, email, password)
                    if err: error = err
                    else:
                        # Session rotation: clear old session, set new
                        session.clear()
                        session.permanent = True
                        session['account_id']    = account_id
                        session['account_name']  = name
                        session['account_email'] = email
                        flash(f'Welcome to NutriAI, {name}! Complete your health analysis below.', 'success')
                        return redirect(url_for('questionnaire'))
    return render_template('auth/register.html', error=error)


@app.route('/login', methods=['GET','POST'])
def login():
    if session.get('account_id'): return redirect(url_for('my_dashboard'))
    error = None
    if request.method == 'POST':
        ip = get_ip(request)
        email = _clean(request.form.get('email',''), 200)

        # ── Brute Force / Account Lockout check ──
        if is_account_locked(email):
            sec_log('ACCOUNT_LOCKED', ip, {'email': email})
            return render_template('auth/login.html',
                error='Account temporarily locked. Try again in 15 minutes.',
                next=request.args.get('next','')), 429

        if not is_allowed(f'login:{ip}', max_calls=10, window_seconds=300):
            error = 'Too many login attempts. Please wait 5 minutes.'
            sec_log('RATE_LIMIT', ip, {'endpoint': '/login', 'limit': '10/5min'})
        else:
            password = request.form.get('password','')
            account, err = login_account(email, password)
            if err:
                error = err
                if record_failed_login(email):
                    sec_log('ACCOUNT_LOCKED', ip, {'email': email, 'trigger': 'failed_attempts'})
                else:
                    sec_log('LOGIN_FAIL', ip, {'email': email, 'reason': err})
            else:
                # Session rotation: clear old session, set new
                session.clear()
                session.permanent = True
                session['account_id']    = account['id']
                session['account_name']  = account['name']
                session['account_email'] = account['email']
                sec_log('LOGIN_SUCCESS', ip, {'email': email})
                next_url = request.form.get('next') or request.args.get('next')
                safe_next = _safe_redirect_url(next_url)
                flash(f'Welcome back, {account["name"]}!', 'success')
                return redirect(safe_next or url_for('my_dashboard'))
    return render_template('auth/login.html', error=error, next=request.args.get('next',''))


@app.route('/logout')
def logout():
    name = session.get('account_name','')
    session.clear()
    flash(f'See you soon, {name}!', 'info')
    return redirect(url_for('index'))


@app.route('/login/google')
def login_google():
    is_mock = not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET
    if is_mock:
        # Redirect to mock consent page
        callback_url = url_for('login_google_callback', code='mock-code-123', _external=True)
        return render_template('auth/mock_consent.html', callback_url=callback_url)
    else:
        # Real Google Auth redirect
        import urllib.parse
        redirect_uri = url_for('login_google_callback', _external=True)
        params = {
            'client_id': Config.GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': secrets.token_hex(16)
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return redirect(auth_url)


@app.route('/login/google/callback')
def login_google_callback():
    ip = get_ip(request)
    code = request.args.get('code')
    
    is_mock = not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET
    
    if is_mock or code == 'mock-code-123':
        # Mock testing data
        google_id = "google-oauth2-1029384756"
        email = "google_test_user@example.com"
        name = "Google Test User"
    else:
        # Real OAuth2 flow
        import urllib.request
        import urllib.parse
        
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = url_for('login_google_callback', _external=True)
        data = urllib.parse.urlencode({
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }).encode('utf-8')
        
        try:
            req = urllib.request.Request(token_url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                access_token = res_data.get('access_token')
            
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            req_info = urllib.request.Request(userinfo_url, headers={'Authorization': f'Bearer {access_token}'})
            with urllib.request.urlopen(req_info, timeout=10) as response_info:
                profile = json.loads(response_info.read().decode('utf-8'))
                google_id = profile.get('sub')
                email = profile.get('email')
                name = profile.get('name', 'Google User')
        except Exception as e:
            sec_log('GOOGLE_LOGIN_FAIL', ip, {'error': str(e)})
            flash('Failed to authenticate with Google. Please try again.', 'danger')
            return redirect(url_for('login'))

    if not email:
        flash('Could not retrieve email address from Google.', 'danger')
        return redirect(url_for('login'))

    account, err = register_google_account(name, email, google_id)
    if err:
        sec_log('GOOGLE_LOGIN_FAIL', ip, {'email': email, 'error': err})
        flash(f'Authentication error: {err}', 'danger')
        return redirect(url_for('login'))

    # Fetch updated account details
    if isinstance(account, int):
        account = get_account_by_id(account)
    elif not account:
        account = get_account_by_email(email)

    if not account:
        flash('Failed to retrieve account details.', 'danger')
        return redirect(url_for('login'))

    session.clear()
    session.permanent = True
    session['account_id']    = account['id']
    session['account_name']  = account['name']
    session['account_email'] = account['email']
    
    sec_log('LOGIN_SUCCESS', ip, {'email': email, 'provider': 'google'})
    flash(f'Welcome, {account["name"]}! Logged in via Google.', 'success')
    return redirect(url_for('my_dashboard'))


@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    """Step 1 — enter email to get reset link."""
    if request.method == 'POST':
        email = _clean(request.form.get('email',''), 200).lower()
        # Always show success to prevent email enumeration
        account = get_account_by_email(email)
        if account:
            token = create_reset_token(email)
            reset_url = url_for('reset_password', token=token, _external=True)
            # In production you'd email this. For now, flash the link.
            flash(f'Reset link generated. Copy this link: {reset_url}', 'info')
        else:
            flash('If that email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET','POST'])
def reset_password(token):
    """Step 2 — enter new password."""
    email = validate_reset_token(token)
    if not email:
        flash('This reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    error = None
    if request.method == 'POST':
        new_pw  = request.form.get('new_password','')
        confirm = request.form.get('confirm_password','')
        pw_valid, pw_err = validate_password(new_pw)
        if not pw_valid:
            error = pw_err
        elif new_pw != confirm:
            error = 'Passwords do not match.'
        else:
            account = get_account_by_email(email)
            if account:
                change_password(account['id'], new_pw)
                mark_token_used(token)
                flash('Password reset successfully! Please log in.', 'success')
                return redirect(url_for('login'))
    return render_template('auth/reset_password.html', token=token, email=email, error=error)


@app.route('/my-dashboard')
@login_required
def my_dashboard():
    account  = get_account_by_id(session['account_id'])
    profiles = get_profiles_for_account(session['account_id'])
    enriched = []
    for p in profiles:
        plan = get_diet_plan_by_user(p['id'])
        prog = get_progress_by_user(p['id'])
        enriched.append({'profile':p,'plan':plan,'progress_count':len(prog),
                         'latest_weight':get_latest_weight(p['id'])})
    return render_template('auth/my_dashboard.html', account=account, profiles=enriched)


@app.route('/account/settings', methods=['GET','POST'])
@login_required
def account_settings():
    account = get_account_by_id(session['account_id'])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name  = _clean(request.form.get('name',''), 200)
            email = _clean(request.form.get('email',''), 200)
            if not name or not email:
                flash('Name and email are required.', 'danger')
            else:
                update_account(session['account_id'], name, email)
                session['account_name']  = name
                session['account_email'] = email
                flash('Profile updated successfully.', 'success')
            return redirect(url_for('account_settings'))
        elif action == 'change_password':
            current_pw = request.form.get('current_password','')
            new_pw  = request.form.get('new_password','')
            confirm = request.form.get('confirm_password','')
            # Verify current password
            if not check_password_hash(account['password'], current_pw):
                flash('Current password is incorrect.', 'danger')
            else:
                pw_valid, pw_err = validate_password(new_pw)
                if not pw_valid:
                    flash(pw_err, 'danger')
                elif new_pw != confirm:
                    flash('Passwords do not match.', 'danger')
                else:
                    change_password(session['account_id'], new_pw)
                    flash('Password changed successfully.', 'success')
            return redirect(url_for('account_settings'))
    return render_template('auth/settings.html', account=account)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'): return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        ip = get_ip(request)
        if not is_allowed(f'admin:{ip}', max_calls=5, window_seconds=300):
            error = 'Too many attempts. Please wait 5 minutes.'
            sec_log('RATE_LIMIT', ip, {'endpoint': '/admin/login', 'limit': '5/5min'})
        elif (request.form.get('username') == Config.ADMIN_USERNAME and
                check_password_hash(_ADMIN_PW_HASH, request.form.get('password',''))):
            # Session rotation for admin
            session.clear()
            session.permanent = True
            session['admin_logged_in'] = True
            session['admin_username']  = request.form.get('username')
            sec_log('ADMIN_LOGIN_SUCCESS', ip, {'username': Config.ADMIN_USERNAME})
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid username or password.'
            sec_log('ADMIN_LOGIN_FAIL', ip, {'username': request.form.get('username')})
    return render_template('admin/login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in',None); session.pop('admin_username',None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats   = get_admin_stats()
    users   = get_all_users_with_plans()
    signups = get_signups_last_30_days()
    return render_template('admin/dashboard.html', stats=stats, users=users,
        signup_labels=json.dumps([s['day'] for s in signups]),
        signup_counts=json.dumps([s['cnt'] for s in signups]))

@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user, plan, progress, diary = get_user_full_detail(user_id)
    if not user: flash('User not found.','danger'); return redirect(url_for('admin_dashboard'))
    week_plan      = json.loads(plan.get('meal_plan','{}'))      if plan else {}
    lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]')) if plan else []
    health_analysis = analyze_health(user, plan if plan else {})
    return render_template('admin/user_detail.html',
        user=user, plan=plan, week_plan=week_plan, lifestyle_tips=lifestyle_tips,
        progress=progress, diary=diary,
        chart_labels=json.dumps([p['date']   for p in progress]),
        chart_weights=json.dumps([p['weight'] for p in progress]),
        health_analysis=health_analysis, days=list(week_plan.keys()))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    delete_user_cascade(user_id)
    flash(f'User #{user_id} deleted.','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/stats')
@admin_required
def admin_api_stats():
    return jsonify(get_admin_stats())


# ── NEW FEATURE API ROUTES ────────────────────────────────────────────────

@app.route('/api/swap-meal', methods=['POST'])
@csrf.exempt
def api_swap_meal():
    ip = get_ip(request)
    if not is_allowed(f'swap:{ip}', max_calls=20, window_seconds=60):
        sec_log('RATE_LIMIT', ip, {'endpoint': '/api/swap-meal'})
        return jsonify({'error': 'Too many requests'}), 429
    try:
        d = request.get_json()
        user_id = d.get('user_id')
        # ── Auth check ──
        if not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        plan_targets = get_diet_plan_by_user(user_id) or {}
        new_meal = swap_meal(
            d.get('day', 'Monday'),
            d.get('meal_type', 'lunch'),
            d.get('current_meal', {}),
            user,
            plan_targets
        )
        return jsonify({'success': True, 'meal': new_meal})
    except Exception as e:
        app.logger.error(f"Swap meal error: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500


@app.route('/api/analyze-food-image', methods=['POST'])
@csrf.exempt
def api_analyze_food_image():
    ip = get_ip(request)
    if not is_allowed(f'vision:{ip}', max_calls=10, window_seconds=60):
        sec_log('RATE_LIMIT', ip, {'endpoint': '/api/analyze-food-image'})
        return jsonify({'error': 'Too many requests'}), 429
    try:
        d = request.get_json() or {}
        user_id = d.get('user_id')
        if not user_id or not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        image_data = d.get('image', '')
        mime_type  = d.get('mime_type', 'image/jpeg')
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        if len(image_data) > 10 * 1024 * 1024:
            return jsonify({'error': 'Image too large (max 10MB)'}), 400
        result = analyze_food_image(image_data, mime_type)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_analyze_food_image: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500


@app.route('/api/voice-log', methods=['POST'])
@csrf.exempt
def api_voice_log():
    ip = get_ip(request)
    if not is_allowed(f'voice:{ip}', max_calls=20, window_seconds=60):
        sec_log('RATE_LIMIT', ip, {'endpoint': '/api/voice-log'})
        return jsonify({'error': 'Too many requests'}), 429
    try:
        d = request.get_json() or {}
        user_id = d.get('user_id')
        if not user_id or not _owns_user(user_id):
            return jsonify({'error': 'Unauthorized'}), 403
        transcript = _clean(d.get('transcript', ''), 2000)
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        user = get_user_by_id(user_id) or {}
        result = analyze_voice_text(transcript, user)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in api_voice_log: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500


@app.route('/api/cache-stats')
@admin_required
def api_cache_stats():
    return jsonify(cache_stats())


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF token missing/invalid errors."""
    flash('Session expired or invalid form submission. Please try again.', 'warning')
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(404)
def not_found(e): return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f'500 error: {e}', exc_info=True)
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
