"""Provision accounts from the imported roster. Run as a module from the project root."""
import argparse
import csv
import hashlib
from pathlib import Path
import re
import secrets
import sqlite3

from diagnostic import accounts, engine, imported_reports


def provision(output, resume=False):
    output = Path(output)
    with sqlite3.connect(f'{imported_reports.STORE.as_uri()}?mode=ro', uri=True) as roster:
        ids = [row[0] for row in roster.execute('SELECT id FROM students ORDER BY length(id),id')]
    conn = engine.connect()
    try:
        accounts.ensure(conn)
        saved = {}
        if resume:
            with output.open(encoding='utf-8-sig', newline='') as existing:
                saved = {row['student_id']: row for row in csv.DictReader(existing)}
        with output.open('a' if resume else 'x', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            if not resume:
                writer.writerow(('student_id', 'username', 'password'))
            for student_id in ids:
                if conn.execute('SELECT 1 FROM student_accounts WHERE student_id=?', (student_id,)).fetchone():
                    continue
                alias = student_id if re.fullmatch(r'[0-9]{1,24}', student_id) else hashlib.sha256(student_id.encode()).hexdigest()[:24]
                username = 'student-' + alias
                password = saved[student_id]['password'] if student_id in saved else secrets.token_urlsafe(24)
                salt, password_hash = accounts.generated_credential(password)
                with conn:
                    # Preserve the canonical space, or the most-used previously linked space.
                    previous = conn.execute("""SELECT learner FROM student_learning_spaces WHERE student_id=?
                        UNION ALL SELECT learner FROM (
                            SELECT p.learner FROM external_profile_links p
                            LEFT JOIN sessions s ON s.learner=p.learner WHERE p.student_id=?
                            GROUP BY p.learner ORDER BY count(s.id) DESC,p.learner LIMIT 1)
                        LIMIT 1""", (student_id, student_id)).fetchone()
                    learner = previous[0] if previous else 'account-' + secrets.token_hex(16)
                    conn.execute('INSERT OR IGNORE INTO student_learning_spaces VALUES (?,?)', (student_id, learner))
                    conn.execute('INSERT OR REPLACE INTO external_profile_links VALUES (?,?)', (learner, student_id))
                    conn.execute('INSERT INTO student_accounts (username,learner,display_name,salt,password_hash,student_id) VALUES (?,?,?,?,?,?)',
                                 (username, learner, imported_reports.display_name(student_id), salt, password_hash, student_id))
                    if student_id not in saved:
                        writer.writerow((student_id, username, password))
                        file.flush()
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='New private CSV path')
    parser.add_argument('--resume', action='store_true', help='Continue an interrupted export using the same CSV')
    args = parser.parse_args()
    provision(args.output, args.resume)
