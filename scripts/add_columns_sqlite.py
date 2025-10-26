import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'db.sqlite')

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA table_info('date')")
cols = [row[1] for row in cur.fetchall()]

if 'explanatorytext' not in cols:
    print('Adding column: explanatorytext')
    cur.execute("ALTER TABLE date ADD COLUMN explanatorytext TEXT")
else:
    print('Column explanatorytext already exists')

conn.commit()
conn.close()
print('Done')
