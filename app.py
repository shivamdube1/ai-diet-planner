import os, uuid, json, secrets
from functools import wraps
from datetime import date
from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, flash, Response, make_response)
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
                                  get_account_by_email)
from models.diary_model  import (add_diary_entry, get_diary_by_user_date,
                                  delete_diary_entry, get_diary_summary)
from models.reset_model  import (create_reset_token_table, create_reset_token,
                                  validate_reset_token, mark_token_used)
from services.diet_calculator  import run_all_calculations
from services.ai_diet_generator import generate_diet_plan
from services.health_analyzer  import analyze_health
from services.rate_limiter import is_allowed, get_ip

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

os.makedirs('database', exist_ok=True)
create_tables()
add_extended_columns()
create_accounts_table()
create_reset_token_table()


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
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    mimetype='application/xml')

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'date': str(date.today())})

@app.route('/manifest.json')
def manifest():
    return jsonify({"name":"NutriAI — AI Diet Planner","short_name":"NutriAI",
        "description":"AI-powered personalised diet plans","start_url":"/",
        "display":"standalone","background_color":"#0f172a","theme_color":"#16a34a",
        "icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},
                 {"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]})


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

@app.route('/analyze', methods=['POST'])
def analyze():
    # ── Rate limit: 5 plans per IP per 10 minutes ──
    ip = get_ip(request)
    if not is_allowed(f'analyze:{ip}', max_calls=5, window_seconds=600):
        flash('Too many requests. Please wait a few minutes before generating another plan.', 'warning')
        return render_template('questionnaire.html',
                               error='Rate limit reached. Please try again in a few minutes.'), 429
    try:
        form = request.form
        user_data = {
            'session_id': str(uuid.uuid4()),
            'name':     form.get('name','').strip() or session.get('account_name','User'),
            'email':    form.get('email','').strip() or session.get('account_email',''),
            'age':      min(max(int(form.get('age',25)), 10), 100),
            'gender':   form.get('gender','male'),
            'height':   float(form.get('height',170)),
            'weight':   float(form.get('weight',70)),
            'country':  form.get('country','India'),
            'goal':     form.get('goal','maintain'),
            'target_weight': float(form.get('target_weight')) if form.get('target_weight') else None,
            'diet_type':    form.get('diet_type','non_vegetarian'),
            'food_allergies':   form.get('food_allergies',''),
            'budget_preference':form.get('budget_preference','moderate'),
            'activity_level':   form.get('exercise_frequency','1-2'),
            'exercise_type':    ', '.join(form.getlist('exercise_type')) or 'Walking',
            'daily_steps':      form.get('daily_steps','3000-6000'),
            'sleep_hours':      float(form.get('sleep_hours',7)),
            'sleep_quality':    form.get('sleep_quality','average'),
            'night_wakeups':    int(form.get('night_wakeups',0)),
            'daytime_fatigue':  form.get('daytime_fatigue','sometimes'),
            'stress_level':     form.get('stress_level','moderate'),
            'stress_sources':   ', '.join(form.getlist('stress_sources')),
            'work_hours':       int(form.get('work_hours',8)),
            'work_type':        form.get('work_type','sedentary'),
            'breakfast_time':   form.get('breakfast_time','08:00'),
            'lunch_time':       form.get('lunch_time','13:00'),
            'dinner_time':      form.get('dinner_time','20:00'),
            'late_night_eating':form.get('late_night_eating','rarely'),
            'water_intake':     form.get('water_intake','1-2 liters'),
            'breakfast_foods':  form.get('breakfast_foods',''),
            'lunch_foods':      form.get('lunch_foods',''),
            'dinner_foods':     form.get('dinner_foods',''),
            'snacks':           form.get('snacks',''),
            'beverages':        form.get('beverages',''),
            'meals_per_day':    int(form.get('meals_per_day',3)),
            'outside_food_frequency': form.get('outside_food_frequency','occasionally'),
            'junk_food_frequency':    form.get('junk_food_frequency','1-2'),
            'medical_conditions': ', '.join(form.getlist('medical_conditions')),
            'medications':        form.get('medications',''),
            'health_issues':      form.get('health_issues',''),
            'menstrual_issues':   form.get('menstrual_issues','not_applicable'),
            'body_fat_pct':       float(form.get('body_fat_pct')) if form.get('body_fat_pct') else None,
            'cuisine_preference': form.get('cuisine_preference','Indian'),
            'food_dislikes':      form.get('food_dislikes',''),
            'cooking_time':       form.get('cooking_time','30 minutes'),
            'cooking_skill':      form.get('cooking_skill','basic'),
            'eating_speed':       form.get('eating_speed','normal'),
            'meal_prep':          form.get('meal_prep','fresh_daily'),
            'alcohol':            form.get('alcohol','never'),
            'smoking':            form.get('smoking','never'),
            'supplements':        form.get('supplements',''),
            'health_motivation':  form.get('health_motivation',''),
        }
        metrics = run_all_calculations(user_data)
        user_data['activity_level'] = metrics['activity_level']
        user_id = save_user(user_data)
        if session.get('account_id'):
            link_user_to_account(user_id, session['account_id'])
        diet_plan_data = generate_diet_plan(user_data, metrics)
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
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)
    if not user or not plan:
        return redirect(url_for('questionnaire'))
    week_plan      = json.loads(plan.get('meal_plan','{}'))
    lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]'))
    health_analysis = analyze_health(user, plan)
    has_medical = bool(user.get('medical_conditions','').strip())
    return render_template('results.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, health_analysis=health_analysis,
        days=list(week_plan.keys()), has_medical=has_medical)


@app.route('/results/<int:user_id>/<int:plan_id>/print')
def results_print(user_id, plan_id):
    """Printable / shareable version of the plan."""
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
#  API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/diary/add', methods=['POST'])
def api_diary_add():
    ip = get_ip(request)
    if not is_allowed(f'diary:{ip}', max_calls=30, window_seconds=60):
        return jsonify({'error': 'Too many requests'}), 429
    try:
        d = request.get_json()
        entry_id = add_diary_entry(
            d.get('user_id'), session.get('account_id'), d.get('meal_type','snack'),
            d.get('food_name',''), d.get('calories',0),
            d.get('protein',0), d.get('carbs',0), d.get('fats',0),
            d.get('notes',''), d.get('date')
        )
        diary   = get_diary_by_user_date(d.get('user_id'), d.get('date'))
        summary = get_diary_summary(d.get('user_id'), d.get('date'))
        return jsonify({'success': True, 'id': entry_id, 'diary': diary, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/diary/delete', methods=['POST'])
def api_diary_delete():
    try:
        d = request.get_json()
        delete_diary_entry(d.get('id'), d.get('user_id'))
        summary = get_diary_summary(d.get('user_id'))
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress/add', methods=['POST'])
def add_progress():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        weight  = float(data.get('weight'))
        if not user_id or not weight: return jsonify({'error':'Missing fields'}),400
        if weight < 20 or weight > 500: return jsonify({'error':'Invalid weight'}),400
        add_progress_entry(user_id, weight, data.get('notes',''))
        progress = get_progress_by_user(user_id)
        return jsonify({'success':True,
                        'labels': [p['date']   for p in progress],
                        'weights':[p['weight'] for p in progress]})
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/bmi-check', methods=['POST'])
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
        return jsonify({'error':str(e)}),400


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
        else:
            name     = request.form.get('name','').strip()
            email    = request.form.get('email','').strip()
            password = request.form.get('password','')
            confirm  = request.form.get('confirm_password','')
            if not name or not email or not password: error = 'All fields are required.'
            elif len(password) < 6: error = 'Password must be at least 6 characters.'
            elif password != confirm: error = 'Passwords do not match.'
            else:
                account_id, err = register_account(name, email, password)
                if err: error = err
                else:
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
        if not is_allowed(f'login:{ip}', max_calls=10, window_seconds=300):
            error = 'Too many login attempts. Please wait 5 minutes.'
        else:
            email    = request.form.get('email','').strip()
            password = request.form.get('password','')
            account, err = login_account(email, password)
            if err: error = err
            else:
                session['account_id']    = account['id']
                session['account_name']  = account['name']
                session['account_email'] = account['email']
                next_url = request.form.get('next') or request.args.get('next')
                flash(f'Welcome back, {account["name"]}!', 'success')
                return redirect(next_url if next_url and next_url.startswith('/') else url_for('my_dashboard'))
    return render_template('auth/login.html', error=error, next=request.args.get('next',''))


@app.route('/logout')
def logout():
    name = session.get('account_name','')
    session.clear()
    flash(f'See you soon, {name}!', 'info')
    return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    """Step 1 — enter email to get reset link."""
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
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
        if len(new_pw) < 6:
            error = 'Password must be at least 6 characters.'
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
            name  = request.form.get('name','').strip()
            email = request.form.get('email','').strip()
            if not name or not email:
                flash('Name and email are required.', 'danger')
            else:
                update_account(session['account_id'], name, email)
                session['account_name']  = name
                session['account_email'] = email
                flash('Profile updated successfully.', 'success')
            return redirect(url_for('account_settings'))
        elif action == 'change_password':
            new_pw  = request.form.get('new_password','')
            confirm = request.form.get('confirm_password','')
            if len(new_pw) < 6: flash('Password must be at least 6 characters.','danger')
            elif new_pw != confirm: flash('Passwords do not match.','danger')
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
        elif (request.form.get('username') == Config.ADMIN_USERNAME and
                request.form.get('password') == Config.ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            session['admin_username']  = request.form.get('username')
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid username or password.'
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


@app.errorhandler(404)
def not_found(e): return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f'500 error: {e}')
    # If admin route, show error details
    from flask import request as req
    if req.path.startswith('/admin'):
        return f'<h2>Admin Error (500)</h2><pre>{e}</pre><a href="/admin/dashboard">Retry</a>', 500
    return render_template('index.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
