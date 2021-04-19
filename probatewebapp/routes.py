from flask import abort, redirect, render_template, url_for#, flash, g, request, session

from . import app
from .forms import SearchForm
from .search import search


@app.route('/', methods=['GET', 'POST'])
def home():
    form = SearchForm()
    if form.validate_on_submit():
        '''deceased_first_names = form.deceased_first_names.data
        deceased_surname = form.deceased_surname.data
        party_first_names = form.party_first_names.data
        party_surname = form.party_surname.data
        start_year = form.start_year.data
        end_year = form.end_year.data'''
        results = search(form.data)
        #results = search(deceased_surname, start_year, end_year)
        return render_template('results.html', title='Search results')
    return render_template('home.html', title='Home', form=form)

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    return redirect(url_for('home'))
    
