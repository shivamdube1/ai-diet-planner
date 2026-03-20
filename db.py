"""
Universal DB adapter — PostgreSQL on Render, SQLite locally.
All models import get_db / execute / fetchone / fetchall / commit from here.
"""
import os, sqlite3
from config import Config

DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2, psycopg2.extras
    # Render gives postgres:// but psycopg2 needs postgresql://
    _pg_dsn = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def get_db():
    if USE_PG:
        conn = psycopg2.connect(_pg_dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def q(sql):
    """Convert SQLite ? placeholders → %s for PostgreSQL."""
    if USE_PG:
        return sql.replace('?', '%s')
    return sql


def fetchone(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(q(sql), params)
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def fetchall(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(q(sql), params)
    return [dict(r) for r in cur.fetchall()]


def execute(conn, sql, params=()):
    """Execute and return lastrowid / cursor."""
    cur = conn.cursor()
    cur.execute(q(sql), params)
    if USE_PG:
        return cur
    return cur


def lastrowid(cur, conn):
    """Get last inserted ID for both backends."""
    if USE_PG:
        return cur.fetchone()['id'] if cur.description else None
    return cur.lastrowid


def serial(col_def):
    """AUTOINCREMENT → SERIAL for PG."""
    if USE_PG:
        return col_def.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    return col_def


PG = USE_PG
