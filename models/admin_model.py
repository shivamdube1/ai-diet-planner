from db import get_db, fetchall, fetchone, execute, q, PG


def get_all_users_with_plans():
    conn = get_db()
    try:
        sql = '''
            SELECT u.id, u.name, u.email, u.age, u.gender, u.height, u.weight,
                   u.country, u.goal, u.diet_type, u.activity_level,
                   u.sleep_hours, u.sleep_quality, u.stress_level,
                   u.water_intake, u.work_type, u.food_allergies,
                   u.breakfast_foods, u.lunch_foods, u.dinner_foods,
                   u.snacks, u.beverages, u.junk_food_frequency,
                   u.outside_food_frequency, u.target_weight,
                   u.exercise_type, u.daily_steps, u.meals_per_day,
                   u.medical_conditions, u.medications, u.supplements,
                   u.cuisine_preference, u.food_dislikes, u.cooking_time,
                   u.health_motivation, u.alcohol, u.smoking, u.body_fat_pct,
                   u.created_at,
                   d.id AS plan_id, d.bmi, d.bmi_category, d.bmr, d.tdee,
                   d.daily_calories, d.protein, d.carbs, d.fats,
                   d.meal_plan, d.lifestyle_tips, d.created_at AS plan_created_at
            FROM users u
            LEFT JOIN diet_plans d ON d.user_id = u.id
                AND d.id = (
                    SELECT id FROM diet_plans WHERE user_id = u.id
                    ORDER BY created_at DESC LIMIT 1
                )
            ORDER BY u.created_at DESC
        '''
        return fetchall(conn, q(sql))
    finally:
        conn.close()


def get_admin_stats():
    conn = get_db()
    try:
        total_users   = (fetchone(conn, 'SELECT COUNT(*) AS c FROM users') or {}).get('c', 0)
        total_plans   = (fetchone(conn, 'SELECT COUNT(*) AS c FROM diet_plans') or {}).get('c', 0)
        total_entries = (fetchone(conn, 'SELECT COUNT(*) AS c FROM progress') or {}).get('c', 0)
        diary_entries = (fetchone(conn, 'SELECT COUNT(*) AS c FROM food_diary') or {}).get('c', 0)

        goal_rows = fetchall(conn, 'SELECT goal, COUNT(*) AS cnt FROM users GROUP BY goal')
        goals = {r['goal']: r['cnt'] for r in goal_rows}

        diet_rows = fetchall(conn, 'SELECT diet_type, COUNT(*) AS cnt FROM users GROUP BY diet_type')
        diets = {r['diet_type']: r['cnt'] for r in diet_rows}

        bmi_rows = fetchall(conn, 'SELECT bmi_category, COUNT(*) AS cnt FROM diet_plans GROUP BY bmi_category')
        bmis = {r['bmi_category']: r['cnt'] for r in bmi_rows}

        avg_cal_row = fetchone(conn, 'SELECT ROUND(AVG(daily_calories),0) AS v FROM diet_plans')
        avg_bmi_row = fetchone(conn, 'SELECT ROUND(AVG(bmi),1) AS v FROM diet_plans')
        recent_row  = fetchone(conn, q(
            "SELECT COUNT(*) AS c FROM users WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'"
            if PG else
            "SELECT COUNT(*) AS c FROM users WHERE created_at >= date('now','-7 days')"
        ))

        return {
            'total_users':   int(total_users or 0),
            'total_plans':   int(total_plans or 0),
            'total_entries': int(total_entries or 0),
            'diary_entries': int(diary_entries or 0),
            'goals':  goals, 'diets': diets, 'bmis': bmis,
            'avg_calories': int(avg_cal_row.get('v') or 0) if avg_cal_row else 0,
            'avg_bmi':      float(avg_bmi_row.get('v') or 0) if avg_bmi_row else 0,
            'new_this_week': int(recent_row.get('c') or 0) if recent_row else 0,
        }
    finally:
        conn.close()


def get_user_full_detail(user_id):
    conn = get_db()
    try:
        user     = fetchone(conn, q('SELECT * FROM users WHERE id = ?'), (user_id,))
        plan     = fetchone(conn, q('SELECT * FROM diet_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1'), (user_id,))
        progress = fetchall(conn, q('SELECT * FROM progress WHERE user_id = ? ORDER BY date ASC'), (user_id,))
        diary    = fetchall(conn, q('SELECT * FROM food_diary WHERE user_id = ? ORDER BY date DESC, created_at DESC LIMIT 30'), (user_id,))
        return user, plan, progress, diary
    finally:
        conn.close()


def delete_user_cascade(user_id):
    conn = get_db()
    try:
        execute(conn, q('DELETE FROM food_diary WHERE user_id = ?'), (user_id,))
        execute(conn, q('DELETE FROM progress   WHERE user_id = ?'), (user_id,))
        execute(conn, q('DELETE FROM diet_plans WHERE user_id = ?'), (user_id,))
        execute(conn, q('DELETE FROM users      WHERE id = ?'),      (user_id,))
        conn.commit()
    finally:
        conn.close()


def get_signups_last_30_days():
    conn = get_db()
    try:
        if PG:
            sql = """
                SELECT TO_CHAR(DATE(created_at),'YYYY-MM-DD') AS day, COUNT(*) AS cnt
                FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(created_at) ORDER BY day ASC
            """
        else:
            sql = """
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM users
                WHERE created_at >= DATE('now','-30 days')
                GROUP BY DATE(created_at) ORDER BY day ASC
            """
        return fetchall(conn, sql)
    finally:
        conn.close()
