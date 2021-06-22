import sqlite3

from flask import current_app, g, render_template
from flask_mail import Message
import jwt

from . import mail


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
    #db.create_function('notify', -1, Notify(current_app))
    with db, current_app.open_resource(current_app.config['SCHEMA']) as schema_file:
        db.executescript(schema_file.read().decode('utf8'))

class Notify:
    '''This class is registered in the db to be used as a callback from a TRIGGER AFTER INSERT ON parties.'''
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, *record):
        record = NotificationRecord(*record)
        print(record)
        # TODO: If it's too slow sending each email using its own connection, add the records to a new db table and send them all at once periodically
        # with mail.connect() as conn:
        # conn.send(message)
        with self.app.app_context():
            message = self.construct_message(record)
            print('Sending')
            mail.send(message)
        print('Sent')
        
    def construct_message(self, record):
        message = Message('Probate Notification', recipients = [record.email])
        token_single = self.create_token(record.id)
        token_all = self.create_token(record.email)
        text = render_template('notification.txt', record=record, token_single=token_single, token_all=token_all)
        html = render_template('notification.html', record=record, token_single=token_single, token_all=token_all)
        message.body = text
        message.html = html
        return message
    
    def create_token(self, value):
        payload = {'key': value}
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
