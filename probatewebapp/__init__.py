import sqlite3
import threading
from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
from .config import Config
#from . import _tests

app = Flask(__name__)
app.config.from_object(Config)
#db = SQLAlchemy(app)
#app.config['SESSION_SQLALCHEMY'] = db
#db.create_all()

from . import database

db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'], check_same_thread=False)
db.row_factory = sqlite3.Row
database.insert_spillover_parties(db)
scraper = threading.Thread(
    target=database.setup_database, 
    args=(
        db, 
        app.config['ELODGMENT_USERNAME'], 
        app.config['ELODGMENT_PASSWORD'], 
        [2021] + list((range(2015, 1828, -1)))
        ))
scraper.start()
#db = _tests.sample_database()

from . import routes
