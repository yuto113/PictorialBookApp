# ↓↓↓ここから↓↓↓
import os
os.makedirs('instance', exist_ok=True)
# ↑↑↑ここまで↑↑↑

from flask_app import app

if __name__ == '__main__':
    app.run()