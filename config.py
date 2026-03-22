import os

# config.py が置いてあるフォルダ（PictorialBookWebApp）の絶対パスを取得
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

# 絶対パスを使ってデータベースの場所を指定
# これにより C:\Users\yuuto\Documents\PictorialBookWebApp\instance\db.sqlite を指すようになります
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'db.sqlite')

SQLALCHEMY_TRACK_MODIFICATIONS = True