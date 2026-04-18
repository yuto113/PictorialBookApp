import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from flask import Flask

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # use_mapカラムを追加
    import sqlite3
    DB_PATH = os.path.join('instance', 'db.sqlite')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info('school')")
    cols = [row[1] for row in cur.fetchall()]
    if 'use_map' not in cols:
        cur.execute("ALTER TABLE school ADD COLUMN use_map INTEGER DEFAULT 1")
        conn.commit()
        print("Added use_map column")
    
    conn.close()
    print("All tables created!")