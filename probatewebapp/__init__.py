import threading
from flask import Flask
from flask_mail import Mail

from .config import Config, TestingConfig

mail = Mail()

from .database import init_db, db_last_update#, close_db
from .update import update_db

def create_app(test=False):
    app = Flask(__name__)
    config = TestingConfig if test else Config
    app.config.from_object(config)
    with app.app_context():
        mail.init_app(app)
        init_db()
        app.config['LAST_UPDATE'] = db_last_update()
        from . import routes
    threading.Thread(target=update_db, args=(app,), kwargs={'years': None, 'setup': False}).start()
    #app.teardown_appcontext(close_db)
    return app

