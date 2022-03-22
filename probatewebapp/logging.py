import datetime
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import sys

def setup_logger(app):
    app.logger.handlers.clear()  # Prevent Pythonista caching problems
    
    class FormatterTZ(logging.Formatter):
        
        def converter(self, timestamp):
            return datetime.datetime.fromtimestamp(timestamp, app.config['TIMEZONE'])
        
        def formatTime(self, record, datefmt=None):
            dt = self.converter(record.created)
            if datefmt:
                string = dt.strftime(datefmt)
            else:
                string = dt.strftime(self.default_time_format)
                string = self.default_msec_format % (string, record.msecs)
            return string
    
    detailed_formatter = FormatterTZ(
        "[%(asctime)s.%(msecs)d] %(levelname)s: %(module)s.%(funcName)s @ %(lineno)d: %(message)s", 
        "%Y-%m-%d %H:%M:%S")
    simple_formatter = FormatterTZ(
        "[%(asctime)s] %(levelname)s: %(message)s", 
        "%H:%M:%S")
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.DEBUG)

    if not app.debug and not app.testing:
        console_handler.setLevel(logging.INFO)
        
        mailhost = (app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        credentials = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        mail_handler = SMTPHandler(mailhost, 
            app.config['MAIL_USERNAME'], 
            app.config['ADMINS'], 
            'Probate Search WA Error', 
            credentials, 
            secure=(), 
            timeout=6)
        mail_handler.setFormatter(detailed_formatter)
        mail_handler.setLevel(logging.WARNING)
        app.logger.addHandler(mail_handler)
        
        file_handler = RotatingFileHandler(app.config['LOG'], maxBytes=102400, backupCount=1, encoding='utf-8')
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(file_handler)

    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

