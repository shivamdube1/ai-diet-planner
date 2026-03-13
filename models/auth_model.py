import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from models.user_model import get_db


def create_accounts_table():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            email        TEXT    UNIQUE NOT NULL,
            password     TEXT    NOT NULL,
            avatar_color TEXT    DEFAULT '#22c55e',
            created_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
            last_login   TEXT
        )
    ''')
    # Add account_id FK to users if it doesn't already exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if 'account_id' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN account_id INTEGER REFERENCES accounts(id)")
    conn.commit()
    conn.close()


def register_account(name, email, password):
    """Create a new account. Returns (account_id, None) or (None, error_msg)."""
    if get_account_by_email(email):
        return None, 'An account with this email already exists.'
    colors = ['#22c55e','#3b82f6','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#ef4444']
    import random
    color = random.choice(colors)
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO accounts (name, email, password, avatar_color) VALUES (?,?,?,?)',
            (name.strip(), email.lower().strip(), generate_password_hash(password), color)
        )
        conn.commit()
        return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, 'Email already registered.'
    finally:
        conn.close()


def login_account(email, password):
    """Verify credentials. Returns (account, None) or (None, error_msg)."""
    account = get_account_by_email(email)
    if not account:
        return None, 'No account found with that email.'
    if not check_password_hash(account['password'], password):
        return None, 'Incorrect password.'
    # Update last_login
    conn = get_db()
    conn.execute("UPDATE accounts SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (account['id'],))
    conn.commit()
    conn.close()
    return account, None


def get_account_by_email(email):
    conn = get_db()
    try:
        row = conn.execute('SELECT * FROM accounts WHERE email = ?', (email.lower().strip(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_account_by_id(account_id):
    conn = get_db()
    try:
        row = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_account(account_id, name, email):
    conn = get_db()
    try:
        conn.execute('UPDATE accounts SET name=?, email=? WHERE id=?', (name, email, account_id))
        conn.commit()
    finally:
        conn.close()


def change_password(account_id, new_password):
    conn = get_db()
    try:
        conn.execute('UPDATE accounts SET password=? WHERE id=?',
                     (generate_password_hash(new_password), account_id))
        conn.commit()
    finally:
        conn.close()


def get_profiles_for_account(account_id):
    """All health profiles (users rows) linked to an account."""
    conn = get_db()
    try:
        rows = conn.execute(
            'SELECT * FROM users WHERE account_id = ? ORDER BY created_at DESC',
            (account_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def link_user_to_account(user_id, account_id):
    conn = get_db()
    try:
        conn.execute('UPDATE users SET account_id=? WHERE id=?', (account_id, user_id))
        conn.commit()
    finally:
        conn.close()
