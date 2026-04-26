import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash

POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL')
if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(POSTGRES_URL)
with engine.connect() as conn:
    user_id = input("テストするユーザーID: ")
    password = input("そのユーザーが入力するパスワード: ")
    
    result = conn.execute(text('SELECT id, name, password FROM "user" WHERE id = :uid'), {'uid': user_id})
    user = result.fetchone()
    
    if not user:
        print("ユーザーが見つかりません")
        sys.exit(0)
    
    print(f"\n--- ユーザー情報 ---")
    print(f"ID: {user[0]}")
    print(f"名前: {user[1]}")
    print(f"DBのパスワード: {user[2][:50]}...")
    
    if user[2].startswith('scrypt:') or user[2].startswith('pbkdf2:'):
        match = check_password_hash(user[2], password)
        print(f"\nハッシュ化チェック結果: {'✅ 一致' if match else '❌ 不一致'}")
    else:
        match = user[2] == password
        print(f"\n平文チェック結果: {'✅ 一致' if match else '❌ 不一致'}")