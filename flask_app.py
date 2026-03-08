from flask import Flask, render_template, request, redirect, session
from models import User, db, Date, Like, Chat, Friend
from sqlalchemy import or_
from datetime import datetime
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)
app.secret_key='secret_key'
app.config.from_object('config')

# グローバル変数でバージョン情報を管理
app_verj = None

db.init_app(app)
db_session = db.session

with app.app_context():
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
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
            # 特定のフレンドのデータを表示
            date = date.filter(Date.user_id == int(Illustrated_friend))
        dates = date.all()

        # 各dateに対して、現在のユーザーがいいね済みかをチェック
        for d in dates:
            d.is_liked = db_session.query(Like).filter_by(user_id=user_id, date_id=d.id).first() is not None

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

    chats = db_session.query(Chat).filter_by(date_id=id).order_by(Chat.created_at).all()
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


@app.route('/reveal', methods=['GET', 'POST'])
def reveal():
    """
    自分の情報表示・編集ページ: ログイン済みの全ユーザが利用可能。
    POST で現在のパスワードを受け取り、正しければ自分の id/name/password を表示する。
    また表示後は現在のパスワードで確認して名前／パスワードの更新が可能。
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # 対象は「ログイン中のユーザ」本人
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user:
        return redirect('/user')
    # # 管理者（id=2）は自己情報表示／編集対象から除外する
    # if user.id == 2:
    #     message = '管理者の自己情報表示はできません。'
    #     return render_template('reveal.html', user=user, revealed=None, message=message)
    # （以前は管理者を自己情報確認・編集から除外していましたが、除外しないように変更しました）

    message = None
    revealed = None
    # Two POST flows:
    # 1) initial confirmation: form posts 'password' to reveal current info
    # 2) update submission: form posts with 'update' flag and fields to change
    if request.method == 'POST':
        # Update submission
        if request.form.get('update'):
            current_pw = request.form.get('current_password')
            new_name = request.form.get('name')
            new_pw = request.form.get('new_password')
            new_pw2 = request.form.get('new_password2')

            # require current password for security
            if not current_pw or current_pw != user.password:
                message = '現在のパスワードが違います。'
            else:
                if new_pw:
                    if new_pw != new_pw2:
                        message = '新しいパスワードが一致しません。'
                    else:
                        user.password = new_pw
                # update name regardless (if provided)
                if new_name:
                    user.name = new_name
                db_session.commit()
                revealed = {'id': user.id, 'name': user.name, 'password': user.password}
                message = '更新しました。'
        else:
            # Confirmation flow: check password to reveal info
            pw = request.form.get('password')
            if pw and pw == user.password:
                revealed = {'id': user.id, 'name': user.name, 'password': user.password}
            else:
                message = 'パスワードが違います。'
    return render_template('reveal.html', user=user, revealed=revealed, message=message)


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
    animal = db_session.query(Date).get(id)
    if existing_like:
        # いいね解除
        db_session.delete(existing_like)
        if animal:
            animal.goodpoint -= 1
    else:
        # いいね追加
        new_like = Like(user_id=user_id, date_id=id)
        db.session.add(new_like)
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
        user = User.query.filter_by(id=id, password=password).first()
        
        if user:
            session['user_id'] = user.id
            return redirect('/user')

        
    return render_template('login.html')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        print(request.form)
        password_s = request.form['password_s']
        password_s2 = request.form['password_s2']
        if password_s == password_s2:
            new_user = User(name=name, password=password_s)
            db.session.add(new_user)
            db.session.commit()
            return render_template('signup.html',messege='自分のIDは'+str(new_user.id)+'です')
        else:
            return render_template('signup.html',messege='パスワードが一致しません')
            

    return render_template('signup.html')


#アップロードの機能を追加する。(エンドポイント)
@app.route('/upload', methods=['GET', 'POST'])
def upload():
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
            if session.get('user_id') == 2:
                subject = request.form.get('subject')
                explanatorytext = request.form.get('explanatorytext')
        except Exception:
            subject = None
            explanatorytext = None
        if file:
            save_date = Date(
                user_id=session.get('user_id'),
                name=name,
                place=place,
                subject=subject,
                explanatorytext=explanatorytext,
                imagepass=file.filename,
                goodpoint=0,
                ido=ido,
                keido=keido
            )
            db.session.add(save_date)
            db.session.commit()
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, file.filename))
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


if __name__ == '__main__':

    app.run(debug=True)