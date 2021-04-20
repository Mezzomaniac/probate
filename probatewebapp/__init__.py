import sqlite3
from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
from .config import Config
from . import scrape

app = Flask(__name__)
app.config.from_object(Config)
#db = SQLAlchemy(app)
#app.config['SESSION_SQLALCHEMY'] = db
#db.create_all()
db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'])
#db.row_factory = sqlite3.Row
scrape.setup_database(db, 
    username=app.config['ELODGMENT_USERNAME'], 
    password=app.config['ELODGMENT_PASSWORD'])

from . import routes
