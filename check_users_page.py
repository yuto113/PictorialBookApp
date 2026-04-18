import os
import sys
from sqlalchemy import create_engine, text

POSTGRES_URL = os.environ.get('DATABASE_PUBLIC_URL')
if POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(POSTGRES_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, name, role FROM "user" ORDER BY id'))
    for row in result:
        print(f"ID:{row[0]} 名前:{row[1]} 役割:{row[2]}")