import os
from sqlalchemy import create_engine, text

POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL')
if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(POSTGRES_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM "like"'))
    print(f'likeテーブルのレコード数: {result.scalar()}')
    
    result = conn.execute(text('SELECT SUM(goodpoint) FROM "date"'))
    print(f'date.goodpointの合計: {result.scalar()}')