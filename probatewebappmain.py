# probate.py - search WASC Probate Division by deceased's name

from waitress import serve
from probatewebapp import app

if __name__ == '__main__':
    #app.run(debug=True, use_reloader=False)
    serve(app, host='0.0.0.0')