from flask import abort, redirect, render_template, url_for#, flash, g, request, session

from . import app
from .forms import SearchForm
from . import processing, session_interface, utils
from intestacywebapp import _tests

@app.route('/', methods=['GET', 'POST'])
def main():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect(url_for('results'))
    return render_template('main.html', title='Probate Search WA', form=form)

@app.route('/results')
def results():
    return render_template('results.html', title='Results - Probate Search WA')

@app.route('/test', methods=['GET', 'POST'])
def test():
    if not app.config['TESTING']:
        abort(403)
    return redirect(url_for('main'))
    
    return render_template('test.html', title='Test')