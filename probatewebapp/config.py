import os

class Config:
    SECRET_KEY = os.urandom(16)
    VERSION = '0.1.0'
    
    TESTING = True
    SEND_FILE_MAX_AGE_DEFAULT = 0  # For development only
    
    SESSION_PERMANENT = False
    #PERMANENT_SESSION_LIFETIME = 60
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///probate.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #SQLALCHEMY_ECHO = True
    #SESSION_TYPE = 'sqlalchemy'
    #SESSION_TYPE = 'filesystem'