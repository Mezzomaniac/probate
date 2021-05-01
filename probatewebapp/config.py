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
    
    TESTING = True
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
    
    ELODGMENT_USERNAME = 'jlondon@robertsonhayles.com' or get_username()  # remove hardcoding after testing
    ELODGMENT_PASSWORD = 'ZhC&6WgPdxwS' or get_password(ELODGMENT_USERNAME)  # remove hardcoding after testing
    LAST_DATABASE_UPDATE = None
    
    SPILLOVER_PARTIES_FILE_URI = os.path.join(BASEDIR, 'spillover_parties.txt')
