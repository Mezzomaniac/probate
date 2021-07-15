import sqlite3

from flask import current_app, g

from . import processing
from .models import Notification


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with db, current_app.open_resource(current_app.config['SCHEMA']) as schema_file:
        db.executescript(schema_file.read().decode('utf8'))
    close_db()

def db_last_update():
    db = get_db()
    try:
        last_update = db.execute("SELECT time FROM events WHERE event = 'last_update'").fetchone()[0]
    except TypeError:
        last_update = None
    close_db()
    return last_update

class Notify:
    '''This class is registered in the db to be used as a callback from a TRIGGER AFTER INSERT ON parties.'''
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, *record):
        record = Notification(*record)
        self.app.logger.debug(f'record={record}')
        # TODO: If it's too slow/frequent sending each email using its own connection, add the records to a new db table and send them in batches to each recipient periodically
        # with mail.connect() as conn:
        # conn.send(message)
        with self.app.app_context(), self.app.test_request_context(base_url=self.app.config['BASE_URL']):
            id_token = processing.create_token(record.id, current_app.config['SECRET_KEY'])
            email_token = processing.create_token(record.email, current_app.config['SECRET_KEY'])
            processing.send_message(record.email, 
                'Probate Notification', 
                'notification', 
                record=record, 
                id_token=id_token, 
                email_token=email_token)
        self.app.logger.debug('Sent')
