from collections import namedtuple
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
        record = NotificationRecord(*record)
        print(record)
        # TODO: If it's too slow/frequent sending each email using its own connection, add the records to a new db table and send them in batches to each recipient periodically
        # with mail.connect() as conn:
        # conn.send(message)
        with self.app.app_context(), self.app.test_request_context(base_url=self.app.config['BASE_URL']):
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

NotificationField = namedtuple('NotificationField', 'description value')

class NotificationRecord:
    
    def __init__(self, 
        id, 
        email, 
        dec_first, 
        dec_sur, 
        dec_strict, 
        party_first, 
        party_sur, 
        party_strict, 
        start_year, 
        end_year, 
        type, 
        number, 
        year, 
        title, 
        party_name
        ):
        
        self.id = id
        self.email = email
        self.dec_first = NotificationField("Deceased's firstnames", dec_first or '[None]')
        self.dec_sur = NotificationField("Deceased's surname", dec_sur or '[None]')
        self.dec_strict = NotificationField("Deceased's names strict", bool(dec_strict))
        self.party_first = NotificationField("Applicant's/party's firstnames", party_first or '[None]')
        self.party_sur = NotificationField("Applicant's/party's surname", party_sur or '[None]')
        self.party_strict = NotificationField("Applicant's/party's names strict", bool(party_strict))
        self.start_year = NotificationField("Start year", start_year)
        self.end_year = NotificationField("End year", end_year)
        self.file_no = NotificationField("File number", f'{type} {number}/{year}')
        self.title = NotificationField("Title", title)
        self.party = NotificationField("Party", party_name.title())
        self.parameters = [self.dec_first, self.dec_sur, self.dec_strict, self.party_first, self.party_sur, self.party_strict, self.start_year, self.end_year]
        self.result = [self.file_no, self.title, self.party]
    
    def __repr__(self):
        attrs = "id, email, dec_first, dec_sur, dec_strict, party_first, party_sur, party_strict, start_year, end_year, file_no, title, party".split(', ')
        return f"NotificationRecord({', '.join(str(getattr(self, attr)) for attr in attrs)}"
    
    def __str__(self):
        return f'NotificationRecord({self.id}, {self.email}, {self.result})'
