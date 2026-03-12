import sqlite3
from config import Config
from datetime import datetime


def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bmi REAL,
            bmi_category TEXT,
            bmr REAL,
            tdee REAL,
            daily_calories REAL,
            protein REAL,
            carbs REAL,
            fats REAL,
            meal_plan TEXT,
            lifestyle_tips TEXT,
            duration_weeks INTEGER DEFAULT 4,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weight REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()


def save_user(data):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (
                session_id, name, email, age, gender, height, weight, country,
                goal, target_weight, diet_type, food_allergies, budget_preference,
                activity_level, exercise_type, daily_steps, sleep_hours, sleep_quality,
                night_wakeups, daytime_fatigue, stress_level, stress_sources,
                work_hours, work_type, breakfast_time, lunch_time, dinner_time,
                late_night_eating, water_intake, breakfast_foods, lunch_foods,
                dinner_foods, snacks, beverages, meals_per_day,
                outside_food_frequency, junk_food_frequency
            ) VALUES (
                :session_id, :name, :email, :age, :gender, :height, :weight, :country,
                :goal, :target_weight, :diet_type, :food_allergies, :budget_preference,
                :activity_level, :exercise_type, :daily_steps, :sleep_hours, :sleep_quality,
                :night_wakeups, :daytime_fatigue, :stress_level, :stress_sources,
                :work_hours, :work_type, :breakfast_time, :lunch_time, :dinner_time,
                :late_night_eating, :water_intake, :breakfast_foods, :lunch_foods,
                :dinner_foods, :snacks, :beverages, :meals_per_day,
                :outside_food_frequency, :junk_food_frequency
            )
        ''', data)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_session(session_id):
    conn = get_db()
    try:
        user = conn.execute(
            'SELECT * FROM users WHERE session_id = ?', (session_id,)
        ).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()
