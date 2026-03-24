"""Password reset tokens stored in DB."""
import secrets
from datetime import datetime, timedelta
from db import get_db, fetchone, execute, q, PG, serial


def create_reset_token_table():
    conn = get_db()
    try:
        conn.cursor().execute(q(serial("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)))
        conn.commit()
    finally:
        conn.close()


def create_reset_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    conn = get_db()
    try:
        # Clear old tokens for this email
        execute(conn, q("DELETE FROM password_resets WHERE email = ?"), (email,))
        returning = " RETURNING id" if PG else ""
        execute(conn, q(f"INSERT INTO password_resets (email, token, expires_at) VALUES (?,?,?){returning}"),
                (email.lower().strip(), token, expires))
        conn.commit()
    finally:
        conn.close()
    return token


def validate_reset_token(token: str):
    """Returns email if valid and not expired, else None."""
    conn = get_db()
    try:
        row = fetchone(conn, q("SELECT * FROM password_resets WHERE token = ? AND used = 0"), (token,))
        if not row:
            return None
        expires = datetime.fromisoformat(row['expires_at'])
        if datetime.utcnow() > expires:
            return None
        return row['email']
    finally:
        conn.close()


def mark_token_used(token: str):
    conn = get_db()
    try:
        execute(conn, q("UPDATE password_resets SET used = 1 WHERE token = ?"), (token,))
        conn.commit()
    finally:
        conn.close()
