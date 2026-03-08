import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db
from flask import Flask

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

with app.app_context():
    # nicknameカラムを削除（存在する場合）
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("ALTER TABLE user DROP COLUMN nickname"))
            conn.commit()
            print("Dropped nickname column")
        except Exception as e:
            print(f"Column might not exist: {e}")
    
    print("Migration completed: dropped nickname column if existed")