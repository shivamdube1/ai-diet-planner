from models.user_model import get_db


def save_diet_plan(data):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO diet_plans (
                user_id, bmi, bmi_category, bmr, tdee, daily_calories,
                protein, carbs, fats, meal_plan, lifestyle_tips, duration_weeks
            ) VALUES (
                :user_id, :bmi, :bmi_category, :bmr, :tdee, :daily_calories,
                :protein, :carbs, :fats, :meal_plan, :lifestyle_tips, :duration_weeks
            )
        ''', data)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_diet_plan_by_user(user_id):
    conn = get_db()
    try:
        plan = conn.execute(
            'SELECT * FROM diet_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
            (user_id,)
        ).fetchone()
        return dict(plan) if plan else None
    finally:
        conn.close()


def get_diet_plan_by_id(plan_id):
    conn = get_db()
    try:
        plan = conn.execute('SELECT * FROM diet_plans WHERE id = ?', (plan_id,)).fetchone()
        return dict(plan) if plan else None
    finally:
        conn.close()
