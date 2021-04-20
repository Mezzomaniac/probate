from getpass import getpass
import os

basedir = os.path.abspath(os.path.dirname(__file__))

def get_username():
    username = os.getenv('ELODGMENT_USERNAME')
    if username is None:
        username = input(f'eCourts Portal username?')
    return username

def get_password(username):
    password = os.getenv('ELODGMENT_PASSWORD')
    if password is None:
        password = getpass(f'eCourts Portal password for {username}?')
    return password

class Config:
    SECRET_KEY = os.urandom(16)
    VERSION = '0.1.0'
    
    TESTING = True
    SEND_FILE_MAX_AGE_DEFAULT = 0  # For development only
    
    SESSION_PERMANENT = False
    #PERMANENT_SESSION_LIFETIME = 60
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join(basedir, 'probate.db')
    SQLITE_DATABASE_URI = os.path.join(basedir, 'probate.db')
    #SQLALCHEMY_TRACK_MODIFICATIONS = False
    #SQLALCHEMY_ECHO = True
    #SESSION_TYPE = 'sqlalchemy'
    #SESSION_TYPE = 'filesystem'
    
    ELODGMENT_USERNAME = get_username()
    ELODGMENT_PASSWORD = get_password(ELODGMENT_USERNAME)
