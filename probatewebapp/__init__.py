import threading

from flask import Flask
from flask_mail import Mail

from .config import Config, TestingConfig
from .logging import setup_logger

mail = Mail()

from .database import init_db, db_last_update, close_db
from .update import update_db

def create_app(test=False, setup=False, years=None):
    app = Flask(__name__)
    config = TestingConfig if test else Config
    app.config.from_object(config)
    with app.app_context():
        mail.init_app(app)
        init_db()
        app.config['LAST_UPDATE'] = db_last_update()
        from . import routes
    #app.teardown_appcontext(close_db)
    app.teardown_request(close_db)
    
    setup_logger(app)
    if app.debug or app.testing:
        app.logger.info('App startup in development/testing mode')
    else:
        app.logger.info('App startup in production mode')

    threading.Thread(target=update_db, name='updater_thread', args=(app,), kwargs={'setup': setup, 'years': years}).start()

    return app

