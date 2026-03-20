from db import get_db, fetchone, fetchall, execute, q, PG
from datetime import date


def add_progress_entry(user_id, weight, notes=''):
    conn = get_db()
    try:
        today = str(date.today())
        execute(conn, q('INSERT INTO progress (user_id, weight, date, notes) VALUES (?,?,?,?)'),
                (user_id, weight, today, notes))
        conn.commit()
    finally:
        conn.close()


def get_progress_by_user(user_id):
    conn = get_db()
    try:
        return fetchall(conn,
            'SELECT * FROM progress WHERE user_id = ? ORDER BY date ASC', (user_id,))
    finally:
        conn.close()


def get_latest_weight(user_id):
    conn = get_db()
    try:
        row = fetchone(conn,
            'SELECT weight FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 1',
            (user_id,))
        return row['weight'] if row else None
    finally:
        conn.close()
