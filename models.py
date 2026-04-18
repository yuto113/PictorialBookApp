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

    knowledge = db.Column(db.Text, nullable=True)
    # リレーションシップ設定
    user = db.relationship(
        'User', 
        backref=db.backref('dates', cascade='all, delete-orphan', passive_deletes=True)
    )
    likes = db.relationship('Like', back_populates='date')
    chats = db.relationship('Chat', back_populates='date', cascade='all, delete-orphan', passive_deletes=True)

class SchoolMessage(db.Model):
    __tablename__ = 'school_message'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='school_messages')
    school = db.relationship('School', backref='messages')
    replies = db.relationship('SchoolMessageReply', backref='message', cascade='all, delete-orphan')


class SchoolMessageReply(db.Model):
    __tablename__ = 'school_message_reply'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.Integer, db.ForeignKey('school_message.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    reply = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='school_message_replies')


class ClassChat(db.Model):
    __tablename__ = 'class_chat'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='class_chats')
    school_class = db.relationship('SchoolClass', backref='chats')
    replies = db.relationship('ClassChatReply', backref='chat', cascade='all, delete-orphan')


class ClassChatReply(db.Model):
    __tablename__ = 'class_chat_reply'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('class_chat.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    reply = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='class_chat_replies')

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
    # ↓↓↓ここから↓↓↓
    use_map = db.Column(db.Integer, default=1)  # 0:OFF 1:ON
    is_active = db.Column(db.Integer, default=1)  # 1:有効 0:停止

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

class ClassTeacher(db.Model):
    """クラスの担任設定"""
    __tablename__ = 'class_teacher'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id', ondelete='CASCADE'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('class_id', name='_class_teacher_uc'),)
    
    teacher = db.relationship('User', backref='teaching_classes')
    school_class = db.relationship('SchoolClass', backref='teacher_assignment')


class Assignment(db.Model):
    """課題"""
    __tablename__ = 'assignment'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id', ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True), nullable=False)
    is_closed = db.Column(db.Integer, default=0)  # 0:open 1:closed
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    school_class = db.relationship('SchoolClass', backref='assignments')
    creator = db.relationship('User', backref='created_assignments')
    submissions = db.relationship('AssignmentSubmission', backref='assignment', cascade='all, delete-orphan')
    chats = db.relationship('AssignmentChat', backref='assignment', cascade='all, delete-orphan')


class AssignmentSubmission(db.Model):
    """課題への投稿"""
    __tablename__ = 'assignment_submission'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id', ondelete='CASCADE'), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey('date.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='submissions')
    date = db.relationship('Date', backref='assignment_submissions')


class AssignmentChat(db.Model):
    """課題チャット"""
    __tablename__ = 'assignment_chat'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='assignment_chats')
    replies = db.relationship('AssignmentChatReply', backref='chat', cascade='all, delete-orphan')


class AssignmentChatReply(db.Model):
    """課題チャットへの返信"""
    __tablename__ = 'assignment_chat_reply'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('assignment_chat.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    reply = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='assignment_chat_replies')

class Review(db.Model):
    """利用者レビュー"""
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    role_label = db.Column(db.String(50), nullable=True)  # 例：小学生、中学生、保護者など
    stars = db.Column(db.Integer, default=5)  # 1-5
    message = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Integer, default=0)  # 0:未承認 1:承認済み
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='reviews')

class AppSetting(db.Model):
    """アプリ全体の設定"""
    __tablename__ = 'app_setting'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

class Friend(db.Model):
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='_user_friend_uc'),)