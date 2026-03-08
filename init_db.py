from flask_app import app
from models import db, User, Date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config

engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

with app.app_context():
    db.metadata.create_all(engine)
    print("Database tables created.")

    # テストユーザー追加
    test_user = User(name='test', password='test')
    session.add(test_user)
    session.commit()
    print("Test user added: name='test', password='test'")

    # テストデータ追加
    test_date = Date(user_id=1, place='Test Place', name='Test Date', subject='Test Subject')
    session.add(test_date)
    session.commit()
    print("Test date added.")

session.close()