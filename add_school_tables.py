import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from flask import Flask

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

with app.app_context():
    db.create_all()
    print("School tables created!")