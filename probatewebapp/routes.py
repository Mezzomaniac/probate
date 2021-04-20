from flask import abort, redirect, render_template, url_for#, flash, g, request, session

from . import app, db
from .forms import SearchForm
from .search import search


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    if form.validate_on_submit():
        results = search(db, **form.data)
        return render_template('results.html', title='Search results')
    return render_template('home.html', title='Home', form=form)

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    return redirect(url_for('home'))
    
