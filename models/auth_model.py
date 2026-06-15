from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, fetchone, fetchall, execute, lastrowid, serial, q, PG
import random


def create_accounts_table():
    conn = get_db()
    try:
        conn.cursor().execute(q(serial('''
            CREATE TABLE IF NOT EXISTS accounts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                email        TEXT    UNIQUE NOT NULL,
                password     TEXT    NOT NULL,
                avatar_color TEXT    DEFAULT '#22c55e',
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
                last_login   TEXT
            )
        ''')))
        conn.commit()
    finally:
        conn.close()

    # Add account_id to users if missing
    conn2 = get_db()
    try:
        if PG:
            existing = [r['column_name'] for r in fetchall(conn2,
                "SELECT column_name FROM information_schema.columns WHERE table_name='users'")]
        else:
            existing = [r[1] for r in conn2.execute("PRAGMA table_info(users)").fetchall()]
        if 'account_id' not in existing:
            conn2.cursor().execute("ALTER TABLE users ADD COLUMN account_id INTEGER")
            conn2.commit()
    except Exception:
        pass
    finally:
        conn2.close()

    # Add google_id to accounts if missing
    conn3 = get_db()
    try:
        if PG:
            existing_acct = [r['column_name'] for r in fetchall(conn3,
                "SELECT column_name FROM information_schema.columns WHERE table_name='accounts'")]
        else:
            existing_acct = [r[1] for r in conn3.execute("PRAGMA table_info(accounts)").fetchall()]
        if 'google_id' not in existing_acct:
            conn3.cursor().execute("ALTER TABLE accounts ADD COLUMN google_id TEXT")
            conn3.commit()
    except Exception:
        pass
    finally:
        conn3.close()


def register_account(name, email, password):
    if get_account_by_email(email):
        return None, 'An account with this email already exists.'
    colors = ['#22c55e','#3b82f6','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#ef4444']
    color = random.choice(colors)
    conn = get_db()
    try:
        returning = " RETURNING id" if PG else ""
        sql = q(f"INSERT INTO accounts (name, email, password, avatar_color) VALUES (?,?,?,?){returning}")
        cur = execute(conn, sql, (name.strip(), email.lower().strip(),
                                   generate_password_hash(password), color))
        row_id = (cur.fetchone() or {}).get('id') if PG else cur.lastrowid
        conn.commit()
        return row_id, None
    except Exception:
        return None, 'Email already registered.'
    finally:
        conn.close()


def login_account(email, password):
    account = get_account_by_email(email)
    if not account:
        return None, 'No account found with that email.'
    if not check_password_hash(account['password'], password):
        return None, 'Incorrect password.'
    conn = get_db()
    try:
        execute(conn, q("UPDATE accounts SET last_login = CURRENT_TIMESTAMP WHERE id = ?"),
                (account['id'],))
        conn.commit()
    finally:
        conn.close()
    return account, None


def get_account_by_email(email):
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM accounts WHERE email = ?',
                        (email.lower().strip(),))
    finally:
        conn.close()


def get_account_by_id(account_id):
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM accounts WHERE id = ?', (account_id,))
    finally:
        conn.close()


def update_account(account_id, name, email):
    conn = get_db()
    try:
        execute(conn, q('UPDATE accounts SET name=?, email=? WHERE id=?'),
                (name, email, account_id))
        conn.commit()
    finally:
        conn.close()


def change_password(account_id, new_password):
    conn = get_db()
    try:
        execute(conn, q('UPDATE accounts SET password=? WHERE id=?'),
                (generate_password_hash(new_password), account_id))
        conn.commit()
    finally:
        conn.close()


def get_profiles_for_account(account_id):
    conn = get_db()
    try:
        return fetchall(conn,
            'SELECT * FROM users WHERE account_id = ? ORDER BY created_at DESC',
            (account_id,))
    finally:
        conn.close()


def link_user_to_account(user_id, account_id):
    conn = get_db()
    try:
        execute(conn, q('UPDATE users SET account_id=? WHERE id=?'), (account_id, user_id))
        conn.commit()
    finally:
        conn.close()


def get_account_by_google_id(google_id):
    if not google_id:
        return None
    conn = get_db()
    try:
        return fetchone(conn, 'SELECT * FROM accounts WHERE google_id = ?', (google_id,))
    finally:
        conn.close()


def register_google_account(name, email, google_id):
    """Register or link a Google account dynamically."""
    existing = get_account_by_email(email)
    if existing:
        # Link existing email/password account with Google ID
        conn = get_db()
        try:
            execute(conn, q('UPDATE accounts SET google_id = ?, name = ? WHERE id = ?'),
                    (google_id, name.strip(), existing['id']))
            conn.commit()
        finally:
            conn.close()
        return get_account_by_id(existing['id']), None

    colors = ['#22c55e','#3b82f6','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#ef4444']
    color = random.choice(colors)
    
    # Generate a secure random password since password field is NOT NULL in database
    import secrets
    random_password = secrets.token_urlsafe(24)
    
    conn = get_db()
    try:
        returning = " RETURNING id" if PG else ""
        sql = q(f"INSERT INTO accounts (name, email, password, google_id, avatar_color) VALUES (?,?,?,?,?){returning}")
        cur = execute(conn, sql, (name.strip(), email.lower().strip(),
                                   generate_password_hash(random_password), google_id, color))
        row_id = (cur.fetchone() or {}).get('id') if PG else cur.lastrowid
        conn.commit()
        return row_id, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()
