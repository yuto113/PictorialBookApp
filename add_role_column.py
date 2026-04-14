import sqlite3
import os

DB_PATH = os.path.join('instance', 'db.sqlite')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info('user')")
cols = [row[1] for row in cur.fetchall()]

if 'role' not in cols:
    print('Adding column: role')
    cur.execute("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'normal'")
    # 管理者（id=2）をadminに設定
    cur.execute("UPDATE user SET role = 'admin' WHERE id = 2")
    conn.commit()
    print('Done')
else:
    print('Column role already exists')

conn.close()