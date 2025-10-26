from flask import Flask, render_template, request, redirect, session
from models import User, db, Date, Like, Chat
from sqlalchemy import or_
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key='secret_key'
app.config.from_object('config')

db.init_app(app)
db_session = db.session


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
    # If a `VERJ` setting exists in config.py, prefer that; otherwise use the default text.
    return dict(verj=app.config.get('VERJ', 'ver.1.0'))

@app.route('/user')
def user_page():
    # user_id = session.get('user_id')
    # if not user_id:
    #     return redirect('/login')
    if session['user_id']:
        search = request.args.get("search",None)
        Illustrated_ev = request.args.get("ev",None)
        Illustrated_ki = request.args.get("ki",None)
        user_id = session['user_id']
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
        date = date.all()

        return render_template('user.html', user=user,dates=date, filter_ev=Illustrated_ev, filter_ki=Illustrated_ki)
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


@app.route('/reveal', methods=['GET', 'POST'])
def reveal():
    """
    管理者用のページ: セッション中の user_id が 2 の場合のみアクセス可能。
    POST でパスワードを受け取り、ユーザ id=2 のパスワードと一致すれば id/name/password を表示する。
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    # この機能は user_id == 2 の人のみ利用可能
    if user_id != 2:
        return redirect('/user')

    admin = db_session.query(User).filter_by(id=2).first()
    if not admin:
        return redirect('/user')

    message = None
    revealed = None
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw and pw == admin.password:
            revealed = {'id': admin.id, 'name': admin.name, 'password': admin.password}
        else:
            message = 'パスワードが違います。'

    return render_template('reveal.html', admin=admin, revealed=revealed, message=message)


@app.route('/users', methods=['GET', 'POST'])
def users_page():
    """
    全ユーザの一覧表示と検索。アクセスはログイン済みかつ session['user_id']==2 の人のみ許可。
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # user_id が 2 の場合のみ許可
    if user_id != 2:
        return redirect('/user')
    # 管理者アカウント（id=2）を取得
    admin = db_session.query(User).filter_by(id=2).first()
    if not admin:
        return redirect('/user')

    # まだ認証していないならパスワードフォームを表示/検証
    if not session.get('users_authed'):
        message = None
        if request.method == 'POST':
            pw = request.form.get('password')
            if pw and pw == admin.password:
                session['users_authed'] = True
                return redirect('/users')
            else:
                message = 'パスワードが違います。'
        return render_template('users_auth.html', message=message)

    # 認証済み: 検索と一覧表示
    search = request.args.get('search', None)
    q = db_session.query(User)
    if search:
        if search.isdigit():
            q = q.filter(or_(User.id == int(search), User.name.like(f"%{search}%")))
        else:
            q = q.filter(User.name.like(f"%{search}%"))

    users = q.all()
    return render_template('users.html', users=users, search=search)

@app.route('/like/<int:id>', methods=['GET','POST'])
def like(id):
    existing_like = db_session.query(Like).filter_by(user_id=session['user_id'], date_id=id).first()
    if existing_like:
        return redirect('/user')
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    new_like = Like(user_id=user_id, date_id=id)
    db.session.add(new_like)
    animal = db_session.query(Date).get(id)
    if animal:
        animal.goodpoint += 1
        db_session.commit()
    # #     return ({'success': True, 'goodpoint': animal.goodpoint})
    # # return ({'success': False}), 404
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
                user_id=session['user_id'],
                name=name,
                place=place,
                subject=subject,
                explanatorytext=explanatorytext,
                imagepass=file.filename,
                goodpoint=0,
            )
            db.session.add(save_date)
            db.session.commit()
            file.save(f'static/uploads/{file.filename}')
            return render_template('upload.html', upload=file.filename)
    
    # fileを受け取る
    return render_template('upload.html')


if __name__ == '__main__':

    app.run(debug=True)