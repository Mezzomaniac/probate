import sqlite3
import threading
from flask import Flask
from flask_mail import Mail
from .config import Config
#from . import _tests

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

from . import database

#db = sqlite3.connect(':memory:', check_same_thread=False)
db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'], check_same_thread=False)
db.row_factory = sqlite3.Row
scraping_schedule = threading.Thread(
    target=database.schedule, 
    kwargs={
        'db': db, 
        'schema_uri': app.config['SCHEMA_URI'], 
        'username': app.config['ELODGMENT_USERNAME'], 
        'password': app.config['ELODGMENT_PASSWORD'], 
        'multipage_matters_file_uri': app.config['MULTIPAGE_MATTERS_FILE_URI'], 
        'timezone': app.config['TIMEZONE'], 
        'years': None, 
        'setup': True}
    )
scraping_schedule.start()
#db = _tests.sample_database()

from . import routes
