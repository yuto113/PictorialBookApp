import os
import os as _os
_os.makedirs(_os.path.join(_os.path.abspath(_os.path.dirname(__file__)), 'instance'), exist_ok=True)

# config.py が置いてあるフォルダ（PictorialBookWebApp）の絶対パスを取得
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_dir, 'db.sqlite')

DEBUG = True

# 絶対パスを使ってデータベースの場所を指定
# これにより C:\Users\yuuto\Documents\PictorialBookWebApp\instance\db.sqlite を指すようになります
db_path = os.environ.get('DATABASE_PATH', os.path.join(basedir, 'instance', 'db.sqlite'))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path

SQLALCHEMY_TRACK_MODIFICATIONS = True