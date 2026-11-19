"""Student credentials and server-side sessions."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

SESSION_AGE = 7 * 24 * 60 * 60
COOKIE = 'atlas_session'


def ensure(conn):
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS student_accounts (
            username TEXT PRIMARY KEY, learner TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL, salt BLOB NOT NULL, password_hash BLOB NOT NULL,
            student_id TEXT UNIQUE)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS student_auth_sessions (
            token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires INTEGER NOT NULL)""")


def digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600_000)


def credential(password):
    salt = secrets.token_bytes(16)
    return salt, digest(password, salt)


def generated_credential(password):
    # Provisioning supplies 192 random bits. User-chosen passwords use PBKDF2.
    salt = secrets.token_bytes(16)
    return salt, b'G' + hashlib.sha256(salt + password.encode('utf-8')).digest()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create(conn, body):
    username = str(body.get('username', '')).strip().lower()
    name = str(body.get('display_name', '')).strip()
    password = body.get('password')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,39}', username) or username.startswith('student-'):
        raise ValueError('Choose a username with 3–40 letters, numbers, hyphens or underscores. Student usernames are reserved.')
    if not 1 <= len(name) <= 80:
        raise ValueError('Enter a display name of 1–80 characters.')
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('Choose a password with 12–128 characters.')
    learner = 'account-' + secrets.token_hex(16)
    try:
        with conn:
            conn.execute('INSERT INTO student_accounts VALUES (?,?,?,?,?,NULL)',
                         (username, learner, name, *credential(password)))
    except sqlite3.IntegrityError:
        raise ValueError('That username is unavailable.') from None
    return username, learner, name


def authenticate(conn, body):
    username = str(body.get('username', '')).strip().lower()[:80]
    password = body.get('password')
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        return None
    row = conn.execute('SELECT username,learner,display_name,salt,password_hash FROM student_accounts WHERE username=?',
                       (username,)).fetchone()
    salt, expected = row[3:] if row else (bytes(16), bytes(32))
    candidate = (b'G' + hashlib.sha256(salt + password.encode('utf-8')).digest()
                 if len(expected) == 33 else digest(password, salt))
    valid = hmac.compare_digest(candidate, expected)
    return row[:3] if valid and row else None


def start(conn, username, old_token):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with conn:
        conn.execute('DELETE FROM student_auth_sessions WHERE expires<=? OR token_hash=?',
                     (now, token_hash(old_token)))
        conn.execute('INSERT INTO student_auth_sessions VALUES (?,?,?)',
                     (token_hash(token), username, now + SESSION_AGE))
    return token


def end(conn, token):
    with conn:
        conn.execute('DELETE FROM student_auth_sessions WHERE token_hash=?', (token_hash(token),))


def current(conn, token):
    if not token:
        return None
    return conn.execute("""SELECT a.username,a.learner,a.display_name
        FROM student_auth_sessions s JOIN student_accounts a ON a.username=s.username
        WHERE s.token_hash=? AND s.expires>?""", (token_hash(token), int(time.time()))).fetchone()


def public(account):
    return dict(zip(('username', 'learner', 'display_name'), account)) if account else None


def authorize(conn, learner, token, allow_legacy_profiles=False):
    # Legacy study/guest codes still work unless they belong to a student space.
    private = learner.startswith(('account-', 'student-')) or (not allow_legacy_profiles and conn.execute("""
        SELECT 1 FROM student_accounts WHERE learner=?
        UNION ALL SELECT 1 FROM external_profile_links WHERE learner=?
        UNION ALL SELECT 1 FROM student_learning_spaces WHERE learner=?
        LIMIT 1""", (learner, learner, learner)).fetchone())
    if private:
        account = current(conn, token)
        if not account or account[1] != learner:
            raise PermissionError('Sign in to access this learning space.')
