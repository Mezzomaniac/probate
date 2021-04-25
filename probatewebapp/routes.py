from flask import abort, redirect, render_template, url_for

from . import app
try:
    from . import db
except ImportError:
    from . import _tests
    db = _tests.sample_database()
from .forms import SearchForm
from .search import search


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    results = None
    if form.validate_on_submit():
        results = search(db, **form.data)
        #return render_template('results.html', title='Search results', results=results)
    return render_template('home.html', title='Home', form=form, results=results)

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    return redirect(url_for('home'))
    
