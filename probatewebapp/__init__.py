from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
from .config import Config

app = Flask(__name__)
app.config.from_object(Config)
#db = SQLAlchemy(app)
#app.config['SESSION_SQLALCHEMY'] = db
#db.create_all()

from . import routes
