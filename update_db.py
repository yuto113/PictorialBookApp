from flask_app import app, db
from sqlalchemy import text

with app.app_context():
    # データベースに「is_admin」という列を無理やり追加する魔法の言葉
    db.session.execute(text('ALTER TABLE user ADD COLUMN is_admin INTEGER DEFAULT 0'))
    db.session.commit()
    print("成功！is_admin列を追加しました。")