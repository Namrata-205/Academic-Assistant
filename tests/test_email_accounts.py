import sqlite3
import unittest
from diagnostic import accounts


class EmailAccountTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:');accounts.ensure(self.conn)
    def tearDown(self):self.conn.close()

    def test_registration_login_and_duplicate_normalization(self):
        details={'name':'  Aanya Dalvi  ','email':'  Aanya@Example.test  ','password':'a-strong-test-password'}
        account=accounts.create(self.conn,details)
        self.assertEqual(accounts.public(account)['display_name'],'Aanya Dalvi')
        self.assertEqual(accounts.public(account)['email'],'aanya@example.test')
        self.assertEqual(accounts.authenticate(self.conn,{'identifier':'AANYA@EXAMPLE.TEST','password':details['password']}),account)
        self.assertIsNone(accounts.authenticate(self.conn,{'email':'aanya@example.test','password':'wrong'}))
        with self.assertRaisesRegex(ValueError,'already exists'):accounts.create(self.conn,dict(details,email='aanya@example.test'))
        stored=self.conn.execute('SELECT password_hash FROM student_accounts').fetchone()[0]
        self.assertNotEqual(stored,details['password'].encode())
        token=accounts.start(self.conn,account[0],'')
        self.assertEqual(accounts.current(self.conn,token),account)
        accounts.end(self.conn,token);self.assertIsNone(accounts.current(self.conn,token))

    def test_invalid_fields_are_rejected(self):
        base={'name':'Aanya','email':'aanya@example.test','password':'a-strong-test-password'}
        for changes in [{'name':''},{'name':None},{'name':' '*10},{'email':''},{'email':'not-an-email'},
                        {'email':'a@@example.test'},{'email':'a..b@example.test'},{'password':'short'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):accounts.create(self.conn,dict(base,**changes))

    def test_legacy_migration_preserves_school_credentials(self):
        conn=sqlite3.connect(':memory:')
        try:
            conn.execute('CREATE TABLE student_accounts(username TEXT PRIMARY KEY,learner TEXT UNIQUE NOT NULL,display_name TEXT NOT NULL,salt BLOB NOT NULL,password_hash BLOB NOT NULL,student_id TEXT UNIQUE)')
            salt,password_hash=accounts.generated_credential('school-issued-password')
            conn.execute('INSERT INTO student_accounts VALUES (?,?,?,?,?,?)',('student-001','student-space','Learner One',salt,password_hash,'001'));conn.commit()
            accounts.ensure(conn);accounts.ensure(conn)
            self.assertEqual(accounts.authenticate(conn,{'username':'student-001','password':'school-issued-password'}),('student-001','student-space','Learner One',None))
            self.assertEqual(conn.execute('SELECT salt,password_hash FROM student_accounts').fetchone(),(salt,password_hash))
            self.assertIn('email',[row[1] for row in conn.execute('PRAGMA table_info(student_accounts)')])
        finally:conn.close()


if __name__=='__main__':unittest.main()
