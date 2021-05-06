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
    VERSION = '0.1.0'
    EMAIL_ADDRESS = 'jeremylondon@outlook.com.au'
    TIMEZONE = datetime.timezone(datetime.timedelta(hours=8))
    
    TESTING = False
    SEND_FILE_MAX_AGE_DEFAULT = 0  # For development only
    
    SESSION_PERMANENT = False
    #PERMANENT_SESSION_LIFETIME = 60
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join(basedir, 'probate.db')
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_DATABASE_URI = os.path.join(BASEDIR, 'probate.db')
    #SQLALCHEMY_TRACK_MODIFICATIONS = False
    #SQLALCHEMY_ECHO = True
    #SESSION_TYPE = 'sqlalchemy'
    #SESSION_TYPE = 'filesystem'
    
    ELODGMENT_USERNAME = get_username()
    ELODGMENT_PASSWORD = get_password(ELODGMENT_USERNAME)
    LAST_DATABASE_UPDATE = None
    
    SPILLOVER_MATTERS_FILE_URI = os.path.join(BASEDIR, 'spillover_matters.txt')
    SPILLOVER_PARTIES_FILE_URI = os.path.join(BASEDIR, 'spillover_parties.yaml')
