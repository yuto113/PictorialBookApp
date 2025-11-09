import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from flask_app import app, db_session
from models import User

with app.app_context():
    admin = db_session.query(User).filter_by(id=2).first()
    print('adminpw=', admin.password)

    with app.test_client() as c:
        with c.session_transaction() as s:
            s['user_id'] = 2
        r = c.get('/reveal')
        text = r.get_data(as_text=True)
        print('status=', r.status_code)
        print('確認フォームがあるか:', '現在のパスワード' in text)
        print('id表示欄があるか:', '<strong>id:</strong>' in text)
