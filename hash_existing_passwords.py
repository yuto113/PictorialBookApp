import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL')
if not POSTGRES_URL:
    print("DATABASE_PUBLIC_URL環境変数を設定してください")
    sys.exit(1)

if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(POSTGRES_URL)
with engine.connect() as conn:
    # 平文パスワードのユーザーを取得
    result = conn.execute(text('''
        SELECT id, name, password FROM "user"
        WHERE password NOT LIKE 'scrypt:%'
        AND password NOT LIKE 'pbkdf2:%'
    '''))
    users = result.fetchall()
    
    print(f"ハッシュ化対象: {len(users)}人")
    for user in users:
        print(f"  - ID:{user[0]} 名前:{user[1]}")
    
    if len(users) == 0:
        print("全員ハッシュ化済みです！")
        sys.exit(0)
    
    confirm = input("\nハッシュ化しますか？ (yes/no): ")
    if confirm != 'yes':
        print("キャンセルしました")
        sys.exit(0)
    
    count = 0
    for user in users:
        hashed = generate_password_hash(user[2])
        conn.execute(
            text('UPDATE "user" SET password = :pw WHERE id = :uid'),
            {'pw': hashed, 'uid': user[0]}
        )
        count += 1
    
    conn.commit()
    print(f"\n✅ {count}人のパスワードをハッシュ化しました！")