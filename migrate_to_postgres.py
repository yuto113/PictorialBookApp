"""
SQLiteからPostgreSQLへのデータ移行スクリプト

使い方:
1. Railwayのダッシュボードで、PostgreSQLサービスの「Variables」タブを開く
2. DATABASE_PUBLIC_URL を確認（外部から接続できるURL）
3. 以下のコマンドを実行（YOUR_URLの部分を置き換える）:

    $env:DATABASE_PUBLIC_URL = "postgresql://..."
    python migrate_to_postgres.py

SQLiteのデータをすべてPostgreSQLに移行します。
"""

import os
import sys
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# SQLiteのパス
SQLITE_PATH = os.path.join('instance', 'db.sqlite')

# PostgreSQLのURL（環境変数から取得）
POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')

if not POSTGRES_URL:
    print("❌ DATABASE_PUBLIC_URL または DATABASE_URL 環境変数が設定されていません")
    print("Railwayで取得したURLを設定してください:")
    print('  $env:DATABASE_PUBLIC_URL = "postgresql://..."')
    sys.exit(1)

if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

if not os.path.exists(SQLITE_PATH):
    print(f"❌ SQLiteファイルが見つかりません: {SQLITE_PATH}")
    sys.exit(1)

print("🔄 データ移行を開始します...")
print(f"  From: {SQLITE_PATH}")
print(f"  To: {POSTGRES_URL[:40]}...")

# PostgreSQLにテーブルを作成
print("\n📋 PostgreSQL側にテーブルを作成中...")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import db
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    print("✅ テーブル作成完了")

# SQLiteに接続
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# PostgreSQLに接続
pg_engine = create_engine(POSTGRES_URL)
PgSession = sessionmaker(bind=pg_engine)
pg_session = PgSession()

# 移行するテーブル（順番が重要：外部キー制約のため）
TABLES = [
    'user',
    'school',
    'school_class',
    'school_member',
    'class_member',
    'class_teacher',
    'date',
    'like',
    'chat',
    'friends',
    'feedback',
    'school_message',
    'school_message_reply',
    'class_chat',
    'class_chat_reply',
    'assignment',
    'assignment_submission',
    'assignment_chat',
    'assignment_chat_reply',
]

total_migrated = 0

for table in TABLES:
    try:
        # SQLiteからデータを取得
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"  ⏭️  {table}: データなし (スキップ)")
            continue

        # カラム名を取得
        columns = [desc[0] for desc in sqlite_cur.description]

        # PostgreSQLに既存のデータがあるかチェック
        # ダブルクォートでテーブル名をエスケープ（userは予約語）
        result = pg_session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
        existing_count = result.scalar()

        if existing_count > 0:
            print(f"  ⚠️  {table}: すでに{existing_count}件のデータあり (スキップ)")
            continue

        # データをPostgreSQLに挿入
        count = 0
        for row in rows:
            row_dict = dict(row)
            columns_str = ', '.join([f'"{c}"' for c in columns])
            placeholders = ', '.join([f':{c}' for c in columns])
            insert_sql = f'INSERT INTO "{table}" ({columns_str}) VALUES ({placeholders})'
            pg_session.execute(text(insert_sql), row_dict)
            count += 1

        pg_session.commit()

        # シーケンスをリセット（PostgreSQLではauto-incrementのシーケンスを手動で更新する必要あり）
        try:
            pg_session.execute(text(f"""
                SELECT setval(pg_get_serial_sequence('"{table}"', 'id'),
                              COALESCE((SELECT MAX(id) FROM "{table}"), 1), true)
            """))
            pg_session.commit()
        except Exception as e:
            pass  # idカラムがないテーブルはスキップ

        print(f"  ✅ {table}: {count}件を移行")
        total_migrated += count

    except Exception as e:
        print(f"  ❌ {table}: エラー - {e}")
        pg_session.rollback()

sqlite_conn.close()
pg_session.close()

print(f"\n🎉 移行完了！合計 {total_migrated} 件のデータを移行しました。")
