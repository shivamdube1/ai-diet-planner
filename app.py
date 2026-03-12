import os
import uuid
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from config import Config
from models.user_model import create_tables, save_user, get_user_by_session, get_user_by_id
from models.diet_plan_model import save_diet_plan, get_diet_plan_by_user
from models.progress_model import add_progress_entry, get_progress_by_user, get_latest_weight
from services.diet_calculator import run_all_calculations
from services.ai_diet_generator import generate_diet_plan
from services.health_analyzer import analyze_health

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Initialize database on startup
os.makedirs('database', exist_ok=True)
create_tables()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Process questionnaire and generate diet plan."""
    try:
        form = request.form

        # Build user data dict with validation
        user_data = {
            'session_id': str(uuid.uuid4()),
            'name': form.get('name', '').strip() or 'User',
            'email': form.get('email', '').strip(),
            'age': int(form.get('age', 25)),
            'gender': form.get('gender', 'male'),
            'height': float(form.get('height', 170)),
            'weight': float(form.get('weight', 70)),
            'country': form.get('country', 'India'),
            'goal': form.get('goal', 'maintain'),
            'target_weight': float(form.get('target_weight')) if form.get('target_weight') else None,
            'diet_type': form.get('diet_type', 'non_vegetarian'),
            'food_allergies': form.get('food_allergies', ''),
            'budget_preference': form.get('budget_preference', 'moderate'),
            'activity_level': form.get('exercise_frequency', '1-2'),
            'exercise_type': ', '.join(form.getlist('exercise_type')) or 'Walking',
            'daily_steps': form.get('daily_steps', '3000-6000'),
            'sleep_hours': float(form.get('sleep_hours', 7)),
            'sleep_quality': form.get('sleep_quality', 'average'),
            'night_wakeups': int(form.get('night_wakeups', 0)),
            'daytime_fatigue': form.get('daytime_fatigue', 'sometimes'),
            'stress_level': form.get('stress_level', 'moderate'),
            'stress_sources': ', '.join(form.getlist('stress_sources')),
            'work_hours': int(form.get('work_hours', 8)),
            'work_type': form.get('work_type', 'sedentary'),
            'breakfast_time': form.get('breakfast_time', '08:00'),
            'lunch_time': form.get('lunch_time', '13:00'),
            'dinner_time': form.get('dinner_time', '20:00'),
            'late_night_eating': form.get('late_night_eating', 'rarely'),
            'water_intake': form.get('water_intake', '1-2 liters'),
            'breakfast_foods': form.get('breakfast_foods', ''),
            'lunch_foods': form.get('lunch_foods', ''),
            'dinner_foods': form.get('dinner_foods', ''),
            'snacks': form.get('snacks', ''),
            'beverages': form.get('beverages', ''),
            'meals_per_day': int(form.get('meals_per_day', 3)),
            'outside_food_frequency': form.get('outside_food_frequency', 'occasionally'),
            'junk_food_frequency': form.get('junk_food_frequency', '1-2')
        }

        # Run health calculations
        metrics = run_all_calculations(user_data)
        user_data['activity_level'] = metrics['activity_level']

        # Save user to database
        user_id = save_user(user_data)

        # Generate AI diet plan
        diet_plan_data = generate_diet_plan(user_data, metrics)

        # Health analysis
        health_analysis = analyze_health(user_data, metrics)

        # Save diet plan to database
        plan_record = {
            'user_id': user_id,
            'bmi': metrics['bmi'],
            'bmi_category': metrics['bmi_category'],
            'bmr': metrics['bmr'],
            'tdee': metrics['tdee'],
            'daily_calories': metrics['daily_calories'],
            'protein': metrics['protein'],
            'carbs': metrics['carbs'],
            'fats': metrics['fats'],
            'meal_plan': json.dumps(diet_plan_data.get('week_plan', {})),
            'lifestyle_tips': json.dumps(diet_plan_data.get('lifestyle_tips', [])),
            'duration_weeks': 4
        }
        plan_id = save_diet_plan(plan_record)

        # Add initial weight to progress
        add_progress_entry(user_id, user_data['weight'], 'Starting weight')

        # Store in session
        session['user_id'] = user_id
        session['user_name'] = user_data['name']

        return redirect(url_for('results', user_id=user_id, plan_id=plan_id))

    except ValueError as e:
        return render_template('questionnaire.html', error=f"Invalid input: {str(e)}"), 400
    except Exception as e:
        app.logger.error(f"Error in /analyze: {e}")
        return render_template('questionnaire.html', error="An error occurred. Please try again."), 500


@app.route('/results/<int:user_id>/<int:plan_id>')
def results(user_id, plan_id):
    """Show personalized results page."""
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)

    if not user or not plan:
        return redirect(url_for('questionnaire'))

    week_plan = json.loads(plan.get('meal_plan', '{}'))
    lifestyle_tips = json.loads(plan.get('lifestyle_tips', '[]'))
    health_analysis = analyze_health(user, plan)

    return render_template('results.html',
        user=user, plan=plan,
        week_plan=week_plan,
        lifestyle_tips=lifestyle_tips,
        health_analysis=health_analysis,
        days=list(week_plan.keys())
    )


@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    """User dashboard with progress tracking."""
    user = get_user_by_id(user_id)
    plan = get_diet_plan_by_user(user_id)
    progress_data = get_progress_by_user(user_id)

    if not user:
        return redirect(url_for('index'))

    # Prepare chart data
    chart_labels = [p['date'] for p in progress_data]
    chart_weights = [p['weight'] for p in progress_data]
    current_weight = get_latest_weight(user_id) or user['weight']
    
    week_plan = {}
    lifestyle_tips = []
    if plan:
        week_plan = json.loads(plan.get('meal_plan', '{}'))
        lifestyle_tips = json.loads(plan.get('lifestyle_tips', '[]'))

    return render_template('dashboard.html',
        user=user, plan=plan,
        week_plan=week_plan,
        lifestyle_tips=lifestyle_tips,
        progress_data=progress_data,
        chart_labels=json.dumps(chart_labels),
        chart_weights=json.dumps(chart_weights),
        current_weight=current_weight,
        days=list(week_plan.keys())[:3] if week_plan else []
    )


@app.route('/api/progress/add', methods=['POST'])
def add_progress():
    """API endpoint to add weight progress."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        weight = float(data.get('weight'))
        notes = data.get('notes', '')

        if not user_id or not weight:
            return jsonify({'error': 'Missing required fields'}), 400
        if weight < 20 or weight > 500:
            return jsonify({'error': 'Invalid weight value'}), 400

        add_progress_entry(user_id, weight, notes)
        progress = get_progress_by_user(user_id)

        return jsonify({
            'success': True,
            'labels': [p['date'] for p in progress],
            'weights': [p['weight'] for p in progress]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bmi-check', methods=['POST'])
def bmi_check():
    """Quick BMI calculator API."""
    try:
        data = request.get_json()
        weight = float(data.get('weight', 0))
        height = float(data.get('height', 0))
        if weight <= 0 or height <= 0:
            return jsonify({'error': 'Invalid values'}), 400
        from services.diet_calculator import calculate_bmi, get_bmi_category
        bmi = calculate_bmi(weight, height)
        return jsonify({'bmi': bmi, 'category': get_bmi_category(bmi)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('index.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
