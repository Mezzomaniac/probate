# probate.py - search WASC Probate Division by deceased's name

from waitress import serve
from probatewebapp import create_app

def run(test=False):
    app = create_app(test)
    if test:
        app.run(debug=True, use_reloader=False)
    else:
        serve(app, port=5000)

if __name__ == '__main__':
    run()
