import sqlite3
import os

DB_PATH = os.path.join('instance', 'db.sqlite')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info('date')")
cols = [row[1] for row in cur.fetchall()]

if 'school_id' not in cols:
    cur.execute("ALTER TABLE date ADD COLUMN school_id INTEGER")
    conn.commit()
    print("Added school_id column")
else:
    print("school_id already exists")

conn.close()