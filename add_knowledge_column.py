# add_knowledge_column.py
import sqlite3
import os

DB_PATH = os.path.join('instance', 'db.sqlite')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA table_info('date')")
cols = [row[1] for row in cur.fetchall()]
if 'knowledge' not in cols:
    cur.execute("ALTER TABLE date ADD COLUMN knowledge TEXT")
    conn.commit()
    print("Added knowledge column")
else:
    print("Already exists")
conn.close()