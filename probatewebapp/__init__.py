import sqlite3
import threading
from flask import Flask
from .config import Config
#from . import _tests

app = Flask(__name__)
app.config.from_object(Config)

from . import database

db = sqlite3.connect(app.config['SQLITE_DATABASE_URI'], check_same_thread=False)
db.row_factory = sqlite3.Row
#for item in sorted(database.find_gaps(db).items(), reverse=True):
    #print(item)
scraper = threading.Thread(
    target=database.schedule, 
    args=(
        db, 
        app.config['ELODGMENT_USERNAME'], 
        app.config['ELODGMENT_PASSWORD']), 
    kwargs={
        'setup': True, 
        'years': [2021] + list(range(2005, 1828, -1))}
    )
scraper.start()
#db = _tests.sample_database()

from . import routes
