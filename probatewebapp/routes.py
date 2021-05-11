from flask import abort, redirect, render_template, url_for

from . import app
try:
    from . import db
except ImportError:
    from ._tests import db
from .forms import SearchForm
from .search import search


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    try:
        last_update = db.execute("SELECT time FROM events WHERE event = 'last_update'").fetchone()[0]
    except TypeError:
        last_update = None
    results = None
    if form.validate_on_submit():
        results = search(db, **form.data)
    #print(last_update)
    return render_template('home.html', title='Home', form=form, last_update=last_update, results=results)

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    try:
        last_update = db.execute("SELECT time FROM events WHERE event = 'last_update'").fetchone()[0]
    except TypeError:
        last_update = None
    #return render_template('test.html', title='Test', last_update=last_update)
    return redirect(url_for('home'))
    
