import os
os.makedirs('/app/instance', exist_ok=True)
from flask import Flask, render_template, request, redirect, session, flash
from models import User, db, Date, Like, Chat, Friend, Feedback, School, SchoolMember, SchoolClass, ClassMember, SchoolMessage, SchoolMessageReply, ClassChat, ClassChatReply, ClassTeacher, Assignment, AssignmentSubmission, AssignmentChat, AssignmentChatReply
from sqlalchemy import or_
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

basedir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)

app = Flask(__name__)
app.secret_key='secret_key'
app.config.from_object('config')

# グローバル変数でバージョン情報を管理　
app_verj = None

db.init_app(app)
db_session = db.session

with app.app_context():
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    # if not os.path.exists(db_path):
    #     db.create_all()
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    if not os.path.exists(db_path):
        db.create_all()

@app.context_processor
def inject_globals():
    global app_verj
    user_id = session.get('user_id')
    user_role = 'normal'
    is_school_user = False
    if user_id:
        user = User.query.get(user_id)
        if user:
            user_role = user.role
            is_school_user = user.role in ['teacher', 'school_admin', 'student']
    return dict(
        now=lambda: datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0),
        verj=app_verj if app_verj else app.config.get('VERJ', 'ver.1.0'),
        user_role=user_role,
        is_school_user=is_school_user
    )

@app.route('/school/messages', methods=['GET', 'POST'])
def school_messages():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'student', 'school_admin']:
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    school = School.query.get(my_member.school_id)
    
    if request.method == 'POST':
        if user.role not in ['teacher', 'school_admin']:
            flash('メッセージの送信は教師・学校管理者のみ可能です。', 'danger')
            return redirect('/school/messages')
        message = request.form.get('message')
        if message:
            new_msg = SchoolMessage(
                school_id=my_member.school_id,
                user_id=user_id,
                message=message,
                created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
            )
            db.session.add(new_msg)
            db.session.commit()
            return redirect('/school/messages')
    
    messages = SchoolMessage.query.filter_by(
        school_id=my_member.school_id
    ).order_by(SchoolMessage.created_at.desc()).all()
    
    return render_template('school_messages.html',
                           user=user,
                           school=school,
                           messages=messages)


@app.route('/school/messages/reply/<int:message_id>', methods=['POST'])
def school_message_reply(message_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    reply_text = request.form.get('reply')
    if reply_text:
        new_reply = SchoolMessageReply(
            message_id=message_id,
            user_id=user_id,
            reply=reply_text,
            created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
        )
        db.session.add(new_reply)
        db.session.commit()
    
    return redirect('/school/messages')


@app.route('/school/messages/delete/<int:message_id>', methods=['POST'])
def delete_school_message(message_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    msg = SchoolMessage.query.get(message_id)
    if msg and (msg.user_id == user_id or User.query.get(user_id).role in ['school_admin'] or user_id == 2):
        db.session.delete(msg)
        db.session.commit()
    
    return redirect('/school/messages')


@app.route('/school/class_chat/<int:class_id>', methods=['GET', 'POST'])
def class_chat(class_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'student', 'school_admin']:
        return redirect('/user')
    
    # クラスメンバーか教師かチェック
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    cls = SchoolClass.query.get(class_id)
    if not cls or not my_member:
        return redirect('/user')
    
    # 同じ学校かチェック
    if cls.school_id != my_member.school_id:
        return redirect('/user')
    
    school = School.query.get(my_member.school_id)
    
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            new_chat = ClassChat(
                class_id=class_id,
                user_id=user_id,
                message=message,
                created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
            )
            db.session.add(new_chat)
            db.session.commit()
            return redirect(f'/school/class_chat/{class_id}')
    
    chats = ClassChat.query.filter_by(
        class_id=class_id
    ).order_by(ClassChat.created_at.desc()).all()
    
    return render_template('class_chat.html',
                           user=user,
                           school=school,
                           cls=cls,
                           chats=chats)


@app.route('/school/class_chat/reply/<int:chat_id>', methods=['POST'])
def class_chat_reply(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    chat = ClassChat.query.get(chat_id)
    reply_text = request.form.get('reply')
    if reply_text and chat:
        new_reply = ClassChatReply(
            chat_id=chat_id,
            user_id=user_id,
            reply=reply_text,
            created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
        )
        db.session.add(new_reply)
        db.session.commit()
    
    return redirect(f'/school/class_chat/{chat.class_id}')


@app.route('/school/class_chat/delete/<int:chat_id>', methods=['POST'])
def delete_class_chat(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    chat = ClassChat.query.get(chat_id)
    if chat and (chat.user_id == user_id or User.query.get(user_id).role in ['school_admin', 'teacher'] or user_id == 2):
        class_id = chat.class_id
        db.session.delete(chat)
        db.session.commit()
        return redirect(f'/school/class_chat/{class_id}')
    
    return redirect('/user')

@app.route('/user')
def user_page():
    # show user page only when logged in
    user_id = session.get('user_id')

    search = request.args.get("search",None)
    Illustrated_ev = request.args.get("ev",None)
    Illustrated_ki = request.args.get("ki",None)
    Illustrated_friend = request.args.get("friend",None)
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        return redirect('/login')
    if user_id:
        check_user = User.query.get(user_id)
        if check_user and check_user.role == 'suspended':
            session.clear()
            flash('このアカウントは停止されています。管理者にお問い合わせください。', 'danger')
            return redirect('/login')
        search = request.args.get("search",None)
        Illustrated_ev = request.args.get("ev",None)
        Illustrated_ki = request.args.get("ki",None)
        Illustrated_friend = request.args.get("friend",None)
        # ログイン中のユーザ情報だけ取得する
        user = db_session.query(User).filter_by(id=user_id).first()
        date = db_session.query(Date)
        if search:
            date = date.filter(
                    or_(
                        Date.place.like(search),
                        Date.subject.like(search),
                        Date.name.like(search)
                    )
                )
        if Illustrated_ki == 'on':
            date = date.filter(Date.user_id == 2)
        if Illustrated_ev == 'on':
            date = date.filter(Date.user_id != 2)
        if Illustrated_friend:
            date = date.filter(Date.user_id == int(Illustrated_friend))
        # 管理者（id=2）は非表示も見える、それ以外は非表示を除外
        if user_id != 2:
            date = date.filter(Date.is_hidden != 1)
        if user.role in ['teacher', 'student', 'school_admin']:
            # 学校ユーザーは学校グループ内のデータのみ
            my_member = SchoolMember.query.filter_by(user_id=user_id).first()
            if my_member:
                school_member_ids = [m.user_id for m in SchoolMember.query.filter_by(school_id=my_member.school_id).all()]
                date = date.filter(Date.user_id.in_(school_member_ids))
            else:
                date = date.filter(Date.id == -1)
        else:
            # 通常ユーザーは学校グループのデータを除外
            school_user_ids = [m.user_id for m in SchoolMember.query.all()]
            date = date.filter(Date.user_id.notin_(school_user_ids))
        
        dates = date.filter(Date.is_hidden != 1).order_by(Date.id.desc()).all()

        # 各dateに対して、現在のユーザーがいいね済みかをチェック
        for d in dates:
            d.is_liked = db_session.query(Like).filter_by(user_id=user_id, date_id=d.id).first() is not None
            d.chat_count = db_session.query(Chat).filter_by(date_id=d.id).count()

        # フレンドリストを取得
        friends = db_session.query(User).join(Friend, 
            ((Friend.user_id == user_id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
            ((Friend.friend_id == user_id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
        ).all()

        my_school_member = SchoolMember.query.filter_by(user_id=user_id).first()
        my_school = School.query.get(my_school_member.school_id) if my_school_member else None
        
        # 所属クラス一覧を取得
        my_class_members = ClassMember.query.filter_by(user_id=user_id).all()
        my_classes = [SchoolClass.query.get(cm.class_id) for cm in my_class_members]
        # 教師・school_adminは学校内の全クラスを表示
        if user.role in ['teacher', 'school_admin'] and my_school_member:
            my_classes = SchoolClass.query.filter_by(school_id=my_school_member.school_id).all()
        
        return render_template('user.html', user=user, dates=dates, filter_ev=Illustrated_ev, filter_ki=Illustrated_ki, filter_friend=Illustrated_friend, friends=friends, my_school=my_school, user_role=user.role, my_classes=my_classes)
    
    from datetime import datetime as dt
    now_dt = dt.now(tz=ZoneInfo("Asia/Tokyo"))
    my_assignments = []
    if user.role in ['teacher', 'school_admin', 'student'] and my_school_member:
        class_ids = [cls.id for cls in my_classes]
        my_assignments = Assignment.query.filter(
                Assignment.class_id.in_(class_ids)
            ).order_by(Assignment.deadline.asc()).all()

    return redirect('/login')

@app.route('/school/toggle_map', methods=['POST'])
def toggle_map():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role != 'school_admin':
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    school = School.query.get(my_member.school_id)
    if school:
        school.use_map = 0 if school.use_map == 1 else 1
        db.session.commit()
    
    return redirect('/school/dashboard')


@app.route('/school/set_teacher', methods=['POST'])
def set_teacher():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role != 'school_admin':
        return redirect('/user')
    
    class_id = request.form.get('class_id')
    teacher_id = request.form.get('teacher_id')
    
    if class_id and teacher_id:
        # 既存の担任を削除
        existing = ClassTeacher.query.filter_by(class_id=int(class_id)).first()
        if existing:
            db.session.delete(existing)
        
        # 新しい担任を設定
        new_teacher = ClassTeacher(
            class_id=int(class_id),
            teacher_id=int(teacher_id)
        )
        db.session.add(new_teacher)
        db.session.commit()
        flash('担任を設定しました！', 'success')
    
    return redirect('/school/dashboard')

# ↓↓↓ここから↓↓↓
@app.route('/school/dashboard')
def school_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    # 学校情報を取得
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    school = School.query.get(my_member.school_id)
    
    # 学校内のクラス一覧
    classes = SchoolClass.query.filter_by(school_id=school.id).all()
    
    # 学校内のメンバー一覧
    members = db.session.query(User).join(SchoolMember, 
        SchoolMember.user_id == User.id
    ).filter(SchoolMember.school_id == school.id).all()
    
    # 学校内の生徒一覧
    students = [m for m in members if m.role == 'student']
    
    # 学校内の教師一覧
    teachers = [m for m in members if m.role in ['teacher', 'school_admin']]
    
    class_teachers = {}
    for cls in classes:
        ct = ClassTeacher.query.filter_by(class_id=cls.id).first()
        class_teachers[cls.id] = ct.teacher if ct else None
    
    return render_template('school_dashboard.html', 
                            user=user,
                            school=school,
                            classes=classes,
                            students=students,
                            teachers=teachers,
                            class_teachers=class_teachers)


@app.route('/school/create_class', methods=['POST'])
def create_class():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    class_name = request.form.get('class_name')
    if class_name:
        from models import generate_code
        code = generate_code(6)
        while SchoolClass.query.filter_by(code=code).first():
            code = generate_code(6)
        
        new_class = SchoolClass(
            school_id=my_member.school_id,
            name=class_name,
            code=code
        )
        db.session.add(new_class)
        db.session.commit()
        flash(f'クラス「{class_name}」を作成しました！コード: {code}', 'success')
    
    return redirect('/school/dashboard')


@app.route('/school/create_student', methods=['POST'])
def create_student():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    name = request.form.get('name')
    password = request.form.get('password')
    
    if name and password:
        new_student = User(name=name, password=password, role='student')
        db.session.add(new_student)
        db.session.commit()
        
        # 学校に追加
        new_member = SchoolMember(school_id=my_member.school_id, user_id=new_student.id)
        db.session.add(new_member)
        db.session.commit()
        flash(f'生徒「{name}」を登録しました！ID: {new_student.id}', 'success')
    
    return redirect('/school/dashboard')


@app.route('/school/create_teacher', methods=['POST'])
def create_teacher():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role != 'school_admin':
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    name = request.form.get('name')
    password = request.form.get('password')
    
    if name and password:
        new_teacher = User(name=name, password=password, role='teacher')
        db.session.add(new_teacher)
        db.session.commit()
        
        # 学校に追加
        new_member = SchoolMember(school_id=my_member.school_id, user_id=new_teacher.id)
        db.session.add(new_member)
        db.session.commit()
        flash(f'教師「{name}」を登録しました！ID: {new_teacher.id}', 'success')
    
    return redirect('/school/dashboard')


@app.route('/school/register_student', methods=['POST'])
def register_student_to_class():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    student_id = request.form.get('student_id')
    class_id = request.form.get('class_id')
    
    if student_id and class_id:
        student = User.query.get(student_id)
        cls = SchoolClass.query.get(class_id)
        
        if student and cls:
            # 最大3クラスチェック
            current_classes = ClassMember.query.filter_by(user_id=student_id).count()
            if current_classes >= 3:
                flash('生徒は最大3クラスまでしか登録できません。', 'danger')
                return redirect('/school/dashboard')
            
            # 重複チェック
            existing = ClassMember.query.filter_by(
                class_id=class_id, user_id=student_id).first()
            if not existing:
                new_cm = ClassMember(class_id=class_id, user_id=student_id)
                db.session.add(new_cm)
                db.session.commit()
                flash(f'「{student.name}」を「{cls.name}」に登録しました！', 'success')
            else:
                flash('すでに登録されています。', 'warning')
    
    return redirect('/school/dashboard')

@app.route('/api/chats/<int:date_id>', methods=['GET'])
def get_chats(date_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    chats = db_session.query(Chat).filter_by(date_id=date_id).order_by(Chat.created_at).all()
    current_user = User.query.get(user_id)
    result = []
    for chat in chats:
        result.append({
            'id': chat.id,
            'user_id': chat.user_id,
            'user_name': chat.user.name,
            'message': chat.message,
            'created_at': str(chat.created_at),
            'can_delete': (chat.user_id == user_id or user_id == 2)
        })
    return {'chats': result}

@app.route('/api/chats/<int:date_id>', methods=['POST'])
def post_chat(date_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    data = request.get_json()
    message = data.get('message')
    if not message:
        return {'error': 'no message'}, 400
    new_chat = Chat(
        user_id=user_id,
        date_id=date_id,
        message=message,
        created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
    )
    db_session.add(new_chat)
    db_session.commit()
    return {'success': True, 'chat': {
        'id': new_chat.id,
        'user_id': new_chat.user_id,
        'user_name': new_chat.user.name,
        'message': new_chat.message,
        'created_at': str(new_chat.created_at),
        'can_delete': True
    }}

@app.route('/api/chats/delete/<int:chat_id>', methods=['DELETE'])
def delete_chat_api(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    chat = db_session.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        return {'error': 'not found'}, 404
    if chat.user_id != user_id and user_id != 2:
        return {'error': 'forbidden'}, 403
    date_id = chat.date_id
    db_session.delete(chat)
    db_session.commit()
    return {'success': True}

@app.route('/date/<int:id>', methods=['GET', 'POST'])
def date_page(id):
    # 日付（=データ）ごとの詳細ページとチャットの投稿を扱う
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    date_obj = db_session.query(Date).filter_by(id=id).first()
    if not date_obj:
        return redirect('/user')

    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            # Store created_at in JST so that DB entries reflect Japan time
            # and remove microseconds for consistent formatting
            new_chat = Chat(user_id=user_id, date_id=id, message=message,
                            created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0))
            db_session.add(new_chat)
            db_session.commit()
            return redirect(f'/date/{id}')

    chats_query = db_session.query(Chat).filter_by(date_id=id)
    # 管理者（id=2）は非表示コメントも見える
    if user_id != 2:
        chats_query = chats_query.filter(Chat.is_hidden != 1)
    chats = chats_query.order_by(Chat.created_at).all()
    current_user = db_session.query(User).filter_by(id=user_id).first()
    return render_template('date.html', date=date_obj, chats=chats, current_user=current_user)


@app.route('/delete_chat/<int:chat_id>', methods=['POST'])
def delete_chat(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    chat = db_session.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        return redirect('/user')

    # 自分のコメントまたは管理者（ID=2）の場合のみ削除可能
    if chat.user_id != user_id and user_id != 2:
        return redirect(f'/date/{chat.date_id}')

    db_session.delete(chat)
    db_session.commit()
    return redirect(f'/date/{chat.date_id}')


@app.route('/delete_date/<int:date_id>', methods=['POST'])
def delete_date(date_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    date_obj = db_session.query(Date).filter_by(id=date_id).first()
    if not date_obj:
        return redirect('/user')

    # 自分のデータまたは管理者（ID=2）の場合のみ削除可能
    if date_obj.user_id != user_id and user_id != 2:
        return redirect('/user')

    db_session.delete(date_obj)
    db_session.commit()
    return redirect('/user')


# @app.route('/reveal', methods=['GET', 'POST'])
# def reveal():
#     """
#     自分の情報表示・編集ページ: ログイン済みの全ユーザが利用可能。
#     POST で現在のパスワードを受け取り、正しければ自分の id/name/password を表示する。
#     また表示後は現在のパスワードで確認して名前／パスワードの更新が可能。
#     """
#     user_id = session.get('user_id')
#     if not user_id:
#         return redirect('/login')

#     # 対象は「ログイン中のユーザ」本人
#     user = db_session.query(User).filter_by(id=user_id).first()
#     if not user:
#         return redirect('/user')
#     # # 管理者（id=2）は自己情報表示／編集対象から除外する
#     # if user.id == 2:
#     #     message = '管理者の自己情報表示はできません。'
#     #     return render_template('reveal.html', user=user, revealed=None, message=message)
#     # （以前は管理者を自己情報確認・編集から除外していましたが、除外しないように変更しました）

#     message = None
#     revealed = None
#     # Two POST flows:
#     # 1) initial confirmation: form posts 'password' to reveal current info
#     # 2) update submission: form posts with 'update' flag and fields to change
#     if request.method == 'POST':
#         # Update submission
#         if request.form.get('update'):
#             current_pw = request.form.get('current_password')
#             new_name = request.form.get('name')
#             new_pw = request.form.get('new_password')
#             new_pw2 = request.form.get('new_password2')

#             # require current password for security
#             if not current_pw or current_pw != user.password:
#                 message = '現在のパスワードが違います。'
#             else:
#                 if new_pw:
#                     if new_pw != new_pw2:
#                         message = '新しいパスワードが一致しません。'
#                     else:
#                         user.password = new_pw
#                 # update name regardless (if provided)
#                 if new_name:
#                     user.name = new_name
#                 db_session.commit()
#                 revealed = {'id': user.id, 'name': user.name, 'password': user.password}
#                 message = '更新しました。'
#         else:
#             # Confirmation flow: check password to reveal info
#             pw = request.form.get('password')
#             if pw and pw == user.password:
#                 revealed = {'id': user.id, 'name': user.name, 'password': user.password}
#             else:
#                 message = 'パスワードが違います。'
#     return render_template('reveal.html', user=user, revealed=revealed, message=message)


@app.route('/users', methods=['GET', 'POST'])
def users_page():
    """
    全ユーザの一覧表示と検索。アクセスはログイン済みかつ session['user_id']==2 の人のみ許可。
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # 管理者アカウント（id=2）を取得（パスワード認証は管理者のパスワードを使用）
    admin = db_session.query(User).filter_by(id=2).first()
    if not admin:
        return redirect('/user')

    # 現在のログインユーザ情報（トップの確認カードに表示するため）
    current_user = db_session.query(User).filter_by(id=user_id).first()

    # 初期値
    message = None
    revealed = None
    users = []
    users_shown = False

    # 検索クエリは用意するが、ユーザ一覧は password が正しく入力された場合のみ表示する
    search = request.args.get('search', None)
    q = db_session.query(User)
    if search:
        if search.isdigit():
            q = q.filter(or_(User.id == int(search), User.name.like(f"%{search}%")))
        else:
            q = q.filter(User.name.like(f"%{search}%"))

    # POST で受け取ったパスワードが管理者パスワードと一致すれば一覧を表示する
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw and pw == admin.password:
            # mark revealed for this render (do not persist in session)
            # 管理者自身が一覧で自分のパスワード等を確認できないようにする
            if current_user and current_user.id != 2:
                revealed = {'id': current_user.id, 'name': current_user.name, 'password': current_user.password}
            users = q.all()
            users_shown = True
        else:
            message = 'パスワードが違います。'

    return render_template('users.html', users=users, search=search, message=message, revealed=revealed, users_shown=users_shown, user_id=user_id)

@app.route('/school/join', methods=['GET', 'POST'])
def school_join():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    
    # teacher/school_adminのみアクセス可能
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    # すでに学校に参加しているか確認
    existing = SchoolMember.query.filter_by(user_id=user_id).first()
    if existing:
        return redirect('/school/dashboard')
    
    message = None
    if request.method == 'POST':
        code = request.form.get('code')
        school = School.query.filter_by(code=code).first()
        
        if not school:
            message = '学校コードが正しくありません。'
        else:
            # 学校内に最初の参加者かどうか確認
            existing_members = SchoolMember.query.filter_by(school_id=school.id).first()
            
            # 最初の参加者はschool_adminに
            if not existing_members:
                user.role = 'school_admin'
                db.session.commit()
            
            new_member = SchoolMember(school_id=school.id, user_id=user_id)
            db.session.add(new_member)
            db.session.commit()
            flash('学校グループに参加しました！', 'success')
            return redirect('/school/dashboard')
    
    return render_template('school_join.html', message=message)

@app.route('/admin/schools', methods=['GET', 'POST'])
def admin_schools():
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        if school_name:
            # コードを自動生成
            from models import generate_code
            code = generate_code(8)
            # 重複チェック
            while School.query.filter_by(code=code).first():
                code = generate_code(8)
            new_school = School(name=school_name, code=code)
            db.session.add(new_school)
            db.session.commit()
            flash(f'学校「{school_name}」を作成しました！コード: {code}', 'success')
            return redirect('/admin/schools')
    
    schools = School.query.order_by(School.created_at.desc()).all()
    return render_template('admin_schools.html', schools=schools)


@app.route('/admin/schools/delete/<int:school_id>', methods=['POST'])
def admin_delete_school(school_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    school = School.query.get(school_id)
    if school:
        db.session.delete(school)
        db.session.commit()
        flash('学校を削除しました。', 'success')
    return redirect('/admin/schools')

@app.route('/update_verj', methods=['POST'])
def update_verj():
    """
    User ID が 2（管理者）の場合のみバージョン情報を更新可能
    """
    global app_verj
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/login')
    
    verj = request.form.get('verj')
    if verj:
        app_verj = verj
    
    return redirect('/users')


@app.route('/like/<int:id>', methods=['GET','POST'])
def like(id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    existing_like = db_session.query(Like).filter_by(user_id=user_id, date_id=id).first()
    animal = db_session.query(Date).filter_by(id=id).first()
    if existing_like:
        # いいね解除
        db_session.delete(existing_like)
        if animal:
            animal.goodpoint -= 1
    else:
        # いいね追加
        new_like = Like(user_id=user_id, date_id=id)
        db_session.add(new_like)
        if animal:
            animal.goodpoint += 1
    db_session.commit()
    return redirect('/user')


#/loginというエンドポイントでlogin.htmlを表示する
@app.route('/login',methods=["GET",'POST'])
def login():
    if request.method == 'POST':
        id = request.form['id']
        password = request.form['password']
        user = db_session.query(User).filter_by(id=id, password=password).first()
        
        if user:
            session['user_id'] = user.id
            session['is_admin'] = getattr(user, 'is_admin', 0)
            return redirect('/user')
        
        if user and user.password == password:
            if user.role == 'suspended':
                flash('このアカウントは停止されています。管理者にお問い合わせください。', 'danger')
                return render_template('login.html')
            session['user_id'] = user.id
            session['is_admin'] = getattr(user, 'is_admin', 0)
            # 学校ユーザーで未参加の場合は参加ページへ
            if user.role in ['teacher', 'school_admin', 'student']:
                existing = SchoolMember.query.filter_by(user_id=user.id).first()
                if not existing:
                    return redirect('/school/join')
            return redirect('/user')

        else:
            flash('ログインに失敗しました。名前かパスワードが間違っています。', 'danger')
            return render_template('login.html')
        
    return render_template('login.html')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        print(request.form)
        password_s = request.form['password_s']
        password_s2 = request.form['password_s2']

        icon_type = request.form.get('icon_type', 'default')
        icon = 'default.png'
        if icon_type == 'upload':
            file = request.files.get('icon_file')
            if file and file.filename != '':
                result = cloudinary.uploader.upload(file)
                icon = result['secure_url']

        if password_s == password_s2:
            new_user = User(name=name, password=password_s, icon_image=icon)
            db_session.add(new_user)
            db_session.commit()
            return render_template('signup.html',messege='自分のIDは'+str(new_user.id)+'です')
        else:
            return render_template('signup.html',messege='パスワードが一致しません')
            

    return render_template('signup.html')

@app.route('/update_role/<int:target_id>', methods=['POST'])
def update_role(target_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return {'error': 'unauthorized'}, 401
    
    data = request.get_json()
    new_role = data.get('role') if data else request.form.get('role')
    if new_role not in ['normal', 'admin', 'limited', 'suspended', 'teacher', 'school_admin', 'student']:
        return {'error': 'invalid role'}, 400
    
    target_user = User.query.get(target_id)
    if target_user and target_id != 2:
        target_user.role = new_role
        db.session.commit()
        
        # 学校関連のroleの場合、学校に追加
        if new_role in ['teacher', 'school_admin', 'student']:
            school_id = data.get('school_id') if data else None
            if school_id:
                school = School.query.filter_by(code=school_id).first()
                if not school:
                    return {'error': '学校コードが見つかりません。'}, 404
                school = School.query.filter_by(code=school_id).first()
                if not school:
                    return {'error': '学校コードが見つかりません。'}, 404
                existing = SchoolMember.query.filter_by(
                    school_id=school.id, user_id=target_id).first()
                if not existing:
                    new_member = SchoolMember(
                        school_id=school.id, user_id=target_id)
        
        return {'success': True, 'role': new_role}
    return {'error': 'not found'}, 404

@app.route('/admin/schools/<int:school_id>')
def admin_school_detail(school_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    school = School.query.get(school_id)
    if not school:
        return redirect('/admin/schools')
    
    classes = SchoolClass.query.filter_by(school_id=school_id).all()
    members = db.session.query(User).join(SchoolMember,
        SchoolMember.user_id == User.id
    ).filter(SchoolMember.school_id == school_id).all()
    
    students = [m for m in members if m.role == 'student']
    teachers = [m for m in members if m.role in ['teacher', 'school_admin']]
    
    # 学校内の投稿一覧
    school_member_ids = [m.id for m in members]
    dates = Date.query.filter(
        Date.user_id.in_(school_member_ids)
    ).order_by(Date.id.desc()).all()
    
    return render_template('admin_school_detail.html',
                            school=school,
                            classes=classes,
                            students=students,
                            teachers=teachers,
                            dates=dates)


@app.route('/admin/create_school_user', methods=['POST'])
def admin_create_school_user():
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')
    school_id = request.form.get('school_id')
    
    if name and password and role in ['teacher', 'school_admin', 'student']:
        new_user = User(name=name, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        if school_id:
            new_member = SchoolMember(school_id=int(school_id), user_id=new_user.id)
            db.session.add(new_member)
            db.session.commit()
        
        flash(f'「{name}」を登録しました！ID: {new_user.id}', 'success')
    
    return redirect(f'/admin/schools/{school_id}')


@app.route('/admin/delete_school_date/<int:date_id>', methods=['POST'])
def admin_delete_school_date(date_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    date_obj = Date.query.get(date_id)
    school_id = request.form.get('school_id')
    if date_obj:
        db.session.delete(date_obj)
        db.session.commit()
        flash('データを削除しました。', 'success')
    
    return redirect(f'/admin/schools/{school_id}')


@app.route('/admin/toggle_school_date/<int:date_id>', methods=['POST'])
def admin_toggle_school_date(date_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    date_obj = Date.query.get(date_id)
    school_id = request.form.get('school_id')
    if date_obj:
        date_obj.is_hidden = 0 if date_obj.is_hidden == 1 else 1
        db.session.commit()
    
    return redirect(f'/admin/schools/{school_id}')

@app.route('/school/mypage', methods=['GET', 'POST'])
def school_mypage():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['student', 'teacher', 'school_admin']:
        return redirect('/user')
    
    # 学校情報
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    my_school = School.query.get(my_member.school_id) if my_member else None
    
    # 所属クラス
    my_class_members = ClassMember.query.filter_by(user_id=user_id).all()
    my_classes = [SchoolClass.query.get(cm.class_id) for cm in my_class_members if SchoolClass.query.get(cm.class_id)]
    # 教師・school_adminは学校内の全クラスを表示
    if user.role in ['teacher', 'school_admin'] and my_member:
        my_classes = SchoolClass.query.filter_by(school_id=my_member.school_id).all()
    
    message = None
    if request.method == 'POST':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        new_pw2 = request.form.get('new_password2')
        
        if current_pw != user.password:
            message = '現在のパスワードが違います。'
        elif new_pw != new_pw2:
            message = '新しいパスワードが一致しません。'
        elif not new_pw:
            message = '新しいパスワードを入力してください。'
        else:
            user.password = new_pw
            db.session.commit()
            flash('パスワードを変更しました！', 'success')
            return redirect('/school/mypage')
    
    return render_template('school_mypage.html',
                            user=user,
                            my_school=my_school,
                            my_classes=my_classes,
                            message=message)

#アップロードの機能を追加する。(エンドポイント)
@app.route('/upload', methods=['GET', 'POST'])
def upload():

    upload_user_id = session.get('user_id')
    if not upload_user_id:
        return redirect('/login')
    upload_user = User.query.get(upload_user_id)
    if upload_user and upload_user.role == 'limited':
        flash('アップロード権限がありません。', 'danger')
        return redirect('/user')
    if upload_user and upload_user.role == 'suspended':
        return redirect('/user')
    my_school = None
    my_classes = []
    available_assignments = []
    school_use_map = True
    
    if upload_user and upload_user.role in ['teacher', 'school_admin', 'student']:
        my_member = SchoolMember.query.filter_by(user_id=upload_user_id).first()
        if my_member:
            my_school = School.query.get(my_member.school_id)
            school_use_map = my_school.use_map == 1 if my_school else True
            
            if upload_user.role == 'student':
                # 生徒は所属クラスのみ
                class_members = ClassMember.query.filter_by(user_id=upload_user_id).all()
                my_classes = [SchoolClass.query.get(cm.class_id) for cm in class_members]
            else:
                # 教師・school_adminは学校内の全クラス
                my_classes = SchoolClass.query.filter_by(school_id=my_member.school_id).all()
            
            # 利用可能な課題を取得（締め切り前のみ）
            from datetime import datetime as dt
            now = dt.now()
            for cls in my_classes:
                assignments = Assignment.query.filter_by(
                    class_id=cls.id,
                    is_closed=0
                ).filter(Assignment.deadline > now).all()
                available_assignments.extend(assignments)
    #リクエストがpostですか
    if request.method == 'POST':
        file = request.files['file']
        name = request.form['name']
        # place（見つけた場所）をフォームで受け取る
        place = request.form.get('place')
        ido=float(request.form.get('lat', 0)) if request.form.get('lat') else None
        keido=float(request.form.get('lng', 0)) if request.form.get('lng') else None
        # `subject` は公式用の「種類」として扱う（存在しない場合はNone）
        subject = None
        explanatorytext = None
        try:
            if session.get('is_admin') == 1:
                subject = request.form.get('subject')
                explanatorytext = request.form.get('explanatorytext')
        except Exception:
            subject = None
            explanatorytext = None
        knowledge = request.form.get('knowledge')
        if file:
            result = cloudinary.uploader.upload(file)
            image_url = result['secure_url']
            save_date = Date(
                user_id=session.get('user_id'),
                name=name,
                place=place,
                subject=subject,
                explanatorytext=explanatorytext,
                imagepass=image_url,
                goodpoint=0,
                ido=ido,
                keido=keido,
                knowledge=knowledge
            )
            db_session.add(save_date)
            db_session.commit()
            
            if upload_user and upload_user.role in ['teacher', 'student', 'school_admin']:
                my_member = SchoolMember.query.filter_by(user_id=upload_user.id).first()
                if my_member:
                    save_date.school_id = my_member.school_id
                    db_session.commit()
                    
                    if upload_user.role == 'student':
                        # 生徒は自動的に所属クラス全部に送信
                        pass
                    else:
                        # 教師・school_adminは送信先を選択
                        pass
                    
                    # 課題への送信
                    assignment_id = request.form.get('assignment_id')
                    if assignment_id:
                        new_submission = AssignmentSubmission(
                            assignment_id=int(assignment_id),
                            date_id=save_date.id,
                            user_id=upload_user.id,
                            submitted_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
                        )
                        db_session.add(new_submission)
                        db_session.commit()
            
            return render_template('upload.html', 
                                    upload=file.filename,
                                    my_school=my_school,
                                    my_classes=my_classes,
                                    available_assignments=available_assignments,
                                    school_use_map=school_use_map)
        # ↑↑↑ここまで↑↑↑
    
    return render_template('upload.html',
                            my_school=my_school,
                            my_classes=my_classes,
                            available_assignments=available_assignments,
                            school_use_map=school_use_map)
    
    # fileを受け取る
    return render_template('upload.html')


@app.route('/friend_search', methods=['GET', 'POST'])
def friend_search():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    search_user = User.query.get(user_id)
    if not search_user:
        return redirect('/login')
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        if nickname:
            if search_user.role in ['teacher', 'student', 'school_admin']:
                my_member = SchoolMember.query.filter_by(user_id=user_id).first()
                if my_member:
                    school_member_ids = [m.user_id for m in SchoolMember.query.filter_by(school_id=my_member.school_id).all()]
                    users = db_session.query(User).filter(
                        User.name.like(f'%{nickname}%'),
                        User.id.in_(school_member_ids)
                    ).all()
                else:
                    users = []
            else:
                school_user_ids = [m.user_id for m in SchoolMember.query.all()]
                users = db_session.query(User).filter(
                    User.name.like(f'%{nickname}%'),
                    User.id.notin_(school_user_ids)
                ).all()
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        if nickname:
            if search_user.role in ['teacher', 'student', 'school_admin']:
                my_member = SchoolMember.query.filter_by(user_id=user_id).first()
                if my_member:
                    school_member_ids = [m.user_id for m in SchoolMember.query.filter_by(school_id=my_member.school_id).all()]
                    users = db_session.query(User).filter(
                        User.name.like(f'%{nickname}%'),
                        User.id.in_(school_member_ids)
                    ).all()
                else:
                    users = []
            else:
                # 通常ユーザーは学校ユーザーを除外
                school_user_ids = [m.user_id for m in SchoolMember.query.all()]
                users = db_session.query(User).filter(
                    User.name.like(f'%{nickname}%'),
                    User.id.notin_(school_user_ids)
                ).all()
            # 各ユーザーとの関係を取得
            friendships = db_session.query(Friend).filter(
                (Friend.user_id == user_id) | (Friend.friend_id == user_id)
            ).all()
            
            # 各ユーザーの関係ステータスを計算
            user_relations = {}
            for user in users:
                relation = {'status': 'none', 'is_requester': False}
                for f in friendships:
                    if (f.user_id == user.id and f.friend_id == user_id) or (f.friend_id == user.id and f.user_id == user_id):
                        relation['status'] = f.status
                        if f.user_id == user_id:
                            relation['is_requester'] = True
                        break
                user_relations[user.id] = relation
            
            return render_template('friend_search.html', users=users, search=nickname, user_relations=user_relations, current_user_id=user_id)
    
    return render_template('friend_search.html')

@app.route('/api/friend/request/<int:friend_id>', methods=['POST'])
def api_request_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    if user_id == friend_id:
        return {'error': 'cannot add yourself'}, 400
    api_user = User.query.get(user_id)
    target_user = User.query.get(friend_id)
    if not api_user or not target_user:
        return {'error': 'user not found'}, 404
    current_is_school = api_user.role in ['teacher', 'student', 'school_admin']
    target_is_school = target_user.role in ['teacher', 'student', 'school_admin']
    if current_is_school != target_is_school:
        return {'error': '学校アカウントと通常アカウントはフレンドになれません。'}, 400
    if current_is_school and target_is_school:
        current_school = SchoolMember.query.filter_by(user_id=user_id).first()
        target_school = SchoolMember.query.filter_by(user_id=friend_id).first()
        if not current_school or not target_school or current_school.school_id != target_school.school_id:
            return {'error': '同じ学校内のユーザーとのみフレンドになれます。'}, 400
    existing = db_session.query(Friend).filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
    ).first()
    if not existing:
        new_request = Friend(user_id=user_id, friend_id=friend_id, status='pending')
        db_session.add(new_request)
        db_session.commit()
    return {'success': True, 'status': 'pending'}

@app.route('/api/friend/cancel/<int:friend_id>', methods=['POST'])
def api_cancel_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    request_record = db_session.query(Friend).filter(
        Friend.user_id == user_id,
        Friend.friend_id == friend_id,
        Friend.status == 'pending'
    ).first()
    if request_record:
        db_session.delete(request_record)
        db_session.commit()
    return {'success': True, 'status': 'none'}

@app.route('/api/friend/accept/<int:requester_id>', methods=['POST'])
def api_accept_friend(requester_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    request_record = db_session.query(Friend).filter(
        Friend.user_id == requester_id,
        Friend.friend_id == user_id,
        Friend.status == 'pending'
    ).first()
    if request_record:
        request_record.status = 'accepted'
        db_session.commit()
    return {'success': True, 'status': 'accepted'}

@app.route('/api/friend/reject/<int:requester_id>', methods=['POST'])
def api_reject_friend(requester_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    request_record = db_session.query(Friend).filter(
        Friend.user_id == requester_id,
        Friend.friend_id == user_id,
        Friend.status == 'pending'
    ).first()
    if request_record:
        db_session.delete(request_record)
        db_session.commit()
    return {'success': True}

@app.route('/api/friend/remove/<int:friend_id>', methods=['POST'])
def api_remove_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    existing = db_session.query(Friend).filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
    ).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()
    return {'success': True}

@app.route('/request_friend/<int:friend_id>', methods=['POST'])
def request_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    req_user = User.query.get(user_id)
    target_user = User.query.get(friend_id)
    if not req_user or not target_user:
        return redirect('/friend_search')
    
    current_is_school = req_user.role in ['teacher', 'student', 'school_admin']
    target_is_school = target_user.role in ['teacher', 'student', 'school_admin']
    
    if current_is_school != target_is_school:
        flash('学校アカウントと通常アカウントはフレンドになれません。', 'danger')
        return redirect('/friend_search')
    
    # 学校ユーザーは同じ学校内のみ
    if current_is_school and target_is_school:
        current_school = SchoolMember.query.filter_by(user_id=user_id).first()
        target_school = SchoolMember.query.filter_by(user_id=friend_id).first()
        if not current_school or not target_school or current_school.school_id != target_school.school_id:
            flash('同じ学校内のユーザーとのみフレンドになれます。', 'danger')
            return redirect('/friend_search')
    
    # 自分自身をフレンドに申請しない
    if user_id == friend_id:
        return redirect('/friend_search')
    
    # すでに申請済みかフレンドかチェック
    existing = db_session.query(Friend).filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
    ).first()
    
    if not existing:
        new_request = Friend(user_id=user_id, friend_id=friend_id, status='pending')
        db_session.add(new_request)
        db_session.commit()
    
    return redirect('/friend_search')


@app.route('/accept_friend/<int:requester_id>', methods=['POST'])
def accept_friend(requester_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # 申請を承認
    request_record = db_session.query(Friend).filter(
        Friend.user_id == requester_id,
        Friend.friend_id == user_id,
        Friend.status == 'pending'
    ).first()
    
    if request_record:
        request_record.status = 'accepted'
        db_session.commit()
    
    return redirect('/friends')


@app.route('/cancel_friend_request/<int:friend_id>', methods=['POST'])
def cancel_friend_request(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # 自分の申請をキャンセル
    request_record = db_session.query(Friend).filter(
        Friend.user_id == user_id,
        Friend.friend_id == friend_id,
        Friend.status == 'pending'
    ).first()
    
    if request_record:
        db_session.delete(request_record)
        db_session.commit()
    
    return redirect('/friend_search')


@app.route('/friends')
def friends():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # フレンドを取得（acceptedのみ）
    friends_list = db_session.query(User).join(Friend, 
        ((Friend.user_id == user_id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
        ((Friend.friend_id == user_id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
    ).all()
    
    # 承認待ちの申請を取得
    pending_requests = db_session.query(User).join(Friend,
        (Friend.user_id == User.id) & (Friend.friend_id == user_id) & (Friend.status == 'pending')
    ).all()
    
    return render_template('friends.html', friends=friends_list, pending_requests=pending_requests)


@app.route('/remove_friend/<int:friend_id>', methods=['POST'])
def remove_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # フレンド関係を削除
    existing = db_session.query(Friend).filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
    ).first()
    
    if existing:
        db_session.delete(existing)
        db_session.commit()
    
    return redirect('/friends')


@app.route('/friend_data/<int:friend_id>')
def friend_data(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    # フレンドかチェック
    is_friend = db_session.query(Friend).filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
    ).first()
    
    if not is_friend:
        return redirect('/friends')
    
    # フレンドのデータを取得
    friend = db_session.query(User).get(friend_id)
    dates = db_session.query(Date).filter_by(user_id=friend_id).all()
    
    return render_template('friend_data.html', friend=friend, dates=dates)

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    # 1. 表示するユーザーの情報を取得
    target_user = User.query.get(user_id)
    if not target_user:
        return "ユーザーが見つかりません", 404

    # ログインしている自分のIDを取得
    login_id = session.get('user_id')
    # 本人かどうかの判定（これが無いと編集ボタンが出ません！）
    is_me = (login_id == user_id)

    # 2. 画像の保存ボタンが押された時の処理
    # 2. 保存ボタン（POST）が押された時の処理
    # 2. 保存ボタン（POST）が押された時の処理
    if request.method == 'POST':
        if is_me: # 本人だけが変更できる
            
            # --- ★追加：パスワードのセキュリティチェック ---
            current_pw = request.form.get('current_password')
            new_pw = request.form.get('new_password')

            # パスワード欄に何か入力されている場合
            if current_pw or new_pw:
                # 現在のパスワードが合っているか確認
                if target_user.password == current_pw:
                    if new_pw: # 新しいパスワードがあれば上書き
                        target_user.password = new_pw
                        flash('パスワードも新しく更新しました！', 'success')
                else:
                    # パスワードが間違っている場合は、名前や画像の保存もキャンセルして弾く！
                    flash('現在のパスワードが間違っています。変更はキャンセルされました。', 'danger')
                    return redirect(f'/profile/{user_id}')

            # --- 名前の処理 ---
            new_name = request.form.get('user_name')
            if new_name:
                target_user.name = new_name

            # --- 画像の処理 ---
            file = request.files.get('icon_file')
            if file and file.filename != '':
                result = cloudinary.uploader.upload(file)
                target_user.icon_image = result['secure_url']
                
            # 問題がなければ全部まとめてデータベースに保存！
            db.session.commit()
            
            # パスワード変更がなかった場合のメッセージ
            if not (current_pw or new_pw):
                flash('プロフィールを更新しました！', 'success')
            
        return redirect(f'/profile/{user_id}')

    # 3. ユーザーの投稿一覧を取得
    user_dates = Date.query.filter_by(user_id=user_id, is_hidden=0).order_by(Date.id.desc()).all()
    
    # 4. フレンドかどうかの判定（元の機能の復活！）
    is_friend = False
    is_pending = False
    is_requester = False
    if login_id:
        friend_relation = db_session.query(Friend).filter(
            ((Friend.user_id == login_id) & (Friend.friend_id == user_id)) |
            ((Friend.user_id == user_id) & (Friend.friend_id == login_id))
        ).first()
        if friend_relation:
            if friend_relation.status == 'accepted':
                is_friend = True
            elif friend_relation.status == 'pending':
                is_pending = True
                is_requester = (friend_relation.user_id == login_id)

    return render_template('profile.html', target_user=target_user, dates=user_dates, is_me=is_me, is_friend=is_friend, is_pending=is_pending, is_requester=is_requester)

    # # ★ ここがエラーの原因でした！ target_user=target_user に直しています！
    # return render_template('profile.html', target_user=target_user, dates=user_dates, is_me=is_me, is_friend=is_friend)

@app.route('/toggle_hide/<int:post_id>')
def toggle_hide(post_id):
    login_id = session.get('user_id')
    if not login_id:
        return redirect('/login')

    post = Date.query.get(post_id)

    # 【修正ポイント】「自分の投稿」か「IDが2番（管理者）」ならOK
    if post and (post.user_id == login_id or login_id == 2):
        if post.is_hidden == 1:
            post.is_hidden = 0
        else:
            post.is_hidden = 1
        db.session.commit()

    # もし管理者なら、トップページや詳細ページから操作することもあるので
    # 直前のページに戻るようにすると便利です
    return redirect(request.referrer or '/user')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            new_feedback = Feedback(
                user_id=user_id,
                message=message,
                created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
            )
            db.session.add(new_feedback)
            db.session.commit()
            flash('フィードバックを送信しました！', 'success')
            return redirect('/feedback')
    
    # 自分のフィードバック一覧
    my_feedbacks = Feedback.query.filter_by(user_id=user_id).order_by(Feedback.created_at.desc()).all()
    return render_template('feedback.html', feedbacks=my_feedbacks)


@app.route('/feedback/admin', methods=['GET', 'POST'])
def feedback_admin():
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return redirect('/user')
    
    if request.method == 'POST':
        feedback_id = request.form.get('feedback_id')
        reply = request.form.get('reply')
        fb = Feedback.query.get(feedback_id)
        if fb and reply:
            fb.reply = reply
            fb.is_read = 1
            fb.replied_at = datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
            db.session.commit()
        return redirect('/feedback/admin')
    
    # 未読を先に表示
    feedbacks = Feedback.query.order_by(Feedback.is_read.asc(), Feedback.created_at.desc()).all()
    # 未読数を取得
    unread_count = Feedback.query.filter_by(is_read=0).count()
    return render_template('feedback_admin.html', feedbacks=feedbacks, unread_count=unread_count)


@app.route('/feedback/read/<int:feedback_id>', methods=['POST'])
def feedback_read(feedback_id):
    user_id = session.get('user_id')
    if not user_id or user_id != 2:
        return {'error': 'unauthorized'}, 401
    fb = Feedback.query.get(feedback_id)
    if fb:
        fb.is_read = 1
        db.session.commit()
    return {'success': True}

@app.route('/toggle_chat_hide/<int:chat_id>')
def toggle_chat_hide(chat_id):
    login_id = session.get('user_id')
    
    # 管理者フラグを使ってコメントを隠せるルールにする
    if session.get('is_admin') != 1:
        return "管理者権限が必要です", 403

    chat = Chat.query.get(chat_id)
    if chat:
        chat.is_hidden = 1 if chat.is_hidden == 0 else 0
        db.session.commit()

    return redirect(request.referrer or '/user')

@app.route('/account', methods=['GET', 'POST'])
def account():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    user = User.query.get(user_id)

    if request.method == 'POST':
        # 名前の更新
        user.name = request.form.get('name')
        
        # 🚩 画像アップロードの処理
        file = request.files.get('icon_file')
        if file and file.filename != '':
            result = cloudinary.uploader.upload(file)
            user.icon_image = result['secure_url']
        if file and file.filename != '':
            # ファイル名を安全なものにして保存
            filename = secure_filename(f"user_{user.id}_{file.filename}")
            # 保存先のパス（フォルダがない場合は作っておいてね！）
            file_path = os.path.join(app.root_path, 'static', 'icons', filename)
            file.save(file_path)
            
            # データベースにファイル名を記録
            user.icon_image = filename

        db.session.commit()
        return redirect(f'/profile/{user.id}')

    return render_template('account.html', user=user)

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect('/user')
    return redirect('/login')

# ↓↓↓ここから↓↓↓
@app.route('/check_role')
def check_role():
    user_id = session.get('user_id')
    if not user_id:
        return 'ログインしていません'
    user = db_session.query(User).filter_by(id=user_id).first()
    return f'user_id={user.id}, name={user.name}, role={user.role}'
# ↑↑↑ここまで↑↑↑

@app.route('/assignments', methods=['GET'])
def assignment_list():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin', 'student']:
        return redirect('/user')
    user = User.query.get(user_id)
    if not user:
        return redirect('/login')
    if user.role not in ['teacher', 'school_admin', 'student']:
        return redirect('/user')
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    if not my_member:
        return redirect('/school/join')
    
    school = School.query.get(my_member.school_id)
    
    # 自分が見られる課題を取得
    from datetime import datetime as dt
    now = dt.now()
    
    if user.role == 'student':
        # 生徒は所属クラスの課題のみ
        class_members = ClassMember.query.filter_by(user_id=user_id).all()
        class_ids = [cm.class_id for cm in class_members]
        assignments = Assignment.query.filter(
            Assignment.class_id.in_(class_ids)
        ).order_by(Assignment.deadline.asc()).all()
    else:
        # 教師・school_adminは学校内の全課題
        class_ids = [cls.id for cls in SchoolClass.query.filter_by(school_id=my_member.school_id).all()]
        assignments = Assignment.query.filter(
            Assignment.class_id.in_(class_ids)
        ).order_by(Assignment.deadline.asc()).all()
    
    # 担任のクラスを取得（課題作成用）
    if user.role == 'teacher':
        my_teaching = ClassTeacher.query.filter_by(teacher_id=user_id).first()
        can_create_classes = [my_teaching.school_class] if my_teaching else []
    elif user.role == 'school_admin':
        can_create_classes = SchoolClass.query.filter_by(school_id=my_member.school_id).all()
    else:
        can_create_classes = []
    
    return render_template('assignment_list.html',
                            user=user,
                            school=school,
                            assignments=assignments,
                            can_create_classes=can_create_classes,
                            now=now)


@app.route('/assignments/create', methods=['POST'])
def create_assignment():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin']:
        return redirect('/user')
    
    title = request.form.get('title')
    description = request.form.get('description')
    class_id = request.form.get('class_id')
    deadline_str = request.form.get('deadline')
    
    if title and class_id and deadline_str:
        from datetime import datetime as dt
        deadline = dt.strptime(deadline_str, '%Y-%m-%dT%H:%M').replace(tzinfo=ZoneInfo("Asia/Tokyo"))
        
        # 教師は自分の担任クラスのみ
        if user.role == 'teacher':
            my_teaching = ClassTeacher.query.filter_by(
                teacher_id=user_id, class_id=int(class_id)).first()
            if not my_teaching:
                flash('担任のクラスにのみ課題を出せます。', 'danger')
                return redirect('/assignments')
        
        new_assignment = Assignment(
            title=title,
            description=description,
            class_id=int(class_id),
            created_by=user_id,
            deadline=deadline
        )
        db.session.add(new_assignment)
        db.session.commit()
        flash(f'課題「{title}」を作成しました！', 'success')
    
    return redirect('/assignments')


@app.route('/assignments/<int:assignment_id>/close', methods=['POST'])
def close_assignment(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    assignment = Assignment.query.get(assignment_id)
    
    if not assignment:
        return redirect('/assignments')
    
    # 担任またはschool_adminのみ
    cls = SchoolClass.query.get(assignment.class_id)
    my_teaching = ClassTeacher.query.filter_by(
        class_id=assignment.class_id, teacher_id=user_id).first()
    
    if user.role == 'school_admin' or my_teaching:
        assignment.is_closed = 1
        db.session.commit()
        flash('課題を締め切りました。', 'success')
    
    return redirect(f'/assignments/{assignment_id}')


@app.route('/assignments/<int:assignment_id>/extend', methods=['POST'])
def extend_assignment(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    assignment = Assignment.query.get(assignment_id)
    
    if not assignment:
        return redirect('/assignments')
    
    my_teaching = ClassTeacher.query.filter_by(
        class_id=assignment.class_id, teacher_id=user_id).first()
    
    if user.role == 'school_admin' or my_teaching:
        deadline_str = request.form.get('deadline')
        if deadline_str:
            from datetime import datetime as dt
            new_deadline = dt.strptime(deadline_str, '%Y-%m-%dT%H:%M').replace(tzinfo=ZoneInfo("Asia/Tokyo"))
            assignment.deadline = new_deadline
            assignment.is_closed = 0
            db.session.commit()
            flash('締め切りを延長しました。', 'success')
    
    return redirect(f'/assignments/{assignment_id}')

@app.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
def assignment_detail(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    user = User.query.get(user_id)
    if user.role not in ['teacher', 'school_admin', 'student']:
        return redirect('/user')
    
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return redirect('/assignments')
    
    from datetime import datetime as dt
    now = dt.now()
    deadline = assignment.deadline.replace(tzinfo=None) if assignment.deadline.tzinfo else assignment.deadline
    is_passed = deadline < now
    is_closed = assignment.is_closed == 1
    can_submit = not is_passed and not is_closed
    
    # 担任チェック
    my_teaching = ClassTeacher.query.filter_by(
        class_id=assignment.class_id, teacher_id=user_id).first()
    can_manage = user.role == 'school_admin' or my_teaching is not None
    
    my_member = SchoolMember.query.filter_by(user_id=user_id).first()
    school = School.query.get(my_member.school_id) if my_member else None
    
    # 提出一覧
    submissions = AssignmentSubmission.query.filter_by(
        assignment_id=assignment_id
    ).order_by(AssignmentSubmission.submitted_at.desc()).all()
    
    # チャット一覧
    chats = AssignmentChat.query.filter_by(
        assignment_id=assignment_id
    ).order_by(AssignmentChat.created_at.asc()).all()
    
    return render_template('assignment_detail.html',
                           user=user,
                           school=school,
                           assignment=assignment,
                           submissions=submissions,
                           chats=chats,
                           can_submit=can_submit,
                           can_manage=can_manage,
                           is_passed=is_passed,
                           is_closed=is_closed,
                           now=now)


@app.route('/api/assignments/<int:assignment_id>/chats', methods=['GET'])
def get_assignment_chats(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    
    chats = AssignmentChat.query.filter_by(
        assignment_id=assignment_id
    ).order_by(AssignmentChat.created_at.asc()).all()
    
    result = []
    for chat in chats:
        replies = []
        for reply in chat.replies:
            replies.append({
                'id': reply.id,
                'user_name': reply.user.name,
                'reply': reply.reply,
                'created_at': str(reply.created_at)
            })
        result.append({
            'id': chat.id,
            'user_id': chat.user_id,
            'user_name': chat.user.name,
            'message': chat.message,
            'created_at': str(chat.created_at),
            'replies': replies,
            'can_delete': (chat.user_id == user_id or user_id == 2)
        })
    return {'chats': result}


@app.route('/api/assignments/<int:assignment_id>/chats', methods=['POST'])
def post_assignment_chat(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    
    data = request.get_json()
    message = data.get('message')
    if not message:
        return {'error': 'no message'}, 400
    
    new_chat = AssignmentChat(
        assignment_id=assignment_id,
        user_id=user_id,
        message=message,
        created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
    )
    db.session.add(new_chat)
    db.session.commit()
    
    return {'success': True, 'chat': {
        'id': new_chat.id,
        'user_id': new_chat.user_id,
        'user_name': new_chat.user.name,
        'message': new_chat.message,
        'created_at': str(new_chat.created_at),
        'replies': [],
        'can_delete': True
    }}


@app.route('/api/assignments/chats/<int:chat_id>/reply', methods=['POST'])
def post_assignment_chat_reply(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    
    data = request.get_json()
    reply_text = data.get('reply')
    if not reply_text:
        return {'error': 'no reply'}, 400
    
    chat = AssignmentChat.query.get(chat_id)
    if not chat:
        return {'error': 'not found'}, 404
    
    new_reply = AssignmentChatReply(
        chat_id=chat_id,
        user_id=user_id,
        reply=reply_text,
        created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0)
    )
    db.session.add(new_reply)
    db.session.commit()
    
    return {'success': True, 'reply': {
        'id': new_reply.id,
        'user_name': new_reply.user.name,
        'reply': new_reply.reply,
        'created_at': str(new_reply.created_at)
    }}


@app.route('/api/assignments/chats/<int:chat_id>/delete', methods=['DELETE'])
def delete_assignment_chat(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    
    chat = AssignmentChat.query.get(chat_id)
    if not chat:
        return {'error': 'not found'}, 404
    
    if chat.user_id != user_id and user_id != 2:
        return {'error': 'forbidden'}, 403
    
    db.session.delete(chat)
    db.session.commit()
    return {'success': True}


@app.route('/api/assignments/<int:assignment_id>/submissions', methods=['GET'])
def get_assignment_submissions(assignment_id):
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'unauthorized'}, 401
    
    submissions = AssignmentSubmission.query.filter_by(
        assignment_id=assignment_id
    ).order_by(AssignmentSubmission.submitted_at.desc()).all()
    
    result = []
    for sub in submissions:
        result.append({
            'id': sub.id,
            'user_name': sub.user.name,
            'date_id': sub.date_id,
            'date_name': sub.date.name,
            'date_image': sub.date.imagepass,
            'submitted_at': str(sub.submitted_at)
        })
    return {'submissions': result}

if __name__ == '__main__':

    app.run(debug=True)