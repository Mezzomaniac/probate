import sqlite3
import threading
from flask import Flask
from flask_mail import Mail
from .config import Config
from .processing import notify

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

from . import database, _tests

#db = sqlite3.connect(':memory:', check_same_thread=False)
#db = _tests.sample_database()
db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'], check_same_thread=False)
db.row_factory = sqlite3.Row
db.create_function('notify', -1, notify)
scraping_schedule = threading.Thread(
    target=database.schedule, 
    kwargs={
        'db': db, 
        'schema_uri': app.config['SCHEMA_URI'], 
        'username': app.config['ELODGMENT_USERNAME'], 
        'password': app.config['ELODGMENT_PASSWORD'], 
        'timezone': app.config['TIMEZONE'], 
        'years': None, 
        'setup': False}
    )
scraping_schedule.start()

from . import routes
