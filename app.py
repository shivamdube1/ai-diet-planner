import os, uuid, json
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, flash)
from config import Config
from models.user_model   import create_tables, save_user, get_user_by_id
from models.diet_plan_model import save_diet_plan, get_diet_plan_by_user
from models.progress_model  import add_progress_entry, get_progress_by_user, get_latest_weight
from models.admin_model  import (get_all_users_with_plans, get_admin_stats,
                                  get_user_full_detail, delete_user_cascade,
                                  get_signups_last_30_days)
from models.auth_model   import (create_accounts_table, register_account, login_account,
                                  get_account_by_id, update_account, change_password,
                                  get_profiles_for_account, link_user_to_account)
from services.diet_calculator  import run_all_calculations
from services.ai_diet_generator import generate_diet_plan
from services.health_analyzer  import analyze_health

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

os.makedirs('database', exist_ok=True)
create_tables()
create_accounts_table()


# ── Decorators ────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('account_id'):
            flash('Please log in to access that page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/register', methods=['GET','POST'])
def register():
    if session.get('account_id'):
        return redirect(url_for('my_dashboard'))
    error = None
    if request.method == 'POST':
        name     = request.form.get('name','').strip()
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        confirm  = request.form.get('confirm_password','')
        if not name or not email or not password:
            error = 'All fields are required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            account_id, err = register_account(name, email, password)
            if err:
                error = err
            else:
                session['account_id']   = account_id
                session['account_name'] = name
                session['account_email']= email
                flash(f'Welcome to NutriAI, {name}! Complete your health analysis below.', 'success')
                return redirect(url_for('questionnaire'))
    return render_template('auth/register.html', error=error)


@app.route('/login', methods=['GET','POST'])
def login():
    if session.get('account_id'):
        return redirect(url_for('my_dashboard'))
    error = None
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        account, err = login_account(email, password)
        if err:
            error = err
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
    session.pop('account_id',   None)
    session.pop('account_name', None)
    session.pop('account_email',None)
    flash(f'You have been logged out. See you soon, {name}!', 'info')
    return redirect(url_for('index'))


@app.route('/my-dashboard')
@login_required
def my_dashboard():
    account  = get_account_by_id(session['account_id'])
    profiles = get_profiles_for_account(session['account_id'])
    # Build enriched profiles list
    enriched = []
    for p in profiles:
        plan = get_diet_plan_by_user(p['id'])
        prog = get_progress_by_user(p['id'])
        enriched.append({'profile': p, 'plan': plan, 'progress_count': len(prog),
                         'latest_weight': get_latest_weight(p['id'])})
    return render_template('auth/my_dashboard.html', account=account, profiles=enriched)


@app.route('/account/settings', methods=['GET','POST'])
@login_required
def account_settings():
    account = get_account_by_id(session['account_id'])
    error = success = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name  = request.form.get('name','').strip()
            email = request.form.get('email','').strip()
            if not name or not email:
                error = 'Name and email are required.'
            else:
                update_account(session['account_id'], name, email)
                session['account_name']  = name
                session['account_email'] = email
                flash('Profile updated successfully.', 'success')
                return redirect(url_for('account_settings'))
        elif action == 'change_password':
            new_pw  = request.form.get('new_password','')
            confirm = request.form.get('confirm_password','')
            if len(new_pw) < 6:
                error = 'Password must be at least 6 characters.'
            elif new_pw != confirm:
                error = 'Passwords do not match.'
            else:
                change_password(session['account_id'], new_pw)
                flash('Password changed successfully.', 'success')
                return redirect(url_for('account_settings'))
    return render_template('auth/settings.html', account=account, error=error)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        form = request.form
        user_data = {
            'session_id': str(uuid.uuid4()),
            'name':     form.get('name','').strip() or session.get('account_name','User'),
            'email':    form.get('email','').strip() or session.get('account_email',''),
            'age':      int(form.get('age',25)),
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
        }
        metrics = run_all_calculations(user_data)
        user_data['activity_level'] = metrics['activity_level']
        user_id = save_user(user_data)
        # Link to logged-in account if exists
        if session.get('account_id'):
            link_user_to_account(user_id, session['account_id'])
        diet_plan_data = generate_diet_plan(user_data, metrics)
        plan_record = {
            'user_id': user_id,
            'bmi': metrics['bmi'], 'bmi_category': metrics['bmi_category'],
            'bmr': metrics['bmr'], 'tdee': metrics['tdee'],
            'daily_calories': metrics['daily_calories'],
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
    return render_template('results.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, health_analysis=health_analysis,
        days=list(week_plan.keys()))


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
    return render_template('dashboard.html',
        user=user, plan=plan, week_plan=week_plan,
        lifestyle_tips=lifestyle_tips, progress_data=progress_data,
        chart_labels=json.dumps(chart_labels), chart_weights=json.dumps(chart_weights),
        current_weight=current_weight, days=list(week_plan.keys())[:3] if week_plan else [])


@app.route('/api/progress/add', methods=['POST'])
def add_progress():
    try:
        data    = request.get_json()
        user_id = data.get('user_id')
        weight  = float(data.get('weight'))
        notes   = data.get('notes','')
        if not user_id or not weight: return jsonify({'error':'Missing fields'}),400
        if weight < 20 or weight > 500: return jsonify({'error':'Invalid weight'}),400
        add_progress_entry(user_id, weight, notes)
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
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if (request.form.get('username') == Config.ADMIN_USERNAME and
                request.form.get('password') == Config.ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            session['admin_username']  = request.form.get('username')
            return redirect(url_for('admin_dashboard'))
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
    user, plan, progress = get_user_full_detail(user_id)
    if not user: flash('User not found.','danger'); return redirect(url_for('admin_dashboard'))
    week_plan      = json.loads(plan.get('meal_plan','{}'))      if plan else {}
    lifestyle_tips = json.loads(plan.get('lifestyle_tips','[]')) if plan else []
    health_analysis = analyze_health(user, plan if plan else {})
    return render_template('admin/user_detail.html',
        user=user, plan=plan, week_plan=week_plan, lifestyle_tips=lifestyle_tips,
        progress=progress,
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


# ── Error handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e): return render_template('index.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('index.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
