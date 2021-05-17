import datetime
from getpass import getpass
import os

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
    VERSION = '0.3.0'
    EMAIL_ADDRESS = 'jeremylondon@outlook.com.au'
    EMAIL_PASSWORD = get_password('EMAIL', EMAIL_ADDRESS)
    TIMEZONE = datetime.timezone(datetime.timedelta(hours=8))
    
    TESTING = False
    SEND_FILE_MAX_AGE_DEFAULT = 0  # For development only
    
    SESSION_PERMANENT = False
    #PERMANENT_SESSION_LIFETIME = 60

    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_DATABASE_URI = os.path.join(BASEDIR, 'probate.db')
    SCHEMA_URI = os.path.join(BASEDIR, 'schema.sql')
    
    ELODGMENT_USERNAME = get_username('ELODGMENT')
    ELODGMENT_PASSWORD = get_password('ELODGMENT', ELODGMENT_USERNAME)
    
    MULTIPAGE_MATTERS_FILE_URI = os.path.join(BASEDIR, 'multipage_matters.txt')
