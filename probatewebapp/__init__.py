import sqlite3
import threading
from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
from .config import Config

app = Flask(__name__)
app.config.from_object(Config)
#db = SQLAlchemy(app)
#app.config['SESSION_SQLALCHEMY'] = db
#db.create_all()

from . import database

db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'], check_same_thread=False)
db.row_factory = sqlite3.Row
scraper = threading.Thread(
    target=database.setup_database, 
    kwargs={
        'db': db, 
        'username': app.config['ELODGMENT_USERNAME'], 
        'password': app.config['ELODGMENT_PASSWORD']})
scraper.start()

from . import routes
