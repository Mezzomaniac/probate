# probate.py - search WASC Probate Division by deceased's name

from waitress import serve
from probatewebapp import create_app


def run(test=False, setup=False, years=False):
    app = create_app(test=test, setup=setup, years=years)
    try:
        if test:
            app.run(debug=True, use_reloader=False)
        else:
            serve(app, port=5000, _quiet=True)
    except Exception:
        app.logger.exception('Unexpected error:')


if __name__ == '__main__':
    run()
