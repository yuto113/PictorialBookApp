import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db
from flask import Flask

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

with app.app_context():
    # statusカラムを追加
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("ALTER TABLE friends ADD COLUMN status TEXT DEFAULT 'pending'"))
            conn.commit()
            print("Added status column to friends table")
        except Exception as e:
            print(f"Column might already exist: {e}")
    
    print("Migration completed")