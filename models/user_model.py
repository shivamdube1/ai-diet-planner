from db import get_db, fetchone, fetchall, execute, lastrowid, serial, q, PG
from datetime import datetime


def create_tables():
    conn = get_db()
    try:
        conn.cursor().execute(q(serial('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                height REAL NOT NULL,
                weight REAL NOT NULL,
                country TEXT,
                goal TEXT NOT NULL,
                target_weight REAL,
                diet_type TEXT NOT NULL,
                food_allergies TEXT,
                budget_preference TEXT,
                activity_level TEXT NOT NULL,
                exercise_type TEXT,
                daily_steps TEXT,
                sleep_hours REAL,
                sleep_quality TEXT,
                night_wakeups INTEGER DEFAULT 0,
                daytime_fatigue TEXT,
                stress_level TEXT,
                stress_sources TEXT,
                work_hours INTEGER,
                work_type TEXT,
                breakfast_time TEXT,
                lunch_time TEXT,
                dinner_time TEXT,
                late_night_eating TEXT,
                water_intake TEXT,
                breakfast_foods TEXT,
                lunch_foods TEXT,
                dinner_foods TEXT,
                snacks TEXT,
                beverages TEXT,
                meals_per_day INTEGER,
                outside_food_frequency TEXT,
                junk_food_frequency TEXT,
                medical_conditions TEXT,
                medications TEXT,
                health_issues TEXT,
                menstrual_issues TEXT,
                body_fat_pct REAL,
                cuisine_preference TEXT,
                food_dislikes TEXT,
                cooking_time TEXT,
                cooking_skill TEXT,
                eating_speed TEXT,
                meal_prep TEXT,
                alcohol TEXT,
                smoking TEXT,
                supplements TEXT,
                health_motivation TEXT,
                account_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')))

        conn.cursor().execute(q(serial('''
            CREATE TABLE IF NOT EXISTS diet_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bmi REAL, bmi_category TEXT, bmr REAL, tdee REAL,
                daily_calories REAL, protein REAL, carbs REAL, fats REAL,
                meal_plan TEXT, lifestyle_tips TEXT,
                duration_weeks INTEGER DEFAULT 4,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')))

        conn.cursor().execute(q(serial('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')))

        conn.cursor().execute(q(serial('''
            CREATE TABLE IF NOT EXISTS food_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                food_name TEXT NOT NULL,
                calories INTEGER DEFAULT 0,
                protein REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                fats REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')))

        conn.commit()
    finally:
        conn.close()


def add_extended_columns():
    """Add any missing columns (migration-safe)."""
    conn = get_db()
    try:
        if PG:
            cols_q = "SELECT column_name FROM information_schema.columns WHERE table_name='users'"
            existing = [r['column_name'] for r in fetchall(conn, cols_q)]
        else:
            existing = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]

        new_cols = [
            ("medical_conditions","TEXT"),("medications","TEXT"),("health_issues","TEXT"),
            ("menstrual_issues","TEXT"),("body_fat_pct","REAL"),("cuisine_preference","TEXT"),
            ("food_dislikes","TEXT"),("cooking_time","TEXT"),("cooking_skill","TEXT"),
            ("eating_speed","TEXT"),("meal_prep","TEXT"),("alcohol","TEXT"),
            ("smoking","TEXT"),("supplements","TEXT"),("health_motivation","TEXT"),
            ("account_id","INTEGER"),
        ]
        for col, ctype in new_cols:
            if col not in existing:
                conn.cursor().execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")
    finally:
        conn.close()


def save_user(data):
    conn = get_db()
    try:
        returning = " RETURNING id" if PG else ""
        sql = q(f'''
            INSERT INTO users (
                session_id, name, email, age, gender, height, weight, country,
                goal, target_weight, diet_type, food_allergies, budget_preference,
                activity_level, exercise_type, daily_steps, sleep_hours, sleep_quality,
                night_wakeups, daytime_fatigue, stress_level, stress_sources,
                work_hours, work_type, breakfast_time, lunch_time, dinner_time,
                late_night_eating, water_intake, breakfast_foods, lunch_foods,
                dinner_foods, snacks, beverages, meals_per_day,
                outside_food_frequency, junk_food_frequency,
                medical_conditions, medications, health_issues, menstrual_issues,
                body_fat_pct, cuisine_preference, food_dislikes, cooking_time,
                cooking_skill, eating_speed, meal_prep, alcohol, smoking,
                supplements, health_motivation
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            ){returning}
        ''')
        params = (
            data.get('session_id'), data.get('name'), data.get('email'),
            data.get('age'), data.get('gender'), data.get('height'), data.get('weight'),
            data.get('country'), data.get('goal'), data.get('target_weight'),
            data.get('diet_type'), data.get('food_allergies'), data.get('budget_preference'),
            data.get('activity_level'), data.get('exercise_type'), data.get('daily_steps'),
            data.get('sleep_hours'), data.get('sleep_quality'), data.get('night_wakeups',0),
            data.get('daytime_fatigue'), data.get('stress_level'), data.get('stress_sources'),
            data.get('work_hours'), data.get('work_type'), data.get('breakfast_time'),
            data.get('lunch_time'), data.get('dinner_time'), data.get('late_night_eating'),
            data.get('water_intake'), data.get('breakfast_foods'), data.get('lunch_foods'),
            data.get('dinner_foods'), data.get('snacks'), data.get('beverages'),
            data.get('meals_per_day'), data.get('outside_food_frequency'), data.get('junk_food_frequency'),
            data.get('medical_conditions'), data.get('medications'), data.get('health_issues'),
            data.get('menstrual_issues'), data.get('body_fat_pct'), data.get('cuisine_preference'),
            data.get('food_dislikes'), data.get('cooking_time'), data.get('cooking_skill'),
            data.get('eating_speed'), data.get('meal_prep'), data.get('alcohol'),
            data.get('smoking'), data.get('supplements'), data.get('health_motivation'),
        )
        cur = execute(conn, sql, params)
        row_id = lastrowid(cur, conn) if not PG else (cur.fetchone() or {}).get('id')
        if row_id is None and not PG:
            row_id = cur.lastrowid
        conn.commit()
        return row_id
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM users WHERE id = ?', (user_id,))
    finally:
        conn.close()


def get_user_by_session(session_id):
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM users WHERE session_id = ?', (session_id,))
    finally:
        conn.close()
