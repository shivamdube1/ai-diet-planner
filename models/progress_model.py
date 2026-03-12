from models.user_model import get_db
from datetime import datetime


def add_progress_entry(user_id, weight, notes=''):
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO progress (user_id, weight, date, notes) VALUES (?, ?, ?, ?)',
            (user_id, weight, datetime.now().strftime('%Y-%m-%d'), notes)
        )
        conn.commit()
    finally:
        conn.close()


def get_progress_by_user(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            'SELECT * FROM progress WHERE user_id = ? ORDER BY date ASC',
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_weight(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT weight FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 1',
            (user_id,)
        ).fetchone()
        return row['weight'] if row else None
    finally:
        conn.close()
