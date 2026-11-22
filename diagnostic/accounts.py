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
        columns={row[1] for row in conn.execute('PRAGMA table_info(student_accounts)')}
        if 'email' not in columns:
            conn.execute('ALTER TABLE student_accounts ADD COLUMN email TEXT')
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS student_account_email ON student_accounts(lower(email)) WHERE email IS NOT NULL')


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
    supplied_name = body.get('name',body.get('display_name', ''))
    name = supplied_name.strip() if isinstance(supplied_name,str) else ''
    email = str(body.get('email','')).strip().lower()
    password = body.get('password')
    if not 1 <= len(name) <= 80:
        raise ValueError('Enter your name using 1–80 characters.')
    if len(email)>254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+",email) or '..' in email or email.startswith('.') or '.@' in email:
        raise ValueError('Enter a valid email address.')
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('Choose a password with 12–128 characters.')
    username = 'user-' + secrets.token_hex(12)
    learner = 'account-' + secrets.token_hex(16)
    try:
        with conn:
            conn.execute('INSERT INTO student_accounts (username,learner,display_name,salt,password_hash,email) VALUES (?,?,?,?,?,?)',
                         (username, learner, name, *credential(password),email))
    except sqlite3.IntegrityError:
        raise ValueError('An account with this email already exists. Sign in instead.') from None
    return username, learner, name, email


def authenticate(conn, body):
    identifier = str(body.get('identifier',body.get('email',body.get('username', '')))).strip().lower()
    password = body.get('password')
    if not 1 <= len(identifier) <= 254 or not isinstance(password, str) or not 1 <= len(password) <= 128:
        return None
    row = conn.execute('SELECT username,learner,display_name,email,salt,password_hash FROM student_accounts WHERE username=? OR lower(email)=?',
                       (identifier,identifier)).fetchone()
    salt, expected = row[4:] if row else (bytes(16), bytes(32))
    candidate = (b'G' + hashlib.sha256(salt + password.encode('utf-8')).digest()
                 if len(expected) == 33 else digest(password, salt))
    valid = hmac.compare_digest(candidate, expected)
    return row[:4] if valid and row else None


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
    return conn.execute("""SELECT a.username,a.learner,a.display_name,a.email
        FROM student_auth_sessions s JOIN student_accounts a ON a.username=s.username
        WHERE s.token_hash=? AND s.expires>?""", (token_hash(token), int(time.time()))).fetchone()


def public(account):
    return dict(zip(('username', 'learner', 'display_name','email'), account)) if account else None


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
