import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)

DEBUG = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_dir, 'db.sqlite')
SQLALCHEMY_TRACK_MODIFICATIONS = False
