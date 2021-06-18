import sqlite3
import threading
from flask import Flask
from flask_mail import Mail
from .config import Config

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

from .database import schedule

db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'])
# Adjust the timeout arg for the db connection if necessary
scraping_schedule = threading.Thread(
    target=schedule, 
    args=(
        app.config['SQLITE_DATABASE_URI'], 
        app.config['SCHEMA_URI'], 
        app.config['ELODGMENT_USERNAME'], 
        app.config['ELODGMENT_PASSWORD'], 
        app.config['TIMEZONE']
    )
    kwargs={'years': None, 'setup': False}
    )
scraping_schedule.start()

from . import routes
