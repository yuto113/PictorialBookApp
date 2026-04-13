import cloudinary
import cloudinary.uploader
import sqlite3
import os

# Cloudinaryの設定
cloudinary.config(
    cloud_name='dcwfvccdg',
    api_key='233222263615635',
    api_secret='6YoOj3a4C1Klf72yUcCG4rpdj90'
)

DB_PATH = os.path.join('instance', 'db.sqlite')
UPLOADS_DIR = os.path.join('static', 'uploads')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT id, imagepass FROM date")
rows = cur.fetchall()

for row in rows:
    id, imagepass = row
    if not imagepass:
        continue
    if imagepass.startswith('http'):
        print(f"ID {id} はすでにCloudinary済み: {imagepass}")
        continue

    local_path = os.path.join(UPLOADS_DIR, imagepass)
    if not os.path.exists(local_path):
        print(f"ID {id} のファイルが見つかりません: {local_path}")
        continue

    print(f"ID {id} をアップロード中: {imagepass}")
    result = cloudinary.uploader.upload(local_path)
    new_url = result['secure_url']
    cur.execute("UPDATE date SET imagepass = ? WHERE id = ?", (new_url, id))
    conn.commit()
    print(f"ID {id} 完了: {new_url}")

conn.close()
print("全て完了！")