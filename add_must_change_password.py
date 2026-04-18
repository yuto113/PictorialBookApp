import os
import sys
from sqlalchemy import create_engine, text

POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL')
if not POSTGRES_URL:
    print("DATABASE_PUBLIC_URL環境変数を設定してください")
    sys.exit(1)

if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(POSTGRES_URL)
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE "user" ADD COLUMN must_change_password INTEGER DEFAULT 0'))
        conn.commit()
        print("✅ Added must_change_password column")
    except Exception as e:
        print(f"カラム追加エラー（既に存在する可能性）: {e}")