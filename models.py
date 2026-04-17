from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    password = db.Column(db.Text)

    icon_image = db.Column(db.Text, default='default.png')

    role = db.Column(db.Text, default='normal')

    is_admin = db.Column(db.Integer, default=0)

    likes = db.relationship('Like',back_populates='user')
    chats = db.relationship('Chat', back_populates='user')
    friends = db.relationship('User', secondary='friends', 
                                primaryjoin='User.id==Friend.user_id',
                                secondaryjoin='User.id==Friend.friend_id',
                                backref='friend_of')

class Date(db.Model):
    __tablename__ = 'date'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    place = db.Column(db.Text)
    name = db.Column(db.Text)
    subject = db.Column(db.Text)
    imagepass = db.Column(db.Text)
    goodpoint = db.Column(db.Integer, default=0)  # いいね数のカラムを追加
    ido = db.Column(db.Float)  # 緯度
    keido = db.Column(db.Float)  # 経度
    # 公式ユーザ向けの追加メタ情報
    # `subject` は公式の「種類」として利用します（既存DBと互換）。
    explanatorytext = db.Column(db.Text, nullable=True) # 説明文（公式のみ入力）
    
    is_hidden = db.Column(db.Integer, default=0)

    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)

    # リレーションシップ設定
    user = db.relationship(
        'User', 
        backref=db.backref('dates', cascade='all, delete-orphan', passive_deletes=True)
    )
    likes = db.relationship('Like', back_populates='date')
    chats = db.relationship('Chat', back_populates='date', cascade='all, delete-orphan', passive_deletes=True)

class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey('date.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'date_id', name='_user_animal_uc'),)

    user = db.relationship('User', back_populates='likes')
    date = db.relationship('Date', back_populates='likes')

class Chat(db.Model):
    __tablename__ = 'chat'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey('date.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    
    is_hidden = db.Column(db.Integer, default=0)

    user = db.relationship('User', back_populates='chats')
    date = db.relationship('Date', back_populates='chats')

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Integer, default=0)  # 0:未読 1:既読
    reply = db.Column(db.Text, nullable=True)  # 管理者の返信
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    replied_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    user = db.relationship('User', backref='feedbacks')

import random
import string

def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class School(db.Model):
    __tablename__ = 'school'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    members = db.relationship('SchoolMember', backref='school', cascade='all, delete-orphan')
    classes = db.relationship('SchoolClass', backref='school', cascade='all, delete-orphan')


class SchoolMember(db.Model):
    __tablename__ = 'school_member'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('school_id', 'user_id', name='_school_user_uc'),)


class SchoolClass(db.Model):
    __tablename__ = 'school_class'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text, unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    members = db.relationship('ClassMember', backref='school_class', cascade='all, delete-orphan')


class ClassMember(db.Model):
    __tablename__ = 'class_member'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('class_id', 'user_id', name='_class_user_uc'),)

class Friend(db.Model):
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='_user_friend_uc'),)