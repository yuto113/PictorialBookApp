import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
        conn.execute(text("ALTER TABLE school ADD COLUMN is_active INTEGER DEFAULT 1"))
        conn.commit()
        print("✅ Added is_active column")
    except Exception as e:
        print(f"カラム追加エラー（既に存在する可能性）: {e}")