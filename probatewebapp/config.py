import datetime
from getpass import getpass
import os

def get_username():
    username = os.getenv('ELODGMENT_USERNAME')
    if username is None:
        username = input('eCourts Portal username?')
    return username

def get_password(username):
    password = os.getenv('ELODGMENT_PASSWORD')
    if password is None:
        password = getpass(f'eCourts Portal password for {username}?')
    return password

class Config:
    SECRET_KEY = os.urandom(16)
    VERSION = '0.2.2'
    EMAIL_ADDRESS = 'jeremylondon@outlook.com.au'
    TIMEZONE = datetime.timezone(datetime.timedelta(hours=8))
    
    TESTING = False
    SEND_FILE_MAX_AGE_DEFAULT = 0  # For development only
    
    SESSION_PERMANENT = False
    #PERMANENT_SESSION_LIFETIME = 60

    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_DATABASE_URI = os.path.join(BASEDIR, 'probate.db')
    SCHEMA_URI = os.path.join(BASEDIR, 'schema.sql')
    
    ELODGMENT_USERNAME = get_username()
    ELODGMENT_PASSWORD = get_password(ELODGMENT_USERNAME)
    
    MULTIPAGE_MATTERS_FILE_URI = os.path.join(BASEDIR, 'multipage_matters.txt')
