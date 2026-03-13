from models.user_model import get_db


def get_all_users_with_plans():
    """Fetch all users joined with their latest diet plan."""
    conn = get_db()
    try:
        rows = conn.execute('''
            SELECT
                u.id, u.name, u.email, u.age, u.gender, u.height, u.weight,
                u.country, u.goal, u.diet_type, u.activity_level,
                u.sleep_hours, u.sleep_quality, u.stress_level,
                u.water_intake, u.work_type, u.food_allergies,
                u.breakfast_foods, u.lunch_foods, u.dinner_foods,
                u.snacks, u.beverages, u.junk_food_frequency,
                u.outside_food_frequency, u.target_weight,
                u.exercise_type, u.daily_steps, u.meals_per_day,
                u.created_at,
                d.id        AS plan_id,
                d.bmi, d.bmi_category, d.bmr, d.tdee,
                d.daily_calories, d.protein, d.carbs, d.fats,
                d.meal_plan, d.lifestyle_tips,
                d.created_at AS plan_created_at
            FROM users u
            LEFT JOIN diet_plans d ON d.user_id = u.id
                AND d.id = (
                    SELECT id FROM diet_plans
                    WHERE user_id = u.id
                    ORDER BY created_at DESC LIMIT 1
                )
            ORDER BY u.created_at DESC
        ''').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_admin_stats():
    """Aggregate stats for the admin overview cards."""
    conn = get_db()
    try:
        total_users   = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_plans   = conn.execute('SELECT COUNT(*) FROM diet_plans').fetchone()[0]
        total_entries = conn.execute('SELECT COUNT(*) FROM progress').fetchone()[0]

        goal_rows = conn.execute(
            "SELECT goal, COUNT(*) AS cnt FROM users GROUP BY goal"
        ).fetchall()
        goals = {r['goal']: r['cnt'] for r in goal_rows}

        diet_rows = conn.execute(
            "SELECT diet_type, COUNT(*) AS cnt FROM users GROUP BY diet_type"
        ).fetchall()
        diets = {r['diet_type']: r['cnt'] for r in diet_rows}

        bmi_rows = conn.execute(
            "SELECT bmi_category, COUNT(*) AS cnt FROM diet_plans GROUP BY bmi_category"
        ).fetchall()
        bmis = {r['bmi_category']: r['cnt'] for r in bmi_rows}

        avg_cal = conn.execute(
            "SELECT ROUND(AVG(daily_calories),0) FROM diet_plans"
        ).fetchone()[0] or 0

        avg_bmi = conn.execute(
            "SELECT ROUND(AVG(bmi),1) FROM diet_plans"
        ).fetchone()[0] or 0

        recent = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now','-7 days')"
        ).fetchone()[0]

        return {
            'total_users':   total_users,
            'total_plans':   total_plans,
            'total_entries': total_entries,
            'goals':         goals,
            'diets':         diets,
            'bmis':          bmis,
            'avg_calories':  int(avg_cal),
            'avg_bmi':       avg_bmi,
            'new_this_week': recent,
        }
    finally:
        conn.close()


def get_user_full_detail(user_id):
    """All columns for a single user + their plan + progress history."""
    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        plan = conn.execute(
            'SELECT * FROM diet_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
            (user_id,)
        ).fetchone()
        progress = conn.execute(
            'SELECT * FROM progress WHERE user_id = ? ORDER BY date ASC',
            (user_id,)
        ).fetchall()
        return (
            dict(user) if user else None,
            dict(plan)  if plan  else None,
            [dict(p) for p in progress]
        )
    finally:
        conn.close()


def delete_user_cascade(user_id):
    """Delete a user and all their related data."""
    conn = get_db()
    try:
        conn.execute('DELETE FROM progress   WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM diet_plans WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users      WHERE id = ?',      (user_id,))
        conn.commit()
    finally:
        conn.close()


def get_bmi_distribution():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT bmi_category, COUNT(*) AS cnt FROM diet_plans GROUP BY bmi_category"
        ).fetchall()
        return {r['bmi_category']: r['cnt'] for r in rows}
    finally:
        conn.close()


def get_signups_last_30_days():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM users
            WHERE created_at >= DATE('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
