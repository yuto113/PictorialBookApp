from sqlalchemy import create_engine, text
import os

url = os.environ.get('DATABASE_URL')
engine = create_engine(url)

sql = '''CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)'''

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()
    print('通知テーブル作成完了')
