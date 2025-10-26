import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'db.sqlite')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA table_info('date')")
cols = [row[1] for row in cur.fetchall()]
print('date table columns:')
for c in cols:
    print(' -', c)
conn.close()
