import datetime
from getpass import getpass
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))

def get_username(service):
    username = os.getenv(f'{service}_USERNAME')
    if username is None:
        username = input(f'{service} username?')
    return username

def get_password(service, username):
    password = os.getenv(f'{service}_PASSWORD')
    if password is None:
        password = getpass(f'{service} password for {username}?')
    return password

class Config:
    SECRET_KEY = os.urandom(16)
    VERSION = '0.9.1'

    TIMEZONE = datetime.timezone(datetime.timedelta(hours=8), 'AWST')
    
    #PREFERRED_URL_SCHEME = 'https'
    BASE_URL = 'https://probate.mez.repl.co/'
    
    MAIL_SERVER = 'smtp-mail.outlook.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'jeremylondon@outlook.com.au'
    MAIL_PASSWORD = get_password('MAIL', MAIL_USERNAME)
    MAIL_DEFAULT_SENDER = ('Probate Search WA', MAIL_USERNAME)
    ADMINS = [MAIL_USERNAME]
    
    SESSION_PERMANENT = False

    LOG = os.path.join(BASEDIR, 'logs', 'probatewebapp.log')

    DATABASE = os.path.join(BASEDIR, 'db', 'probate.db')
    SCHEMA = os.path.join(BASEDIR, 'schema.sql')
    
    ELODGMENT_USERNAME = get_username('ELODGMENT')
    ELODGMENT_PASSWORD = get_password('ELODGMENT', ELODGMENT_USERNAME)
    LAST_UPDATE = None

class TestingConfig(Config):
    TESTING = True
    BASE_URL = 'http://localhost:5000/'
    SEND_FILE_MAX_AGE_DEFAULT = 0
    DATABASE = os.path.join(BASEDIR, 'db', 'test.db')
