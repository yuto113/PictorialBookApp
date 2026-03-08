import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from models import User, db, Date, Like, Chat, Friend
from sqlalchemy import or_, create_engine
from sqlalchemy.orm import sessionmaker
import config
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import shutil
from header import Header
from footer import Footer

# データベース設定
engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
db_session = Session()

# グローバル変数でバージョン情報を管理
app_verj = "ver.1.0"

# データベース初期化
db_path = config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
if not os.path.exists(db_path):
    db.metadata.create_all(engine)

class Header:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg="white", relief="raised", bd=2)
        self.update_header()

    def update_header(self):
        # 既存のウィジェットを削除
        for widget in self.frame.winfo_children():
            widget.destroy()
        tk.Label(self.frame, text="図鑑", font=("Arial", 18, "bold"), fg="#ff6b6b", bg="white").pack(side=tk.LEFT, padx=10)
        tk.Label(self.frame, text="オンライン図鑑", font=("Arial", 12), fg="gray", bg="white").pack(side=tk.LEFT)
        if self.app.current_user:
            tk.Label(self.frame, text=f"ようこそ、{self.app.current_user.name} さん", bg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=10)
            tk.Button(self.frame, text="アップロード", command=self.app.open_upload, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
            tk.Button(self.frame, text="フレンド検索", command=self.app.open_friend_search, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
            tk.Button(self.frame, text="フレンドリスト", command=self.app.open_friends, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
            if self.app.current_user.id == 2:
                tk.Button(self.frame, text="ユーザ一覧", command=self.app.open_users, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
            tk.Button(self.frame, text="アカウント設定", command=self.app.open_reveal, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.frame, text="ログアウト", command=self.app.logout, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)

class Main:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg="#fff7f0")

        # 検索バー
        search_frame = tk.Frame(self.frame, bg="#fff7f0")
        search_frame.pack(pady=10)
        tk.Label(search_frame, text="名前で検索:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, font=("Arial", 12), width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="検索", command=self.app.search_dates, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

        # フィルタ
        filter_frame = tk.Frame(self.frame, bg="#fff7f0")
        filter_frame.pack(pady=5)
        self.ev_var = tk.BooleanVar()
        self.ki_var = tk.BooleanVar()
        tk.Checkbutton(filter_frame, text="みんなが投稿した図鑑", variable=self.ev_var, command=self.app.filter_dates, bg="#fff7f0", fg="#333", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(filter_frame, text="基本図鑑", variable=self.ki_var, command=self.app.filter_dates, bg="#fff7f0", fg="#333", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

        # フレンドセレクト
        tk.Label(filter_frame, text="フレンド:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.friend_combo = ttk.Combobox(filter_frame, values=["フレンド選択"], state="readonly", width=15, font=("Arial", 10))
        self.friend_combo.pack(side=tk.LEFT)
        self.friend_combo.bind("<<ComboboxSelected>>", self.app.filter_friends)

        # 日付リスト
        self.date_tree = ttk.Treeview(self.frame, columns=("name", "place", "subject", "likes"), show="headings", height=15)
        self.date_tree.heading("name", text="名前")
        self.date_tree.heading("place", text="場所")
        self.date_tree.heading("subject", text="種類")
        self.date_tree.heading("likes", text="いいね")
        self.date_tree.column("name", width=150)
        self.date_tree.column("place", width=150)
        self.date_tree.column("subject", width=150)
        self.date_tree.column("likes", width=100)
        self.date_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        self.date_tree.bind("<Double-1>", self.app.show_date_detail)

    def load_friends(self):
        if self.app.current_user:
            friends = db_session.query(User).join(Friend, 
                ((Friend.user_id == self.app.current_user.id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
                ((Friend.friend_id == self.app.current_user.id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
            ).all()
            friend_names = ["フレンド選択"] + [f"{friend.name} ({friend.id})" for friend in friends]
            self.friend_combo['values'] = friend_names

    def load_dates(self):
        self.date_tree.delete(*self.date_tree.get_children())
        dates = db_session.query(Date).all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

class Footer:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg="#fff7f0")
        tk.Button(self.frame, text="いいね", command=self.app.like_date, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=5)
    def like_date(self):
        selected = self.app.main.date_tree.selection()
        if selected:
            item = self.app.main.date_tree.item(selected)
            date_name = item['values'][0]
            date_obj = db_session.query(Date).filter_by(name=date_name).first()
            if date_obj:
                existing_like = db_session.query(Like).filter_by(user_id=self.app.current_user.id, date_id=date_obj.id).first()
                if not existing_like:
                    new_like = Like(user_id=self.app.current_user.id, date_id=date_obj.id)
                    db_session.add(new_like)
                    date_obj.goodpoint += 1
                    db_session.commit()
                    messagebox.showinfo("成功", "いいねしました！")
                    self.app.main.load_dates()
                else:
                    messagebox.showinfo("情報", "すでにいいねしています")
class PictorialBookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pictorial Book")
        self.root.geometry("1000x700")
        self.current_user = None

        # スタイル設定
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 12, "bold"), background="#ff6b6b", foreground="white")
        style.configure("TLabel", font=("Arial", 12), background="#fff7f0")
        style.configure("TEntry", font=("Arial", 12))
        style.configure("Treeview", font=("Arial", 10), background="#f0f9ff")
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
        self.root.configure(bg="#fff7f0")

        self.login_frame = tk.Frame(root, bg="#fff7f0")
        self.user_frame = tk.Frame(root, bg="#fff7f0")

        self.setup_login()
        self.setup_user()

        self.show_login()

    def setup_login(self):
        tk.Label(self.login_frame, text="ユーザー名:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 14)).pack(pady=10)
        self.username_entry = tk.Entry(self.login_frame, font=("Arial", 12), width=30)
        self.username_entry.pack(pady=5)

        tk.Label(self.login_frame, text="パスワード:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 14)).pack(pady=10)
        self.password_entry = tk.Entry(self.login_frame, show="*", font=("Arial", 12), width=30)
        self.password_entry.pack(pady=5)

        tk.Button(self.login_frame, text="ログイン", command=self.login, bg="#ff6b6b", fg="white", font=("Arial", 12, "bold")).pack(pady=20)
        tk.Button(self.login_frame, text="サインアップ", command=self.signup, bg="#ff6b6b", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

    def setup_user(self):
        self.header = Header(self.user_frame, self)
        self.main = Main(self.user_frame, self)
        self.footer = Footer(self.user_frame, self)

        self.header.frame.pack(fill=tk.X, pady=5)
        self.main.frame.pack(fill=tk.BOTH, expand=True)
        self.footer.frame.pack(fill=tk.X, pady=5)

    def show_login(self):
        self.user_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)

    def show_user(self):
        self.login_frame.pack_forget()
        self.user_frame.pack(fill=tk.BOTH, expand=True)
        self.header.update_header()
        self.main.load_friends()
        self.main.load_dates()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = db_session.query(User).filter_by(name=username, password=password).first()
        if user:
            self.current_user = user
            self.show_user()
        else:
            messagebox.showerror("エラー", "ユーザー名またはパスワードが間違っています")

    def signup(self):
        signup_window = tk.Toplevel(self.root)
        signup_window.title("サインアップ")
        signup_window.configure(bg="#fff7f0")
        tk.Label(signup_window, text="ユーザー名:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        name_entry = tk.Entry(signup_window, font=("Arial", 12), width=30)
        name_entry.pack(pady=5)
        tk.Label(signup_window, text="パスワード:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        pw_entry = tk.Entry(signup_window, show="*", font=("Arial", 12), width=30)
        pw_entry.pack(pady=5)
        tk.Label(signup_window, text="パスワード確認:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        pw2_entry = tk.Entry(signup_window, show="*", font=("Arial", 12), width=30)
        pw2_entry.pack(pady=5)
        def register():
            name = name_entry.get()
            pw = pw_entry.get()
            pw2 = pw2_entry.get()
            if not name or not pw:
                messagebox.showerror("エラー", "全てのフィールドを入力してください")
                return
            if pw != pw2:
                messagebox.showerror("エラー", "パスワードが一致しません")
                return
            existing = db_session.query(User).filter_by(name=name).first()
            if existing:
                messagebox.showerror("エラー", "そのユーザー名は既に使われています")
                return
            new_user = User(name=name, password=pw)
            db_session.add(new_user)
            db_session.commit()
            messagebox.showinfo("成功", f"アカウントを作成しました。あなたのIDは{new_user.id}です")
            signup_window.destroy()
        tk.Button(signup_window, text="登録", command=register, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)

    def open_upload(self):
        upload_window = tk.Toplevel(self.root)
        upload_window.title("アップロード")
        upload_window.configure(bg="#fff7f0")
        tk.Label(upload_window, text="名前:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        name_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
        name_entry.pack(pady=5)
        tk.Label(upload_window, text="場所:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        place_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
        place_entry.pack(pady=5)
        tk.Label(upload_window, text="緯度:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        lat_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
        lat_entry.pack(pady=5)
        tk.Label(upload_window, text="経度:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        lng_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
        lng_entry.pack(pady=5)
        subject_entry = None
        explanatory_entry = None
        if self.current_user.id == 2:
            tk.Label(upload_window, text="種類:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
            subject_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
            subject_entry.pack(pady=5)
            tk.Label(upload_window, text="説明:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
            explanatory_entry = tk.Entry(upload_window, font=("Arial", 12), width=30)
            explanatory_entry.pack(pady=5)
        tk.Label(upload_window, text="ファイル:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        file_label = tk.Label(upload_window, text="ファイル未選択", bg="#fff7f0", font=("Arial", 10))
        file_label.pack(pady=5)
        def select_file():
            file_path = filedialog.askopenfilename()
            if file_path:
                file_label.config(text=file_path)
        tk.Button(upload_window, text="ファイル選択", command=select_file, bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(pady=5)
        def upload():
            name = name_entry.get()
            place = place_entry.get()
            lat = lat_entry.get()
            lng = lng_entry.get()
            subject = subject_entry.get() if subject_entry else None
            explanatorytext = explanatory_entry.get() if explanatory_entry else None
            file_path = file_label.cget("text")
            if name and place and file_path != "ファイル未選択":
                filename = os.path.basename(file_path)
                ido = float(lat) if lat else 0.0
                keido = float(lng) if lng else 0.0
                save_date = Date(
                    user_id=self.current_user.id,
                    name=name,
                    place=place,
                    subject=subject,
                    explanatorytext=explanatorytext,
                    imagepass=filename,
                    goodpoint=0,
                    ido=ido,
                    keido=keido
                )
                db_session.add(save_date)
                db_session.commit()
                upload_dir = os.path.join('static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                shutil.copy(file_path, os.path.join(upload_dir, filename))
                messagebox.showinfo("成功", "アップロードしました")
                upload_window.destroy()
                self.load_dates()
            else:
                messagebox.showerror("エラー", "全てのフィールドを入力してください")
        tk.Button(upload_window, text="アップロード", command=upload, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)

    def open_friend_search(self):
        search_window = tk.Toplevel(self.root)
        search_window.title("フレンド検索")
        search_window.configure(bg="#fff7f0")
        tk.Label(search_window, text="ユーザー名で検索:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        nickname_entry = tk.Entry(search_window, font=("Arial", 12), width=30)
        nickname_entry.pack(pady=5)
        result_frame = tk.Frame(search_window, bg="#fff7f0")
        result_frame.pack(pady=10)
        def search():
            nickname = nickname_entry.get()
            if nickname:
                users = db_session.query(User).filter(User.name.like(f'%{nickname}%')).all()
                friendships = db_session.query(Friend).filter(
                    (Friend.user_id == self.current_user.id) | (Friend.friend_id == self.current_user.id)
                ).all()
                user_relations = {}
                for user in users:
                    relation = {'status': 'none', 'is_requester': False}
                    for f in friendships:
                        if (f.user_id == user.id and f.friend_id == self.current_user.id) or (f.friend_id == user.id and f.user_id == self.current_user.id):
                            relation['status'] = f.status
                            if f.user_id == self.current_user.id:
                                relation['is_requester'] = True
                            break
                    user_relations[user.id] = relation
                for widget in result_frame.winfo_children():
                    widget.destroy()
                for user in users:
                    if user.id == self.current_user.id:
                        continue
                    frame = tk.Frame(result_frame, bg="#fff7f0")
                    frame.pack(pady=5)
                    tk.Label(frame, text=user.name, bg="#fff7f0", fg="#333", font=("Arial", 12)).pack(side=tk.LEFT)
                    relation = user_relations[user.id]
                    if relation['status'] == 'accepted':
                        tk.Label(frame, text="フレンド", bg="#fff7f0", fg="green", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
                    elif relation['status'] == 'pending':
                        if relation['is_requester']:
                            tk.Label(frame, text="申請中", bg="#fff7f0", fg="orange", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
                            tk.Button(frame, text="申請解除", command=lambda u=user: self.cancel_friend_request(u.id), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
                        else:
                            tk.Label(frame, text="承認待ち", bg="#fff7f0", fg="blue", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
                    else:
                        tk.Button(frame, text="フレンド申請", command=lambda u=user: self.request_friend(u.id), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Button(search_window, text="検索", command=search, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)

    def request_friend(self, friend_id):
        existing = db_session.query(Friend).filter(
            ((Friend.user_id == self.current_user.id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == self.current_user.id))
        ).first()
        if not existing:
            new_friend = Friend(user_id=self.current_user.id, friend_id=friend_id, status='pending')
            db_session.add(new_friend)
            db_session.commit()
            messagebox.showinfo("成功", "フレンド申請しました")
        else:
            messagebox.showinfo("情報", "すでに申請済みまたはフレンドです")

    def cancel_friend_request(self, friend_id):
        request_record = db_session.query(Friend).filter(
            Friend.user_id == self.current_user.id,
            Friend.friend_id == friend_id,
            Friend.status == 'pending'
        ).first()
        if request_record:
            db_session.delete(request_record)
            db_session.commit()
            messagebox.showinfo("成功", "申請を解除しました")
        else:
            messagebox.showerror("エラー", "解除できません")

    def open_friends(self):
        friends_window = tk.Toplevel(self.root)
        friends_window.title("フレンドリスト")
        friends_window.configure(bg="#fff7f0")
        tk.Label(friends_window, text="フレンド:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 14)).pack(pady=5)
        friends_frame = tk.Frame(friends_window, bg="#fff7f0")
        friends_frame.pack(pady=5)
        friends = db_session.query(User).join(Friend, 
            ((Friend.user_id == self.current_user.id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
            ((Friend.friend_id == self.current_user.id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
        ).all()
        for f in friends:
            frame = tk.Frame(friends_frame, bg="#fff7f0")
            frame.pack(pady=2)
            tk.Label(frame, text=f.name, bg="#fff7f0", fg="#333", font=("Arial", 12)).pack(side=tk.LEFT)
            tk.Button(frame, text="データを見る", command=lambda fid=f.id: self.open_friend_data(fid), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
            tk.Button(frame, text="削除", command=lambda fid=f.id: self.remove_friend(fid), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Label(friends_window, text="承認待ち:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 14)).pack(pady=5)
        pending_listbox = tk.Listbox(friends_window, bg="#f0f9ff", height=5, font=("Arial", 10))
        pending_listbox.pack(pady=5)
        pending_requests = db_session.query(User).join(Friend,
            (Friend.user_id == User.id) & (Friend.friend_id == self.current_user.id) & (Friend.status == 'pending')
        ).all()
        for p in pending_requests:
            pending_listbox.insert(tk.END, p.name)
        def accept_friend():
            selected = pending_listbox.curselection()
            if selected:
                name = pending_listbox.get(selected)
                user = db_session.query(User).filter_by(name=name).first()
                if user:
                    friend_req = db_session.query(Friend).filter(
                        (Friend.user_id == user.id) & (Friend.friend_id == self.current_user.id) & (Friend.status == 'pending')
                    ).first()
                    if friend_req:
                        friend_req.status = 'accepted'
                        db_session.commit()
                        messagebox.showinfo("成功", "フレンドを承認しました")
                        friends_window.destroy()
                        self.open_friends()
        tk.Button(friends_window, text="承認", command=accept_friend, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)

    def remove_friend(self, friend_id):
        if messagebox.askyesno("確認", "フレンドを削除しますか？"):
            existing = db_session.query(Friend).filter(
                ((Friend.user_id == self.current_user.id) & (Friend.friend_id == friend_id)) |
                ((Friend.user_id == friend_id) & (Friend.friend_id == self.current_user.id))
            ).first()
            if existing:
                db_session.delete(existing)
                db_session.commit()
                messagebox.showinfo("成功", "削除しました")
            else:
                messagebox.showerror("エラー", "削除できません")

    def open_friend_data(self, friend_id):
        is_friend = db_session.query(Friend).filter(
            ((Friend.user_id == self.current_user.id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == self.current_user.id))
        ).first()
        if not is_friend:
            messagebox.showerror("エラー", "フレンドではありません")
            return
        friend = db_session.query(User).get(friend_id)
        dates = db_session.query(Date).filter_by(user_id=friend_id).all()
        friend_data_window = tk.Toplevel(self.root)
        friend_data_window.title(f"{friend.name}のコレクション")
        friend_data_window.configure(bg="#fff7f0")
        tk.Label(friend_data_window, text=f"{friend.name}のコレクション", font=("Arial", 16, "bold"), fg="#ff6b6b", bg="#fff7f0").pack(pady=10)
        date_tree = ttk.Treeview(friend_data_window, columns=("name", "place", "subject", "likes"), show="headings", height=10)
        date_tree.heading("name", text="名前")
        date_tree.heading("place", text="場所")
        date_tree.heading("subject", text="種類")
        date_tree.heading("likes", text="いいね")
        date_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))
        if not dates:
            tk.Label(friend_data_window, text=f"{friend.name}さんはまだデータをアップしていません。", bg="#fff7f0", fg="#333", font=("Arial", 12)).pack(pady=20)
        tk.Button(friend_data_window, text="閉じる", command=friend_data_window.destroy, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)

    def logout(self):
        self.current_user = None
        self.header.update_header()
        self.show_login()

    def open_reveal(self):
        reveal_window = tk.Toplevel(self.root)
        reveal_window.title("アカウント設定")
        reveal_window.configure(bg="#fff7f0")
        tk.Label(reveal_window, text="現在のパスワード:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        pw_entry = tk.Entry(reveal_window, show="*", font=("Arial", 12), width=30)
        pw_entry.pack(pady=5)
        info_frame = tk.Frame(reveal_window, bg="#fff7f0")
        def confirm():
            pw = pw_entry.get()
            if pw == self.current_user.password:
                for widget in info_frame.winfo_children():
                    widget.destroy()
                tk.Label(info_frame, text=f"ID: {self.current_user.id}", bg="#fff7f0", fg="#333", font=("Arial", 12)).pack(pady=2)
                tk.Label(info_frame, text="新しい名前:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=2)
                name_entry = tk.Entry(info_frame, font=("Arial", 12), width=30)
                name_entry.insert(0, self.current_user.name)
                name_entry.pack(pady=2)
                tk.Label(info_frame, text="新しいパスワード:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=2)
                new_pw_entry = tk.Entry(info_frame, show="*", font=("Arial", 12), width=30)
                new_pw_entry.pack(pady=2)
                tk.Label(info_frame, text="パスワード確認:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=2)
                confirm_pw_entry = tk.Entry(info_frame, show="*", font=("Arial", 12), width=30)
                confirm_pw_entry.pack(pady=2)
                def update():
                    new_name = name_entry.get()
                    new_pw = new_pw_entry.get()
                    confirm_pw = confirm_pw_entry.get()
                    if new_pw and new_pw != confirm_pw:
                        messagebox.showerror("エラー", "パスワードが一致しません")
                        return
                    if new_name:
                        self.current_user.name = new_name
                    if new_pw:
                        self.current_user.password = new_pw
                    db_session.commit()
                    messagebox.showinfo("成功", "更新しました")
                    reveal_window.destroy()
                tk.Button(info_frame, text="更新", command=update, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)
            else:
                messagebox.showerror("エラー", "パスワードが違います")
        tk.Button(reveal_window, text="確認", command=confirm, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)
        info_frame.pack(pady=10)

    def open_users(self):
        if self.current_user.id != 2:
            messagebox.showerror("エラー", "管理者専用です")
            return
        users_window = tk.Toplevel(self.root)
        users_window.title("ユーザ一覧")
        users_window.configure(bg="#fff7f0")
        tk.Label(users_window, text="管理者パスワード:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
        pw_entry = tk.Entry(users_window, show="*", font=("Arial", 12), width=30)
        pw_entry.pack(pady=5)
        list_frame = tk.Frame(users_window, bg="#fff7f0")
        def confirm():
            pw = pw_entry.get()
            admin = db_session.query(User).filter_by(id=2).first()
            if pw == admin.password:
                for widget in list_frame.winfo_children():
                    widget.destroy()
                users = db_session.query(User).all()
                for u in users:
                    tk.Label(list_frame, text=f"ID: {u.id}, Name: {u.name}", bg="#fff7f0", fg="#333", font=("Arial", 12)).pack(pady=2)
                tk.Label(list_frame, text="バージョン情報編集:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
                verj_entry = tk.Entry(list_frame, font=("Arial", 12), width=30)
                verj_entry.insert(0, app_verj)
                verj_entry.pack(pady=5)
                def update_verj():
                    global app_verj
                    app_verj = verj_entry.get()
                    messagebox.showinfo("成功", "バージョン情報を更新しました")
                tk.Button(list_frame, text="更新", command=update_verj, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)
            else:
                messagebox.showerror("エラー", "パスワードが違います")
        tk.Button(users_window, text="確認", command=confirm, bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=10)
        list_frame.pack(pady=10)

    def load_friends(self):
        if self.current_user:
            friends = db_session.query(User).join(Friend, 
                ((Friend.user_id == self.current_user.id) & (Friend.friend_id == User.id) & (Friend.status == 'accepted')) |
                ((Friend.friend_id == self.current_user.id) & (Friend.user_id == User.id) & (Friend.status == 'accepted'))
            ).all()
            friend_names = ["フレンド選択"] + [f"{friend.name} ({friend.id})" for friend in friends]
            self.friend_combo['values'] = friend_names

    def filter_friends(self, event):
        selected = self.friend_combo.get()
        if selected != "フレンド選択":
            friend_id = int(selected.split('(')[-1].strip(')'))
            self.date_tree.delete(*self.date_tree.get_children())
            dates = db_session.query(Date).filter_by(user_id=friend_id).all()
            for d in dates:
                likes = db_session.query(Like).filter_by(date_id=d.id).count()
                self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def search_dates(self):
        search = self.search_entry.get()
        self.date_tree.delete(*self.date_tree.get_children())
        query = db_session.query(Date)
        if search:
            query = query.filter(or_(Date.place.like(f"%{search}%"), Date.subject.like(f"%{search}%"), Date.name.like(f"%{search}%")))
        dates = query.all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def filter_dates(self):
        self.date_tree.delete(*self.date_tree.get_children())
        query = db_session.query(Date)
        if self.ev_var.get():
            query = query.filter(Date.user_id != 2)
        if self.ki_var.get():
            query = query.filter(Date.user_id == 2)
        dates = query.all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def search_dates(self):
        search = self.search_entry.get()
        self.date_tree.delete(*self.date_tree.get_children())
        query = db_session.query(Date)
        if search:
            query = query.filter(or_(Date.place.like(f"%{search}%"), Date.subject.like(f"%{search}%"), Date.name.like(f"%{search}%")))
        dates = query.all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def filter_dates(self):
        self.date_tree.delete(*self.date_tree.get_children())
        query = db_session.query(Date)
        if self.ev_var.get():
            query = query.filter(Date.user_id != 2)
        if self.ki_var.get():
            query = query.filter(Date.user_id == 2)
        dates = query.all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def load_dates(self):
        self.date_tree.delete(*self.date_tree.get_children())
        dates = db_session.query(Date).all()
        for d in dates:
            likes = db_session.query(Like).filter_by(date_id=d.id).count()
            self.date_tree.insert("", tk.END, values=(d.name, d.place, d.subject, likes))

    def like_date(self):
        selected = self.date_tree.selection()
        selected = self.main.date_tree.selection()
        if selected:
            item = self.date_tree.item(selected)
            item = self.main.date_tree.item(selected)
            date_name = item['values'][0]
            date_obj = db_session.query(Date).filter_by(name=date_name).first()
            if date_obj:
                existing_like = db_session.query(Like).filter_by(user_id=self.current_user.id, date_id=date_obj.id).first()
                if not existing_like:
                    new_like = Like(user_id=self.current_user.id, date_id=date_obj.id)
                    db_session.add(new_like)
                    date_obj.goodpoint += 1
                    db_session.commit()
                    messagebox.showinfo("成功", "いいねしました！")
                    self.load_dates()
                    self.main.load_dates()
                else:
                    messagebox.showinfo("情報", "すでにいいねしています")

    def show_date_detail(self, event):
        selected = self.main.date_tree.selection()
        if selected:
            item = self.main.date_tree.item(selected)
            date_name = item['values'][0]
            date_obj = db_session.query(Date).filter_by(name=date_name).first()
            if date_obj:
                detail_window = tk.Toplevel(self.root)
                detail_window.title(f"詳細: {date_name}")
                detail_window.configure(bg="#fff7f0")
                tk.Label(detail_window, text=f"場所: {date_obj.place}", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
                tk.Label(detail_window, text=f"種類: {date_obj.subject or 'なし'}", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
                tk.Label(detail_window, text=f"説明: {date_obj.explanatorytext or 'なし'}", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack(pady=5)
                if date_obj.user_id == self.current_user.id or self.current_user.id == 2:
                    tk.Button(detail_window, text="削除", command=lambda: self.delete_date(date_obj.id, detail_window), bg="#ff6b6b", fg="white", font=("Arial", 12)).pack(pady=5)
                chat_frame = tk.Frame(detail_window, bg="#fff7f0")
                chat_frame.pack(pady=10)
                tk.Label(chat_frame, text="チャット:", bg="#fff7f0", fg="#ff6b6b", font=("Arial", 12)).pack()
                self.chat_text = scrolledtext.ScrolledText(chat_frame, width=50, height=10, bg="#f0f9ff", font=("Arial", 10))
                self.chat_text.pack()
                self.load_chats(date_obj.id)
                input_frame = tk.Frame(detail_window, bg="#fff7f0")
                input_frame.pack(pady=5)
                self.chat_entry = tk.Entry(input_frame, width=40, font=("Arial", 12))
                self.chat_entry.pack(side=tk.LEFT)
                tk.Button(input_frame, text="送信", command=lambda: self.send_chat(date_obj.id), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)
                tk.Button(input_frame, text="チャット削除", command=lambda: self.delete_chat_menu(date_obj.id), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

    def load_chats(self, date_id):
        chats = db_session.query(Chat).filter_by(date_id=date_id).order_by(Chat.created_at).all()
        self.chat_text.delete(1.0, tk.END)
        for chat in chats:
            user = db_session.query(User).filter_by(id=chat.user_id).first()
            self.chat_text.insert(tk.END, f"{user.name}: {chat.message}\n")

    def send_chat(self, date_id):
        message = self.chat_entry.get()
        if message and self.current_user:
            new_chat = Chat(user_id=self.current_user.id, date_id=date_id, message=message, created_at=datetime.now(tz=ZoneInfo("Asia/Tokyo")).replace(microsecond=0))
            db_session.add(new_chat)
            db_session.commit()
            self.chat_entry.delete(0, tk.END)
            self.load_chats(date_id)

    def delete_chat_menu(self, date_id):
        chats = db_session.query(Chat).filter_by(date_id=date_id, user_id=self.current_user.id).all()
        if not chats:
            messagebox.showinfo("情報", "削除できるチャットがありません")
            return
        delete_window = tk.Toplevel(self.root)
        delete_window.title("チャット削除")
        delete_window.configure(bg="#fff7f0")
        for chat in chats:
            frame = tk.Frame(delete_window, bg="#fff7f0")
            frame.pack(pady=5)
            tk.Label(frame, text=chat.message, bg="#fff7f0", fg="#333", font=("Arial", 10)).pack(side=tk.LEFT)
            tk.Button(frame, text="削除", command=lambda c=chat: self.delete_chat(c.id, date_id, delete_window), bg="#ff6b6b", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

    def delete_chat(self, chat_id, date_id, window=None):
        chat = db_session.query(Chat).filter_by(id=chat_id, user_id=self.current_user.id).first()
        if chat:
            db_session.delete(chat)
            db_session.commit()
            messagebox.showinfo("成功", "削除しました")
            if window:
                window.destroy()
            self.load_chats(date_id)
        else:
            messagebox.showerror("エラー", "削除できません")

    def delete_date(self, date_id, window):
        if messagebox.askyesno("確認", "このデータを削除しますか？"):
            date_obj = db_session.query(Date).filter_by(id=date_id).first()
            if date_obj and (date_obj.user_id == self.current_user.id or self.current_user.id == 2):
                db_session.delete(date_obj)
                db_session.commit()
                messagebox.showinfo("成功", "削除しました")
                window.destroy()
                self.load_dates()
            else:
                messagebox.showerror("エラー", "削除できません")

if __name__ == "__main__":
    root = tk.Tk()
    app = PictorialBookApp(root)
    root.mainloop()