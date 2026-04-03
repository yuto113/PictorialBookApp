import sqlite3

# データベースの場所を指定
db_path = 'instance/db.sqlite'

# データベースに接続
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("データベースの更新をスタートします...")

# 1. Userテーブルにアイコン用の項目を足す
try:
    cursor.execute("ALTER TABLE user ADD COLUMN icon_image TEXT DEFAULT 'default.png'")
    print("✅ Userテーブルに icon_image を追加しました！")
except Exception as e:
    print("⚠️ Userテーブルの更新スキップ（すでに追加されているか、エラーです）:", e)

# 2. Dateテーブルに非表示用の項目を足す
try:
    cursor.execute("ALTER TABLE date ADD COLUMN is_hidden INTEGER DEFAULT 0")
    print("✅ Dateテーブルに is_hidden を追加しました！")
except Exception as e:
    print("⚠️ Dateテーブルの更新スキップ:", e)

# 3. Chatテーブルに非表示用の項目を足す
try:
    cursor.execute("ALTER TABLE chat ADD COLUMN is_hidden INTEGER DEFAULT 0")
    print("✅ Chatテーブルに is_hidden を追加しました！")
except Exception as e:
    print("⚠️ Chatテーブルの更新スキップ:", e)

# 変更を保存して閉じる
conn.commit()
conn.close()

print("すべての作業が終わりました！")