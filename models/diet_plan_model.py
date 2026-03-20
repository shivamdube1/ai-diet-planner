from db import get_db, fetchone, fetchall, execute, lastrowid, serial, q, PG


def save_diet_plan(data):
    conn = get_db()
    try:
        returning = " RETURNING id" if PG else ""
        sql = q(f'''
            INSERT INTO diet_plans
            (user_id, bmi, bmi_category, bmr, tdee, daily_calories,
             protein, carbs, fats, meal_plan, lifestyle_tips, duration_weeks)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?){returning}
        ''')
        params = (
            data['user_id'], data['bmi'], data['bmi_category'], data['bmr'],
            data['tdee'], data['daily_calories'], data['protein'], data['carbs'],
            data['fats'], data['meal_plan'], data['lifestyle_tips'], data.get('duration_weeks', 4)
        )
        cur = execute(conn, sql, params)
        row_id = (cur.fetchone() or {}).get('id') if PG else cur.lastrowid
        conn.commit()
        return row_id
    finally:
        conn.close()


def get_diet_plan_by_user(user_id):
    conn = get_db()
    try:
        return fetchone(conn,
            'SELECT * FROM diet_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
            (user_id,))
    finally:
        conn.close()


def get_diet_plan_by_id(plan_id):
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM diet_plans WHERE id = ?', (plan_id,))
    finally:
        conn.close()
