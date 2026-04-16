from flask import Flask, render_template, request, redirect, session, flash
from models import User, db, Date, Like, Chat, Friend
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

os.makedirs('instance', exist_ok=True)

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
def utility_now():
    # Provide a `now()` function to Jinja templates (e.g. now().year)
    # Return current time in Japan Standard Time (UTC+9)
    # Return a datetime in JST with microseconds cleared so templates
    # display times like "2025-10-26 11:44:39" (no microseconds)
    return dict(now=lambda: datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0))


@app.context_processor
def inject_verj():
    # Provide a global `verj` variable to all templates.
    # If app_verj is set, use that; otherwise use config.py's VERJ setting
    global app_verj
    if app_verj:
        return dict(verj=app_verj)
    return dict(verj=app.config.get('VERJ', 'ver.1.0'))

@app.route('/user')
def user_page():
    # show user page only when logged in
    user_id = session.get('user_id')
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
        dates = date.order_by(Date.id.desc()).all()

        # 各dateに対して、現在のユーザーがいいね済みかをチェック
        for d in dates:
            d.is_liked = db_session.query(Like).filter_by(user_id=user_id, date_id=d.id).first() is not None
            d.chat_count = db_session.query(Chat).filter_by(date_id=d.id).count()

        # フレンドリストを取得
        friends = db_session.query(User).join(Friend, 
            ((Friend.user_id == user_id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
            ((Friend.friend_id == user_id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
        ).all()

        return render_template('user.html', user=user,dates=dates, filter_ev=Illustrated_ev, filter_ki=Illustrated_ki, filter_friend=Illustrated_friend, friends=friends)
    return redirect('/login')


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
        return redirect('/login')
    
    new_role = request.form.get('role')
    if new_role not in ['normal', 'admin', 'limited', 'suspended']:
        return redirect('/users')
    
    target_user = User.query.get(target_id)
    if target_user and target_id != 2:
        target_user.role = new_role
        db.session.commit()
    
    return redirect('/users')

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
                    keido=keido
                )
            db_session.add(save_date)
            db_session.commit()
            return render_template('upload.html', upload=file.filename)
    
    # fileを受け取る
    return render_template('upload.html')


@app.route('/friend_search', methods=['GET', 'POST'])
def friend_search():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        if nickname:
            users = db_session.query(User).filter(User.name.like(f'%{nickname}%')).all()
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


@app.route('/request_friend/<int:friend_id>', methods=['POST'])
def request_friend(friend_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
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

if __name__ == '__main__':

    app.run(debug=True)