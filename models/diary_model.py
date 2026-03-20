from db import get_db, fetchall, fetchone, execute, lastrowid, q, PG
from datetime import date


def add_diary_entry(user_id, account_id, meal_type, food_name, calories, protein, carbs, fats, notes='', entry_date=None):
    conn = get_db()
    try:
        today = entry_date or str(date.today())
        returning = " RETURNING id" if PG else ""
        sql = q(f"""INSERT INTO food_diary
            (user_id, account_id, date, meal_type, food_name, calories, protein, carbs, fats, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?){returning}""")
        cur = execute(conn, sql, (user_id, account_id, today, meal_type, food_name,
                                   int(calories or 0), float(protein or 0),
                                   float(carbs or 0), float(fats or 0), notes))
        row_id = (cur.fetchone() or {}).get('id') if PG else cur.lastrowid
        conn.commit()
        return row_id
    finally:
        conn.close()


def get_diary_by_user_date(user_id, diary_date=None):
    today = diary_date or str(date.today())
    conn = get_db()
    try:
        return fetchall(conn, q('SELECT * FROM food_diary WHERE user_id=? AND date=? ORDER BY created_at ASC'),
                        (user_id, today))
    finally:
        conn.close()


def get_diary_by_account(account_id, diary_date=None):
    today = diary_date or str(date.today())
    conn = get_db()
    try:
        return fetchall(conn,
            q('SELECT * FROM food_diary WHERE account_id=? AND date=? ORDER BY meal_type,created_at'),
            (account_id, today))
    finally:
        conn.close()


def delete_diary_entry(entry_id, user_id):
    conn = get_db()
    try:
        execute(conn, q('DELETE FROM food_diary WHERE id=? AND user_id=?'), (entry_id, user_id))
        conn.commit()
    finally:
        conn.close()


def get_diary_summary(user_id, diary_date=None):
    today = diary_date or str(date.today())
    conn = get_db()
    try:
        row = fetchone(conn, q('''
            SELECT COALESCE(SUM(calories),0) AS total_cal,
                   COALESCE(SUM(protein),0)  AS total_protein,
                   COALESCE(SUM(carbs),0)    AS total_carbs,
                   COALESCE(SUM(fats),0)     AS total_fats,
                   COUNT(*) AS entries
            FROM food_diary WHERE user_id=? AND date=?
        '''), (user_id, today))
        return row or {}
    finally:
        conn.close()
