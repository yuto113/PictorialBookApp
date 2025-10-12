from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    password = db.Column(db.Text)
    likes = db.relationship('Like',back_populates='user')

class Date(db.Model):
    __tablename__ = 'date'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    place = db.Column(db.Text)
    name = db.Column(db.Text)
    subject = db.Column(db.Text)
    imagepass = db.Column(db.Text)
    goodpoint = db.Column(db.Integer, default=0)  # いいね数のカラムを追加
    
    # リレーションシップ設定
    user = db.relationship(
        'User', 
        backref=db.backref('dates', cascade='all, delete-orphan', passive_deletes=True)
    )
    likes = db.relationship('Like', back_populates='date')

class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey('date.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'date_id', name='_user_animal_uc'),)

    user = db.relationship('User', back_populates='likes')
    date = db.relationship('Date', back_populates='likes')