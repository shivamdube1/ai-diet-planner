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
                    SELECT id FROM diet_plans dp2
                    WHERE dp2.user_id = u.id
                    ORDER BY dp2.created_at DESC LIMIT 1
                )
            ORDER BY u.created_at DESC
        '''
        return fetchall(conn, sql)
    except Exception as e:
        print(f"get_all_users_with_plans error: {e}")
        return []
    finally:
        conn.close()


def get_admin_stats():
    conn = get_db()
    try:
        def safe_count(sql):
            try:
                row = fetchone(conn, sql)
                if row:
                    v = list(row.values())[0]
                    return int(v) if v is not None else 0
            except Exception:
                return 0
            return 0

        def safe_group(sql):
            try:
                rows = fetchall(conn, sql)
                return {r[list(r.keys())[0]]: r[list(r.keys())[1]] for r in rows}
            except Exception:
                return {}

        total_users   = safe_count('SELECT COUNT(*) AS c FROM users')
        total_plans   = safe_count('SELECT COUNT(*) AS c FROM diet_plans')
        total_entries = safe_count('SELECT COUNT(*) AS c FROM progress')
        diary_entries = safe_count('SELECT COUNT(*) AS c FROM food_diary')

        goals = safe_group('SELECT goal, COUNT(*) AS cnt FROM users GROUP BY goal')
        diets = safe_group('SELECT diet_type, COUNT(*) AS cnt FROM users GROUP BY diet_type')
        bmis  = safe_group('SELECT bmi_category, COUNT(*) AS cnt FROM diet_plans GROUP BY bmi_category')

        try:
            avg_cal_row = fetchone(conn, 'SELECT ROUND(AVG(daily_calories),0) AS v FROM diet_plans')
            avg_cal = int(avg_cal_row.get('v') or 0) if avg_cal_row else 0
        except Exception:
            avg_cal = 0

        try:
            avg_bmi_row = fetchone(conn, 'SELECT ROUND(AVG(bmi),1) AS v FROM diet_plans')
            avg_bmi = float(avg_bmi_row.get('v') or 0) if avg_bmi_row else 0
        except Exception:
            avg_bmi = 0

        # Recent signups — different syntax for PG vs SQLite
        try:
            if PG:
                recent_sql = "SELECT COUNT(*) AS c FROM users WHERE created_at >= NOW() - INTERVAL '7 days'"
            else:
                recent_sql = "SELECT COUNT(*) AS c FROM users WHERE created_at >= date('now','-7 days')"
            recent = safe_count(recent_sql)
        except Exception:
            recent = 0

        return {
            'total_users':   total_users,
            'total_plans':   total_plans,
            'total_entries': total_entries,
            'diary_entries': diary_entries,
            'goals':  goals,
            'diets':  diets,
            'bmis':   bmis,
            'avg_calories':  avg_cal,
            'avg_bmi':       avg_bmi,
            'new_this_week': recent,
        }
    except Exception as e:
        print(f"get_admin_stats error: {e}")
        return {
            'total_users':0,'total_plans':0,'total_entries':0,'diary_entries':0,
            'goals':{},'diets':{},'bmis':{},'avg_calories':0,'avg_bmi':0,'new_this_week':0
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
    except Exception as e:
        print(f"get_user_full_detail error: {e}")
        return None, None, [], []
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
    except Exception as e:
        print(f"delete_user_cascade error: {e}")
    finally:
        conn.close()


def get_signups_last_30_days():
    conn = get_db()
    try:
        if PG:
            sql = """
                SELECT TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day, COUNT(*) AS cnt
                FROM users
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """
        else:
            sql = """
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                FROM users
                WHERE created_at >= DATE('now','-30 days')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """
        return fetchall(conn, sql)
    except Exception as e:
        print(f"get_signups_last_30_days error: {e}")
        return []
    finally:
        conn.close()
