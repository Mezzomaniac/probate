# probate.py - search WASC Probate Division by deceased's name

from probatewebapp import app

if __name__ == '__main__':
    #app.run()
    app.run(debug=True, use_reloader=False)
